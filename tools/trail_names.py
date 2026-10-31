"""What the numbers of a debug build's trail stand for, read off the marks in the merged records
(so they cannot drift apart from them): trail_names.json, for the bridge.

    python tools/trail_names.py <file>       (under COOP_TRAIL=1; build.py --trail runs it)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_module import as_op, load

MARK = "script_coop_trail"


def hint(block):
    """What a trigger is about: the first script it calls, or the first global it touches."""
    for op in block:
        t = as_op(op)
        if len(t) > 1 and isinstance(t[1], str) and t[1] != MARK and t[1].startswith(("script_", "$")):
            return t[1].replace("script_", "", 1)
    return ""


def names(lists):
    scripts, simple_triggers, triggers, menus, presentations, missions, dialogs, _ = lists
    out = {}

    def note(block, text):
        for op in block:
            t = as_op(op)
            if len(t) > 2 and t[1] == MARK:
                out[t[2]] = " ".join(text.split())
                return

    for s in scripts:
        note(s[1], f"script {s[0]}")
    for m in menus:
        note(m[4], f"menu {m[0]}")
        for o in m[5]:
            note(o[3], f"option {m[0]}: {o[0]}")
    for d in dialogs:
        note(d[5], f"line {d[1]} -> {d[4]}: {d[3][:60]}")
    for p in presentations:
        for k, event in enumerate(p[3]):
            note(event[1], f"screen {p[0]} " + ("opens" if k == 0 else f"event {k}"))
    for k, t in enumerate(triggers):
        note(t[4], f"trigger {k} {hint(list(t[3]) + list(t[4]))}")
    for k, t in enumerate(simple_triggers):
        note(t[1], f"simple trigger {k} {hint(t[1])}")
    for mt in missions:
        for t in mt[5]:
            note(t[4], f"mission {mt[0]}")
    return out


def main():
    ops, *lists = load()
    found = names(lists)
    Path(sys.argv[1]).write_text(json.dumps(found, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"trail: {len(found)} places named")


if __name__ == "__main__":
    main()
