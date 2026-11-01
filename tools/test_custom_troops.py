"""Tests for src/custom_troops: the player's own army, from the build's real troops and items.

    python -I tools/test_custom_troops.py
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
from header_items import *  # noqa: E402,F403
from header_troops import tf_guarantee_horse, tf_guarantee_ranged, tf_mounted  # noqa: E402
from custom_troops import constants as c, dialogs, game_menus, item_tiers, presentations, scripts, stats  # noqa: E402
from custom_troops.constants import BRANCH_NAMES, KINDS, LEVELS, TIERS, kind_of, troop_id  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  ", msg)


def built():
    from module_items import items
    from module_troops import troops
    return troops, items


def test_troops():
    troops, _ = built()
    ids = [t[0] for t in troops]
    first = ids.index(troop_id(0, 1))
    check(len(KINDS) * len(LEVELS) == 39, "39 soldiers")
    for kind in range(len(KINDS)):
        for level in LEVELS:
            check(ids[first + 3 * kind + level - 1] == troop_id(kind, level), "")
    check("custom_army" in ids, "the army's name has a troop to live on")
    check(ids.index("custom_army") == first + 39, "the new troops stand last: the old ones keep their numbers")
    check(c.custom_first == "trp_" + ids[first], "the scripts count from the first of them")
    check(len(KINDS) - 1 == len(BRANCH_NAMES) * len(TIERS), "a recruit, then three branches of four tiers")
    for branch, start in zip(BRANCH_NAMES, range(1, len(KINDS), len(TIERS))):
        check(kind_of(branch, 2) == start, "")
        check(kind_of(branch, 5) % len(TIERS) == 0, f"a {branch} soldier of tier 5 ends its branch, as the scripts count it")
    check(c.custom_kinds == len(KINDS) and len(c.custom_kind_labels) == len(KINDS), "each kind has a line on the names screen")


def test_upgrades():
    troops, _ = built()
    by_id = {t[0]: t for t in troops}

    def path(troop):
        return [troops[n][0] for n in by_id[troop][14:16] if n > 0]

    for level in LEVELS:
        check(path(troop_id(0, level)) == [troop_id(kind_of("inf", 2), 1), troop_id(kind_of("arc", 2), 1)],
              f"a recruit of level {level} grows into footmen and archers")
    for branch in BRANCH_NAMES:
        for tier in TIERS:
            for level in LEVELS:
                wanted = [] if tier == 5 else [troop_id(kind_of(branch, tier + 1), 1)]
                if tier == 2 and branch != "cav":
                    wanted.append(troop_id(kind_of("cav", 2), 1))
                check(path(troop_id(kind_of(branch, tier), level)) == wanted, "")
    print("ok   a tier's three levels share one way up, and militia on foot may rise to the riders")
    check(all(by_id[troop_id(kind_of("cav", t), 1)][3] & tf_mounted for t in TIERS), "riders ride")
    check(not by_id[troop_id(0, 1)][3] & tf_mounted, "recruits walk")


def test_training_field():
    troops, _ = built()
    by_id = {t[0]: t for t in troops}
    for kind, (_, tier, branch) in enumerate(KINDS):
        for level in LEVELS:
            flags = by_id[troop_id(kind, level)][3]
            check(bool(flags & tf_guarantee_horse) == (branch == "cav"), "")
            check(bool(flags & tf_guarantee_ranged) == (branch == "arc"), "")
    print("ok   the training field takes a footman for a footman: only riders and archers get a quarter in melee")


def test_levels_leave_tiers():
    options = game_menus.train_options()
    check([o[0] for o in options] == ["custom_train_1", "custom_train_2", "custom_train_none"],
          "John's menu holds the picked soldier's levels 2 and 3 and nothing else")
    calls = [(name, op) for name, ops in scripts.scripts for op in ops if isinstance(op, tuple) and "script_custom_swap" in op]
    check([name for name, _ in calls] == ["custom_train"], "only training changes a soldier's troop by script")
    train = dict(scripts.scripts)["custom_train"]
    made = [op for op in train if isinstance(op, tuple) and "script_custom_troop" in op]
    check([op[2] for op in made] == [":kind", ":kind"], "and it stays within the kind, so within the tier")


def test_stats():
    troops, items = built()
    by_id = {t[0]: t for t in troops}
    worth = stats.averages(troops, items)
    check(len(worth) == len(KINDS), "an average for every kind")
    first_skill = 1 + stats.ATTRIBUTES + stats.PROFICIENCIES
    for kind, (_, tier, branch) in enumerate(KINDS):
        row = {level: stats.numbers(by_id[troop_id(kind, level)]) for level in LEVELS}
        mean = worth[(tier, branch)]
        check(row[1][0] == row[2][0] == row[3][0], f"{KINDS[kind][0]}: its levels take the same to rise")
        for k in range(1, len(mean)):
            check(row[1][k] <= row[2][k] <= row[3][k], "")
            if mean[k] >= 5 and k < first_skill:
                check(abs(row[1][k] - 0.8 * mean[k]) <= 1, "")
                check(abs(row[2][k] - mean[k]) <= 1, "")
                check(abs(row[3][k] - 1.1 * mean[k]) <= 1, "")
    check(all(v <= 10 for k in range(len(KINDS)) for v in stats.numbers(by_id[troop_id(k, 3)])[first_skill:]), "no skill above 10")
    for branch in BRANCH_NAMES:
        for tier in TIERS[:-1]:
            low, high = worth[(tier, branch)], worth[(tier + 1, branch)]
            check(all(a <= b for a, b in zip(low, high)), f"{branch}: tier {tier + 1} is no worse than tier {tier}")
    t5 = stats.numbers(by_id[troop_id(kind_of("cav", 5), 2)])
    t1 = stats.numbers(by_id[troop_id(0, 2)])
    print("     recruit:", t1[:5], "rider of tier 5:", t5[:5])
    check(t5[1] > t1[1] and t5[0] > t1[0], "tier 5 stands far above a recruit")
    check(stats.numbers(by_id[troop_id(kind_of("cav", 4), 1)])[first_skill + 31] == 0, "no stray number from the header")


def test_gear():
    troops, items = built()
    by_id = {t[0]: t for t in troops}
    for kind, (_, tier, branch) in enumerate(KINDS):
        gear = [items[n] for n in by_id[troop_id(kind, 1)][7]]
        check(len(gear) <= c.custom_gear_max, "")
        check(sum(1 for i in gear if i[3] & 0xFF == itp_type_body_armor) == 1, "")  # noqa: F405
        check(any(i[3] & 0xFF == itp_type_horse for i in gear) == (branch == "cav"), "")  # noqa: F405
        check(any(i[3] & 0xFF == itp_type_bow for i in gear) == (branch == "arc"), "")  # noqa: F405
    print("ok   only riders have horses, only archers bows")


def test_items():
    _, items = built()
    lists = item_tiers.tier_lists(items)
    sets = [set(x) for x in lists]
    by_id = {i[0]: i for i in items}
    check(len(lists) == 5, "five lists")
    check(all(a < b for a, b in zip(sets, sets[1:])), f"each tier adds to the one before: {[len(x) for x in lists]}")
    check(all(len(set(x)) == len(x) for x in lists), "no item twice")
    share = len(lists[3]) * 100 / len(lists[4])
    check(share >= 90, f"tier 4 has 90% of the game's items ({share:.0f}%)")
    for name in lists[0]:
        item = by_id[name]
        kind = item[3] & 0xFF
        check(kind != itp_type_body_armor or item[5] <= 320, "")  # noqa: F405
        check(kind != itp_type_horse or item[5] <= 240, "")  # noqa: F405
    for name in ("mail_hauberk", "great_sword", "plate_armor", "heavy_lance"):
        if name in by_id:
            check(name not in sets[0], f"tier 1 has no {name}")
    for name in lists[4]:
        item = by_id[name]
        check(not item[3] & itp_unique, "")  # noqa: F405
        check(len(item) <= 9 or not item[9], "")
        check(item[3] & itp_merchandise, "")  # noqa: F405
    tiers = item_tiers.first_tiers(lists)
    check(all(tiers[n] == 1 for n in lists[0]), "a tier 1 item stands at tier 1")
    check(set(tiers) == sets[4], "every item has its tier")
    sorts = {t for _, t in presentations.CATEGORIES}
    check({by_id[n][3] & 0xFF for n in lists[4]} <= sorts, "the gear screen has a list for every sort of item")
    check(presentations.CATEGORIES[-1][1] == itp_type_horse, "horses last: only riders see them")  # noqa: F405
    check(presentations.RIDERS_FROM == kind_of("cav", 2), "the screen knows riders by their kind")


def test_own_gear():
    names = [s[0] for s in scripts.scripts]
    check("custom_gear_spread" not in names and "custom_gear_climb" not in names, "a purchase stays with its tier")
    buy = dict(scripts.scripts)["custom_buy"]
    changes = [op for op in buy if isinstance(op, tuple) and "script_custom_item_change" in op]
    check(len(changes) == 1 and changes[0][2] == ":kind", "it goes on the kind that was picked, on nobody else")


def test_prices():
    check(c.custom_recruits == (5, 10, 20) and c.custom_recruit_cost == 20, "5, 10 or 20 men at 20 dinars")
    check(c.custom_train_cost[1] == (3000, 5000) and c.custom_train_cost[5] == (30000, 40000), "training as ordered")
    check(all(a < b for a, b in c.custom_train_cost.values()), "level 3 costs more than level 2")
    check(all(c.custom_train_cost[t][1] <= c.custom_train_cost[t + 1][0] for t in range(1, 5)), "and a higher tier more")


def test_dialogs():
    lines = dialogs.dialogs
    froms = {d[1] for d in lines}
    tos = {d[4] for d in lines}
    check(tos - froms == {"close_window"}, f"every line leads on: {tos - froms}")
    check(froms - tos == {"start"}, f"every line can be reached: {froms - tos}")
    main = [d for d in lines if d[1] == "custom_main"]
    check(any(d[3] == "Sorry, there is nothing I can do for you." for d in lines), "a client without an army is told so")
    starts = [d for d in lines if d[1] == "start"]
    check(len(starts) == 3 and all(d[2][:2] == dialogs.JOHN for d in starts), "John's lines are his alone")
    check(starts[-1][2] == dialogs.JOHN, "and the one with no other condition comes last")
    renames = [d for d in main if "rename" in d[3]]
    check(len(renames) == 1 and renames[0][2] == dialogs.NOT_CLIENT, "one line to rename, for the host only")
    what = [d for d in lines if d[1] == "custom_rename_what"]
    check([d[5][0][2] for d in what[:2]] == [c.custom_screen_soldiers, c.custom_screen_company], "the army and the company apart")
    pick = [d for d in lines if d[1] == "custom_pick"]
    check([d[4] for d in pick] == ["close_window", "custom_tiers", "custom_tiers", "custom_tiers", "custom_what"],
          "the recruit is picked at once, a branch asks for its tier")
    check(len([d for d in lines if d[1] == "custom_pick_tier"]) == len(TIERS) + 1, "all four tiers, or someone else")
    for branch, name in enumerate(BRANCH_NAMES):
        check(1 + branch * len(TIERS) == kind_of(name, 2), "")  # as script_custom_tier_kind counts it
    check(all(d[4] == "custom_who" for d in main if "gear" in d[3] or "stats" in d[3] if d[2] == dialogs.HAS_MEN),
          "gear and training both ask whom")
    check(len([d for d in lines if d[1] == "custom_buy_many"]) == 4, "5, 10, 20, or nothing")


if __name__ == "__main__":
    test_troops()
    test_upgrades()
    test_training_field()
    test_levels_leave_tiers()
    test_stats()
    test_gear()
    test_items()
    test_own_gear()
    test_prices()
    test_dialogs()
    print("all tests passed")
