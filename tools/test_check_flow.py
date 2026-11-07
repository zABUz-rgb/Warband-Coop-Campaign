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
from header_dialogs import anyone, plyr, repeat_for_parties  # noqa: E402
from header_presentations import prsntf_read_only  # noqa: E402
from header_operations import *  # noqa: E402,F403
from header_triggers import ti_on_presentation_load  # noqa: E402

from dplmc_fix.dialogs import LEAVE_TEXT, STUCK_STATES, leave_lines  # noqa: E402
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
    last = [anyone | plyr, "ask", [(eq, reg1, 2)], LEAVE_TEXT, "close_window", []]
    check("D4" not in rules(flow([HELLO, maybe, last])), "the last-resort line counts as always there")
    state = STUCK_STATES[0]
    asked = [anyone | plyr, state, [(eq, reg1, 1)], "Yes.", "close_window", []]
    made = leave_lines([asked])
    check(len(made) == 1 and made[0][0] == anyone | plyr and made[0][2][-1] == (eq, ":any", 0)
          and made[0][2].count((eq, reg1, 1)) == 1, "it is offered when the choices it copies all fail")
    listed = [anyone | plyr | repeat_for_parties, state, [(eq, reg1, 1)], "{s1}", "close_window", []]
    check(leave_lines([listed])[0][2] == [], "a repeating list always keeps it")
    spoken = [anyone, state, [(eq, reg1, 1)], "Yes.", "close_window", []]
    check(leave_lines([spoken])[0][:3] == [anyone, state, []], "an answer of the other side needs no test")
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


def test_hero_reads_what_it_writes():
    from coop.profile import PROFILE_IN, PROFILE_OUT, profile_scripts
    block = {s[0]: s[1] for s in profile_scripts}
    written = [op for op in block["coop_profile_build"] if isinstance(op, tuple) and op[:3] == (ops.troop_set_slot, PROFILE_OUT, ":at")]
    taken = [op for op in block["coop_profile_apply"] if isinstance(op, tuple) and op[0] == ops.troop_get_slot and op[2:4] == (PROFILE_IN, ":at")]
    check(len(written) == len(taken) == 38, f"a kept hero is read as it was written: {len(written)} and {len(taken)} kinds of number")


def test_town_events_ask_first():
    # 19:32, 1.11: a click nobody meant on the row under Native's arena called the friend at once
    from coop.mp_campaign import coop_mp_arena_option, coop_mp_tournament_option, coop_mp_training_option
    for option in (coop_mp_arena_option, coop_mp_tournament_option, coop_mp_training_option):
        check(option[3][0][0] == jump_to_menu, f"{option[0]}: one click calls nobody, a menu asks first")


def test_holders_apart():
    from coop.players import OFFER
    from coop.profile import PROFILE_IN, PROFILE_OUT
    from coop.together import NOTES, STORE
    from trail.marks import trail_holder, trail_slot_seq
    holders = [PROFILE_IN, PROFILE_OUT, NOTES, STORE, OFFER]
    check(len(set(holders)) == len(holders), f"no two buffers on one troop: {holders}")
    check(trail_holder not in (PROFILE_IN, PROFILE_OUT, STORE, OFFER), "the debug trail writes over no buffer that is read as items")
    check(trail_slot_seq >= 64, "the debug trail starts past the notes")


def test_item_numbers_checked():
    import module_scripts
    from module_constants import all_items_end
    block = {s[0]: s[1] for s in module_scripts.scripts}
    for name in ("coop_profile_apply", "custom_reply", "custom_mp_gear", "coop_store_show", "coop_mp_reply"):
        body = block[name]
        for at, op in enumerate(body):
            if isinstance(op, tuple) and op[0] in (troop_add_item, troop_set_inventory_slot) and op[-1 if op[0] == troop_set_inventory_slot else 2] == ":item":
                near = [o for o in body[max(0, at - 5):at] if isinstance(o, tuple) and ":item" in o and all_items_end in o]
                check(near, f"{name}: a number that comes from outside is looked at before the engine takes it as an item")


def test_tournament_teams():
    import module_scripts
    kills = next(s[1] for s in module_scripts.scripts if s[0] == "add_kill_death_counts")
    for team, count in ((":killer_agent_team", team_get_bot_kill_count), (":dead_agent_team", team_get_bot_death_count)):
        at = next(i for i, op in enumerate(kills) if isinstance(op, tuple) and op[0] == count)
        check(kills[at - 1] == (lt, team, 3), "the engine counts bots of three teams: the tournament's others stay out")


def test_victory_to_map():
    # 11-04: after the loot screen of a field battle the host's game never came back to the map; then, sent to the
    # map, the emptied beaten party stayed on it and a talk with it went black
    import module_game_menus
    block = next(m[4] for m in module_game_menus.game_menus if m[0] == "total_victory")
    at = block.index((val_add, "$g_total_victories", 1))
    check(block[at + 1:at + 4] == [leave_encounter, (call_script, "script_coop_remove_beaten", "$g_enemy_party"),
                                   change_screen_map], "a won field battle ends on the map, the beaten party gone")
    menu = next(m for m in module_game_menus.game_menus if m[0] == "simple_encounter")
    leave = next(o for o in menu[5] if o[0] == "encounter_leave")
    check(leave[3][-2:] == [leave_encounter, change_screen_map], "the encounter's Leave goes to the map")
    at = menu[4].index((eq, "$g_leave_encounter", 1))
    check(menu[4][at + 1:at + 3] == [leave_encounter, change_screen_map], "a talk ended with farewell goes to the map")
    empty = next(m for m in module_game_menus.game_menus if m[0] == "coop_empty_party")
    check(empty[4][-2:] == [leave_encounter, change_screen_map], "a party with nobody in it is no talk: back to the map")
    check([m[0] for m in module_game_menus.game_menus[-3:]] == ["coop_empty_party", "coop_fief_gift", "coop_siege_actions"],
          "the new menus are the last: saves keep the others")
    names = [m[0] for m in module_game_menus.game_menus]
    check(names.index("coop_mp_invite") < names.index("coop_custom_screen" if "coop_custom_screen" in names else "custom_screen")
          and names.index("coop_siege_actions") > names.index("coop_smith_shop"),
          "the joint actions at the walls come after every menu of 1.1 and 1.2.0 (11-07: they had moved 1.1's)")
    import module_scripts
    party_met = next(s[1] for s in module_scripts.scripts if s[0] == "game_event_party_encounter")
    check((jump_to_menu, "mnu_coop_empty_party") in party_met, "meeting an empty party opens that menu")


def test_own_caravan_talk():
    # 11-04: the host's own caravan got the talk of a party one attacks, and the game went out after it
    import module_dialogs
    starts = [d for d in module_dialogs.dialogs if d[1] == "start"]
    ours = next(i for i, d in enumerate(starts) if d[4] == "coop_cv_met")
    attacked = next(i for i, d in enumerate(starts) if d[3] == "What do you want?")
    check(ours < attacked, "a players' caravan has its own words, before the talk of a party one attacks")
    leave = [d for d in module_dialogs.dialogs if d[1] == "coop_cv_met"]
    check(len(leave) == 1 and leave[0][4] == "close_window" and (assign, "$g_leave_encounter", 1) in leave[0][5],
          "the caravan's talk ends with the encounter left")


def ops_of(block):
    """Every op of a block, nested lists flattened."""
    return [op for op in block if isinstance(op, tuple)]


def test_siege_and_waves():
    # 11-05: some of the garrison came behind doors no bot opens; both sides stood under the walls; the
    # armies came all at once (no reinforcements)
    from coop import mp
    from coop.constants import coop_mp_field_bots, coop_mp_mode_arena
    from header_common import reg0
    import coop_bridge
    import module_scripts
    import module_mission_templates
    check(sorted(mp.DEFENDER_ENTRIES) == sorted(mp.SIEGE_SCENES), "every Siege map has its garrison's spawn points")
    check(all(0 < len(e) <= 100 and max(e) <= 63 for e in mp.DEFENDER_ENTRIES.values()),
          "the points are the mission's and fit their slots")
    import siege_scenes
    if all((siege_scenes.SCENE_DIR / f"{s}.sco").exists() for s in mp.SIEGE_SCENES):
        check(siege_scenes.all_maps() == mp.DEFENDER_ENTRIES, "the points are what the scenes give (tools/siege_scenes.py)")
    else:
        print("skip  the game's scenes are not here: the points are not read again")
    block = {s[0]: s[1] for s in module_scripts.scripts}
    send = ops_of(block["coop_mp_send_bot"])
    picked = send.index((gt, "$coop_mp_entries_n", 0))
    native = send.index((call_script, "script_multiplayer_find_spawn_point", 0, 1, 0))
    check(picked < native, "the garrison spawns at those points; Native's only on a map without them")
    sent = [op for name in ("coop_mp_storm", "coop_mp_hold") for op in block[name] if isinstance(op, tuple)
            and op[0] == agent_set_scripted_destination]
    check(len(sent) >= 4, "the storming bots are sent up the walls and to the flag, the garrison to its posts")
    triggers = module_mission_templates.mission_templates
    bt = next(t for t in triggers if t[0] == "multiplayer_bt")[5]
    gate = [i for t in bt for i, op in enumerate(t[4]) if op == (call_script, "script_cf_coop_mp_may_end")]
    check(len(gate) == 1, "Battle's own end waits while reinforcements are to come")
    ours = mp.mp_battle_triggers
    siege_end = next(t for t in ours if (eq, "$coop_mp_mode", 1) in t[3])
    check((call_script, "script_coop_mp_reserves") in siege_end[4], "a siege counts the men still to come")
    field_end = next(t for t in ours if (eq, "$coop_mp_mode", 0) in t[3])
    check((call_script, "script_coop_mp_reserves") in field_end[4] and (call_script, "script_coop_mp_fallen") in field_end[4],
          "a field battle too, and a side that lost nobody is not beaten")
    events = [t for t in ours if (ge, "$coop_mp_mode", coop_mp_mode_arena) in t[3] and t[0] == 0]
    waves = [t for t in ours if (lt, "$coop_mp_mode", coop_mp_mode_arena) in t[3] and t[0] == 0]
    check(len(events) == 1 and len(waves) == 1, "a joint event spawns as before, a campaign battle by waves")
    check((call_script, "script_coop_mp_send_bot", reg0) in waves[0][4], "a wave takes the next stack's men")
    check(coop_bridge.MP_MAX_BOTS == 1500 and coop_mp_field_bots == 150, "1500 men a battle, 150 on the field at once")
    from coop.constants import coop_mp_max_stacks
    check(coop_bridge.MP_MAX_STACKS == coop_mp_max_stacks, "the bridge sends no more stacks than the server keeps")
    wave = next(t for t in ours if t[0] == 1 and (call_script, "script_coop_mp_reserves") in t[4]
                and (call_script, "script_coop_mp_tell_all") in t[4])
    check(any(isinstance(op, tuple) and op[0] == store_mission_timer_a for op in wave[4]),
          "the waves are told now and then, not each one")
    storm = next(t for t in ours if (call_script, "script_coop_mp_storm") in t[4])
    check((call_script, "script_coop_mp_hold") in storm[4], "the storm and the hold run together")


def test_storm_and_gift():
    # 11-05: walls stormed together went to nobody; a client could not start a storm; a fief could not be given
    import module_game_menus
    import module_scripts
    menus = {m[0]: m for m in module_game_menus.game_menus}
    scripts = {s[0]: s[1] for s in module_scripts.scripts}
    for name in ("castle_outside", "town"):
        check(any(o[0] == "coop_mp_storm" for o in menus[name][5]), f"{name}: a client may storm the walls together")
    siege = next(o for o in menus["castle_besiege"][5] if o[0] == "coop_mp_siege")
    check(not any(isinstance(op, tuple) and len(op) > 1 and op[1] == "$players_kingdom" for op in siege[1]),
          "the siege camp's storm asks no kingdom of a client")
    check(any(o[0] == "coop_fief_gift_meet" for o in menus["simple_encounter"][5]),
          "a fief is given to a friend met on the map")
    check(any(o[0].startswith("coop_pl_fief_") for o in menus["coop_players"][5]), "or from the players menu")
    capture = ops_of(scripts["coop_server_capture"])
    check((eq, ":kingdom", "fac_player_supporters_faction") in capture
          and (call_script, "script_coop_walls_cleared", ":center", ":kingdom") in capture,
          "walls go to the host's own realm too, and its enemies leave them")
    proxy = ops_of(scripts["coop_fief_proxy_set"])
    check((this_or_next | eq, ":faction", "fac_player_supporters_faction") in proxy,
          "a friend's stand-in may serve the host's own realm")
    host = scripts["coop_host_player_request"]
    url = next(op for op in host if isinstance(op, tuple) and op[0] == str_store_string and op[1] == 10)
    check("&rlm={reg10}&hw={reg11}" in url[2], "the host's game says its realm and whom it fights")
    taken = next(o for o in menus["coop_mp_wait"][5] if o[0] == "coop_mp_taken")
    check(any(isinstance(op, tuple) and op[:2] == (call_script, "script_coop_walls_cleared") for op in taken[3])
          or any(isinstance(op, tuple) and op[0] == call_script and op[1] == "script_coop_walls_cleared"
                 for op in ops_of(taken[3])), "the host's own capture sends its enemies out of the walls")


if __name__ == "__main__":
    test_dialogs()
    test_talks()
    test_menus()
    test_presentations()
    test_scripts()
    test_texts()
    test_data()
    test_john()
    test_hero_reads_what_it_writes()
    test_town_events_ask_first()
    test_holders_apart()
    test_item_numbers_checked()
    test_tournament_teams()
    test_victory_to_map()
    test_own_caravan_talk()
    test_siege_and_waves()
    test_storm_and_gift()
    test_real()
    print("all tests passed")
