"""Tests for coop/tree.py: the troop tree's layout, from the build's real troops.

    python -I tools/test_coop_tree.py
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
from coop import tree  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  ", msg)


def test_branches():
    from module_troops import troops
    ids = {t[0]: t for t in troops}
    rows = tree.layout()
    check(len(rows) == len(tree.BRANCHES) + 1, "a branch for each name, and In development last")
    check(rows[-1] == [] and tree.DEVELOPMENT_TEXT, "In development holds no troop yet, and says why")
    for (name, _), branch in zip(tree.BRANCHES, rows):
        check(len(branch) >= 3, f"{name}: {len(branch)} troops")
    shown = [row[0] for branch in rows for row in branch]
    check(len(shown) == len(set(shown)), "a troop stands in one branch only")
    check(all(troop in ids for troop in shown), "every troop shown exists")
    for root in ("swadian_knight", "nord_champion", "khergit_lancer", "rhodok_sharpshooter", "sarranid_mamluke",
                 "vaegir_guard", "hired_blade", "sword_sister", "slaver_chief", "brigand"):
        check(root in shown, f"the tree reaches {root}")
    # every troop that grows into another stands in the tree with it, unless that one is another branch's
    for branch in rows:
        here = {row[0] for row in branch}
        for troop_id, depth, parent in branch:
            if parent >= 0:
                check(branch[parent][1] == depth - 1 and parent < branch.index((troop_id, depth, parent)),
                      f"{troop_id} stands right under {branch[parent][0]}")
                check(troop_id in tree.upgrades_of(ids[branch[parent][0]], troops),
                      f"{branch[parent][0]} does grow into {troop_id}")
            check(troop_id in here, "")


def test_fits():
    from module_troops import troops
    ids = {t[0]: t for t in troops}
    for (name, _), branch in zip(tree.BRANCHES, tree.layout()):
        height = len(branch) * tree.ROW_HEIGHT
        widest = max(d * tree.ROW_INDENT + 6 + len(ids[t][1]) * tree.TEXT_WIDTH for t, d, _ in branch)
        check(widest <= tree.TREE_WIDTH, f"{name}: the widest row ({widest}) fits the box")
        check(height <= tree.TREE_HEIGHT * 2, f"{name}: {height} high, with the box's scroll bar at the worst")
    bottom = 660 - len(tree.BRANCHES) * 52
    check(bottom >= 30, f"all the branch buttons fit on the screen (the last at {bottom})")
    check(tree.TREE_X + tree.TREE_WIDTH <= tree.DETAIL_X, "the tree and the troop's panel do not overlap")
    gap = [row for branch in tree.layout() for row in branch]
    needed = 40 + 3 * len(max(tree.layout(), key=len))
    check(needed < tree.MAP_SLOTS, f"overlays of a branch fit the table of what they stand for ({needed}, {len(gap)} troops)")


if __name__ == "__main__":
    test_branches()
    test_fits()
    print("ALL OK")
