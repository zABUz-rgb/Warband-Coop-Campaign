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


# Camp menu: co-op roles (prototype; the bridge is tools/coop_bridge.py)
camp_coop_options = [
  ("coop_role_server", [(eq, "$coop_role", coop_role_single)], "CoopWorld: run this game as the WORLD SERVER.",
   [(call_script, "script_coop_become_server"), (change_screen_return)]),
  # a client game that loaded the held server's save starts in the held role: it may switch at once
  ("coop_role_client", [(this_or_next|eq, "$coop_role", coop_role_single), (eq, "$coop_role", coop_role_held)],
   "CoopWorld: run this game as a CLIENT.",
   [(call_script, "script_coop_become_client"), (change_screen_return)]),
  ("coop_role_hold", [(eq, "$coop_role", coop_role_server)],
   "CoopWorld: hold the world for a joining client.",
   [(call_script, "script_coop_server_hold"), (change_screen_return)]),
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
  menu_options(menus, "camp")[0:0] = camp_coop_options
  # joint battles on the multiplayer server
  from coop.mp_campaign import mp_campaign_menus, coop_mp_encounter_option
  options = menu_options(menus, "simple_encounter")
  options.insert(find_by_id(options, "encounter_leave"), coop_mp_encounter_option)
  menus.extend(mp_campaign_menus)
