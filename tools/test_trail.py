"""Tests for src/trail: a debug build marks what it should, and a plain one holds none of it. It loads the
module in a process of its own, as a build does, so COOP_TRAIL decides.

    python -I tools/test_trail.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = r"""
import json, sys
sys.path.insert(0, r"%(tools)s")
from check_module import as_op, blocks, load
from trail_names import names
ops, *lists = load()
scripts, simple_triggers, triggers, menus, presentations, missions, dialogs, _ = lists
all_ops = [(where, as_op(op)) for where, _, block in blocks(*lists) for op in block]
blocks_once = {id(block): block for _, _, block in blocks(*lists)}.values()  # records may share a list
marks = [t[2] for block in blocks_once for t in map(as_op, block) if len(t) > 2 and t[1] == "script_coop_trail"]
handler = dict((s[0], s[1]) for s in scripts)["game_receive_url_response"]
from header_common import reg55
print(json.dumps({
    "marks": marks,
    "scripts": [s[0] for s in scripts],
    "names": {str(k): v for k, v in names(lists).items()},
    "pending_at": next((i for i, op in enumerate(handler) if as_op(op)[:2] == (ops.assign, "$coop_net_pending")), None),
    "ack_at": next((i for i, op in enumerate(handler) if len(as_op(op)) > 2 and as_op(op)[2] == 7779), None),
    "menu_first": [repr(as_op(m[4][0])) for m in menus if m[4]][:3],
    "reg55": sorted({w for w, t in all_ops if reg55 in t[1:]}),
    "s27": sorted({w for w, t in all_ops if any(isinstance(p, str) and "{s27}" in p for p in t[1:])}),
    "flush": sum(1 for t in triggers if "script_coop_trail_flush" in repr(t[3])),
    "records": [len(simple_triggers), len(triggers), [m[0] for m in menus], len(presentations), len(dialogs),
                [mt[0] for mt in missions]],
}))
"""


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  ", msg)


def probe(trail):
    env = {k: v for k, v in os.environ.items() if k != "COOP_TRAIL"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if trail:
        env["COOP_TRAIL"] = "1"
    done = subprocess.run([sys.executable, "-c", PROBE % {"tools": ROOT / "tools"}], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, cwd=ROOT)
    if done.returncode != 0:
        raise AssertionError(done.stderr[-2000:])
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_plain():
    plain = probe(False)
    check(not plain["marks"], "a plain build has no mark")
    check("coop_trail" not in plain["scripts"], "and no trail script")
    check(plain["ack_at"] is None and plain["flush"] == 0, "its reply handler and map triggers are untouched")
    return plain


def test_marked(plain):
    marked = probe(True)
    marks = marked["marks"]
    check(len(marks) > 5000, f"a debug build marks the game: {len(marks)} places")
    check(len(set(marks)) == len(marks), "every place has its own number")
    kinds = {m // 100000 for m in marks}
    check(kinds == set(range(1, 9)), "menus, options, lines, screens, triggers, missions and game scripts")
    check(set(marked["names"]) == {str(m) for m in marks}, "each number has its name")
    check(all("script_coop_trail" in first for first in marked["menu_first"]), "a menu says so first thing on load")
    check(marked["ack_at"] is not None and marked["pending_at"] is not None and marked["ack_at"] < marked["pending_at"],
          "the trail's reply stops before it could free a request of the game's")
    check(marked["flush"] == 1, "the map sends once a frame")
    # the reply handler only copies every register a reply can fill, before anything of the trail can run
    check(set(marked["reg55"]) <= {"script coop_trail_flush", "script game_receive_url_response"},
          f"reg55 is the trail's alone: {marked['reg55']}")
    check(not any(w != "script coop_trail_flush" for w in marked["s27"]), f"s27 is the trail's alone: {marked['s27']}")
    check(set(marked["scripts"]) - set(plain["scripts"]) == {"coop_trail", "coop_trail_flush"}, "two scripts more, no other change of the list")
    check(marked["scripts"][:len(plain["scripts"])] == plain["scripts"], "scripts keep their numbers")
    check(marked["records"] == plain["records"], "no trigger, menu, screen, line or mission more: saves stay the same")


def test_slots():
    sys.path.insert(0, str(ROOT / "src"))
    from coop.constants import coop_note_cap
    from trail.marks import trail_ring, trail_slot_ring, trail_slot_seq
    check(coop_note_cap * 4 <= trail_slot_seq and trail_slot_seq + 3 <= trail_slot_ring, "the ring stays clear of the notes")
    check(trail_ring > 0 and trail_slot_ring + trail_ring < 1000, "a sane size")


if __name__ == "__main__":
    plain_build = test_plain()
    test_marked(plain_build)
    test_slots()
    print("all tests passed")
