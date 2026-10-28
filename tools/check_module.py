"""Checks of the merged module, for mistakes the module system compiles without a word:

  - an empty "@" string (its quick string has no text: the next build step drops it and every
    quick string after it shifts against the code already written);
  - unbalanced try blocks: a try_end too many, an else_try outside a try, a block left open
    (Diplomacy lost an else_try in game_receive_network_message this way);
  - a script that can fail called outside a try, where its failure silently ends the rest of the
    caller (Native names such scripts cf_...; the check lists the others);
  - CoopWorld globals read but never set anywhere (a typo, or a state nobody starts).

    python tools/check_module.py          (from the repository root)

Exit status 1 when something is found in CoopWorld's own code (src/coop, src/dplmc_fix,
src/freelancer); findings in Diplomacy's and Native's own code are listed as notes.
"""
import os
import runpy
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# the Python 2 string helpers the module system expects (as tools/run_step.py)
string.replace = lambda s, old, new, *n: s.replace(old, new, *n)
string.lower = lambda s: s.lower()
string.upper = lambda s: s.upper()
string.strip = lambda s, *c: s.strip(*c)
string.find = lambda s, sub, *a: s.find(sub, *a)
string.split = lambda s, *a: s.split(*a)
string.join = lambda words, sep=" ": sep.join(words)
string.atoi = int


def load():
    os.chdir(SRC)
    sys.path.insert(0, str(SRC))
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        import header_operations as ops
        from module_scripts import scripts
        from module_simple_triggers import simple_triggers
        from module_triggers import triggers
        from module_game_menus import game_menus
        from module_presentations import presentations
        from module_mission_templates import mission_templates
        from module_dialogs import dialogs
        from module_scene_props import scene_props
    return ops, scripts, simple_triggers, triggers, game_menus, presentations, mission_templates, dialogs, scene_props


def blocks(scripts, simple_triggers, triggers, game_menus, presentations, mission_templates, dialogs, scene_props):
    """(where, kind, block): kind is "condition" (failing there is its purpose) or "consequence"."""
    for s in scripts:
        yield f"script {s[0]}", "script", s[1]
    for k, t in enumerate(simple_triggers):
        yield f"simple trigger {k}", "consequence", t[1]
    for k, t in enumerate(triggers):
        yield f"trigger {k}", "condition", t[3]
        yield f"trigger {k}", "consequence", t[4]
    for m in game_menus:
        yield f"menu {m[0]}", "consequence", m[4]
        for o in m[5]:
            yield f"menu {m[0]} option {o[0]} (condition)", "condition", o[1]
            yield f"menu {m[0]} option {o[0]}", "consequence", o[3]
            if len(o) > 5 and isinstance(o[5], list):
                yield f"menu {m[0]} option {o[0]} (door)", "consequence", o[5]
    for p in presentations:
        for k, t in enumerate(p[3]):
            yield f"presentation {p[0]} trigger {k}", "consequence", t[1]
    for mt in mission_templates:
        for k, t in enumerate(mt[5]):
            yield f"mission {mt[0]} trigger {k} (condition)", "condition", t[3]
            yield f"mission {mt[0]} trigger {k}", "consequence", t[4]
    for k, d in enumerate(dialogs):
        yield f"dialog {k} {d[1]}->{d[4]} (condition)", "condition", d[2]
        yield f"dialog {k} {d[1]}->{d[4]}", "consequence", d[5]
    for sp in scene_props:
        for k, t in enumerate(sp[4]):
            yield f"scene prop {sp[0]} trigger {k}", "consequence", t[1]


def compiled_scripts(path):
    """{script: [operation codes]} of a compiled scripts.txt (flags off)."""
    toks = path.read_text("utf-8", "replace").split()
    i, out = 4, {}
    n = int(toks[3])  # "scriptsfile version 1", then the number of scripts
    for _ in range(n):
        name, cnt = toks[i], int(toks[i + 2])
        i += 3
        codes = []
        for _ in range(cnt):
            code, na = int(toks[i]), int(toks[i + 1])
            codes.append(code & 0xFFFFFFF)
            i += 2 + na
        out[name] = codes
    return out


def compiled_quick_refs(path):
    """{script: [quick string index, ...]} in the order its compiled operations use them."""
    toks = path.read_text("utf-8", "replace").split()
    i, out = 4, {}
    tag = 22 << 56  # opmask_quick_string
    for _ in range(int(toks[3])):
        name, cnt = toks[i], int(toks[i + 2])
        i += 3
        refs = []
        for _ in range(cnt):
            na = int(toks[i + 1])
            for v in toks[i + 2:i + 2 + na]:
                v = int(v)
                if v >> 56 == 22:
                    refs.append(v - tag)
            i += 2 + na
        out[name] = refs
    return out


def hook_length(name):
    def length():
        import coop.mp as mp
        return len({"game_receive_network_message": mp.mp_network_hook}[name]())
    return length


MP_HOOKED = {"game_receive_network_message": hook_length("game_receive_network_message")}


def as_op(op):
    return tuple(op) if isinstance(op, (list, tuple)) else (op,)


def main():
    global EXPORT
    ops, *lists = load()
    from module_info import export_dir as EXPORT
    scripts = lists[0]
    openers = {ops.try_begin} | {getattr(ops, n) for n in dir(ops) if n.startswith("try_for_")}
    can_fail = set(ops.can_fail_operations)
    flags = ops.neg | ops.this_or_next
    lhs = set(ops.lhs_operations) | set(getattr(ops, "global_lhs_operations", []))

    own_scripts = set()
    sys.path.insert(0, str(SRC))
    for pkg in ("coop", "dplmc_fix", "freelancer"):
        for f in (SRC / pkg).glob("*.py"):
            text = f.read_text("utf-8", "replace")
            for s in scripts:
                if f'"{s[0]}"' in text:
                    own_scripts.add(s[0])

    all_blocks = list(blocks(*lists))
    problems, notes = [], []

    def own(where):
        name = where.split()[1] if where.startswith("script ") else ""
        return name in own_scripts or "coop" in where

    # 0. two records of one id: the engine finds the first by its name (a game_* hook, a menu...) and
    #    the other never runs (CoopWorld's speed hook sat behind Diplomacy's this way)
    from collections import Counter
    for kind, records in (("script", lists[0]), ("menu", lists[3]), ("presentation", lists[4]),
                          ("mission template", lists[5]), ("scene prop", lists[7])):
        for rid, n in Counter(r[0] for r in records).items():
            if n > 1:
                problems.append(f"{n} {kind}s named {rid}: only the first one is used")

    # 1. empty "@" strings, 2. the structure of try blocks
    for where, kind, block in all_blocks:
        depth = 0
        for i, op in enumerate(block):
            t = as_op(op)
            code = t[0] & ~flags if isinstance(t[0], int) else t[0]
            for p in t[1:]:
                if isinstance(p, str) and p.startswith("@") and not p[1:].strip():
                    (problems if own(where) else notes).append(f'{where}: op {i}: an empty "@" string')
            if code in openers:
                depth += 1
            elif code == ops.else_try:
                if depth == 0:
                    (problems if own(where) else notes).append(f"{where}: op {i}: else_try outside a try block")
            elif code == ops.try_end:
                depth -= 1
                if depth < 0:
                    (problems if own(where) else notes).append(f"{where}: op {i}: try_end without a try")
                    depth = 0
        if depth != 0:
            (problems if own(where) else notes).append(f"{where}: {depth} try block(s) left open")

    # 3. scripts that can fail, called where their failure ends the caller
    script_block = {s[0]: s[1] for s in scripts}

    def top_level(block):
        depth = 0
        for op in block:
            t = as_op(op)
            code = t[0] & ~flags if isinstance(t[0], int) else t[0]
            if code in openers:
                depth += 1
            elif code == ops.try_end:
                depth -= 1
            elif depth == 0 and code != ops.else_try:
                yield t, code

    fails = set()
    changed = True
    while changed:
        changed = False
        for name, block in script_block.items():
            if name in fails:
                continue
            for t, code in top_level(block):
                if code in can_fail or (code == ops.call_script and len(t) > 1
                                        and str(t[1]).replace("script_", "", 1) in fails):
                    fails.add(name)
                    changed = True
                    break
    for where, kind, block in all_blocks:
        if kind == "condition":
            continue
        top = list(top_level(block))
        for n, (t, code) in enumerate(top):
            if code != ops.call_script or len(t) < 2:
                continue
            callee = str(t[1]).replace("script_", "", 1)
            if callee in fails and not callee.startswith("cf_") and n < len(top) - 1:
                if where.startswith("script ") and where.split()[1].startswith("cf_"):
                    continue  # a cf_ script failing with its callee is what it is for
                msg = f"{where}: calls {callee} outside a try; when it fails, the rest of {where} does not run"
                (problems if (callee in own_scripts or own(where)) else notes).append(msg)

    # 4. CoopWorld globals read but never set
    read, written = {}, set()
    for where, kind, block in all_blocks:
        for op in block:
            t = as_op(op)
            if not isinstance(t[0], int):
                continue
            code = t[0] & ~flags
            for k, p in enumerate(t[1:]):
                if isinstance(p, str) and p.startswith("$"):
                    if k == 0 and code in lhs:
                        written.add(p)
                    else:
                        read.setdefault(p, where)
    for g, where in sorted(read.items()):
        if g.startswith("$coop_") and g not in written:
            problems.append(f"{g} is read ({where}) but never set")

    # 5. the multiplayer scripts against the game's own Native (game/Modules/Native, compiled): the
    #    shape of their try blocks; Diplomacy's lost else_try showed this way
    native = ROOT / "game" / "Modules" / "Native" / "scripts.txt"
    built = Path(EXPORT) / "scripts.txt"
    if native.exists() and built.exists():
        a, b = compiled_scripts(native), compiled_scripts(built)
        for name, nat_ops in a.items():
            if name not in b or not any(k in name for k in ("multiplayer", "network", "mp_", "ccoop")):
                continue
            ours_ops = b[name]
            if name in MP_HOOKED:
                ours_ops = ours_ops[MP_HOOKED[name]():]
            shape = lambda o: (sum(1 for c in o if c in openers), o.count(ops.else_try), o.count(ops.try_end))
            if shape(nat_ops) != shape(ours_ops):
                notes.append(f"script {name}: try/else_try/try_end {shape(ours_ops)}, Native {shape(nat_ops)}")

    # 6. the compiled quick strings: the count the game reads first, one "id text" per line; a line
    #    lost or split shifts every quick string after it against the code
    qs = Path(EXPORT) / "quick_strings.txt"
    if qs.exists():
        lines = qs.read_text("utf-8", "replace").splitlines()
        entries = [l for l in lines[1:] if l.strip()]
        if not lines or not lines[0].strip().isdigit() or int(lines[0]) != len(entries):
            problems.append(f"quick_strings.txt: says {lines[0] if lines else '?'} entries, holds {len(entries)}")
        for l in entries:
            if len(l.split(" ")) != 2 or not l.split(" ")[1]:
                problems.append(f"quick_strings.txt: not an 'id text' line: {l[:80]!r}")

    # 7. every "@..." string of every script against the text its compiled code really points to
    #    (the request URL of joint battles pointed to "&hero=" this way)
    if qs.exists() and built.exists():
        texts = [l.split(" ", 1)[1] for l in qs.read_text("utf-8", "replace").splitlines()[1:] if " " in l]
        refs = compiled_quick_refs(built)
        for s in scripts:
            source = [p[1:] for op in s[1] for p in as_op(op)[1:] if isinstance(p, str) and p.startswith("@")]
            compiled = [texts[i] if i < len(texts) else f"<index {i} past the end>" for i in refs.get(s[0], [])]
            want = [x.replace(" ", "_").replace("	", "_") for x in source]
            if want != compiled:
                bad = next((k for k, (w, c) in enumerate(zip(want, compiled)) if w != c), min(len(want), len(compiled)))
                (problems if own(f"script {s[0]}") else notes).append(
                    f"script {s[0]}: quick string {bad} is {compiled[bad] if bad < len(compiled) else '-'!r} "
                    f"in the compiled code, {want[bad] if bad < len(want) else '-'!r} in the source")

    for n in notes:
        print("note:", n)
    for p in problems:
        print("PROBLEM:", p)
    print(f"{len(problems)} problem(s) in CoopWorld's code, {len(notes)} note(s) in Diplomacy/Native")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
