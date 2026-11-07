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
    # the host's save loaded on another PC: no bridge of a host answers this game
    (this_or_next|eq, "$coop_role", coop_role_server),
    (eq, "$coop_role", coop_role_held),
    (le, "$coop_hold_alive", 0),
    (str_store_string, s1, "@a copy of the host's save: choose CLIENT to join the host's world"),
  (else_try),
    (eq, "$coop_role", coop_role_server),
    (eq, "$coop_srv_player", 1),
    (str_store_string, s1, "@the HOST (the world lives in this game, you play in it)"),
  (else_try),
    (eq, "$coop_role", coop_role_server),
    (str_store_string, s1, "@the WORLD SERVER only"),
  (else_try),
    (eq, "$coop_role", coop_role_held),
    (str_store_string, s1, "@the HOST, the world HELD for a joining friend"),
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
  ("coop_role_client_held", [(this_or_next|eq, "$coop_role", coop_role_server), (eq, "$coop_role", coop_role_held),
                             (le, "$coop_hold_alive", 0)],
   "CoopWorld: run this game as a CLIENT.",
   [(call_script, "script_coop_become_client"), (change_screen_return)]),
  ("coop_role_hold", [(eq, "$coop_role", coop_role_server), (gt, "$coop_hold_alive", 0)],
   "CoopWorld: hold the world for a joining client.",
   [(call_script, "script_coop_server_hold"), (change_screen_return)]),
  ("coop_role_resume", [(eq, "$coop_role", coop_role_held), (gt, "$coop_hold_alive", 0)],
   "CoopWorld: let the world run again (stop holding it).",
   [(assign, "$coop_role", coop_role_server),
    (display_message, "@CoopWorld: the world runs again.", 0x66CCFF),
    (change_screen_return)]),
  ("coop_take_spoils", [(this_or_next|eq, "$coop_role", coop_role_client), (eq, "$coop_srv_player", 1),
                        (eq, "$coop_loot_ready", 1), (neq, "$g_player_is_captive", 1)],
   "CoopWorld: take your share of the spoils of the joint battle (then back to the map).",
   [(assign, "$coop_loot_step", 1), (jump_to_menu, "mnu_coop_loot")]),
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
  from coop.mp_campaign import coop_mp_lord_option, coop_mp_storm_option
  from coop.mp_campaign import coop_mp_lord_siege_option, coop_mp_lord_defend_option
  from coop.mp_campaign import coop_mp_arena_option, coop_mp_tournament_option, coop_mp_training_option
  menu_options(menus, "world_map_soldier")[0:0] = [coop_mp_lord_option, coop_mp_lord_siege_option,
                                                   coop_mp_lord_defend_option]
  # a besieged town or castle: joint actions - hold the walls or storm them beside the besiegers (11-07). They take
  # the place of the defence alone (coop_mp_defend) and of the storm beside friendly besiegers (coop_mp_join_siege).
  from coop.mp_campaign import coop_siege_actions_option
  town = menu_options(menus, "town")
  town.insert(0, coop_siege_actions_option("town"))
  town.insert(1, coop_mp_storm_option) #a client at peace here in its own game, its friends not
  town.insert(find_by_id(town, "join_tournament") + 1, coop_mp_tournament_option)
  town.insert(find_by_id(town, "town_arena") + 1, coop_mp_arena_option)
  training = menu_options(menus, "training_ground")
  training.insert(find_by_id(training, "camp_train_melee") + 1, coop_mp_training_option)
  outside = menu_options(menus, "castle_outside")
  outside.insert(find_by_id(outside, "castle_leave"), coop_siege_actions_option("castle_outside"))
  outside.insert(find_by_id(outside, "castle_leave"), coop_mp_storm_option)
  # a siege of the world by a friendly kingdom: the players may storm with the besiegers (on the attackers' side)
  sighted = menu_options(menus, "join_siege_outside")
  sighted.insert(find_by_id(sighted, "leave"), coop_siege_actions_option("join_siege_outside"))
  allies = menu_options(menus, "besiegers_camp_with_allies")
  allies.insert(find_by_id(allies, "join_siege_with_allies") + 1, coop_siege_actions_option("besiegers_camp_with_allies"))
  siege = menu_options(menus, "castle_besiege")
  siege.insert(find_by_id(siege, "castle_lead_attack") + 1, coop_mp_siege_option)
  # meeting another player's party opens the encounter menu with the co-op choices at once: Native
  # would talk to its leader first, and a friendly talk ends the encounter before the menu shows
  from coop.triggers import puppet_range as _puppets
  encounter = menu_block(menus, "simple_encounter")
  talk = find_line(encounter, (call_script, "script_setup_party_meeting", "$g_encountered_party"))
  first_puppet, end_puppet = _puppets()
  # the party that took this player prisoner a moment ago (script_coop_truce_begin): no talk, no new
  # capture; the encounter ends at once (11-06: the escaped player was met and taken again)
  encounter[talk:talk + 1] = [
    (try_begin),
      (call_script, "script_cf_coop_truce_party"),
      (eq, reg0, "$g_encountered_party"),
      (str_store_party_name, s1, "$g_encountered_party"),
      (display_message, "@CoopWorld: {s1} let you go only lately and leaves you alone for now.", 0xFFDD66),
      (leave_encounter),
      (change_screen_map),
    (else_try),
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
  # a client's battle of its own game holds the world (fight=1); its menus and talks no longer do (11-07)
  options[find_by_id(options, "encounter_attack")][3].insert(0, (call_script, "script_coop_client_fight_start"))
  join = menu_options(menus, "join_battle")
  join[find_by_id(join, "join_attack")][3].insert(0, (call_script, "script_coop_client_fight_start"))
  siege[find_by_id(siege, "castle_lead_attack")][3].insert(0, (call_script, "script_coop_client_fight_start"))
  menus.extend(mp_campaign_menus)
  # players together: giving troops
  from coop.players import players_menus, encounter_options, camp_options
  options.insert(find_by_id(options, "encounter_leave"), encounter_options()[0])
  from coop import fiefs as _fiefs
  options.insert(find_by_id(options, "encounter_leave"), _fiefs.gift_encounter_option())
  menus.extend(players_menus)
  stop = find_by_id(coop_camp, "coop_role_stop")
  coop_camp[stop:stop] = camp_options()
  coop_camp.append(("coop_camp_back", [], "Back.", [(jump_to_menu, "mnu_camp")]))
  # together without meeting: the ride after a friend, the treasury and the store, duels; lairs,
  # caravans and villages defended on the battle server
  from coop.mp_campaign import coop_mp_event_ready
  from coop import together
  menus.extend(together.together_menus)
  stop = find_by_id(coop_camp, "coop_role_stop")
  coop_camp[stop:stop] = together.camp_options()
  # trade caravans of the players: from the company's camp (and a town's guild master, coop/dialogs.py)
  from coop import caravans
  shared = menu_options(menus, "coop_shared")
  shared.insert(find_by_id(shared, "coop_blackborn"), caravans.camp_option())
  # the smith of every town
  from coop import smith
  town = menu_options(menus, "town")
  town.insert(find_by_id(town, "town_leave"), smith.town_option())
  # a client's fiefs live in the host's world: Native's ways of running one act on this game's copy only
  from coop import fiefs
  town.insert(find_by_id(town, "town_leave"), fiefs.garrison_option())
  for option_id in ("walled_center_manage", "walled_center_move_court", "castle_station_troops",
                    "dplmc_castle_give_troops"):
    fiefs.client_only(town[find_by_id(town, option_id)])
  village = menu_options(menus, "village")
  fiefs.client_only(village[find_by_id(village, "village_manage")])
  players = menu_options(menus, "coop_players")
  at = find_by_id(players, "coop_pl_write_hero")
  for k in range(coop_max_players):
    puppet = f"p_coop_puppet_{k + 1}"
    name = [(party_is_active, puppet), (str_store_party_name, s1, puppet)]
    players[at:at] = together.players_menu_options(k, name) + [fiefs.gift_players_option(k, name)]
    at = find_by_id(players, "coop_pl_write_hero")
  players.insert(at, together.players_stop_option())
  lair = menu_options(menus, "bandit_lair")
  lair.insert(find_by_id(lair, "leave_no_attack"), together.lair_option(coop_mp_event_ready))
  pre_join = menu_options(menus, "pre_join")
  pre_join.insert(find_by_id(pre_join, "pre_join_leave"), together.pre_join_option(coop_mp_event_ready))
  menu_options(menus, "village").insert(0, together.village_option(coop_mp_event_ready))
  village_options = menu_options(menus, "village")
  village_options.insert(find_by_id(village_options, "village_attack_bandits"),
                         together.bandits_option(coop_mp_event_ready))
  # a client's fight of its own: the host's world and the others hear of it
  menu_block(menus, "village_infestation_removed")[0:0] = [
    (call_script, "script_coop_note", coop_note_bandits, "$g_encountered_party", 1, 0),
  ]
  # the camp stops the map's requests: a call to battle must still get through
  menu_block(menus, "camp")[0:0] = [(call_script, "script_coop_ping_kick")]
  # a field battle won, the loot screen closed: Native goes back to the map with change_screen_return. After a
  # screen of its own (the loot screen) that return can do nothing (the camp's exit, 11-03); on 11-04 the host's game
  # stood after it with the loot screen's last picture and messages running, then black, and asked the bridge nothing
  # more. change_screen_map goes to the map from wherever the game stands; the encounter is left just before.
  # The engine's return also took the emptied beaten party off the map: without it that party stayed with 0 men, and
  # a talk with it went black (11-04), so it goes here (script_coop_remove_beaten).
  victory = menu_block(menus, "total_victory")
  done = find_line(victory, (val_add, "$g_total_victories", 1))
  if victory[done + 1:done + 3] != [(leave_encounter), (change_screen_return)]:
    raise MergeError("total_victory: expected leave_encounter, change_screen_return after the victories count")
  victory[done + 2:done + 3] = [(call_script, "script_coop_remove_beaten", "$g_enemy_party"), (change_screen_map)]
  # the same return did nothing in the encounter's menu (11-04): "Leave." stood, and a talk ended with "farewell"
  # ($g_leave_encounter) came back to the menu. Both go to the map as the victory now does.
  leave = options[find_by_id(options, "encounter_leave")][3]
  if leave[-2:] != [(leave_encounter), (change_screen_return)]:
    raise MergeError("simple_encounter: expected Leave to end with leave_encounter, change_screen_return")
  leave[-1] = (change_screen_map)
  farewell = find_line(encounter, (eq, "$g_leave_encounter", 1))
  if encounter[farewell + 1] != (change_screen_return):
    raise MergeError("simple_encounter: expected change_screen_return after $g_leave_encounter")
  encounter[farewell + 1:farewell + 2] = [(leave_encounter), (change_screen_map)]
  # "Retreat, leaving some men behind": its Continue... stood dead (11-06), as Leave did on 11-04 - the same
  # return after the encounter's menu. It goes to the map the same way.
  retreat = menu_options(menus, "encounter_retreat")
  go = retreat[find_by_id(retreat, "continue")][3]
  at = go.index((leave_encounter))
  if go[at + 1] != (change_screen_return):
    raise MergeError("encounter_retreat: expected leave_encounter, change_screen_return in Continue")
  go[at + 1] = (change_screen_map)
  # the captivity's first screen ("Your enemies take you prisoner"): its Continue... stood dead for the host on 11-06
  # (the same return as above), and the encounter with the captor, still open, came back with the captor's talk. The
  # encounter ends there and the game goes to the map, where the captivity runs its hours.
  taken = menu_options(menus, "captivity_wilderness_taken_prisoner")
  go = taken[find_by_id(taken, "continue")][3]
  if go[-1] != (change_screen_return):
    raise MergeError("captivity_wilderness_taken_prisoner: expected Continue to end with change_screen_return")
  go[-1:] = [(leave_encounter), (change_screen_map)]
  # an escape from captivity: the truce with the captor lasts a day more (script_coop_truce_escape), and the map
  # comes back the same way
  escape = menu_options(menus, "captivity_end_wilderness_escape")
  go = escape[find_by_id(escape, "continue")][3]
  at = go.index((change_screen_return))
  go[at] = (change_screen_map)
  go.insert(0, (call_script, "script_coop_truce_escape"))
