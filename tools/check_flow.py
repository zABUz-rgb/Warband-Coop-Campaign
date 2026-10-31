"""Walks the game's flow without running it, over the merged records of the module:

  D1  a line ends in a state no line starts from;
  D2  lines of a state no line leads to;
  D3  a line no one ever says: one before it in its state always holds;
  D4  a state where every line may fail: the talk stops there with nothing to say;
  D5  a talk opened (start_map_conversation: state event_triggered, change_screen_map_conversation:
      state start) with no line for that troop (John Blackborn's "dialog error" was this);
  D6  a player's line followed by a state holding only the player's lines: nobody answers;
  M1  a menu with no options and nothing that leaves it;
  M2  a menu whose every option may be hidden;
  M3  a menu nothing opens;
  M4  menus jumping to each other on load, for ever (a hang);
  P1  a presentation closed and another started in one go (the next one closes too: the tree's clicks);
  P2  a presentation nothing closes;
  P3  a container overlay left open at the end of a block;
  P4  positions set before the fixed point multiplier;
  S1  a script called with fewer arguments than it reads;
  S2  a script called with more arguments than it reads;
  S3  scripts calling themselves;
  S4  a script of ours nothing calls (a note);
  V1  a text showing a register nothing has set for it;
  G2  a slot of ours on a number the base game uses for the same family of objects;
  B1  the bridge and the game disagreeing on a number or a word of the request.

    python tools/check_flow.py            (from the repository root)
    python tools/check_flow.py --notes    also lists what was found in Diplomacy's and Native's code

Exit status 1 when something is found in our own code: what the merge added or changed compared with
the module built with no mods (--base gives that comparison). Findings in the rest are notes. A finding
checked by hand and found harmless goes into KNOWN, with the reason.
"""
import hashlib
import importlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_module import ROOT, SRC, as_op, blocks, load

ENGINE_STATES = ("start", "party_encounter", "prisoner_liberated", "enemy_defeated", "party_relieved",
                 "event_triggered", "close_window", "trade", "exchange_members", "trade_prisoners",
                 "buy_mercenaries", "view_char", "training", "member_chat", "prisoner_chat")
# what the engine runs by itself, not through a call in the code
ENGINE_SCRIPT = "game_"

ANYONE, PLYR, REPEATS, TROOP_BITS, PARTY_TPL = 0xfff, 0x10000, 0x7000, 0xfff, 0x20000
BLOCK_PLACES = ("menu", "dialog", "presentation", "mission", "trigger", "simple", "scene")

# words of a request the bridge has no use for: seq only makes each url differ
UNREAD = ("seq",)

# (rule, key): why it is fine, checked by hand
KNOWN = {
    ("M2", "coop_mp_invite"): "Decline hides only for kinds 2 and 3, and To battle! hides only for a duel, kind 7",
    ("S2", ("script cf_freelancer_player_can_upgrade", "troop_can_use_item")): "Freelancer passes a modifier, which is ignored",
    ("S2", ("script freelancer_equip_troop", "troop_can_use_item")): "Freelancer passes a modifier, which is ignored",
    ("M2", "upgrade_path"): "its only jump stands behind (gt, the first upgrade, 1), and the first option wants just that upgrade",
}


def fingerprint(record):
    return hashlib.md5(repr(record).encode("utf-8", "replace")).hexdigest()[:16]


class Flow:
    """The records and the questions every rule asks of them. `own(record)` says it is our code."""

    def __init__(self, ops, lists, own):
        self.ops = ops
        self.scripts, self.simple_triggers, self.triggers, self.menus, self.presentations, \
            self.missions, self.dialogs, self.scene_props = lists
        self.own = own
        self.all_blocks = list(blocks(*lists))
        self.by_script = {s[0]: s[1] for s in self.scripts}
        self.flags = ops.neg | ops.this_or_next
        self.openers = {ops.try_begin} | {getattr(ops, n) for n in dir(ops) if n.startswith("try_for_")}
        self.can_fail = set(ops.can_fail_operations)
        self.lhs = set(ops.lhs_operations) | set(getattr(ops, "global_lhs_operations", []))
        self.string_writers = {getattr(ops, n) for n in dir(ops) if n.startswith("str_") and n != "str_is_empty"
                               and isinstance(getattr(ops, n), int)}
        self._may_fail, self._writes = {}, {}

    def code(self, op):
        t = as_op(op)
        return t[0] & ~self.flags if isinstance(t[0], int) else t[0]

    def calls(self, block):
        for op in block:
            t = as_op(op)
            if self.code(op) == self.ops.call_script and len(t) > 1 and isinstance(t[1], str):
                yield t[1].replace("script_", "", 1), t

    def reachable(self, block):
        """The block and every script it leads to."""
        seen, stack, out = set(), [block], []
        while stack:
            b = stack.pop()
            out.append(b)
            for name, _ in self.calls(b):
                if name not in seen and name in self.by_script:
                    seen.add(name)
                    stack.append(self.by_script[name])
        return out

    def top_level(self, block):
        depth = 0
        for op in block:
            code = self.code(op)
            if code in self.openers:
                depth += 1
            elif code == self.ops.try_end:
                depth -= 1
            elif depth == 0 and code != self.ops.else_try:
                yield op

    def script_may_fail(self, name, path=()):
        if name in path or name not in self.by_script:
            return False
        if name not in self._may_fail:
            self._may_fail[name] = any(self.op_may_fail(op, path + (name,)) for op in self.top_level(self.by_script[name]))
        return self._may_fail[name]

    def op_may_fail(self, op, path=()):
        t = as_op(op)
        if self.code(op) in self.can_fail:
            return True
        return self.code(op) == self.ops.call_script and len(t) > 1 and isinstance(t[1], str) \
            and self.script_may_fail(t[1].replace("script_", "", 1), path)

    def always_holds(self, block):
        return not any(self.op_may_fail(op) for op in self.top_level(block))

    def together_always_hold(self, conditions):
        """Do these blocks of conditions leave no case uncovered? Each test counts as a yes-or-no question
        of its own, so "x" on one line and "not x" on another cover everything; anything subtler does not."""
        def tests(block):
            out, ors = [], []
            for op in self.top_level(block):
                if not self.op_may_fail(op):
                    continue
                t = as_op(op)
                plain = (t[0] & ~self.flags,) + t[1:]
                ors.append((repr(plain), bool(t[0] & self.ops.neg)))
                if not t[0] & self.ops.this_or_next:
                    out.append(ors)
                    ors = []
            return out + ([ors] if ors else [])

        parsed = [tests(b) for b in conditions]
        if any(not p for p in parsed):
            return True
        atoms = sorted({a for p in parsed for ors in p for a, _ in ors})
        if len(atoms) > 12:
            return False
        for values in itertools.product((False, True), repeat=len(atoms)):
            truth = dict(zip(atoms, values))
            if not any(all(any(truth[a] != neg for a, neg in ors) for ors in p) for p in parsed):
                return False
        return True

    def writes(self, block):
        """Registers (reg numbers as "reg7", strings as "s7") the block and what it calls set."""
        out = set()
        for b in self.reachable(block):
            key = id(b)
            if key not in self._writes:
                found = set()
                for op in b:
                    t = as_op(op)
                    code = self.code(op)
                    if len(t) < 2:
                        continue
                    if code in self.lhs and isinstance(t[1], int) and t[1] >> 56 == self.ops_register_tag():
                        found.add(f"reg{t[1] & 0xffffffff}")
                    if code in self.string_writers and isinstance(t[1], int) and 0 <= t[1] < 128:
                        found.add(f"s{t[1]}")
                self._writes[key] = found
            out |= self._writes[key]
        return out

    def ops_register_tag(self):
        import header_common
        return header_common.opmask_register >> 56


def state_lines(flow):
    states = {}
    for line in flow.dialogs:
        states.setdefault(line[1], []).append(line)
    return states


def rule_dialogs(flow):
    """D1, D2, D3, D4, D6."""
    states = state_lines(flow)
    entered = {}
    for line in flow.dialogs:
        entered.setdefault(line[4], []).append(line)
    is_plyr = lambda l: bool(l[0] & PLYR)  # noqa: E731
    conditional = lambda l: l[0] & REPEATS or not flow.always_holds(l[2])  # noqa: E731

    for state, lines in entered.items():
        # ours when we lead to it or wrote all of it: a line added to a state of the base game does not
        # make that state's other lines ours
        mine = any(flow.own(l) for l in lines) or all(flow.own(l) for l in states.get(state, [None]) if l)
        if state in ENGINE_STATES and state not in ("member_chat", "prisoner_chat", "event_triggered", "start"):
            continue
        if state == "close_window":
            continue
        if state not in states:
            yield mine, "D1", state, f'state {state}: "{lines[0][3][:50]}" ends here and no line goes on'
            continue
        npc = [l for l in states[state] if not is_plyr(l)]
        if any(is_plyr(l) for l in lines) and not npc:
            yield mine, "D6", state, f'state {state}: the player speaks ("{next(l for l in lines if is_plyr(l))[3][:50]}") and nobody can answer'
        for after_player in (True, False):
            coming = [l for l in lines if is_plyr(l) == after_player]
            nexts = npc if after_player else states[state]
            if not coming or not nexts:
                continue
            if any(l[0] & REPEATS == 0 and flow.always_holds(l[2]) for l in nexts):
                continue
            if not flow.together_always_hold([l[2] for l in nexts if not l[0] & REPEATS]):
                who = "nobody may answer" if after_player else "there may be nothing to say"
                yield mine, "D4", state, f'state {state}: every line may fail, {who} after "{coming[0][3][:50]}"'
                break

    for state, lines in states.items():
        if state not in entered and state not in ENGINE_STATES:
            yield any(flow.own(l) for l in lines), "D2", state, f'state {state}: no line leads to "{lines[0][3][:50]}"'
        troops, everyone = set(), False
        for line in lines:
            if is_plyr(line):
                continue
            speaker = line[0] & TROOP_BITS if not line[0] & PARTY_TPL else None
            if (everyone or speaker in troops) and speaker is not None:
                yield flow.own(line), "D3", (state, line[3]), f'state {state}: "{line[3][:50]}" is never said, a line before it always holds'
            if not conditional(line) and speaker is not None:
                if speaker == ANYONE:
                    everyone = True
                troops.add(speaker)


def troop_number(value):
    if isinstance(value, int) and value < 1 << 32:
        return value
    if isinstance(value, str) and value.startswith("trp_"):
        try:
            import ID_troops
        except ImportError:
            return None
        return getattr(ID_troops, value, None)
    return None


def rule_talks(flow):
    """D5."""
    states = state_lines(flow)
    wanted = {flow.ops.start_map_conversation: "event_triggered", flow.ops.change_screen_map_conversation: "start"}
    for where, kind, block in flow.all_blocks:
        for op in block:
            state = wanted.get(flow.code(op))
            t = as_op(op)
            if state is None or len(t) < 2:
                continue
            number = troop_number(t[1])
            if number is None:
                continue

            def speaks(line):
                if line[0] & PLYR or line[0] & PARTY_TPL:
                    return False
                if line[0] & TROOP_BITS == number:
                    return True
                if line[0] & TROOP_BITS != ANYONE:
                    return False
                # not a line for everyone: the one left in event_triggered is Native's "[ERROR-" line,
                # which John Blackborn's talk ended in
                return any(p == t[1] or troop_number(p) == number for c in line[2] for p in as_op(c)[1:])

            if not any(speaks(l) for l in states.get(state, ())):
                yield flow.own(block), "D5", (where, state), f'{where}: opens a talk with {t[1]} in state {state}, no line there is for them'


def menu_id(value):
    if isinstance(value, str) and value.startswith("mnu_"):
        return value[4:]
    return None


def on_load_jumps(flow, block):
    """{menu: always}: where the block jumps. `always`: no test stands before it."""
    found = {}

    def walk(b, sure, path):
        depth = 0
        for op in b:
            code = flow.code(op)
            t = as_op(op)
            if code in flow.openers:
                depth += 1
            elif code == flow.ops.try_end:
                depth -= 1
            at_top = sure and depth == 0
            if code == flow.ops.jump_to_menu and len(t) > 1 and menu_id(t[1]):
                found[menu_id(t[1])] = found.get(menu_id(t[1]), False) or at_top
            elif code == flow.ops.call_script and len(t) > 1 and isinstance(t[1], str):
                name = t[1].replace("script_", "", 1)
                if name in flow.by_script and name not in path:
                    walk(flow.by_script[name], at_top, path | {name})
            if depth == 0 and flow.op_may_fail(op):
                sure = False

    walk(block, True, frozenset())
    return found


def rule_menus(flow):
    """M1, M2, M3, M4."""
    leaves = {flow.ops.jump_to_menu, flow.ops.change_screen_return, flow.ops.change_screen_map,
              flow.ops.finish_mission if hasattr(flow.ops, "finish_mission") else flow.ops.jump_to_menu}
    used = set()
    for where, kind, block in flow.all_blocks:
        for op in block:
            used.update(p for p in as_op(op)[1:] if menu_id(p))
    edges = {}
    for m in flow.menus:
        mine = flow.own(m)
        jumps = on_load_jumps(flow, m[4])
        edges[m[0]] = jumps
        names = [n for n in dir(flow.ops) if n.startswith("change_screen") or n.startswith("start_presentation")
                 or n in ("jump_to_menu", "set_jump_mission", "leave_encounter", "finish_party_battle_mode")]
        leaving = {getattr(flow.ops, n) for n in names} | leaves
        walks_off = any(flow.code(op) in leaving for b in flow.reachable(m[4]) for op in b)
        if not m[5]:
            if not walks_off:
                yield mine, "M1", m[0], f"menu {m[0]}: no options and nothing leaves it"
            continue
        if not flow.together_always_hold([o[1] for o in m[5]]) and not walks_off:
            yield mine, "M2", m[0], f"menu {m[0]}: every option may be hidden, the player may be left with none"
        if f"mnu_{m[0]}" not in used:
            yield mine, "M3", m[0], f"menu {m[0]}: nothing opens it"

    for start in edges:
        for path in itertools.islice(cycles_from(start, edges), 1):
            sure = all(edges[a][b] for a, b in zip(path, path[1:]))
            mine = any(flow.own(m) for m in flow.menus if m[0] in path)
            if sure:
                yield mine, "M4", tuple(sorted(path)), f"menus {' -> '.join(path)}: each jumps to the next on load, for ever"
            else:
                yield False, "M4", tuple(sorted(path)), f"menus {' -> '.join(path)}: jump to each other on load, when their tests allow"


def cycles_from(start, edges):
    stack = [(start, (start,))]
    seen = set()
    while stack:
        node, path = stack.pop()
        for target in edges.get(node, ()):
            if target == start:
                yield path + (start,)
            elif target not in path and target not in seen and target in edges:
                seen.add(target)
                stack.append((target, path + (target,)))


def rule_presentations(flow):
    """P1, P2, P3, P4."""
    ops = flow.ops
    fixed = ops.set_fixed_point_multiplier
    for p in flow.presentations:
        mine = flow.own(p)
        closes = False
        for k, event in enumerate(p[3]):
            block = event[1]
            closed, overlay, multiplier = False, None, False
            for op in block:
                code = flow.code(op)
                t = as_op(op)
                if code in (ops.else_try, ops.try_end):
                    closed = False
                if code == ops.presentation_set_duration and len(t) > 1 and t[1] == 0:
                    closed = True
                if code == ops.start_presentation and closed:
                    yield mine, "P1", (p[0], k), f"presentation {p[0]} event {k}: closed and another started in one go; start_presentation alone swaps them"
                if code == ops.set_container_overlay and len(t) > 1:
                    overlay = t[1]
                if code == fixed or (code == ops.call_script and any(
                        flow.code(o) == fixed for b in flow.reachable([op]) for o in b)):
                    multiplier = True
                if code in (ops.position_set_x, ops.position_set_y) and not multiplier:
                    yield mine, "P4", (p[0], k), f"presentation {p[0]} event {k}: positions set before set_fixed_point_multiplier"
                    multiplier = True
            if overlay not in (None, -1):
                yield mine, "P3", (p[0], k), f"presentation {p[0]} event {k}: set_container_overlay is not back to -1 at the end"
            for b in flow.reachable(block):
                for op in b:
                    t = as_op(op)
                    if flow.code(op) == ops.start_presentation or \
                            (flow.code(op) == ops.presentation_set_duration and len(t) > 1 and t[1] == 0):
                        closes = True
        read_only = p[1] & getattr(_presentation_flags(), "prsntf_read_only", 0)
        if not closes and not read_only:
            yield mine, "P2", p[0], f"presentation {p[0]}: nothing closes it"


def _presentation_flags():
    import header_presentations
    return header_presentations


def params_read(flow, block):
    most = 0
    for op in block:
        t = as_op(op)
        code = flow.code(op)
        if code == flow.ops.store_script_param_1:
            most = max(most, 1)
        elif code == flow.ops.store_script_param_2:
            most = max(most, 2)
        elif code == flow.ops.store_script_param and len(t) > 2 and isinstance(t[2], int):
            most = max(most, t[2])
    return most


def rule_scripts(flow):
    """S1, S2, S3, S4."""
    reads = {name: params_read(flow, block) for name, block in flow.by_script.items()}
    called = set()
    for where, kind, block in flow.all_blocks:
        for op in block:
            called.update(p.replace("script_", "", 1) for p in as_op(op)[1:] if isinstance(p, str) and p.startswith("script_"))
        for name, t in flow.calls(block):
            if name not in reads:
                continue
            passed, need = len(t) - 2, reads[name]
            mine = flow.own(t)
            if passed < need:
                yield mine, "S1", (where, name), f"{where}: {name} gets {passed} argument(s), reads {need}"
            elif passed > need:
                yield mine, "S2", (where, name), f"{where}: {name} gets {passed} argument(s), reads {need}"

    graph = {name: {c for c, _ in flow.calls(block) if c in flow.by_script} for name, block in flow.by_script.items()}
    ours = {(name, c) for name, block in flow.by_script.items() for c, t in flow.calls(block) if flow.own(t)}
    seen = set()
    for start in graph:
        for path in cycles_from(start, graph):
            key = tuple(sorted(set(path)))
            if key not in seen:
                seen.add(key)
                mine = any(step in ours for step in zip(path, path[1:]))
                yield mine, "S3", key, f"scripts {' -> '.join(path)}: call themselves"

    for s in flow.scripts:
        if flow.own(s[1]) and s[0] not in called and not s[0].startswith(ENGINE_SCRIPT):
            yield False, "S4", s[0], f"script {s[0]}: nothing calls it"


REGISTER = re.compile(r"\{(reg\d+|s\d+)\}")


def rule_texts(flow):
    """V1: a text of ours showing a register nothing sets on the way to it."""
    states = state_lines(flow)
    before = {}
    for line in flow.dialogs:
        before.setdefault(line[4], []).append(line)
    for line in flow.dialogs:
        if not flow.own((line[1], line[3])) or not REGISTER.search(line[3]):
            continue
        set_here = flow.writes(line[2])
        for other in states[line[1]] + before.get(line[1], []):
            set_here = set_here | flow.writes(other[2]) | flow.writes(other[5])
        for name in sorted(set(REGISTER.findall(line[3])) - set_here):
            yield True, "V1", (line[1], line[3]), f'state {line[1]}: "{line[3][:50]}" shows {{{name}}}, nothing sets it'
    for m in flow.menus:
        loaded = flow.writes(m[4])
        if flow.own((m[0], m[2])):
            for name in sorted(set(REGISTER.findall(m[2])) - loaded):
                yield True, "V1", m[0], f"menu {m[0]}: its text shows {{{name}}}, nothing sets it"
        for o in m[5]:
            if flow.own(o):
                for name in sorted(set(REGISTER.findall(o[2])) - loaded - flow.writes(o[1])):
                    yield True, "V1", (m[0], o[0]), f"menu {m[0]} option {o[0]}: shows {{{name}}}, nothing sets it"


SLOT_FAMILIES = (
    ("party", ("slot_party_", "slot_town_", "slot_center_", "slot_village_", "slot_castle_")),
    ("troop", ("slot_troop_", "slot_lord_", "slot_lady_")),
    ("faction", ("slot_faction_",)),
    ("item", ("slot_item_",)),
    ("agent", ("slot_agent_",)),
    ("player", ("slot_player_",)),
)


def rule_slots(base, ours):
    """G2: {name: number} of the base game's and of our slots."""
    def family(name):
        return next((f for f, starts in SLOT_FAMILIES if name.startswith(starts)), None)

    taken = {}
    for name, number in base.items():
        taken.setdefault((family(name), number), name)
    for name, number in ours.items():
        if name in base or family(name) is None or base.get(name) == number:
            continue
        clash = taken.get((family(name), number))
        if clash:
            yield True, "G2", name, f"slot {name} = {number} is {clash} too"


def rule_bridge(bridge, constants, game_strings):
    """B1: the module tools/coop_bridge.py, coop's and the army's constants as {name: value}, the texts
    of the game's requests."""
    def same(ours, theirs, what):
        if ours != theirs:
            yield True, "B1", what, f"{what}: the game has {ours}, the bridge {theirs}"

    notes = {v: k[len("coop_note_"):] for k, v in constants.items()
             if k.startswith("coop_note_") and k != "coop_note_cap"}
    yield from same(notes, dict(getattr(bridge, "GAME_NOTES")) and {k: v[0] if isinstance(v, (tuple, list)) else v
                                                                    for k, v in bridge.GAME_NOTES.items()}, "notes")
    for prefix, starts in (("coop_kind_", "KIND_"), ("coop_tell_", "TELL_")):
        for name, value in constants.items():
            if name.startswith(prefix) and isinstance(value, int):
                other = starts + name[len(prefix):].upper()
                yield from same(value, getattr(bridge, other, None), other)
    yield from same(constants.get("custom_kinds"), bridge.ARMY_KINDS, "ARMY_KINDS")
    yield from same(constants.get("custom_gear_max"), bridge.ARMY_GEAR_MAX, "ARMY_GEAR_MAX")
    yield from same(constants.get("trail_ack"), bridge.TRAIL_ACK, "TRAIL_ACK")
    source = Path(bridge.__file__).read_text("utf-8", "replace")
    for name in sorted({m for text in game_strings for m in re.findall(r"[?&](\w+)=", text)} - set(UNREAD)):
        if f'"{name}"' not in source and f"&{name}=" not in source:
            yield True, "B1", name, f"the game sends &{name}=, the bridge never reads it"


RULES = (rule_dialogs, rule_talks, rule_menus, rule_presentations, rule_scripts, rule_texts)


def run(flow):
    out = []
    for rule in RULES:
        out += list(rule(flow))
    return out


def base_prints():
    """The fingerprints of the module with no mods, as JSON on stdout."""
    sys.path.insert(0, str(SRC))
    import coop_mods
    coop_mods.MODS.clear()
    ops, *lists = load()
    prints = [fingerprint(b) for _, _, b in blocks(*lists)]
    prints += [fingerprint(as_op(op)) for _, _, b in blocks(*lists) for op in b
               if isinstance(as_op(op)[0], int) and as_op(op)[0] & ~(ops.neg | ops.this_or_next) == ops.call_script]
    for line in lists[6]:
        prints += [fingerprint(line), fingerprint((line[1], line[3]))]
    for m in lists[3]:
        prints += [fingerprint(m), fingerprint((m[0], m[2]))]
        prints += [fingerprint(o) for o in m[5]]
    prints += [fingerprint(p) for p in lists[4]]
    print(json.dumps(sorted(set(prints))))


def constants_of(*modules):
    out = {}
    for name in modules:
        out.update({k: v for k, v in vars(importlib.import_module(name)).items()
                    if not k.startswith("__") and isinstance(v, (int, str))})
    return out


def main():
    if "--base" in sys.argv:
        return base_prints()
    done = subprocess.run([sys.executable, __file__, "--base"], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=ROOT)
    if done.returncode != 0:
        print(done.stdout, done.stderr)
        print("PROBLEM: the module with no mods would not load")
        sys.exit(1)
    base = set(json.loads(done.stdout.strip().splitlines()[-1]))
    ops, *lists = load()
    flow = Flow(ops, lists, lambda record: fingerprint(record) not in base)
    found = run(flow)

    import module_constants
    own = constants_of("coop.constants", "custom_troops.constants", "freelancer.constants", "trail.marks")
    plain = {k: v for k, v in vars(module_constants).items() if k.startswith("slot_") and isinstance(v, int)}
    found += list(rule_slots({k: v for k, v in plain.items() if k not in own},
                             {k: v for k, v in own.items() if k.startswith("slot_") and isinstance(v, int)}))
    strings = [p[1:] for _, _, b in flow.all_blocks if flow.own(b) for op in b for p in as_op(op)[1:]
               if isinstance(p, str) and p.startswith("@") and "=" in p]
    sys.path.insert(0, str(ROOT / "tools"))
    import coop_bridge
    found += list(rule_bridge(coop_bridge, own, strings))

    problems, notes, seen = [], [], set()
    for mine, rule, key, text in found:
        if (rule, key) in seen:
            continue
        seen.add((rule, key))
        if mine and (rule, key) not in KNOWN:
            problems.append(f"{rule} {text}")
        else:
            notes.append(f"{rule} {text}")
    for gone in sorted(set(KNOWN) - seen, key=repr):
        problems.append(f"KNOWN {gone} no longer happens: take it out")
    if "--notes" in sys.argv:
        for n in notes:
            print("note:", n)
    for p in problems:
        print("PROBLEM:", p)
    print(f"flow: {len(problems)} problem(s) in our code, {len(notes)} note(s) in Diplomacy/Native")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
