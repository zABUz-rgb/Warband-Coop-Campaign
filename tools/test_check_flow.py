"""Tests for tools/check_flow.py: each rule on a small record of its own, then the real module.

    python -I tools/test_check_flow.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))
import header_operations as ops  # noqa: E402
from header_common import reg1  # noqa: E402
from header_dialogs import anyone, plyr  # noqa: E402
from header_presentations import prsntf_read_only  # noqa: E402
from header_operations import *  # noqa: E402,F403
from header_triggers import ti_on_presentation_load  # noqa: E402

import check_flow  # noqa: E402
from check_flow import Flow  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  ", msg)


def flow(dialogs=(), menus=(), presentations=(), scripts=()):
    return Flow(ops, [list(scripts), [], [], list(menus), list(presentations), [], list(dialogs), []], lambda r: True)


def rules(f):
    return sorted({finding[1] for finding in check_flow.run(f) if finding[0]})


HELLO = [anyone, "start", [], "Hello.", "ask", []]
BYE = [anyone | plyr, "ask", [], "Farewell.", "close_window", []]
LEAVE = ("leave", [], "Leave.", [(change_screen_map,)])
OPENED = ("opener", [(jump_to_menu, "mnu_m")])


def test_dialogs():
    check(rules(flow([HELLO, BYE])) == [], "a talk with a way out passes")
    check(rules(flow([[anyone, "start", [], "Hello.", "gone", []]])) == ["D1"], "a state with no line")
    check("D2" in rules(flow([HELLO, BYE, [anyone, "orphan", [], "Nobody hears this.", "close_window", []]])), "lines nothing leads to")
    second = [anyone, "start", [], "Never.", "ask", []]
    check("D3" in rules(flow([HELLO, second, BYE])), "a line behind one that always holds")
    check("D3" not in rules(flow([[anyone, "start", [(eq, "$x", 1)], "Maybe.", "ask", []], HELLO, BYE])), "a test before it leaves it alive")
    maybe = [anyone | plyr, "ask", [(eq, "$x", 1)], "Yes.", "close_window", []]
    check("D4" in rules(flow([HELLO, maybe])), "every line may fail")
    other = [anyone | plyr, "ask", [(neq, "$x", 1)], "No.", "close_window", []]
    check("D4" not in rules(flow([HELLO, maybe, other])), "a test and its opposite cover everything")
    either = [anyone | plyr, "ask", [(this_or_next | eq, "$x", 1), (eq, "$y", 1)], "Yes.", "close_window", []]
    both = [anyone | plyr, "ask", [(neq, "$x", 1), (neq, "$y", 1)], "No.", "close_window", []]
    check("D4" not in rules(flow([HELLO, either, both])), "or-chains count as well")
    check("D6" in rules(flow([HELLO, [anyone | plyr, "ask", [], "Hm.", "more", []], [anyone | plyr, "more", [], "Bye.", "close_window", []]])),
          "a player's line with no answer")


def test_talks():
    john = 5
    opener = ("opener", [(start_map_conversation, john)])
    line = [anyone, "event_triggered", [(eq, "$g_talk_troop", john)], "Yes?", "close_window", []]
    check("D5" in rules(flow([HELLO, BYE], scripts=[opener])), "a talk opened with no line for them (John's error)")
    check("D5" not in rules(flow([HELLO, BYE, line], scripts=[opener])), "a line naming the troop answers")
    swapped = ("opener", [(change_screen_map_conversation, john)])
    check("D5" in rules(flow([line], scripts=[swapped])), "change_screen_map_conversation wants state start")


def test_menus():
    def menu(name="m", load=(), options=(LEAVE,)):
        return (name, 0, "text", "none", list(load), list(options))

    check(rules(flow(menus=[menu()], scripts=[OPENED])) == [], "a menu with a way out passes")
    check("M1" in rules(flow(menus=[menu(options=())], scripts=[OPENED])), "no options")
    check("M1" not in rules(flow(menus=[menu(load=[(change_screen_map,)], options=())], scripts=[OPENED])), "none needed when the load leaves")
    hidden = ("o", [(eq, "$x", 1)], "Maybe.", [])
    check("M2" in rules(flow(menus=[menu(options=[hidden])], scripts=[OPENED])), "every option may hide")
    check("M3" in rules(flow(menus=[menu()])), "a menu nothing opens")
    a, b = menu("a", [(jump_to_menu, "mnu_b")]), menu("b", [(jump_to_menu, "mnu_a")])
    check("M4" in rules(flow(menus=[a, b])), "two menus jumping to each other for ever")
    c = menu("c", [(eq, "$x", 1), (jump_to_menu, "mnu_d")])
    d = menu("d", [(jump_to_menu, "mnu_c")])
    found = [f for f in check_flow.run(flow(menus=[c, d])) if f[1] == "M4"]
    check(found and not found[0][0], "a test on the way makes it a note")
    through = ("hop", [(jump_to_menu, "mnu_e")])
    e = menu("e", [(call_script, "script_hop")])
    check("M4" in rules(flow(menus=[e], scripts=[through])), "through a script too")


def test_presentations():
    def screen(*ops_, flags=0):
        return ("p", flags, 0, [(ti_on_presentation_load, list(ops_))])

    closes = (presentation_set_duration, 0)
    check(rules(flow(presentations=[screen(closes)])) == [], "a presentation that closes passes")
    check("P1" in rules(flow(presentations=[screen(closes, (start_presentation, "prsnt_p"))])), "closed and started in one go")
    check("P2" in rules(flow(presentations=[screen((presentation_set_duration, 999999))])), "nothing closes it")
    check("P2" not in rules(flow(presentations=[screen((presentation_set_duration, 999999), flags=prsntf_read_only)])), "a read-only one needs no closing")
    check("P3" in rules(flow(presentations=[screen((set_container_overlay, 5), closes)])), "a container left open")
    check("P3" not in rules(flow(presentations=[screen((set_container_overlay, 5), (set_container_overlay, -1), closes)])), "a container put back")
    check("P4" in rules(flow(presentations=[screen((position_set_x, 1, 10), closes)])), "a position before the multiplier")
    check("P4" not in rules(flow(presentations=[screen((set_fixed_point_multiplier, 1000), (position_set_x, 1, 10), closes)])), "after it")


def test_scripts():
    two = ("two", [(store_script_param, ":a", 1), (store_script_param, ":b", 2)])
    check(rules(flow(scripts=[two, ("c", [(call_script, "script_two", 1, 2)])])) == [], "the right arguments pass")
    check("S1" in rules(flow(scripts=[two, ("c", [(call_script, "script_two", 1)])])), "too few arguments")
    check("S2" in rules(flow(scripts=[two, ("c", [(call_script, "script_two", 1, 2, 3)])])), "too many arguments")
    loop = [("a", [(call_script, "script_b")]), ("b", [(call_script, "script_a")])]
    check("S3" in rules(flow(scripts=loop)), "scripts calling themselves")


def test_texts():
    shown = ("m", 0, "You have {reg1}.", "none", [], [LEAVE])
    check("V1" in rules(flow(menus=[shown], scripts=[OPENED])), "a register nothing sets")
    filled = ("m", 0, "You have {reg1}.", "none", [(assign, reg1, 3)], [LEAVE])
    check("V1" not in rules(flow(menus=[filled], scripts=[OPENED])), "set on load")
    by_script = ("m", 0, "You have {reg1}.", "none", [(call_script, "script_fill")], [LEAVE])
    check("V1" not in rules(flow(menus=[by_script], scripts=[OPENED, ("fill", [(assign, reg1, 3)])])), "set by a script it calls")
    line = [anyone, "start", [], "It is {s1}.", "ask", []]
    check("V1" in rules(flow([line, BYE])), "in a line too")
    fills = [anyone, "start", [(str_store_string, 1, "@x")], "It is {s1}.", "ask", []]
    check("V1" not in rules(flow([fills, BYE])), "a string set by the line's test")


def test_data():
    check(list(check_flow.rule_slots({"slot_town_a": 5}, {"slot_party_b": 5})), "a party slot on a town slot")
    check(not list(check_flow.rule_slots({"slot_troop_a": 5}, {"slot_party_b": 5})), "other families may share a number")
    import coop_bridge
    constants = check_flow.constants_of("coop.constants", "custom_troops.constants", "trail.marks")
    check(not list(check_flow.rule_bridge(coop_bridge, constants, ["/cli?seq=1&h=2"])), "the bridge and the game agree")
    check(list(check_flow.rule_bridge(coop_bridge, dict(constants, coop_kind_lair=9), [])), "a kind apart is found")
    check(list(check_flow.rule_bridge(coop_bridge, dict(constants, custom_kinds=5), [])), "the army's size apart is found")
    check(list(check_flow.rule_bridge(coop_bridge, constants, ["&nosuchword=1"])), "a word the bridge never reads")


def test_john():
    """On the real records: the mod's talks have their lines, and the mistake that gave John Blackborn's
    error (a talk opened in the state where he has none) would stop the build."""
    from check_module import load
    real_ops, *lists = load()
    real = Flow(real_ops, lists, lambda r: True)
    check(not [f for f in check_flow.rule_talks(real) if "trp_tutorial_trainer" in f[3]], "John's talk has its lines")
    wrong = ("wrong", [(start_map_conversation, "trp_tutorial_trainer")])
    mistaken = Flow(real_ops, [lists[0] + [wrong]] + lists[1:], lambda r: True)
    check(any("trp_tutorial_trainer" in f[3] for f in check_flow.rule_talks(mistaken)), "opened the old way, the check says so")


def test_real():
    done = subprocess.run([sys.executable, str(ROOT / "tools" / "check_flow.py")], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=ROOT)
    check(done.returncode == 0, "the real module has nothing wrong: " + done.stdout[-300:])


if __name__ == "__main__":
    test_dialogs()
    test_talks()
    test_menus()
    test_presentations()
    test_scripts()
    test_texts()
    test_data()
    test_john()
    test_real()
    print("all tests passed")
