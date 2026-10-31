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
    check(len(rows) == len(tree.BRANCHES) + 1, "a branch for each name, and the player's army last")
    check(len(rows[-1]) == 13 and tree.ARMY_TEXT, "the army shows each kind of soldier once, and says how to raise it")
    army = rows.pop()
    check([row[1] for row in army] == [0] + [1, 2, 3, 4] * 3 and [row[2] for row in army[:6]] == [-1, 0, 1, 2, 3, 0],
          "a recruit, and three branches growing from it")
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
                      f"{troop_id} stands right after {branch[parent][0]}")
                check(troop_id in tree.upgrades_of(ids[branch[parent][0]], troops),
                      f"{branch[parent][0]} does grow into {troop_id}")
            check(troop_id in here, "")


def test_fits():
    for (name, _), branch in zip(tree.BRANCHES + [("the army", [])], tree.layout()):
        at = tree.place(branch)
        check(len(set(at)) == len(at), f"{name}: no two portraits on one spot")
        right = max(x for x, _ in at) + tree.PORTRAIT // 2
        check(right <= tree.TREE_WIDTH - 20, f"{name}: the tree ends at {right}, within the box and its scroll bar")
        low = min(y for _, y in at) - tree.PORTRAIT // 2 - tree.NAME_HEIGHT
        check(low >= 0, f"{name}: the lowest name ends at {low}, inside the box")
        for i, (troop_id, depth, parent) in enumerate(branch):
            if parent >= 0:
                check(at[parent][0] + tree.COLUMN == at[i][0], "")
        for x, y, width, height in tree.links(branch, at):
            check(width > 0 and height > 0 and y >= 0 and x + width <= tree.TREE_WIDTH, "")
        rows = {y for _, y in at}
        for row in sorted(rows):
            xs = sorted(x for x, y in at if y == row)
            check(all(b - a >= tree.COLUMN for a, b in zip(xs, xs[1:])), "")
    bottom = 660 - len(tree.BRANCHES) * 52
    check(bottom >= 30, f"all the branch buttons fit on the screen (the last at {bottom})")
    check(24 + 8 * 19 <= tree.TREE_X + 20, "the branch buttons stop where the box starts")
    check(tree.TREE_X + tree.TREE_WIDTH <= 1000, "the box stays on the screen")
    check(tree.TREE_Y + tree.TREE_HEIGHT <= 705, "and under the titles")
    longest = 2 * len(tree.SKILLS) // 2 + len(tree.PROFICIENCIES) + 3
    check(tree.CARD_TOP - longest * tree.CARD_ROW > 60, "a card's skills and proficiencies fit without a scroll bar")
    check(tree.CARD_TOP - tree.GEAR_HEIGHT - 10 >= 60, "a card's gear stands above the button")
    needed = 40 + max(2 * len(branch) + len(tree.links(branch, tree.place(branch))) for branch in tree.layout())
    check(needed < tree.MAP_SLOTS, f"overlays of a branch fit the table of what they stand for ({needed})")


if __name__ == "__main__":
    test_branches()
    test_fits()
    print("ALL OK")
