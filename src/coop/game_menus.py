from header_common import *
from header_operations import *
from header_game_menus import *
from module_constants import *
from coop.constants import *

# Turned out for not paying: the gates stay closed until dawn.
# Uses Native's $g_leave_town branch further down the town menu to leave.
town_ban_check = [
  (try_begin),
    (eq, "$coop_ban_center", "$current_town"),
    (store_current_hours, ":now"),
    (lt, ":now", "$coop_ban_until"),
    (str_store_party_name, s1, "$current_town"),
    (display_message, "@The gates of {s1} are closed to you until dawn.", 0xFF6666),
    (assign, "$g_leave_town", 1),
  (try_end),
]

# Entering a peaceful town = taking lodgings: time passes at once (like Native "Wait here");
# clicking the map ends the rest and opens the town menu. Paid nightly by Native's accommodation trigger.
town_auto_lodging = [
  (try_begin),
    (eq, "$coop_lodging_started", 0),
    (eq, "$g_leave_town", 0),
    (eq, "$freelancer_state", 0),
    (eq, "$g_defending_against_siege", 0),
    (eq, "$sneaked_into_town", 0),
    (eq, "$quest_auto_menu", 0),
    (party_slot_eq, "$current_town", slot_party_type, spt_town),
    (store_faction_of_party, ":town_faction", "$current_town"),
    (store_relation, ":relation", ":town_faction", "fac_player_supporters_faction"),
    (ge, ":relation", 0),
    (assign, "$coop_lodging_started", 1),
    (str_store_party_name, s1, "$current_town"),
    (display_message, "@You take lodgings in {s1}. Time passes while you stay; click to walk the town."),
    (assign, "$auto_enter_town", "$current_town"),
    (assign, "$g_town_visit_after_rest", 1),
    (assign, "$g_last_rest_center", "$current_town"),
    (assign, "$g_last_rest_payment_until", -1),
    (rest_for_hours_interactive, 24 * 7, coop_world_time_speed, 0), #rest while not attackable
    (assign, "$coop_menu_hours", -2), #our own rest: time flows, it is not a menu
    (change_screen_return),
  (try_end),
]


# Camp - CoopWorld: the co-op menu (roles, the other players, news); the bridge is tools/coop_bridge.py
coop_role_text = [
  (try_begin),
    (eq, "$coop_role", coop_role_client),
    (str_store_string, s1, "@a CLIENT (your hero in the host's world)"),
  (else_try),
    (eq, "$coop_role", coop_role_server),
    (eq, "$coop_srv_player", 1),
    (str_store_string, s1, "@the HOST (the world lives in this game, you play in it)"),
  (else_try),
    (eq, "$coop_role", coop_role_server),
    (str_store_string, s1, "@the WORLD SERVER only"),
  (else_try),
    (eq, "$coop_role", coop_role_held),
    (gt, "$coop_hold_alive", 0),
    (str_store_string, s1, "@the HOST, the world HELD for a joining friend"),
  (else_try),
    (eq, "$coop_role", coop_role_held),
    (str_store_string, s1, "@the host's held save: choose CLIENT to join the host's world"),
  (else_try),
    (str_store_string, s1, "@off (an ordinary single player game)"),
  (try_end),
]

camp_coop_options = [
  ("coop_role_host", [(eq, "$coop_role", coop_role_single)],
   "CoopWorld: run this game as the WORLD SERVER and play in it (host).",
   [(call_script, "script_coop_become_server", 1), (change_screen_return)]),
  ("coop_role_server", [(eq, "$coop_role", coop_role_single)],
   "CoopWorld: run this game as the WORLD SERVER only (unattended).",
   [(call_script, "script_coop_become_server", 0), (change_screen_return)]),
  # a friend's game that loaded the held host's save starts in the held role and switches at once;
  # the host's own held game (the bridge answers it) gets the choices of a host instead
  # (two options: this_or_next joins only the two conditions it stands between, so "single, or held
  # and not the host" cannot be one condition list; as one it hid the choice in every single game
  # whose save had seen a hold)
  ("coop_role_client", [(eq, "$coop_role", coop_role_single)],
   "CoopWorld: run this game as a CLIENT.",
   [(call_script, "script_coop_become_client"), (change_screen_return)]),
  ("coop_role_client_held", [(eq, "$coop_role", coop_role_held), (le, "$coop_hold_alive", 0)],
   "CoopWorld: run this game as a CLIENT.",
   [(call_script, "script_coop_become_client"), (change_screen_return)]),
  ("coop_role_hold", [(eq, "$coop_role", coop_role_server)],
   "CoopWorld: hold the world for a joining client.",
   [(call_script, "script_coop_server_hold"), (change_screen_return)]),
  ("coop_role_resume", [(eq, "$coop_role", coop_role_held), (gt, "$coop_hold_alive", 0)],
   "CoopWorld: let the world run again (stop holding it).",
   [(assign, "$coop_role", coop_role_server),
    (display_message, "@CoopWorld: the world runs again.", 0x66CCFF),
    (change_screen_return)]),
  ("coop_take_spoils", [(this_or_next|eq, "$coop_role", coop_role_client), (eq, "$coop_srv_player", 1),
                        (eq, "$coop_loot_ready", 1), (neq, "$g_player_is_captive", 1)],
   "CoopWorld: take your share of the spoils of the joint battle.",
   [(call_script, "script_coop_client_mp_loot_take")]),
  ("coop_read_news", [(eq, "$coop_role", coop_role_server), (eq, "$coop_srv_player", 1),
                      (call_script, "script_coop_count_news"), (gt, reg0, 0)],
   "CoopWorld: read the news held back ({reg0}). The world waits meanwhile.",
   [(assign, "$coop_read_news", 1), (store_current_hours, "$coop_news_since"), (change_screen_return)]),
  # a way out if the camp does not let the player back to the map (a battle's state left behind)
  ("coop_to_map", [(neq, "$coop_role", coop_role_single)], "CoopWorld: back to the map (if the camp keeps you here).",
   [(assign, "$auto_menu", -1), (assign, "$g_camp_mode", 0), (leave_encounter), (change_screen_map)]),
  ("coop_role_stop", [(neq, "$coop_role", coop_role_single)], "CoopWorld: stop co-op.",
   [(call_script, "script_coop_stop"), (change_screen_return)]),
]


def merge(menus):
  from coop_merge import menu_block, insert_after, find_line, find_by_id, MergeError
  block = menu_block(menus, "town")
  insert_after(block, (store_encountered_party, "$current_town"), town_ban_check)
  pos = find_line(block, (eq, "$g_leave_town", 1)) - 1
  if block[pos] != (try_begin):
    raise MergeError("town menu: expected try_begin before the $g_leave_town check")
  block[pos:pos] = town_auto_lodging
  from coop_merge import menu_options
  coop_camp = list(camp_coop_options)
  menu_options(menus, "camp")[0:0] = [
    ("coop_camp", [], "CoopWorld: co-op...", [(jump_to_menu, "mnu_coop_camp")]),
  ]
  menus.append(
    ("coop_camp", 0, "CoopWorld: co-op.^^This game is {s1}.", "none", coop_role_text, coop_camp))
  # joint battles on the multiplayer server
  from coop.mp_campaign import mp_campaign_menus, coop_mp_encounter_option, coop_mp_siege_option
  from coop.mp_campaign import coop_mp_defend_option
  menu_options(menus, "town").insert(0, coop_mp_defend_option)
  outside = menu_options(menus, "castle_outside")
  outside.insert(find_by_id(outside, "castle_leave"), coop_mp_defend_option)
  siege = menu_options(menus, "castle_besiege")
  siege.insert(find_by_id(siege, "castle_lead_attack") + 1, coop_mp_siege_option)
  # meeting another player's party opens the encounter menu with the co-op choices at once: Native
  # would talk to its leader first, and a friendly talk ends the encounter before the menu shows
  from coop.triggers import puppet_range as _puppets
  encounter = menu_block(menus, "simple_encounter")
  talk = find_line(encounter, (call_script, "script_setup_party_meeting", "$g_encountered_party"))
  first_puppet, end_puppet = _puppets()
  encounter[talk:talk + 1] = [
    (try_begin),
      (neg | is_between, "$g_encountered_party", first_puppet, end_puppet),
      encounter[talk],
    (try_end),
  ]
  options = menu_options(menus, "simple_encounter")
  options.insert(find_by_id(options, "encounter_leave"), coop_mp_encounter_option)
  # another player's party is fought only in a joint battle, never in a local one against its puppet
  from coop.triggers import puppet_range
  first, end = puppet_range()
  for option_id in ("encounter_attack", "encounter_order_attack"):
    options[find_by_id(options, option_id)][1].insert(0, (neg | is_between, "$g_encountered_party", first, end))
  menus.extend(mp_campaign_menus)
  # players together: joining a player's party, giving troops
  from coop.players import players_menus, encounter_options, camp_options
  options.insert(find_by_id(options, "encounter_leave"), encounter_options()[0])
  options.insert(find_by_id(options, "encounter_leave"), encounter_options()[1])
  menus.extend(players_menus)
  stop = find_by_id(coop_camp, "coop_role_stop")
  coop_camp[stop:stop] = camp_options()
  coop_camp.append(("coop_camp_back", [], "Back.", [(jump_to_menu, "mnu_camp")]))
