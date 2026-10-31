from header_common import *
from header_operations import *
from header_mission_templates import *
from header_triggers import *
from header_items import *
from header_troops import *
from module_constants import *
from coop.constants import *

# Joint battles: a campaign battle is fought on a Warband multiplayer server, so every player
# fights it in person. The server is this module's "Battle" game type, hosted on the host's PC;
# it asks the bridge (tools/coop_bridge.py, /mp requests) whether a battle is waiting.
#
# Phases ($coop_mp_phase): 0 an ordinary round, nothing from the campaign
#   1 a battle arrived: the round restarts      2 the armies spawn, one bot a frame
#   3 the battle runs                            4 over: the losses go to the bridge until it acks
#   5 the server changes its game type (Battle for the field, Siege for a castle or town)
# A siege ($coop_mp_mode 1) is fought in the Siege game type on one of its maps: team 0 holds the
# walls (the garrison), team 1 storms them. The attackers win by the flag or when no defender
# stands; the defenders when no attacker bot stands. The bots fight on foot; the ladders go up the
# walls once the troops are on the field (the AI mesh climbs the wall there), and a storming bot that
# stands under a wall is sent to a ladder (script_coop_mp_storm).
# A hero or companion spawns with its campaign hit points (slot_troop_coop_mp_hp, _max).
# A joint event (mode coop_mp_mode_arena, _tournament, _training) is fought in Battle by the players'
# heroes alone, side by side on team 0, in practice gear and at full health, against bots on team 1.
# An arena's opponents come a few at a time (the hint says how many), and the bridge plays a
# tournament's rounds one after the other (the hint is the round): the same battle, started again.
# Stacks are kept on trp_temp_array_a, COOP_MP_STRIDE slots each (troop, team, group = the MP
# player who commands them or -1, count, fallen, spawned); trp_temp_array_b holds the last reply.
#
# The players' heroes: up to four players fight as their campaign hero, with its equipment,
# attributes, combat skills and proficiencies. The battle server borrows the four tutorial
# students for them (never used in multiplayer; new troops would change the campaign's saves),
# and tells every game the stats it gave them (network event coop_mp_event_hero_stat).

MP_ARR = "trp_temp_array_a"
HERO_TROOPS = "trp_tutorial_student_1"  # .. _4
# Native's Siege maps whose AI mesh takes bots up the walls (by a ladder's place or a standing ladder).
# Maps 8 and 15 have no AI mesh at all: bots there only walk straight at the walls and stand.
SIEGE_SCENES = ["scn_multi_scene_3", "scn_multi_scene_10", "scn_multi_scene_13", "scn_multi_scene_16"]
# The ladders the attackers raise in Siege (they lie on the ground when a round starts); the AI mesh
# goes up the wall where they stand raised, so a bot walking there needs the ladder up
LADDERS = ["spr_siege_ladder_move_6m", "spr_siege_ladder_move_8m", "spr_siege_ladder_move_10m",
           "spr_siege_ladder_move_12m", "spr_siege_ladder_move_14m"]
FIELD_SCENE = "scn_random_multi_plain_medium"
# Battle maps for the terrain the battle was met on (party_get_current_terrain, header_terrain_types)
TERRAIN_SCENES = [
  (2, "scn_random_multi_steppe_medium"),  # steppe
  (10, "scn_multi_scene_18"),             # steppe forest: Forest Hideout
  (11, "scn_multi_scene_18"),             # forest
  (9, "scn_multi_scene_18"),              # mountain forest
  (1, "scn_multi_scene_4"),               # mountain: Ruined Fort
  (4, "scn_multi_scene_14"),              # snow: Battle on Ice
  (12, "scn_multi_scene_9"),              # snow forest: Snowy Village
  (5, "scn_multi_scene_19"),              # desert: Canyon
  (13, "scn_multi_scene_20"),             # desert forest: Desert Town
  (8, "scn_multi_scene_7"),               # river: Field by the River
]
# Joint events: Native's multiplayer arena for the arena, the tournament and a duel, an open field for
# the training. The single player arenas and training grounds have no AI mesh: bots there would not walk.
EVENT_SCENES = [
  (coop_mp_mode_arena, "scn_multi_scene_17"),       # The Arena
  (coop_mp_mode_tournament, "scn_multi_scene_17"),
  (coop_mp_mode_training, "scn_multi_scene_7"),     # Field by the River
  (coop_mp_mode_duel, "scn_multi_scene_17"),
]
# The practice gear of a joint event: 0 one handed, 1 two handed, 2 polearm, 3 ranged, then more. The bots
# take the sets in turn, the heroes another one each round of an arena or a tournament. A training is
# sparring, by hand, as in Native (the first SPARRING_SETS only), each hero with the set nearest to its
# own weapons.
EVENT_SETS = [
  ["itm_practice_sword", "itm_practice_shield"],
  ["itm_heavy_practice_sword"],
  ["itm_practice_staff"],
  ["itm_practice_bow", "itm_practice_arrows", "itm_practice_dagger"],
  ["itm_practice_crossbow", "itm_practice_bolts", "itm_practice_dagger"],
  ["itm_practice_javelin", "itm_practice_sword", "itm_practice_shield"],
]
SPARRING_SETS = 3
# The sides of a joint event: (team, entry point, helmet, tunic). Team 2 is Native's spectators, and the
# mission knows no entry past 63: these stand around the sand of the arena's map (read from its scene).
EVENT_SIDES = [
  (0, 36, "itm_red_tourney_helmet", "itm_arena_tunic_red"),       # the fighters on the players' side
  (1, multi_initial_spawn_point_team_2, "itm_blue_tourney_helmet", "itm_arena_tunic_blue"),
  (3, 37, "itm_green_tourney_helmet", "itm_arena_tunic_green"),
  (4, 52, "itm_gold_tourney_helmet", "itm_arena_tunic_yellow"),
]
ARENA_SIDES = [1, 3, 4]    # an arena's fighters all are of team 1, enemies of each other: only their looks differ
EVENT_FIGHTER_ITEMS = ["itm_practice_sword", "itm_practice_shield", "itm_heavy_practice_sword",
                       "itm_practice_staff", "itm_arena_tunic_blue"]
MP_BUF = "trp_temp_array_b"
S_TROOP, S_TEAM, S_GROUP, S_COUNT, S_FALLEN, S_SPAWNED = range(6)


def stack_slot(field):
  """Ops: ':slot' = the slot of `field` of stack ':i'."""
  return [
    (store_mul, ":slot", ":i", coop_mp_stride),
    (val_add, ":slot", field),
  ]


mp_scripts = [
  # script_coop_mp_reply: a /mp reply on the multiplayer server, copied to MP_BUF
  # kind 2: a chunk of stacks  bid|offset|n|(team, group, troop, count)*n
  # kind 1: start              bid|stacks|mode|hint|n|(player, team)*n
  # kind 4: the losses arrived bid|more (1: the bridge has another round of this tournament)
  # kind 3: tell one player s0 (an invitation waits in that player's campaign window)
  # kind 5: a player's hero    bid|player|coop_hero_numbers values (before the start, or while the
  #                            battle runs: a player who got to the battle server or accepted late)
  # kind 6: a companion        bid|troop|coop_hero_numbers values
  # kind 9: a late hero's side bid|player|team (after its kind 5, while the battle runs)
  ("coop_mp_reply",
   [
     (assign, "$coop_mp_pending", 0),
     (troop_get_slot, ":kind", MP_BUF, 1),
     (troop_get_slot, ":bid", MP_BUF, 2),
     (try_begin),
       (eq, ":kind", 2),
       (eq, "$coop_mp_phase", 0),
       (troop_get_slot, ":offset", MP_BUF, 3),
       (troop_get_slot, ":n", MP_BUF, 4),
       (try_begin),
         (eq, ":offset", 0), #a new battle: no heroes yet
         (assign, "$coop_mp_heroes", 0),
         (try_for_range, ":k", 0, 4),
           (store_add, ":troop", HERO_TROOPS, ":k"),
           (troop_set_slot, ":troop", slot_troop_coop_mp_hp_max, 0),
         (try_end),
         (get_max_players, ":num_players"),
         (try_for_range, ":player_no", 0, ":num_players"),
           (player_is_active, ":player_no"),
           (player_set_slot, ":player_no", slot_player_coop_hero, 0),
           (player_set_slot, ":player_no", slot_player_coop_health, 0),
           (player_set_slot, ":player_no", slot_player_coop_fallen, 0),
           (player_set_slot, ":player_no", slot_player_coop_kills, 0),
           (try_for_range, ":wpt", 0, coop_hero_profs),
             (store_add, ":slot", slot_player_coop_hits, ":wpt"),
             (player_set_slot, ":player_no", ":slot", 0),
             (store_add, ":slot", slot_player_coop_damage, ":wpt"),
             (player_set_slot, ":player_no", ":slot", 0),
           (try_end),
         (try_end),
       (try_end),
       (try_for_range, ":k", 0, ":n"),
         (store_add, ":i", ":offset", ":k"),
         (lt, ":i", coop_mp_max_stacks),
         (store_mul, ":src", ":k", 4),
         (val_add, ":src", 5),
         (store_mul, ":dst", ":i", coop_mp_stride),
         (troop_get_slot, ":v", MP_BUF, ":src"),
         (store_add, ":slot", ":dst", S_TEAM),
         (troop_set_slot, MP_ARR, ":slot", ":v"),
         (val_add, ":src", 1),
         (troop_get_slot, ":v", MP_BUF, ":src"),
         (store_add, ":slot", ":dst", S_GROUP),
         (troop_set_slot, MP_ARR, ":slot", ":v"),
         (val_add, ":src", 1),
         (troop_get_slot, ":v", MP_BUF, ":src"),
         (store_add, ":slot", ":dst", S_TROOP),
         (troop_set_slot, MP_ARR, ":slot", ":v"),
         (val_add, ":src", 1),
         (troop_get_slot, ":v", MP_BUF, ":src"),
         (store_add, ":slot", ":dst", S_COUNT),
         (troop_set_slot, MP_ARR, ":slot", ":v"),
         (store_add, ":slot", ":dst", S_FALLEN),
         (troop_set_slot, MP_ARR, ":slot", 0),
         (store_add, ":slot", ":dst", S_SPAWNED),
         (troop_set_slot, MP_ARR, ":slot", 0),
       (try_end),
     (else_try),
       (eq, ":kind", 5), #a player's hero: player, then coop_hero_numbers values
       (is_between, "$coop_mp_phase", 0, 4),
       (troop_get_slot, ":player_no", MP_BUF, 3),
       (player_is_active, ":player_no"),
       (player_slot_eq, ":player_no", slot_player_coop_hero, 0),
       (lt, "$coop_mp_heroes", 4),
       (store_add, ":troop", HERO_TROOPS, "$coop_mp_heroes"),
       (store_add, ":kept_at", coop_mp_heroes_slot, "$coop_mp_heroes"),
       (troop_set_slot, MP_ARR, ":kept_at", ":player_no"),
       (val_add, "$coop_mp_heroes", 1),
       (player_set_slot, ":player_no", slot_player_coop_hero, "$coop_mp_heroes"),
       (try_for_range, ":ek", 0, coop_hero_items),
         (store_add, ":at", ":ek", 4),
         (troop_get_slot, ":item", MP_BUF, ":at"),
         (troop_set_inventory_slot, ":troop", ":ek", ":item"),
       (try_end),
       (assign, ":at", 4 + coop_hero_items),
       (try_for_range, ":attribute", 0, 4),
         (troop_get_slot, ":value", MP_BUF, ":at"),
         (call_script, "script_coop_mp_hero_stat_to_all", ":troop", ":attribute", ":value"),
         (val_add, ":at", 1),
       (try_end),
       ] + [op for skill in coop_hero_skills for op in [
       (troop_get_slot, ":value", MP_BUF, ":at"),
       (call_script, "script_coop_mp_hero_stat_to_all", ":troop", 10 + skill, ":value"),
       (val_add, ":at", 1),
       ]] + [
       (try_for_range, ":wpt", 0, coop_hero_profs),
         (troop_get_slot, ":value", MP_BUF, ":at"),
         (store_add, ":code", ":wpt", 100),
         (call_script, "script_coop_mp_hero_stat_to_all", ":troop", ":code", ":value"),
         (val_add, ":at", 1),
       (try_end),
       # its hit points in the campaign, given to it when it spawns
       (troop_get_slot, ":value", MP_BUF, ":at"),
       (troop_set_slot, ":troop", slot_troop_coop_mp_hp, ":value"),
       (val_add, ":at", 1),
       (troop_get_slot, ":value", MP_BUF, ":at"),
       (troop_set_slot, ":troop", slot_troop_coop_mp_hp_max, ":value"),
     (else_try),
       (eq, ":kind", 6), #a companion: troop, then coop_hero_numbers values (spawned as a bot of its stack)
       (eq, "$coop_mp_phase", 0),
       (troop_get_slot, ":troop", MP_BUF, 3),
       (gt, ":troop", 0),
       (try_for_range, ":ek", 0, coop_hero_items),
         (store_add, ":at", ":ek", 4),
         (troop_get_slot, ":item", MP_BUF, ":at"),
         (troop_set_inventory_slot, ":troop", ":ek", ":item"),
       (try_end),
       (assign, ":at", 4 + coop_hero_items),
       (try_for_range, ":attribute", 0, 4),
         (troop_get_slot, ":value", MP_BUF, ":at"),
         (call_script, "script_coop_mp_hero_stat_to_all", ":troop", ":attribute", ":value"),
         (val_add, ":at", 1),
       (try_end),
       ] + [op for skill in coop_hero_skills for op in [
       (troop_get_slot, ":value", MP_BUF, ":at"),
       (call_script, "script_coop_mp_hero_stat_to_all", ":troop", 10 + skill, ":value"),
       (val_add, ":at", 1),
       ]] + [
       (try_for_range, ":wpt", 0, coop_hero_profs),
         (troop_get_slot, ":value", MP_BUF, ":at"),
         (store_add, ":code", ":wpt", 100),
         (call_script, "script_coop_mp_hero_stat_to_all", ":troop", ":code", ":value"),
         (val_add, ":at", 1),
       (try_end),
       # its hit points in the campaign, given to it when it spawns
       (troop_get_slot, ":value", MP_BUF, ":at"),
       (troop_set_slot, ":troop", slot_troop_coop_mp_hp, ":value"),
       (val_add, ":at", 1),
       (troop_get_slot, ":value", MP_BUF, ":at"),
       (troop_set_slot, ":troop", slot_troop_coop_mp_hp_max, ":value"),
     (else_try),
       # start: bid|stacks|mode|scene hint|n|(player, team)*n
       (eq, ":kind", 1),
       (eq, "$coop_mp_phase", 0),
       (assign, "$coop_mp_battle", ":bid"),
       (troop_get_slot, "$coop_mp_n", MP_BUF, 3),
       (val_min, "$coop_mp_n", coop_mp_max_stacks),
       (troop_get_slot, "$coop_mp_mode", MP_BUF, 4),
       (troop_get_slot, ":hint", MP_BUF, 5),
       (assign, "$coop_mp_hint", ":hint"),
       (assign, "$coop_mp_event_turn", 0),
       (store_random_in_range, ":step", 1, len(EVENT_SETS)), #never the set of the last fight
       (val_add, "$coop_mp_event_round", ":step"),
       (assign, "$coop_mp_no_hero_left", 0),
       # the players' sides, kept until the battle's mission is up
       (troop_get_slot, "$coop_mp_pairs", MP_BUF, 6),
       (try_for_range, ":k", 0, "$coop_mp_pairs"),
         (store_mul, ":src", ":k", 2),
         (val_add, ":src", 7),
         (store_mul, ":dst", ":k", 2),
         (val_add, ":dst", coop_mp_pairs_slot),
         (troop_get_slot, ":v", MP_BUF, ":src"),
         (troop_set_slot, MP_ARR, ":dst", ":v"),
         (val_add, ":src", 1),
         (val_add, ":dst", 1),
         (troop_get_slot, ":v", MP_BUF, ":src"),
         (troop_set_slot, MP_ARR, ":dst", ":v"),
       (try_end),
       (assign, "$coop_mp_old_round_seconds", "$g_multiplayer_round_max_seconds"),
       (call_script, "script_coop_mp_horses_back"), #a siege takes them again, bot by bot
       (call_script, "script_coop_mp_gear_back"), #and a joint event its practice gear
       (try_begin),
         (ge, "$coop_mp_mode", coop_mp_mode_arena),
         (call_script, "script_coop_mp_arm_fighters"),
       (try_end),
       (assign, ":game_type", multiplayer_game_type_battle),
       (try_begin),
         (eq, "$coop_mp_mode", 1),
         (assign, ":game_type", multiplayer_game_type_siege),
       (try_end),
       # the map: a castle for a siege (by the center), else one fitting the terrain (the hint)
       (assign, ":scene", FIELD_SCENE),
       (try_begin),
         (eq, "$coop_mp_mode", 1),
         (store_mod, ":pick", ":hint", len(SIEGE_SCENES)),
         ] + [op for k, scn in enumerate(SIEGE_SCENES) for op in [
         (try_begin), (eq, ":pick", k), (assign, ":scene", scn), (try_end),
         ]] + [
       (else_try),
         (ge, "$coop_mp_mode", coop_mp_mode_arena),
         ] + [op for mode, scn in EVENT_SCENES for op in [
         (try_begin), (eq, "$coop_mp_mode", mode), (assign, ":scene", scn), (try_end),
         ]] + [
       (else_try),
         ] + [op for terrain, scn in TERRAIN_SCENES for op in [
         (try_begin), (eq, ":hint", terrain), (assign, ":scene", scn), (try_end),
         ]] + [
       (try_end),
       (try_begin),
         (this_or_next|neq, "$g_multiplayer_game_type", ":game_type"),
         (neq, "$g_multiplayer_selected_map", ":scene"),
         # another game type or map: its own mission; the sides are set once it is up
         (assign, "$g_multiplayer_game_type", ":game_type"),
         (assign, "$g_multiplayer_selected_map", ":scene"),
         (call_script, "script_game_multiplayer_get_game_type_mission_template", ":game_type"),
         (start_multiplayer_mission, reg0, ":scene", 1),
         (assign, "$coop_mp_phase", 5),
       (else_try),
         (call_script, "script_coop_mp_assign_teams"),
         # one long round: no time limit and no flags while the campaign battle lasts
         (assign, "$g_multiplayer_round_max_seconds", coop_mp_round_seconds),
         (assign, "$g_round_ended", 1),
         (assign, "$g_round_finish_time", -100000), #the next round starts at once
         (assign, "$coop_mp_phase", 1),
       (try_end),
     (else_try),
       # a late hero's side: kept with the others, the player is put there before it spawns
       (eq, ":kind", 9),
       (is_between, "$coop_mp_phase", 1, 4),
       (eq, ":bid", "$coop_mp_battle"),
       (lt, "$coop_mp_pairs", 25), #coop_mp_pairs_slot .. coop_mp_heroes_slot
       (troop_get_slot, ":player_no", MP_BUF, 3),
       (troop_get_slot, ":team", MP_BUF, 4),
       (player_slot_ge, ":player_no", slot_player_coop_hero, 1), #its kind 5 came through
       (store_mul, ":dst", "$coop_mp_pairs", 2),
       (val_add, ":dst", coop_mp_pairs_slot),
       (troop_set_slot, MP_ARR, ":dst", ":player_no"),
       (val_add, ":dst", 1),
       (troop_set_slot, MP_ARR, ":dst", ":team"),
       (val_add, "$coop_mp_pairs", 1),
       (player_is_active, ":player_no"),
       (player_get_agent_id, ":agent_no", ":player_no"),
       (this_or_next|lt, ":agent_no", 0),
       (neg|agent_is_alive, ":agent_no"),
       (call_script, "script_coop_mp_put_on_side", ":player_no", ":team"),
     (else_try),
       (eq, ":kind", 3),
       (store_mul, ":player_no", ":bid", 1), #the player number comes where a battle number would
       (player_is_active, ":player_no"),
       (try_begin),
         (multiplayer_get_my_player, ":me"),
         (eq, ":player_no", ":me"), #the player of a server started from the game
         (display_message, s0, 0xFFDD66),
       (else_try),
         (multiplayer_send_string_to_player, ":player_no", multiplayer_event_show_server_message, s0),
       (try_end),
     (else_try),
       (eq, ":kind", 4),
       (eq, "$coop_mp_phase", 4),
       (eq, ":bid", "$coop_mp_battle"),
       (assign, "$coop_mp_phase", 0),
       (assign, "$coop_mp_battle", 0),
       # a tournament's rounds follow each other without the team window: it comes after the last one
       (try_begin),
         (eq, "$coop_mp_mode", coop_mp_mode_tournament),
         (troop_slot_eq, MP_BUF, 3, 0),
         (store_add, ":end", HERO_TROOPS, 4),
         (get_max_players, ":num_players"),
         (try_for_range, ":player_no", 0, ":num_players"),
           (player_is_active, ":player_no"),
           (player_get_troop_id, ":troop", ":player_no"),
           (is_between, ":troop", HERO_TROOPS, ":end"),
           (player_set_troop_id, ":player_no", -1), #picks a class of the ordinary game again
           (multiplayer_send_message_to_player, ":player_no", multiplayer_event_force_start_team_selection),
         (try_end),
       (try_end),
     (try_end),
    ]),

  # script_coop_mp_hero_stat: arg1 = troop, arg2 = code (0-3 attribute, 10 + skill, 100 + weapon
  # proficiency), arg3 = the value the troop gets
  ("coop_mp_hero_stat",
   [
     (store_script_param, ":troop", 1),
     (store_script_param, ":code", 2),
     (store_script_param, ":value", 3),
     (try_begin),
       (eq, ":code", coop_mp_stat_team_event),
       (call_script, "script_coop_mp_team_event_set", ":value"),
     (else_try),
       (lt, ":code", 4),
       (store_attribute_level, ":now", ":troop", ":code"),
       (store_sub, ":delta", ":value", ":now"),
       (troop_raise_attribute, ":troop", ":code", ":delta"),
     (else_try),
       (lt, ":code", 100),
       (store_sub, ":skill", ":code", 10),
       (store_skill_level, ":now", ":skill", ":troop"),
       (store_sub, ":delta", ":value", ":now"),
       (troop_raise_skill, ":troop", ":skill", ":delta"),
     (else_try),
       (store_sub, ":wpt", ":code", 100),
       (store_proficiency_level, ":now", ":troop", ":wpt"),
       (store_sub, ":delta", ":value", ":now"),
       (troop_raise_proficiency_linear, ":troop", ":wpt", ":delta"),
     (try_end),
    ]),

  # script_coop_mp_hero_stat_to_all: the same here and in every player's game
  ("coop_mp_hero_stat_to_all",
   [
     (store_script_param, ":troop", 1),
     (store_script_param, ":code", 2),
     (store_script_param, ":value", 3),
     (call_script, "script_coop_mp_hero_stat", ":troop", ":code", ":value"),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 1, ":num_players"), #0 is the server itself
       (player_is_active, ":player_no"),
       (multiplayer_send_3_int_to_player, ":player_no", coop_mp_event_hero_stat, ":troop", ":code", ":value"),
     (try_end),
    ]),

  # script_cf_coop_mp_may_spawn: arg1 = player. While a campaign battle is on only the players who
  # fight as their hero spawn: a fallen hero stays out, and a player without a hero in this battle
  # (one who came late, before the bridge sent its hero) watches instead of fighting with the gear
  # picked in the multiplayer window.
  ("cf_coop_mp_may_spawn",
   [
     (store_script_param, ":player_no", 1),
     (player_slot_eq, ":player_no", slot_player_coop_fallen, 0),
     (assign, ":may", 1),
     (try_begin),
       (is_between, "$coop_mp_phase", 1, 4),
       (neg|player_slot_ge, ":player_no", slot_player_coop_hero, 1),
       (assign, ":may", 0),
     (try_end),
     (eq, ":may", 1),
    ]),

  # script_cf_coop_mp_late_hero: arg1 = player. Succeeds for a campaign hero while its battle is on:
  # it spawns even after Battle's first seconds (a hero that got there late).
  ("cf_coop_mp_late_hero",
   [
     (store_script_param, ":player_no", 1),
     (is_between, "$coop_mp_phase", 1, 4),
     (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
     (player_slot_eq, ":player_no", slot_player_coop_fallen, 0),
    ]),

  # script_cf_coop_mp_hero_spawn: arg1 = player about to spawn. Fails unless the player fights as a
  # campaign hero in this battle; then the player is that hero, with the hero's equipment.
  ("cf_coop_mp_hero_spawn",
   [
     (store_script_param, ":player_no", 1),
     (is_between, "$coop_mp_phase", 1, 4),
     (player_get_slot, ":hero", ":player_no", slot_player_coop_hero),
     (gt, ":hero", 0),
     (store_add, ":troop", HERO_TROOPS, ":hero"),
     (val_sub, ":troop", 1),
     (player_set_troop_id, ":player_no", ":troop"),
     (try_begin),
       (ge, "$coop_mp_mode", coop_mp_mode_arena),
       (neq, "$coop_mp_mode", coop_mp_mode_duel), #friends duel with their own weapons
       (call_script, "script_coop_mp_event_hero_gear", ":player_no", ":troop"),
     (else_try),
       (try_for_range, ":ek", 0, coop_hero_items),
         (troop_get_inventory_slot, ":item", ":troop", ":ek"),
         (ge, ":item", 0),
         (player_add_spawn_item, ":player_no", ":ek", ":item"),
       (try_end),
     (try_end),
    ]),

  # script_coop_mp_event_hero_gear: arg1 = player, arg2 = its hero's troop: the practice gear of a joint
  # event: in a training the set nearest to the hero's own weapons, else another one each round
  ("coop_mp_event_hero_gear",
   [
     (store_script_param, ":player_no", 1),
     (store_script_param, ":troop", 2),
     (assign, ":set", -1),
     (try_for_range, ":ek", 0, 4),
       (eq, ":set", -1),
       (troop_get_inventory_slot, ":item", ":troop", ":ek"),
       (ge, ":item", 0),
       (item_get_type, ":type", ":item"),
       (try_begin),
         (eq, ":type", itp_type_one_handed_wpn),
         (assign, ":set", 0),
       (else_try),
         (eq, ":type", itp_type_two_handed_wpn),
         (assign, ":set", 1),
       (else_try),
         (eq, ":type", itp_type_polearm),
         (assign, ":set", 2),
       (else_try),
         (this_or_next|eq, ":type", itp_type_bow),
         (eq, ":type", itp_type_crossbow),
         (assign, ":set", 3),
       (try_end),
     (try_end),
     (val_max, ":set", 0),
     (try_begin),
       (neq, "$coop_mp_mode", coop_mp_mode_training),
       (store_add, ":set", "$coop_mp_event_round", ":player_no"),
       (val_mod, ":set", len(EVENT_SETS)),
     (else_try),
       (ge, ":set", SPARRING_SETS),
       (assign, ":set", 0),
     (try_end),
     ] + [op for k, items in enumerate(EVENT_SETS) for op in [
     (try_begin),
       (eq, ":set", k),
       ] + [(player_add_spawn_item, ":player_no", ek, item) for ek, item in enumerate(items)] + [
     (try_end),
     ]] + [
     (player_add_spawn_item, ":player_no", ek_head, "itm_red_tourney_helmet"),
     (player_add_spawn_item, ":player_no", ek_body, "itm_arena_tunic_red"),
     (player_add_spawn_item, ":player_no", ek_foot, "itm_practice_boots"),
    ]),

  # script_coop_mp_event_bot_gear: arg1 = the bot's team, arg2 = the bot's turn: its practice gear, through
  # an entry point's override (as Native's arena gives it). reg0 = that entry point: each side has its own
  ("coop_mp_event_bot_gear",
   [
     (store_script_param, ":side", 1),
     (store_script_param, ":turn", 2),
     (try_begin),
       (eq, "$coop_mp_mode", coop_mp_mode_arena),
       (store_mod, ":pick", ":turn", len(ARENA_SIDES)),
       ] + [op for k, side in enumerate(ARENA_SIDES) for op in [
       (try_begin), (eq, ":pick", k), (assign, ":side", side), (try_end),
       ]] + [
     (try_end),
     ] + [op for side, entry, helmet, tunic in EVENT_SIDES for op in [
     (try_begin),
       (eq, ":side", side),
       (assign, ":entry", entry),
       (assign, ":helmet", helmet),
       (assign, ":tunic", tunic),
     (try_end),
     ]] + [
     (try_begin),
       (eq, "$coop_mp_mode", coop_mp_mode_training),
       (store_mod, ":set", ":turn", SPARRING_SETS),
     (else_try),
       (store_mod, ":set", ":turn", len(EVENT_SETS)),
     (try_end),
     (mission_tpl_entry_set_override_flags, "mt_multiplayer_bt", ":entry", af_override_everything),
     (mission_tpl_entry_clear_override_items, "mt_multiplayer_bt", ":entry"),
     ] + [op for k, items in enumerate(EVENT_SETS) for op in [
     (try_begin),
       (eq, ":set", k),
       ] + [(mission_tpl_entry_add_override_item, "mt_multiplayer_bt", ":entry", item) for item in items] + [
     (try_end),
     ]] + [
     (mission_tpl_entry_add_override_item, "mt_multiplayer_bt", ":entry", ":helmet"),
     (mission_tpl_entry_add_override_item, "mt_multiplayer_bt", ":entry", ":tunic"),
     (mission_tpl_entry_add_override_item, "mt_multiplayer_bt", ":entry", "itm_practice_boots"),
     (assign, reg0, ":entry"),
    ]),

  # script_coop_mp_gear_back: the spawn points of the bots give their own gear again
  ("coop_mp_gear_back",
   [
     ] + [op for side, entry, helmet, tunic in EVENT_SIDES for op in [
     (mission_tpl_entry_set_override_flags, "mt_multiplayer_bt", entry, 0),
     (mission_tpl_entry_clear_override_items, "mt_multiplayer_bt", entry),
     ]] + [
    ]),

  # script_coop_mp_team_event_set: arg1 = $coop_mp_team_event: the mode of the joint event whose sides are
  # more than Native's two (an arena, a tournament), 0 none. Runs in every game: the relations are each
  # game's own, and Native's count of the living ends no such round.
  ("coop_mp_team_event_set",
   [
     (store_script_param, "$coop_mp_team_event", 1),
     (assign, ":own", 1),
     (try_begin),
       (eq, "$coop_mp_team_event", coop_mp_mode_arena),
       (assign, ":own", -1), #each fighter of team 1 is an enemy of the others
     (try_end),
     (team_set_relation, 1, 1, ":own"),
     ] + [(team_set_relation, a[0], b[0], -1) for i, a in enumerate(EVENT_SIDES) for b in EVENT_SIDES[i + 1:]] + [
    ]),

  # script_coop_mp_team_event_tell: arg1 = as above: here and in the players' games
  ("coop_mp_team_event_tell",
   [
     (store_script_param, ":event", 1),
     (call_script, "script_coop_mp_team_event_set", ":event"),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 1, ":num_players"), #0 is the server itself
       (player_is_active, ":player_no"),
       (multiplayer_send_3_int_to_player, ":player_no", coop_mp_event_hero_stat, 0, coop_mp_stat_team_event, ":event"),
     (try_end),
    ]),

  # script_coop_mp_arm_fighters: the arena's fighters own nothing but boots (Native's arena gives them
  # all they fight with): once a run, the battle server gives them practice weapons of their own
  ("coop_mp_arm_fighters",
   [
     (try_begin),
       (eq, "$coop_mp_fighters_armed", 0),
       (assign, "$coop_mp_fighters_armed", 1),
       (store_add, ":end", "trp_arena_training_fighter_10", 1),
       (try_for_range, ":troop", "trp_arena_training_fighter_1", ":end"),
         ] + [(troop_add_item, ":troop", item) for item in EVENT_FIGHTER_ITEMS] + [
       (try_end),
     (try_end),
    ]),

  # script_cf_coop_mp_bot_may_spawn: an arena's opponents come a few at a time ($coop_mp_hint); the
  # next one comes as soon as one is beaten
  ("cf_coop_mp_bot_may_spawn",
   [
     (assign, ":may", 1),
     (try_begin),
       (eq, "$coop_mp_mode", coop_mp_mode_arena),
       (assign, ":standing", 0),
       (try_for_agents, ":agent_no"),
         (agent_is_alive, ":agent_no"),
         (agent_is_human, ":agent_no"),
         (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
         (val_add, ":standing", 1),
       (try_end),
       (ge, ":standing", "$coop_mp_hint"),
       (assign, ":may", 0),
     (try_end),
     (eq, ":may", 1),
    ]),

  # script_coop_mp_assign_teams: the players of the campaign onto their sides (kept at kind 1)
  ("coop_mp_assign_teams",
   [
     (try_for_range, ":k", 0, "$coop_mp_pairs"),
       (store_mul, ":src", ":k", 2),
       (val_add, ":src", coop_mp_pairs_slot),
       (troop_get_slot, ":player_no", MP_ARR, ":src"),
       (val_add, ":src", 1),
       (troop_get_slot, ":team", MP_ARR, ":src"),
       (player_is_active, ":player_no"),
       (call_script, "script_coop_mp_put_on_side", ":player_no", ":team"),
     (try_end),
    ]),

  # script_coop_mp_put_on_side: arg1 = player (no agent alive), arg2 = its side. A hero gets the side
  # and the hero's troop at once, without the team window (a window per change, opened again every
  # time the side was off, came up over and over); a player without a hero picks its troop there.
  ("coop_mp_put_on_side",
   [
     (store_script_param, ":player_no", 1),
     (store_script_param, ":team", 2),
     (player_get_team_no, ":old_team", ":player_no"),
     (player_get_troop_id, ":old_troop", ":player_no"),
     (player_get_slot, ":hero", ":player_no", slot_player_coop_hero),
     (try_begin),
       (gt, ":hero", 0),
       (store_add, ":troop", HERO_TROOPS, ":hero"),
       (val_sub, ":troop", 1),
       (this_or_next|neq, ":old_team", ":team"),
       (neq, ":old_troop", ":troop"),
       (player_set_team_no, ":player_no", ":team"),
       (player_set_troop_id, ":player_no", ":troop"),
     (else_try),
       (le, ":hero", 0),
       (neq, ":old_team", ":team"),
       (player_set_troop_id, ":player_no", -1),
       (player_set_team_no, ":player_no", ":team"),
       (multiplayer_send_message_to_player, ":player_no", multiplayer_event_force_start_team_selection),
     (try_end),
    ]),

  # script_coop_mp_go: the sides stand and the round is up (a new map, or the next round on this one): the
  # bots may come. A joint event's rules and the word of what begins go out only now: what is said while
  # a map loads or a round restarts reaches nobody, the player of this very game included
  ("coop_mp_go",
   [
     (assign, "$g_multiplayer_num_bots_required_team_1", 0), #only the campaign's armies
     (assign, "$g_multiplayer_num_bots_required_team_2", 0),
     (assign, "$coop_mp_spawn_i", 0),
     (assign, "$g_multiplayer_ready_for_spawning_agent", 1), #a bot of the last fight that never came
     (assign, "$coop_mp_spawn_wait", 0),
     (assign, "$coop_mp_phase", 2),
     (assign, ":event", 0),
     (try_begin),
       (this_or_next|eq, "$coop_mp_mode", coop_mp_mode_arena),
       (eq, "$coop_mp_mode", coop_mp_mode_tournament),
       (assign, ":event", "$coop_mp_mode"),
     (try_end),
     (call_script, "script_coop_mp_team_event_tell", ":event"),
     (try_begin),
       (eq, "$coop_mp_mode", 1),
       (str_store_string, s0, "@CoopWorld: a siege of the campaign begins! Team 1 holds the walls, team 2 storms them."),
     (else_try),
       (eq, "$coop_mp_mode", coop_mp_mode_arena),
       (str_store_string, s0, "@CoopWorld: the arena fight begins! All players stand together, every fighter is against all."),
     (else_try),
       (eq, "$coop_mp_mode", coop_mp_mode_tournament),
       (store_mod, reg20, "$coop_mp_hint", 10), #round + 10 * teams
       (assign, reg21, coop_mp_tournament_rounds),
       (store_div, reg22, "$coop_mp_hint", 10),
       (str_store_string, s0, "@CoopWorld: the tournament, round {reg20} of {reg21}, {reg22} teams! All players stand together."),
     (else_try),
       (eq, "$coop_mp_mode", coop_mp_mode_training),
       (str_store_string, s0, "@CoopWorld: the training begins! All players stand together."),
     (else_try),
       (eq, "$coop_mp_mode", coop_mp_mode_duel),
       (str_store_string, s0, "@CoopWorld: the duel begins! One against the other, in your own gear."),
     (else_try),
       (str_store_string, s0, "@CoopWorld: a battle of the campaign begins!"),
     (try_end),
     (call_script, "script_coop_mp_tell_all"),
    ]),

  # script_coop_mp_tell_all: s0 to every player and the host
  ("coop_mp_tell_all",
   [
     (display_message, s0, 0xFFDD66),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 1, ":num_players"), #0 is the server itself
       (player_is_active, ":player_no"),
       (multiplayer_send_string_to_player, ":player_no", multiplayer_event_show_server_message, s0),
     (try_end),
    ]),

  # script_coop_mp_raise_ladders: every ladder lying on the ground goes up the wall, here and in every
  # player's game (as when a player raises it)
  ("coop_mp_raise_ladders",
   [
     (get_max_players, ":num_players"),
     ] + [op for kind in LADDERS for op in [
     (scene_prop_get_num_instances, ":num", kind),
     (try_for_range, ":k", 0, ":num"),
       (scene_prop_get_instance, ":instance", kind, ":k"),
       (scene_prop_slot_eq, ":instance", scene_prop_open_or_close_slot, 0),
       (call_script, "script_use_item", ":instance", -1),
       (try_for_range, ":player_no", 1, ":num_players"), #0 is the server itself
         (player_is_active, ":player_no"),
         (multiplayer_send_2_int_to_player, ":player_no", multiplayer_event_use_item, ":instance", -1),
       (try_end),
     (try_end),
     ]] + [
    ]),

  # script_coop_mp_pick_ladder: arg1 = a storming bot; reg0 = the raised ladder it goes to (the nearest
  # the first time, then the others in turn), -1 if none stands
  ("coop_mp_pick_ladder",
   [
     (store_script_param, ":agent_no", 1),
     (assign, reg0, -1),
     (set_fixed_point_multiplier, 100),
     (agent_get_position, pos1, ":agent_no"),
     (assign, ":n", 0),
     (assign, ":nearest", 0),
     (assign, ":best", -1),
     ] + [op for kind in LADDERS for op in [
     (scene_prop_get_num_instances, ":num", kind),
     (try_for_range, ":k", 0, ":num"),
       (scene_prop_get_instance, ":instance", kind, ":k"),
       (scene_prop_slot_eq, ":instance", scene_prop_open_or_close_slot, 1),
       (prop_instance_get_starting_position, pos2, ":instance"),
       (get_distance_between_positions, ":dist", pos1, pos2),
       (try_begin),
         (this_or_next|eq, ":best", -1),
         (lt, ":dist", ":best"),
         (assign, ":best", ":dist"),
         (assign, ":nearest", ":n"),
       (try_end),
       (val_add, ":n", 1),
     (try_end),
     ]] + [
     (try_begin),
       (gt, ":n", 0),
       (agent_get_slot, ":tries", ":agent_no", slot_agent_coop_tries),
       (store_add, ":pick", ":nearest", ":tries"),
       (val_mod, ":pick", ":n"),
       (val_add, ":tries", 1),
       (agent_set_slot, ":agent_no", slot_agent_coop_tries, ":tries"),
       (assign, ":n", 0),
       ] + [op for kind in LADDERS for op in [
       (scene_prop_get_num_instances, ":num", kind),
       (try_for_range, ":k", 0, ":num"),
         (scene_prop_get_instance, ":instance", kind, ":k"),
         (scene_prop_slot_eq, ":instance", scene_prop_open_or_close_slot, 1),
         (try_begin),
           (eq, ":n", ":pick"),
           (assign, reg0, ":instance"),
         (try_end),
         (val_add, ":n", 1),
       (try_end),
       ]] + [
     (try_end),
    ]),

  # script_coop_mp_storm: the storming bots of a siege (team 1), every 2 s. Bots walk the AI mesh to
  # the defenders; where it leads to a closed gate or a ladder that is down they stand under the wall.
  # A bot that stood coop_mp_storm_still_s with no enemy near (archers shooting excepted) is sent to a
  # raised ladder; at its foot (or in a fight, or after coop_mp_storm_walk_s) it is let go, and the AI
  # mesh takes it up the wall.
  ("coop_mp_storm",
   [
     (set_fixed_point_multiplier, 100),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_is_human, ":agent_no"),
       (agent_is_non_player, ":agent_no"),
       (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
       (agent_get_team, ":team", ":agent_no"),
       (eq, ":team", 1),
       (agent_get_position, pos1, ":agent_no"),
       (position_get_x, ":x", pos1),
       (position_get_y, ":y", pos1),
       (agent_get_slot, ":old_x", ":agent_no", slot_agent_coop_x),
       (agent_get_slot, ":old_y", ":agent_no", slot_agent_coop_y),
       (agent_set_slot, ":agent_no", slot_agent_coop_x, ":x"),
       (agent_set_slot, ":agent_no", slot_agent_coop_y, ":y"),
       (store_sub, ":dx", ":x", ":old_x"),
       (val_abs, ":dx"),
       (store_sub, ":dy", ":y", ":old_y"),
       (val_abs, ":dy"),
       (store_add, ":moved", ":dx", ":dy"),
       (assign, ":busy", 0), #an enemy near, or a ranged weapon in hand
       (try_for_agents, ":other", pos1, 400),
         (eq, ":busy", 0),
         (agent_is_alive, ":other"),
         (agent_is_human, ":other"),
         (agent_get_team, ":other_team", ":other"),
         (neq, ":other_team", ":team"),
         (assign, ":busy", 1),
       (try_end),
       (try_begin),
         (agent_get_wielded_item, ":item", ":agent_no", 0),
         (ge, ":item", 0),
         (item_get_type, ":type", ":item"),
         (this_or_next|eq, ":type", itp_type_bow),
         (this_or_next|eq, ":type", itp_type_crossbow),
         (eq, ":type", itp_type_thrown),
         (assign, ":busy", 1),
       (try_end),
       (agent_get_slot, ":ladder", ":agent_no", slot_agent_coop_ladder),
       (agent_get_slot, ":still", ":agent_no", slot_agent_coop_still),
       (try_begin),
         (gt, ":ladder", 0), #on its way to a ladder: ":still" counts the walk
         (val_add, ":still", 2),
         (store_sub, ":instance", ":ladder", 1),
         (prop_instance_get_starting_position, pos2, ":instance"),
         (get_distance_between_positions, ":dist", pos1, pos2),
         (try_begin),
           (this_or_next|lt, ":dist", 250),
           (this_or_next|eq, ":busy", 1),
           (ge, ":still", coop_mp_storm_walk_s),
           (agent_clear_scripted_mode, ":agent_no"),
           (agent_set_slot, ":agent_no", slot_agent_coop_ladder, 0),
           (assign, ":still", 0),
         (try_end),
       (else_try),
         (try_begin),
           (eq, ":busy", 0),
           (lt, ":moved", 100), #under a metre in 2 s
           (val_add, ":still", 2),
         (else_try),
           (assign, ":still", 0),
         (try_end),
         (ge, ":still", coop_mp_storm_still_s),
         (assign, ":still", 0),
         (call_script, "script_coop_mp_pick_ladder", ":agent_no"),
         (ge, reg0, 0),
         (prop_instance_get_starting_position, pos2, reg0),
         (agent_set_scripted_destination, ":agent_no", pos2, 1),
         (store_add, ":ladder", reg0, 1),
         (agent_set_slot, ":agent_no", slot_agent_coop_ladder, ":ladder"),
       (try_end),
       (agent_set_slot, ":agent_no", slot_agent_coop_still, ":still"),
     (try_end),
    ]),

  # script_coop_mp_horses_back: the Siege map's spawn points give horses again (a campaign siege
  # takes them from the bots)
  ("coop_mp_horses_back",
   [
     (try_for_range, ":entry", 0, 64),
       (mission_tpl_entry_set_override_flags, "mt_multiplayer_sg", ":entry", 0),
     (try_end),
    ]),

  # script_coop_mp_request: s10 = the next /mp request
  # st: the phase; pl: the players by number and name; w, r, hp, wx, kl: the outcome (phase 4)
  ("coop_mp_request",
   [
     (str_clear, s11),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 0, ":num_players"),
       (player_is_active, ":player_no"),
       (str_store_player_username, s13, ":player_no"),
       (assign, reg20, ":player_no"),
       (str_store_string, s11, "@{s11}{reg20}~{s13};"),
     (try_end),
     (str_clear, s12),
     (try_begin),
       (eq, "$coop_mp_phase", 4),
       (assign, reg20, "$coop_mp_winner"),
       (str_store_string, s12, "@&w={reg20}&r="),
       (try_for_range, ":i", 0, "$coop_mp_n"),
         ] + stack_slot(S_FALLEN) + [
         (troop_get_slot, reg21, MP_ARR, ":slot"),
         (gt, reg21, 0),
         (assign, reg20, ":i"),
         (str_store_string, s12, "@{s12}{reg20},{reg21};"),
       (try_end),
       # each hero's health: player, percent
       (str_store_string, s12, "@{s12}&hp="),
       (try_for_range, ":player_no", 0, ":num_players"),
         (player_is_active, ":player_no"),
         (player_get_slot, reg21, ":player_no", slot_player_coop_health),
         (gt, reg21, 0),
         (val_sub, reg21, 1),
         (assign, reg20, ":player_no"),
         (str_store_string, s12, "@{s12}{reg20},{reg21};"),
       (try_end),
       # how each hero fought: player, proficiency, hits, damage
       (str_store_string, s12, "@{s12}&wx="),
       (try_for_range, ":player_no", 0, ":num_players"),
         (player_is_active, ":player_no"),
         (try_for_range, ":wpt", 0, coop_hero_profs),
           (store_add, ":slot", slot_player_coop_hits, ":wpt"),
           (player_get_slot, reg22, ":player_no", ":slot"),
           (gt, reg22, 0),
           (store_add, ":slot", slot_player_coop_damage, ":wpt"),
           (player_get_slot, reg23, ":player_no", ":slot"),
           (assign, reg20, ":player_no"),
           (assign, reg21, ":wpt"),
           (str_store_string, s12, "@{s12}{reg20},{reg21},{reg22},{reg23};"),
         (try_end),
       (try_end),
       # the opponents each hero beat in a joint event: player, count
       (str_store_string, s12, "@{s12}&kl="),
       (try_for_range, ":player_no", 0, ":num_players"),
         (player_is_active, ":player_no"),
         (player_get_slot, reg21, ":player_no", slot_player_coop_kills),
         (gt, reg21, 0),
         (assign, reg20, ":player_no"),
         (str_store_string, s12, "@{s12}{reg20},{reg21};"),
       (try_end),
     (try_end),
     (val_add, "$coop_mp_seq", 1),
     (assign, reg20, "$coop_mp_seq"),
     (assign, reg21, "$coop_mp_phase"),
     (assign, reg22, "$coop_mp_battle"),
     (str_store_string, s10, "@" + coop_mp_url + "/mp?seq={reg20}&st={reg21}&bid={reg22}{s12}&pl={s11}"),
    ]),
]


def mp_reply_hook():
  """Prepended to game_receive_url_response: multiplayer replies never reach the campaign code."""
  copy = [(troop_set_slot, MP_BUF, i, reg(i)) for i in range(coop_net_max_numbers)]
  return [
    (try_begin),
      (multiplayer_is_server),
      (store_script_param, ":mp_num_integers", 1),
      (ge, ":mp_num_integers", 2),
      (eq, reg0, coop_mp_marker),
      ] + copy + [
      (call_script, "script_coop_mp_reply"),
    (try_end),
  ]


mp_battle_triggers = [
  # every player's game: the team window waits for the server's word on the team picked; when it
  # never comes the window hangs (clicks on the banners do nothing). After a few seconds without an
  # answer the pick counts as confirmed (a refusal still comes back as one). No team limit here either.
  (1, 0, 0, [(neg | multiplayer_is_dedicated_server)],
   [
     (try_begin),
       (neq, "$g_multiplayer_auto_team_balance_limit", 1000),
       (assign, "$g_multiplayer_auto_team_balance_limit", 1000),
     (try_end),
     # while the team window is open: what it waits for, every few seconds (to find why it hangs)
     (try_begin),
       (is_presentation_active, "prsnt_multiplayer_team_select"),
       (val_add, "$coop_mp_team_window_s", 1),
       (store_mod, ":every", "$coop_mp_team_window_s", 5),
       (eq, ":every", 0),
       (multiplayer_get_my_player, ":me"),
       (assign, reg20, "$g_waiting_for_confirmation_to_terminate"),
       (assign, reg21, "$g_confirmation_result"),
       (assign, reg22, -1),
       (try_begin),
         (ge, ":me", 0),
         (player_get_team_no, reg22, ":me"),
       (try_end),
       (assign, reg23, "$g_multiplayer_auto_team_balance_limit"),
       (assign, reg24, coop_build_id),
       (display_message, "@CoopWorld [team window]: waiting {reg20}, answer {reg21}, my team {reg22}, limit {reg23}, build {reg24}", 0xFFDD66),
     (else_try),
       (assign, "$coop_mp_team_window_s", 0),
     (try_end),
     (try_begin),
       (eq, "$g_waiting_for_confirmation_to_terminate", 1),
       (eq, "$g_confirmation_result", 0),
       (val_add, "$coop_mp_confirm_wait", 1),
       (ge, "$coop_mp_confirm_wait", coop_mp_confirm_wait_s),
       (assign, "$coop_mp_confirm_wait", 0),
       (assign, "$g_confirmation_result", 1),
       (display_message, "@CoopWorld: team taken as picked (no word from the server).", 0xFFDD66),
     (else_try),
       (assign, "$coop_mp_confirm_wait", 0),
     (try_end),
    ]),
  # no team limit: the players of a campaign battle often stand on one side. A window that had a
  # campaign loaded also carries that save's globals, where the limit is 0 and no team could be
  # picked at all
  (1, 0, 0, [(multiplayer_is_server), (neq, "$g_multiplayer_auto_team_balance_limit", 1000)],
   [
     (assign, "$g_multiplayer_auto_team_balance_limit", 1000),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 1, ":num_players"), #0 is the server itself
       (player_is_active, ":player_no"),
       (multiplayer_send_int_to_player, ":player_no", multiplayer_event_return_auto_team_balance_limit, 1000),
     (try_end),
    ]),
  # ask the bridge; while a request is out, ask again only after a while (a lost reply)
  (0.5, 0, 0, [(multiplayer_is_server)],
   [
     (val_add, "$coop_mp_frames", 1),
     (try_begin),
       (this_or_next|eq, "$coop_mp_pending", 0),
       (ge, "$coop_mp_frames", 10),
       (assign, "$coop_mp_pending", 1),
       (assign, "$coop_mp_frames", 0),
       (call_script, "script_coop_mp_request"),
       (send_message_to_url, s10),
     (try_end),
    ]),

  # phase 5 -> 2: the battle's own mission is up (its first round runs already)
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 5),
     (store_mission_timer_a, ":seconds"),
     (ge, ":seconds", coop_mp_switch_wait),
   ],
   [
     (call_script, "script_coop_mp_assign_teams"),
     (assign, "$g_multiplayer_round_max_seconds", coop_mp_round_seconds),
     (call_script, "script_coop_mp_go"),
    ]),

  # a siege ends when one side has nobody standing, bots and heroes (Siege brings players back, but a
  # fallen hero stays out)
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (eq, "$coop_mp_mode", 1),
     (eq, "$g_round_ended", 0),
   ],
   [
     (assign, ":had_0", 0),
     (assign, ":had_1", 0),
     (try_for_range, ":i", 0, "$coop_mp_n"),
       ] + stack_slot(S_TEAM) + [
       (troop_get_slot, ":team", MP_ARR, ":slot"),
       (try_begin),
         (eq, ":team", 0),
         (assign, ":had_0", 1),
       (else_try),
         (assign, ":had_1", 1),
       (try_end),
     (try_end),
     (try_for_range, ":k", 0, "$coop_mp_pairs"), #the players' heroes are there too
       (store_mul, ":src", ":k", 2),
       (val_add, ":src", coop_mp_pairs_slot + 1),
       (troop_slot_eq, MP_ARR, ":src", 1),
       (assign, ":had_1", 1),
     (try_end),
     (assign, ":alive_0", 0),
     (assign, ":alive_1", 0),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_is_human, ":agent_no"),
       (assign, ":counts", 0),
       (try_begin),
         (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1), #a bot of the campaign's armies
         (assign, ":counts", 1),
       (else_try),
         (neg|agent_is_non_player, ":agent_no"), #a player's hero
         (agent_get_player_id, ":player_no", ":agent_no"),
         (ge, ":player_no", 0),
         (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
         (assign, ":counts", 1),
       (try_end),
       (eq, ":counts", 1),
       (agent_get_team, ":team", ":agent_no"),
       (try_begin),
         (eq, ":team", 0),
         (val_add, ":alive_0", 1),
       (else_try),
         (val_add, ":alive_1", 1),
       (try_end),
     (try_end),
     (assign, ":winner", -1),
     (try_begin),
       (eq, ":had_1", 1),
       (eq, ":alive_1", 0),
       (assign, ":winner", 0), #the storm is broken
     (else_try),
       (eq, ":alive_0", 0),
       (assign, ":winner", 1), #the walls are empty
     (try_end),
     (ge, ":winner", 0),
     (assign, "$g_winner_team", ":winner"),
     (store_mission_timer_a, "$g_round_finish_time"),
     (assign, "$g_round_ended", 1),
     (assign, ":unused", ":had_0"),
    ]),

  # phase 1 -> 2: the new round has started
  (0.5, 0, 0, [(multiplayer_is_server), (eq, "$coop_mp_phase", 1), (eq, "$g_round_ended", 0)],
   [
     (call_script, "script_coop_mp_go"),
    ]),

  # an arena or a tournament ends here: Native counts teams 0 and 1 only, it would end one with a third
  # team on the sand or with the next fighters still to come. The players are beaten when their last hero
  # falls; none having fallen yet, the check for no hero at all below sees to it.
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (is_between, "$coop_mp_phase", 2, 4),
     (gt, "$coop_mp_team_event", 0),
     (eq, "$g_round_ended", 0),
   ],
   [
     (assign, ":heroes", 0),
     (assign, ":fallen", 0),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 0, ":num_players"),
       (player_is_active, ":player_no"),
       (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
       (try_begin),
         (player_slot_eq, ":player_no", slot_player_coop_fallen, 0),
         (val_add, ":heroes", 1),
       (else_try),
         (val_add, ":fallen", 1),
       (try_end),
     (try_end),
     (assign, ":foes", 0),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_is_human, ":agent_no"),
       (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
       (agent_get_team, ":team", ":agent_no"),
       (neq, ":team", 0),
       (val_add, ":foes", 1),
     (try_end),
     (assign, ":winner", -1),
     (try_begin),
       (eq, ":heroes", 0),
       (gt, ":fallen", 0),
       (assign, ":winner", 1),
     (else_try),
       (eq, "$coop_mp_phase", 3), #all came
       (eq, ":foes", 0),
       (assign, ":winner", 0),
     (try_end),
     (ge, ":winner", 0),
     (assign, "$g_winner_team", ":winner"),
     (store_mission_timer_a, "$g_round_finish_time"),
     (assign, "$g_round_ended", 1),
    ]),

  # while a campaign battle is on: a player who was still loading its map when the sides were set (or
  # who left and came back) gets the side and the hero again; a side is changed only before spawning
  (1, 0, 0, [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4), (eq, "$g_round_ended", 0)],
   [
     (try_for_range, ":k", 0, "$coop_mp_heroes"),
       (store_add, ":kept_at", coop_mp_heroes_slot, ":k"),
       (troop_get_slot, ":player_no", MP_ARR, ":kept_at"),
       (player_is_active, ":player_no"),
       (store_add, ":hero", ":k", 1),
       (neg|player_slot_eq, ":player_no", slot_player_coop_hero, ":hero"),
       (player_set_slot, ":player_no", slot_player_coop_hero, ":hero"),
     (try_end),
     (try_for_range, ":k", 0, "$coop_mp_pairs"),
       (store_mul, ":src", ":k", 2),
       (val_add, ":src", coop_mp_pairs_slot),
       (troop_get_slot, ":player_no", MP_ARR, ":src"),
       (val_add, ":src", 1),
       (troop_get_slot, ":team", MP_ARR, ":src"),
       (player_is_active, ":player_no"),
       (player_slot_eq, ":player_no", slot_player_coop_fallen, 0),
       (player_get_agent_id, ":agent_no", ":player_no"),
       (this_or_next|lt, ":agent_no", 0),
       (neg|agent_is_alive, ":agent_no"),
       (call_script, "script_coop_mp_put_on_side", ":player_no", ":team"),
     (try_end),
    ]),

  # a hero who falls stays out of the battle (Native's spawn checks slot_player_coop_fallen)
  (ti_on_agent_killed_or_wounded, 0, 0,
   [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4)],
   [
     (store_trigger_param_1, ":agent_no"),
     (agent_is_human, ":agent_no"),
     (neg|agent_is_non_player, ":agent_no"),
     (agent_get_player_id, ":player_no", ":agent_no"),
     (ge, ":player_no", 0),
     (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
     (player_set_slot, ":player_no", slot_player_coop_fallen, 1),
     (str_store_player_username, s1, ":player_no"),
     (str_store_string, s0, "@CoopWorld: {s1}'s hero has fallen and does not come back to this battle."),
     (call_script, "script_coop_mp_tell_all"),
    ]),

  # a joint event: the opponents a hero beats count for that player (the arena's prize goes by them)
  (ti_on_agent_killed_or_wounded, 0, 0,
   [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4), (ge, "$coop_mp_mode", coop_mp_mode_arena)],
   [
     (store_trigger_param_1, ":agent_no"),
     (store_trigger_param_2, ":killer"),
     (ge, ":killer", 0),
     (agent_is_human, ":agent_no"),
     (agent_is_non_player, ":agent_no"),
     (agent_is_human, ":killer"),
     (neg|agent_is_non_player, ":killer"),
     (agent_get_player_id, ":player_no", ":killer"),
     (ge, ":player_no", 0),
     (player_get_slot, ":kills", ":player_no", slot_player_coop_kills),
     (val_add, ":kills", 1),
     (player_set_slot, ":player_no", slot_player_coop_kills, ":kills"),
    ]),

  # a joint event is fought by the heroes alone: with none left on the server (all gone from it)
  # the bots would stand there for good and no battle could start again
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (is_between, "$coop_mp_phase", 2, 4),
     (ge, "$coop_mp_mode", coop_mp_mode_arena),
     (eq, "$g_round_ended", 0),
   ],
   [
     (assign, ":heroes", 0),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 0, ":num_players"),
       (player_is_active, ":player_no"),
       (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
       (player_slot_eq, ":player_no", slot_player_coop_fallen, 0),
       (val_add, ":heroes", 1),
     (try_end),
     (try_begin),
       (gt, ":heroes", 0),
       (assign, "$coop_mp_no_hero_left", 0),
     (else_try),
       (val_add, "$coop_mp_no_hero_left", 1),
       (ge, "$coop_mp_no_hero_left", coop_mp_no_hero_s),
       (assign, "$coop_mp_no_hero_left", 0),
       (assign, "$g_winner_team", 1),
       (try_begin),
         (eq, "$coop_mp_mode", coop_mp_mode_duel), #nobody beat anybody: a draw
         (assign, "$g_winner_team", -1),
       (try_end),
       (store_mission_timer_a, "$g_round_finish_time"),
       (assign, "$g_round_ended", 1),
     (try_end),
    ]),

  # a joint event's rules again, for a player who was still loading the map when they went out
  (5, 0, 0, [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4), (gt, "$coop_mp_team_event", 0)],
   [
     (call_script, "script_coop_mp_team_event_tell", "$coop_mp_team_event"),
    ]),

  # a bot asked for never came and the game does not say so: the ones after it, and the next round's,
  # would wait for it for good
  (1, 0, 0,
   [(multiplayer_is_server), (eq, "$coop_mp_phase", 2), (eq, "$g_multiplayer_ready_for_spawning_agent", 0)],
   [
     (val_add, "$coop_mp_spawn_wait", 1),
     (ge, "$coop_mp_spawn_wait", coop_mp_spawn_wait_s),
     (assign, "$coop_mp_spawn_wait", 0),
     (assign, "$g_multiplayer_ready_for_spawning_agent", 1),
     (display_message, "@CoopWorld: a fighter did not come, the next one goes on.", 0xFFDD66),
    ]),

  # phase 2: one bot a frame, as Native spawns bots
  (0, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 2),
     (eq, "$g_multiplayer_ready_for_spawning_agent", 1),
     (call_script, "script_cf_coop_mp_bot_may_spawn"),
   ],
   [
     (assign, ":i", "$coop_mp_spawn_i"),
     (assign, ":found", -1),
     (try_for_range, ":i", "$coop_mp_spawn_i", "$coop_mp_n"),
       (eq, ":found", -1),
       ] + stack_slot(S_SPAWNED) + [
       (troop_get_slot, ":spawned", MP_ARR, ":slot"),
       ] + stack_slot(S_COUNT) + [
       (troop_get_slot, ":count", MP_ARR, ":slot"),
       (lt, ":spawned", ":count"),
       (assign, ":found", ":i"),
     (try_end),
     (try_begin),
       (eq, ":found", -1),
       (assign, "$coop_mp_phase", 3),
       (try_begin),
         (lt, "$coop_mp_mode", coop_mp_mode_arena),
         (str_store_string, s0, "@CoopWorld: all troops are on the field. To battle!"),
         (call_script, "script_coop_mp_tell_all"),
       (try_end),
       (try_begin),
         (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
         (call_script, "script_coop_mp_raise_ladders"),
         (assign, "$coop_mp_ladders_s", 0),
         # the bots storm and hold the walls on foot: a horse that came all the same is told
         (assign, ":mounted", 0),
         (try_for_agents, ":agent_no"),
           (agent_is_human, ":agent_no"),
           (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
           (agent_get_horse, ":horse", ":agent_no"),
           (ge, ":horse", 0),
           (val_add, ":mounted", 1),
         (try_end),
         (gt, ":mounted", 0),
         (assign, reg20, ":mounted"),
         (str_store_string, s0, "@CoopWorld: {reg20} bots came on horses all the same."),
         (call_script, "script_coop_mp_tell_all"),
       (try_end),
     (else_try),
       (assign, ":i", ":found"),
       (assign, "$coop_mp_spawn_i", ":i"),
       ] + stack_slot(S_SPAWNED) + [
       (troop_get_slot, ":spawned", MP_ARR, ":slot"),
       (val_add, ":spawned", 1),
       (troop_set_slot, MP_ARR, ":slot", ":spawned"),
       ] + stack_slot(S_TROOP) + [
       (troop_get_slot, ":troop", MP_ARR, ":slot"),
       ] + stack_slot(S_TEAM) + [
       (troop_get_slot, ":team", MP_ARR, ":slot"),
       ] + stack_slot(S_GROUP) + [
       (troop_get_slot, ":group", MP_ARR, ":slot"),
       (try_begin),
         (neg|player_is_active, ":group"),
         (assign, ":group", -1), #its player is not here: the AI leads it
       (try_end),
       (try_begin),
         (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
         (eq, ":team", 0), #the garrison: inside the walls, where Siege puts its defenders
         (call_script, "script_multiplayer_find_spawn_point", 0, 1, 0),
         (assign, ":entry", reg0),
       (else_try),
         (eq, ":team", 0),
         (assign, ":entry", multi_initial_spawn_point_team_1),
       (else_try),
         (assign, ":entry", multi_initial_spawn_point_team_2),
       (try_end),
       (try_begin),
         (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
         (mission_tpl_entry_set_override_flags, "mt_multiplayer_sg", ":entry", af_override_horse), #on foot
       (try_end),
       (try_begin),
         (ge, "$coop_mp_mode", coop_mp_mode_arena),
         (call_script, "script_coop_mp_event_bot_gear", ":team", "$coop_mp_event_turn"),
         (assign, ":entry", reg0),
         (val_add, "$coop_mp_event_turn", 1),
       (try_end),
       (assign, "$coop_mp_spawning_stack", ":i"),
       (store_current_scene, ":cur_scene"),
       (modify_visitors_at_site, ":cur_scene"),
       (store_mod, ":visitor_team", ":team", 2), #no bot ever comes for a team above 1: ti_on_agent_spawn sets it
       (val_min, ":visitor_team", ":team"),
       (add_visitors_to_current_scene, ":entry", ":troop", 1, ":visitor_team", ":group"),
       (assign, "$g_multiplayer_ready_for_spawning_agent", 0),
     (try_end),
    ]),

  # a hero's blow: the kind of weapon it was learns from it (Native raises proficiency for hits)
  (ti_on_agent_hit, 0, 0, [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4)],
   [
     (assign, ":item", reg0), #the weapon, before any operation changes reg0
     (store_trigger_param_1, ":victim"),
     (store_trigger_param_2, ":attacker"),
     (store_trigger_param_3, ":damage"),
     (ge, ":attacker", 0),
     (ge, ":item", 0),
     (agent_is_human, ":attacker"),
     (neg|agent_is_non_player, ":attacker"),
     (agent_get_player_id, ":player_no", ":attacker"),
     (ge, ":player_no", 0),
     (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
     (agent_get_team, ":attacker_team", ":attacker"),
     (agent_get_team, ":victim_team", ":victim"),
     (neq, ":attacker_team", ":victim_team"), #hitting friends teaches nothing
     (item_get_type, ":type", ":item"),
     (assign, ":wpt", -1),
     (try_begin),
       (eq, ":type", itp_type_one_handed_wpn),
       (assign, ":wpt", wpt_one_handed_weapon),
     (else_try),
       (eq, ":type", itp_type_two_handed_wpn),
       (assign, ":wpt", wpt_two_handed_weapon),
     (else_try),
       (eq, ":type", itp_type_polearm),
       (assign, ":wpt", wpt_polearm),
     (else_try),
       (this_or_next|eq, ":type", itp_type_bow),
       (eq, ":type", itp_type_arrows),
       (assign, ":wpt", wpt_archery),
     (else_try),
       (this_or_next|eq, ":type", itp_type_crossbow),
       (eq, ":type", itp_type_bolts),
       (assign, ":wpt", wpt_crossbow),
     (else_try),
       (eq, ":type", itp_type_thrown),
       (assign, ":wpt", wpt_throwing),
     (else_try),
       (this_or_next|eq, ":type", itp_type_pistol),
       (this_or_next|eq, ":type", itp_type_musket),
       (eq, ":type", itp_type_bullets),
       (assign, ":wpt", wpt_firearm),
     (try_end),
     (ge, ":wpt", 0),
     (store_add, ":slot", slot_player_coop_hits, ":wpt"),
     (player_get_slot, ":hits", ":player_no", ":slot"),
     (val_add, ":hits", 1),
     (player_set_slot, ":player_no", ":slot", ":hits"),
     (store_add, ":slot", slot_player_coop_damage, ":wpt"),
     (player_get_slot, ":sum", ":player_no", ":slot"),
     (val_add, ":sum", ":damage"),
     (player_set_slot, ":player_no", ":slot", ":sum"),
    ]),

  # which stack a bot belongs to
  (ti_on_agent_spawn, 0, 0, [(multiplayer_is_server), (eq, "$coop_mp_phase", 2)],
   [
     (store_trigger_param_1, ":agent_no"),
     (agent_is_human, ":agent_no"),
     (agent_is_non_player, ":agent_no"),
     (assign, "$coop_mp_spawn_wait", 0),
     (store_add, ":tag", "$coop_mp_spawning_stack", 1),
     (agent_set_slot, ":agent_no", slot_agent_coop_stack, ":tag"),
     (assign, ":i", "$coop_mp_spawning_stack"),
     ] + stack_slot(S_TEAM) + [
     (troop_get_slot, ":team", MP_ARR, ":slot"),
     (try_begin),
       (agent_get_team, ":now", ":agent_no"),
       (neq, ":now", ":team"), #the entry point's own team came first
       (agent_set_team, ":agent_no", ":team"),
     (try_end),
     ] + [(agent_set_slot, ":agent_no", slot, 0) for slot in
          (slot_agent_coop_x, slot_agent_coop_y, slot_agent_coop_still, slot_agent_coop_ladder,
           slot_agent_coop_tries)] + [
    ]),

  # a hero or companion from the campaign comes with its hit points there (the most, and now)
  (ti_on_agent_spawn, 0, 0, [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4)],
   [
     (store_trigger_param_1, ":agent_no"),
     (agent_is_human, ":agent_no"),
     (agent_get_troop_id, ":troop", ":agent_no"),
     (ge, ":troop", 0),
     (troop_get_slot, ":max", ":troop", slot_troop_coop_mp_hp_max),
     (gt, ":max", 0),
     (troop_get_slot, ":hp", ":troop", slot_troop_coop_mp_hp),
     (val_max, ":hp", 1),
     (val_min, ":hp", ":max"),
     (agent_set_max_hit_points, ":agent_no", ":max", 1),
     (agent_set_hit_points, ":agent_no", ":hp", 1),
    ]),

  # a siege: a ladder pushed off the wall goes up again after a while
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
     (eq, "$g_round_ended", 0),
   ],
   [
     (val_add, "$coop_mp_ladders_s", 1),
     (ge, "$coop_mp_ladders_s", coop_mp_ladders_s),
     (assign, "$coop_mp_ladders_s", 0),
     (call_script, "script_coop_mp_raise_ladders"),
    ]),

  # a siege: storming bots that stand under the walls go to the ladders
  (2, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
     (eq, "$g_round_ended", 0),
   ],
   [
     (call_script, "script_coop_mp_storm"),
    ]),

  (ti_on_agent_killed_or_wounded, 0, 0,
   [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4)],
   [
     (store_trigger_param_1, ":agent_no"),
     (agent_get_slot, ":tag", ":agent_no", slot_agent_coop_stack),
     (gt, ":tag", 0),
     (store_sub, ":i", ":tag", 1),
     ] + stack_slot(S_FALLEN) + [
     (troop_get_slot, ":fallen", MP_ARR, ":slot"),
     (val_add, ":fallen", 1),
     (troop_set_slot, MP_ARR, ":slot", ":fallen"),
     (agent_set_slot, ":agent_no", slot_agent_coop_stack, 0),
    ]),

  # the round ended: one side has nobody left standing (or the long round ran out)
  (1, 0, 0,
   [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4), (eq, "$g_round_ended", 1)],
   [
     (assign, "$coop_mp_winner", "$g_winner_team"),
     (assign, "$g_multiplayer_round_max_seconds", "$coop_mp_old_round_seconds"),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 0, ":num_players"),
       (player_is_active, ":player_no"),
       (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
       # the hero's wounds go back to the campaign: health in percent, 0 if the hero fell
       (assign, ":health", 0),
       (try_begin),
         (player_get_agent_id, ":agent_no", ":player_no"),
         (ge, ":agent_no", 0),
         (agent_is_alive, ":agent_no"),
         (store_agent_hit_points, ":health", ":agent_no"),
       (try_end),
       (val_add, ":health", 1),
       (player_set_slot, ":player_no", slot_player_coop_health, ":health"),
       (player_set_slot, ":player_no", slot_player_coop_hero, 0),
       (player_set_slot, ":player_no", slot_player_coop_fallen, 0),
       (neq, "$coop_mp_mode", coop_mp_mode_tournament), #its next round may follow: kind 4 tells
       (player_set_troop_id, ":player_no", -1), #picks a class of the ordinary game again
       (multiplayer_send_message_to_player, ":player_no", multiplayer_event_force_start_team_selection),
     (try_end),
     (assign, "$coop_mp_phase", 4),
     (call_script, "script_coop_mp_horses_back"),
     (call_script, "script_coop_mp_gear_back"),
     (call_script, "script_coop_mp_team_event_tell", 0),
     (assign, "$coop_mp_pending", 0), #report at once
     (str_store_string, s0, "@CoopWorld: the battle is over. The outcome goes back to the campaign."),
     (call_script, "script_coop_mp_tell_all"),
    ]),
]


def mp_network_hook():
  """Prepended to game_receive_network_message: a hero's stats, sent by the battle server; and the
  team picked by the player of a server started from the game (not a dedicated one)."""
  return [
    # That player and the server share one player: the team window sets the new team before its
    # request is handled, Native then sees no change and never confirms, and the window waits for
    # good (clicks on the banners do nothing). The shared confirmation is given here.
    (try_begin),
      (multiplayer_is_server),
      (store_script_param, ":coop_event", 2),
      (eq, ":coop_event", multiplayer_event_change_team_no),
      (store_script_param, ":coop_player", 1),
      (multiplayer_get_my_player, ":coop_me"),
      (eq, ":coop_player", ":coop_me"),
      (store_script_param, ":coop_team", 3),
      (is_between, ":coop_team", 0, multi_team_spectator),
      (player_get_team_no, ":coop_now", ":coop_player"),
      (eq, ":coop_now", ":coop_team"),
      (eq, "$g_waiting_for_confirmation_to_terminate", 1),
      (eq, "$g_confirmation_result", 0),
      (store_mission_timer_a, ":coop_time"),
      (player_set_slot, ":coop_player", slot_player_last_team_select_time, ":coop_time"),
      (assign, "$g_confirmation_result", 1),
    (try_end),
    (try_begin),
      (neg|multiplayer_is_server),
      (store_script_param, ":coop_event", 2),
      (eq, ":coop_event", coop_mp_event_hero_stat),
      (store_script_param, ":coop_troop", 3),
      (store_script_param, ":coop_code", 4),
      (store_script_param, ":coop_value", 5),
      (call_script, "script_coop_mp_hero_stat", ":coop_troop", ":coop_code", ":coop_value"),
    (try_end),
  ]


def merge_battle_template(mission_templates):
  """The Battle and Siege game types: the campaign's battles run in them; a hero player spawns
  as the hero."""
  from coop_merge import get_by_id, MergeError
  buy = (call_script, "script_multiplayer_buy_agent_equipment", ":player_no")
  may_spawn = (player_slot_eq, ":player_no", slot_player_spawned_this_round, 0)
  spawn_new = (eq, ":spawn_new", 1)
  round_over = (this_or_next|eq, ":team1_living_players", 0)
  for template_id in ("multiplayer_bt", "multiplayer_sg"):
    template_triggers = get_by_id(mission_templates, template_id)[5]
    found = 0
    gates = 0
    late = 0
    counts = 0
    for trigger in template_triggers:
      block = trigger[4]
      i = 0
      while i < len(block):
        op = block[i]
        if op == may_spawn:  # in a campaign battle only a hero spawns, and a fallen one does not again
          block.insert(i + 1, (call_script, "script_cf_coop_mp_may_spawn", ":player_no"))
          gates += 1
          i += 1
        elif op == round_over and template_id == "multiplayer_bt":  # see "an arena or a tournament ends here"
          block.insert(i, (eq, "$coop_mp_team_event", 0))
          counts += 1
          i += 1
        elif op == spawn_new and template_id == "multiplayer_bt":  # Battle lets players spawn only in a round's first seconds: a hero later too
          block[i:i] = [
            (try_begin),
              (eq, ":spawn_new", 0),
              (eq, "$g_round_ended", 0),
              (call_script, "script_cf_coop_mp_late_hero", ":player_no"),
              (assign, ":spawn_new", 1),
            (try_end),
          ]
          late += 1
          i += 6
        elif op == buy:  # the player is about to spawn (Siege picks the spawn point in between)
          block[i:i + 1] = [
            (try_begin),
              (call_script, "script_cf_coop_mp_hero_spawn", ":player_no"),
            (else_try),
              buy,
            (try_end),
          ]
          found += 1
          i += 5
        i += 1
    if found < 1:
      raise MergeError(f"{template_id}: expected a player spawn buying equipment, found none")
    if gates != 1:
      raise MergeError(f"{template_id}: expected one player spawn check, found {gates}")
    if template_id == "multiplayer_bt" and late != 1:
      raise MergeError(f"{template_id}: expected one 'may a new agent spawn' check, found {late}")
    if template_id == "multiplayer_bt" and counts != 1:
      raise MergeError(f"{template_id}: expected one count of the living ending a round, found {counts}")
    template_triggers.extend(mp_battle_triggers)
