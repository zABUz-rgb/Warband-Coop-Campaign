from header_common import *
from header_operations import *
from header_mission_templates import *
from header_presentations import *
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
# stands (nor any to come); the defenders when no attacker bot stands. The bots fight on foot. The
# garrison spawns at points the attackers reach (DEFENDER_ENTRIES). Once the first troops are on the
# field the castle's room doors open (only a defender player opens them, never a bot: walls and yard
# were cut apart), the ladders go up and the siege towers stand at the walls (the AI mesh climbs the
# walls there); the storming bots go up them (script_coop_mp_storm), the garrison holds their tops and
# the flag (script_coop_mp_hold).
# A campaign battle (a field battle or a siege) puts coop_mp_field_bots of its men on the field at once,
# each side by its share; the others come in waves as their side falls (reinforcements).
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
# A raised ladder stands where the scene has it; its top is its length up its z axis (on the wall walk)
LADDER_LENGTH = {kind: int(kind.rsplit("_", 1)[1][:-1]) for kind in LADDERS}
# The siege towers (body, the bridge at its top): Native moves one only while players push it, and the AI
# mesh runs over it where it stands at the wall: the bots went there and stood under the wall
BELFRIES = [("spr_belfry_a", "spr_belfry_platform_a"), ("spr_belfry_b", "spr_belfry_b_platform_a")]
BELFRY_PARTS = ["spr_belfry_a", "spr_belfry_b", "spr_belfry_platform_a", "spr_belfry_platform_b",
                "spr_belfry_b_platform_a", "spr_belfry_wheel"]
# Room and tower doors only a defender opens (check_castle_door_use_trigger); a bot never does
ROOM_DOORS = ["spr_castle_f_door_a", "spr_castle_f_door_b"]
# The garrison's spawn points on each Siege map (of the mission's 0..63): on the part of the AI mesh that
# holds the flag with the room doors open, not above the walls, away from doors. Native's Siege puts
# walkers at high points, some behind doors: bots stood there for good (11-05). tools/siege_scenes.py
# reads them from the scenes.
DEFENDER_ENTRIES = {
  "scn_multi_scene_3": [0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 31, 34, 35, 36, 37, 38, 39, 40, 41,
                        42, 43, 44, 45, 46, 53, 56, 57, 58, 59, 60, 61, 63],
  "scn_multi_scene_10": [0, 1, 2, 3, 5, 6, 7, 8, 11, 12, 13, 15, 17, 18, 21, 22, 23, 24, 25, 26, 30, 31, 33, 34, 35,
                         36, 38, 39, 40, 41, 42, 43, 49, 50, 53, 54, 55, 56, 57, 59, 62],
  "scn_multi_scene_13": [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29,
                         31, 50, 51, 52, 53, 54, 55],
  "scn_multi_scene_16": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24, 26,
                         27, 28, 29, 30, 31],
}
# The garrison's horse spawns on each Siege map (11-07, the user's ask): entry points outside the walls, on the ground
# the attackers walk, away from their spawn where the map allows (scratchpad probe of the scenes with the AI mesh of
# tools/siege_scenes.py). A third of a garrison's horsemen ride out from here, so the walls never stand empty.
CAVALRY_ENTRIES = {
  "scn_multi_scene_3": [16, 17, 18, 49, 51, 62],
  "scn_multi_scene_10": [51, 14, 58, 10, 29, 37],
  "scn_multi_scene_13": [40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 56, 58, 59],
  "scn_multi_scene_16": [33, 34, 35, 36, 37],
}
# A Khergit town is stormed on the map with the most ground outside its walls; the storming bots start at its far edge
# (cm, ~190 m from the flag; the map's farthest entry point is 155 m off), and two of three of the garrison ride out
# The storming horsemen's spawns (11-07, the user's ask: a third of the attackers' horsemen ride up to the walls and
# storm on foot): entry points by the attackers' own, never the garrison's horse spawns (a spawn point's horse flag is
# one for all who come there)
ATTACKER_CAVALRY_ENTRIES = {
  "scn_multi_scene_3": [23, 25, 33],
  "scn_multi_scene_10": [45, 46, 47, 48, 60],
  "scn_multi_scene_13": [33, 34, 35, 36, 37, 38, 39, 62, 63],
  "scn_multi_scene_16": [46, 47, 48, 49, 55, 56, 57],
}
STEPPE_SCENE = "scn_multi_scene_3"
STEPPE_FAR_SPOTS = [(27000, 8100, 920), (27000, 5800, 650), (26600, 4200, 630), (27000, 17500, 1200)]
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
  (coop_mp_mode_arena, ["scn_multi_scene_17", "scn_multi_scene_18", "scn_multi_scene_11"]),  # The Arena,
  (coop_mp_mode_tournament, ["scn_multi_scene_17", "scn_multi_scene_18", "scn_multi_scene_11"]),  # Forest Hideout,
  (coop_mp_mode_training, ["scn_multi_scene_7"]),   # Field by the River                         # Nord Town
  (coop_mp_mode_duel, ["scn_multi_scene_17"]),
]
# An arena's or a tournament's map changes from one fight to the next (by the battle's number).
# The practice gear of a joint event: 0 one handed, 1 two handed, 2 polearm, 3 ranged, then more. The bots
# take the sets in turn, the heroes another one each round of an arena or a tournament. A training is
# sparring, by hand, as in Native (the first SPARRING_SETS only), each hero with the set nearest to its
# own weapons.
EVENT_SETS = [
  ["itm_practice_sword", "itm_practice_shield"],
  ["itm_heavy_practice_sword"],
  ["itm_practice_staff"],
  ["itm_practice_bow", "itm_practice_arrows", "itm_cudgel", "itm_practice_shield"],  # a club and a shield for the
  ["itm_practice_crossbow", "itm_practice_bolts", "itm_cudgel", "itm_practice_shield"],  # melee (11-06: no dagger)
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
# More places for each side on the maps of an arena or a tournament (entry points, read from their scenes with
# their AI mesh: on the ground, all reachable), the bots spread over them in turn; the first is the side's own.
EVENT_SPOTS = {
  "scn_multi_scene_17": {0: [36, 1, 44], 1: [32, 34, 17], 3: [37, 38, 7], 4: [52, 25, 29]},
  "scn_multi_scene_18": {0: [54, 55, 56], 1: [32, 36, 60], 3: [1, 5, 26], 4: [19, 23, 29]},
  "scn_multi_scene_11": {0: [2, 3, 10], 1: [16, 15, 1], 3: [17, 18, 21], 4: [12, 13, 11]},
}
EVENT_ENTRIES = sorted({e for side, entry, h, t in EVENT_SIDES for e in [entry]}
                       | {e for spots in EVENT_SPOTS.values() for entries in spots.values() for e in entries})
ARENA_SIDES = [1, 3, 4]    # an arena's fighters all are of team 1, enemies of each other: only their looks differ
EVENT_FIGHTER_ITEMS = ["itm_practice_sword", "itm_practice_shield", "itm_heavy_practice_sword",
                       "itm_practice_staff", "itm_arena_tunic_blue"]
# the windows of Native's multiplayer a player works in: the counter is not made anew over them
HUD_YIELDS = ["multiplayer_welcome_message", "multiplayer_team_select", "multiplayer_troop_select",
              "multiplayer_item_select", "multiplayer_escape_menu", "multiplayer_poll_menu",
              "multiplayer_show_players_list", "multiplayer_show_maps_list", "multiplayer_show_factions_list",
              "multiplayer_show_number_of_bots_list", "game_multiplayer_admin_panel"]
MP_BUF = "trp_temp_array_b"
S_TROOP, S_TEAM, S_GROUP, S_COUNT, S_FALLEN, S_SPAWNED = range(6)


def stack_slot(field):
  """Ops: ':slot' = the slot of `field` of stack ':i'."""
  return [
    (store_mul, ":slot", ":i", coop_mp_stride),
    (val_add, ":slot", field),
  ]


WAY_FOOT, WAY_TOP = 2, 5  # a way up the walls: kind, scene prop, foot x y z, top x y z


def way_pos(way, field, pos):
  """Ops: `pos` = the foot (WAY_FOOT) or the top (WAY_TOP) of way `way` (fixed point multiplier 100)."""
  return [
    (store_mul, ":wslot", way, 8),
    (val_add, ":wslot", coop_mp_ways_slot + field),
    (init_position, pos),
    (troop_get_slot, ":wv", MP_ARR, ":wslot"),
    (position_set_x, pos, ":wv"),
    (val_add, ":wslot", 1),
    (troop_get_slot, ":wv", MP_ARR, ":wslot"),
    (position_set_y, pos, ":wv"),
    (val_add, ":wslot", 1),
    (troop_get_slot, ":wv", MP_ARR, ":wslot"),
    (position_set_z, pos, ":wv"),
  ]


def way_kind(way, dest):
  """Ops: `dest` = the kind of way `way` up the walls: 0 a ladder, 1 a siege tower."""
  return [
    (store_mul, ":wslot", way, 8),
    (val_add, ":wslot", coop_mp_ways_slot),
    (troop_get_slot, dest, MP_ARR, ":wslot"),
  ]


def led_by_orders():
  """Ops for a bot ':agent_no' of a siege: fail while its player leads it by orders (slot_player_coop_orders):
  the storm and the hold leave it be then."""
  return [
    (agent_get_group, ":group", ":agent_no"),
    (assign, ":led", 0),
    (try_begin),
      (ge, ":group", 0),
      (player_is_active, ":group"),
      (player_slot_eq, ":group", slot_player_coop_orders, 1),
      (assign, ":led", 1),
    (try_end),
    (eq, ":led", 0),
  ]


def stuck_nudge(pos, autoset_z):
  """Ops in a storming bot's walk to `pos` (sent there): one that stood still coop_mp_storm_nudge_s is sent
  there again, a new path (bots stood at a siege tower's foot, 11-05)."""
  return [
    (agent_get_slot, ":stuck", ":agent_no", slot_agent_coop_stuck),
    (try_begin),
      (lt, ":moved", 100),
      (val_add, ":stuck", 2),
    (else_try),
      (assign, ":stuck", 0),
    (try_end),
    (try_begin),
      (ge, ":stuck", coop_mp_storm_nudge_s),
      (assign, ":stuck", 0),
      (agent_clear_scripted_mode, ":agent_no"),
      (agent_set_scripted_destination, ":agent_no", pos, autoset_z),
    (try_end),
    (agent_set_slot, ":agent_no", slot_agent_coop_stuck, ":stuck"),
  ]


def use_closed(kinds):
  """A script's ops: every scene prop of `kinds` still shut (a ladder lying on the ground, a door) is used
  as by a player: here and in every player's game."""
  return [
    (get_max_players, ":num_players"),
    ] + [op for kind in kinds for op in [
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
    ]]


def bot_look():
  """Ops, every 2 s, for bot ':agent_no' of a siege: pos1 and ':z' its place, ':moved' how far it went since
  the last look (cm), ':calm' counted down, ':still' and ':sent' from its slots (bot_save keeps them)."""
  return [
    (agent_get_position, pos1, ":agent_no"),
    (position_get_x, ":x", pos1),
    (position_get_y, ":y", pos1),
    (position_get_z, ":z", pos1),
    (agent_get_slot, ":old_x", ":agent_no", slot_agent_coop_x),
    (agent_get_slot, ":old_y", ":agent_no", slot_agent_coop_y),
    (agent_set_slot, ":agent_no", slot_agent_coop_x, ":x"),
    (agent_set_slot, ":agent_no", slot_agent_coop_y, ":y"),
    (store_sub, ":dx", ":x", ":old_x"),
    (val_abs, ":dx"),
    (store_sub, ":dy", ":y", ":old_y"),
    (val_abs, ":dy"),
    (store_add, ":moved", ":dx", ":dy"),
    (agent_get_slot, ":calm", ":agent_no", slot_agent_coop_calm),
    (val_sub, ":calm", 2),
    (val_max, ":calm", 0),
    (agent_get_slot, ":still", ":agent_no", slot_agent_coop_still),
    (agent_get_slot, ":sent", ":agent_no", slot_agent_coop_sent),
  ]


def bot_fight(radius):
  """Ops after bot_look: ':fight' 1 when the bot (team ':team') has an enemy on its level within `radius` cm,
  or only within coop_mp_reach while it is calm. Then its own AI leads it to the fight, and the point it was
  sent to is dropped (':sent' 0). One that stands coop_mp_storm_still_s at an enemy it does not reach
  (behind the bars of a gate) is calm for coop_mp_calm_s: it goes its way."""
  return [
    (assign, ":near", -1),
    (try_for_agents, ":other", pos1, radius),
      (agent_is_alive, ":other"),
      (agent_is_human, ":other"),
      (agent_get_team, ":other_team", ":other"),
      (neq, ":other_team", ":team"),
      (agent_get_position, pos2, ":other"),
      (position_get_z, ":other_z", pos2),
      (store_sub, ":dz", ":other_z", ":z"),
      (val_abs, ":dz"),
      (le, ":dz", coop_mp_hold_level),
      (get_distance_between_positions, ":dist", pos1, pos2),
      (this_or_next|lt, ":near", 0),
      (lt, ":dist", ":near"),
      (assign, ":near", ":dist"),
    (try_end),
    (assign, ":fight", 0),
    (try_begin),
      (ge, ":near", 0),
      (this_or_next|le, ":calm", 0),
      (le, ":near", coop_mp_reach),
      (assign, ":fight", 1),
      (try_begin),
        (eq, ":sent", 1),
        (agent_clear_scripted_mode, ":agent_no"),
        (assign, ":sent", 0),
      (try_end),
      (try_begin),
        (lt, ":moved", 100),
        (gt, ":near", coop_mp_reach),
        (val_add, ":still", 2),
      (else_try),
        (assign, ":still", 0),
      (try_end),
      (ge, ":still", coop_mp_storm_still_s),
      (assign, ":still", 0),
      (assign, ":calm", coop_mp_calm_s),
    (try_end),
  ]


def bot_save():
  """Ops: what bot_look read and the bot's script changed goes back to its slots."""
  return [
    (agent_set_slot, ":agent_no", slot_agent_coop_calm, ":calm"),
    (agent_set_slot, ":agent_no", slot_agent_coop_still, ":still"),
    (agent_set_slot, ":agent_no", slot_agent_coop_sent, ":sent"),
  ]


def storm_back():
  """Ops: a storming bot goes back to stage 0 and picks a way up at once (an archer too)."""
  return [
    (try_begin),
      (eq, ":sent", 1),
      (agent_clear_scripted_mode, ":agent_no"),
    (try_end),
    (assign, ":sent", 0),
    (assign, ":stage", 0),
    (assign, ":still", coop_mp_storm_shoot_s),
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
         (lt, ":item", all_items_end),
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
         (lt, ":item", all_items_end),
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
       (assign, "$coop_mp_steppe", 0),
       (try_begin),
         (eq, "$coop_mp_mode", 1),
         (ge, ":hint", coop_mp_steppe_hint), #a Khergit town (11-07)
         (val_sub, ":hint", coop_mp_steppe_hint),
         (assign, "$coop_mp_steppe", 1),
       (try_end),
       (assign, "$coop_mp_hint", ":hint"),
       (assign, "$coop_mp_def_turn", 0),
       (assign, "$coop_mp_cav_turn", 0),
       (assign, "$coop_mp_acav_turn", 0),
       (assign, "$coop_mp_lord_s", 0),
       # who started it (the bridge lists that player first): the AI's men of its side obey it (11-07)
       (assign, "$coop_mp_starter", -1),
       (assign, "$coop_mp_starter_team", -1),
       (try_begin),
         (troop_slot_ge, MP_BUF, 6, 1),
         (troop_get_slot, "$coop_mp_starter", MP_BUF, 7),
         (troop_get_slot, "$coop_mp_starter_team", MP_BUF, 8),
       (try_end),
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
         (try_begin),
           (eq, "$coop_mp_steppe", 1),
           (assign, ":scene", STEPPE_SCENE),
         (try_end),
       (else_try),
         (ge, "$coop_mp_mode", coop_mp_mode_arena),
         ] + [op for mode, scenes in EVENT_SCENES for op in [
         (try_begin),
           (eq, "$coop_mp_mode", mode),
           (store_mod, ":pick", "$coop_mp_battle", len(scenes)),
           ] + [op2 for k, scn in enumerate(scenes) for op2 in [
           (try_begin), (eq, ":pick", k), (assign, ":scene", scn), (try_end),
           ]] + [
         (try_end),
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
       (eq, ":code", coop_mp_stat_campaign), #the escape menu offers the retreat
       (assign, "$coop_mp_campaign_on", ":value"),
     (else_try),
       (eq, ":code", coop_mp_stat_foes), #the counter: the opponents still standing (sent last), -1 it goes
       (try_begin),
         (neq, "$coop_mp_hud_foes", ":value"),
         (assign, "$coop_mp_hud_dirty", 1),
       (try_end),
       (assign, "$coop_mp_hud_foes", ":value"),
       (try_begin),
         (lt, ":value", 0),
         (assign, "$coop_mp_hud_kind", 0),
       (try_end),
       (call_script, "script_coop_mp_hud_show"),
     (else_try),
       (eq, ":code", coop_mp_stat_kills), #and those this player beat
       (try_begin),
         (neq, "$coop_mp_hud_kills", ":value"),
         (assign, "$coop_mp_hud_dirty", 1),
       (try_end),
       (assign, "$coop_mp_hud_kills", ":value"),
     (else_try),
       (eq, ":code", coop_mp_stat_own_side), #a battle of the campaign: this player's side, standing and in reserve
       (try_begin),
         (this_or_next|neq, "$coop_mp_hud_own", ":troop"),
         (neq, "$coop_mp_hud_own_reserve", ":value"),
         (assign, "$coop_mp_hud_dirty", 1),
       (try_end),
       (assign, "$coop_mp_hud_own", ":troop"),
       (assign, "$coop_mp_hud_own_reserve", ":value"),
       (assign, "$coop_mp_hud_kind", 1),
     (else_try),
       (eq, ":code", coop_mp_stat_enemy_side), #and the other side
       (try_begin),
         (this_or_next|neq, "$coop_mp_hud_enemy", ":troop"),
         (neq, "$coop_mp_hud_enemy_reserve", ":value"),
         (assign, "$coop_mp_hud_dirty", 1),
       (try_end),
       (assign, "$coop_mp_hud_enemy", ":troop"),
       (assign, "$coop_mp_hud_enemy_reserve", ":value"),
     (else_try),
       (ge, ":code", coop_mp_stat_team_event), #a code of a later version: nothing here
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

  # script_coop_mp_hud_show: the counter shows what came last. A text overlay is centred by the text it is made with
  # (made empty, the counter's left edge stood in the middle of the screen, 11-06): a new value makes it anew.
  ("coop_mp_hud_show",
   [
     (try_begin),
       (ge, "$coop_mp_hud_foes", 0),
       (this_or_next|neg|is_presentation_active, "prsnt_coop_mp_hud"),
       (eq, "$coop_mp_hud_dirty", 1),
       # not over a window of the player's (the escape menu, the choice of a team...): it might close it. The
       # counter's own frame puts the text in meanwhile, and shows the window anew once that one is gone.
       ] + [(neg|is_presentation_active, f"prsnt_{p}") for p in HUD_YIELDS] + [
       (start_presentation, "prsnt_coop_mp_hud"),
     (try_end),
    ]),

  # script_coop_mp_hud_text: s0 = what the counter says: a joint event's opponents left, or a campaign battle's sides
  ("coop_mp_hud_text",
   [
     (try_begin),
       (eq, "$coop_mp_hud_kind", 1),
       (assign, reg0, "$coop_mp_hud_own"),
       (assign, reg1, "$coop_mp_hud_own_reserve"),
       (assign, reg2, "$coop_mp_hud_enemy"),
       (assign, reg3, "$coop_mp_hud_enemy_reserve"),
       (assign, reg4, "$coop_mp_hud_kills"),
       (str_store_string, s0, "@Your side: {reg0} standing, {reg1} in reserve     Enemy: {reg2} standing, {reg3} in reserve     Your kills: {reg4}"),
     (else_try),
       (assign, reg0, "$coop_mp_hud_foes"),
       (assign, reg1, "$coop_mp_hud_kills"),
       (str_store_string, s0, "@Opponents left: {reg0}     Your kills: {reg1}"),
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
     # the side's place on this map: the bots of a side take its places in turn
     (store_div, ":spot", ":turn", len(ARENA_SIDES)),
     (val_mod, ":spot", 3),
     ] + [op for scn, spots in EVENT_SPOTS.items() for side, entries in spots.items() for k, e in enumerate(entries)
          for op in [
     (try_begin),
       (eq, "$g_multiplayer_selected_map", scn),
       (eq, ":side", side),
       (eq, ":spot", k),
       (assign, ":entry", e),
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
     ] + [op for entry in EVENT_ENTRIES for op in [
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
     (call_script, "script_coop_mp_field_shares"),
     (assign, "$coop_mp_entries_n", 0),
     (assign, "$coop_mp_ways", 0),
     (try_begin),
       (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
       (call_script, "script_coop_mp_siege_entries"),
       (call_script, "script_coop_mp_find_ways"),
     (try_end),
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

  # script_coop_mp_tell_player: arg1 = a player: s0 to that player alone (0 is the server's own player)
  ("coop_mp_tell_player",
   [
     (store_script_param, ":player_no", 1),
     (try_begin),
       (eq, ":player_no", 0),
       (display_message, s0, 0xFFDD66),
     (else_try),
       (player_is_active, ":player_no"),
       (multiplayer_send_string_to_player, ":player_no", multiplayer_event_show_server_message, s0),
     (try_end),
    ]),

  # script_coop_mp_bot_to_take: arg1 = a player whose hero fell in a campaign battle, arg2 = its fallen agent; reg0 =
  # the bot it takes over (-1 none): its own soldier nearest to where it fell, else one the AI leads, else a friend's
  # (11-07: a friend with no men of its own left came back in none of the host's). Native's respawn as a bot takes
  # the player's own men only; Siege had nothing (11-05, the user's ask).
  ("coop_mp_bot_to_take",
   [
     (store_script_param, ":player_no", 1),
     (store_script_param, ":fallen", 2),
     (set_fixed_point_multiplier, 100),
     (player_get_team_no, ":team", ":player_no"),
     (agent_get_position, pos1, ":fallen"),
     (assign, ":best", -1),
     (assign, ":best_score", 0),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_is_human, ":agent_no"),
       (agent_is_non_player, ":agent_no"),
       (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
       (agent_get_team, ":agent_team", ":agent_no"),
       (eq, ":agent_team", ":team"),
       (agent_get_group, ":group", ":agent_no"),
       (assign, ":rank", 2), #a friend's soldier: the last choice
       (try_begin),
         (eq, ":group", ":player_no"),
         (assign, ":rank", 0),
       (else_try),
         (lt, ":group", 0),
         (assign, ":rank", 1),
       (else_try),
         (neg|player_is_active, ":group"), #its player left: the AI leads it
         (assign, ":rank", 1),
       (else_try),
         (player_get_agent_id, ":leader", ":group"), #not the soldier that friend itself controls now
         (eq, ":leader", ":agent_no"),
         (assign, ":rank", 3),
       (try_end),
       (lt, ":rank", 3),
       (agent_get_position, pos2, ":agent_no"),
       (get_distance_between_positions, ":score", pos1, pos2),
       (val_mul, ":rank", 10000000), #the AI's men only when none of its own stands, a friend's after them
       (val_add, ":score", ":rank"),
       (this_or_next|lt, ":best", 0),
       (lt, ":score", ":best_score"),
       (assign, ":best", ":agent_no"),
       (assign, ":best_score", ":score"),
     (try_end),
     (assign, reg0, ":best"),
    ]),

  # script_coop_mp_retreat: arg1 = a player who sounded the retreat (the escape menu), in any battle of the
  # campaign, on either side: the battle ends with nobody the winner, as when its time runs out. Nobody is taken
  # prisoner and the men still standing are kept: a storm fails and the siege goes on, defenders leave the walls
  # to the besiegers, a field battle's enemy keeps the field (11-05, the user's ask)
  ("coop_mp_retreat",
   [
     (store_script_param, ":player_no", 1),
     (try_begin),
       (eq, "$coop_mp_phase", 3),
       (lt, "$coop_mp_mode", coop_mp_mode_arena),
       (eq, "$g_round_ended", 0),
       (player_is_active, ":player_no"),
       (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
       (player_get_team_no, ":team", ":player_no"),
       (lt, ":team", multi_team_spectator),
       (str_store_player_username, s1, ":player_no"),
       (try_begin),
         (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
         (eq, ":team", 1),
         (str_store_string, s0, "@CoopWorld: {s1} sounds the retreat: the storm is over, the men still standing go back to the siege camp."),
       (else_try),
         (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
         (str_store_string, s0, "@CoopWorld: {s1} sounds the retreat: the walls are left to the enemy, the men still standing get away."),
       (else_try),
         (str_store_string, s0, "@CoopWorld: {s1} sounds the retreat: the battle is over, the men still standing get away and the enemy keeps the field."),
       (try_end),
       (call_script, "script_coop_mp_tell_all"),
       (assign, "$g_winner_team", -1), #nobody won: as a battle whose time ran out, nobody is taken prisoner
       (store_mission_timer_a, "$g_round_finish_time"),
       (assign, "$g_round_ended", 1),
     (else_try),
       (str_store_string, s0, "@CoopWorld: only a player of a campaign battle may sound the retreat."),
       (call_script, "script_coop_mp_tell_player", ":player_no"),
     (try_end),
    ]),

  # script_coop_mp_raise_ladders: every ladder lying on the ground goes up the wall, here and in every
  # player's game (as when a player raises it)
  ("coop_mp_raise_ladders", use_closed(LADDERS)),

  # script_coop_mp_open_doors: the castle's room and tower doors open, here and in every player's game.
  # Only a defender opens them, never a bot: walls and yard stood cut apart, and bots that came behind one
  # stayed there for good (11-05)
  ("coop_mp_open_doors", use_closed(ROOM_DOORS)),

  # script_coop_mp_place_belfries: the siege towers stand at the walls, their bridges down (where the scene
  # has them; Native moves one only while players push it)
  ("coop_mp_place_belfries",
   [
     (set_fixed_point_multiplier, 100),
     ] + [op for kind in BELFRY_PARTS for op in [
     (scene_prop_get_num_instances, ":num", kind),
     (try_for_range, ":k", 0, ":num"),
       (scene_prop_get_instance, ":instance", kind, ":k"),
       (prop_instance_stop_animating, ":instance"),
       (prop_instance_get_starting_position, pos1, ":instance"),
       (prop_instance_set_position, ":instance", pos1),
     (try_end),
     ]] + [op for body, _ in BELFRIES for op in [
     (scene_prop_get_num_instances, ":num", body),
     (try_for_range, ":k", 0, ":num"),
       (scene_prop_get_instance, ":instance", body, ":k"),
       (scene_prop_set_slot, ":instance", scene_prop_belfry_platform_moved, 1), #Native's push leaves it be
     (try_end),
     ]] + [
    ]),

  # script_coop_mp_siege_entries: the garrison's spawn points on this map (DEFENDER_ENTRIES), kept at
  # coop_mp_entries_slot; $coop_mp_entries_n of them (0: a map not in the list, Native's points then)
  ("coop_mp_siege_entries",
   [
     (assign, "$coop_mp_entries_n", 0),
     (store_current_scene, ":scene"),
     ] + [op for scene, entries in DEFENDER_ENTRIES.items() for op in [
     (try_begin),
       (eq, ":scene", scene),
       ] + [(troop_set_slot, MP_ARR, coop_mp_entries_slot + k, entry) for k, entry in enumerate(entries)] + [
       (assign, "$coop_mp_entries_n", len(entries)),
     (try_end),
     ]] + [
     (assign, "$coop_mp_acav_n", 0),
     ] + [op for scene, entries in ATTACKER_CAVALRY_ENTRIES.items() for op in [
     (try_begin),
       (eq, ":scene", scene),
       ] + [(troop_set_slot, MP_ARR, coop_mp_acav_slot + k, entry) for k, entry in enumerate(entries)] + [
       (assign, "$coop_mp_acav_n", len(entries)),
     (try_end),
     ]] + [
     (assign, "$coop_mp_cav_n", 0),
     ] + [op for scene, entries in CAVALRY_ENTRIES.items() for op in [
     (try_begin),
       (eq, ":scene", scene),
       ] + [(troop_set_slot, MP_ARR, coop_mp_cav_slot + k, entry) for k, entry in enumerate(entries)] + [
       (assign, "$coop_mp_cav_n", len(entries)),
     (try_end),
     ]] + [
    ]),

  # script_coop_mp_find_ways: the ways up the walls on this map ($coop_mp_ways of them): every ladder (its
  # foot and top where it stands raised) and every siege tower (its back on the ground, its bridge at the wall)
  ("coop_mp_find_ways",
   [
     (assign, "$coop_mp_ways", 0),
     (set_fixed_point_multiplier, 100),
     ] + [op for kind in LADDERS for op in [
     (scene_prop_get_num_instances, ":num", kind),
     (try_for_range, ":k", 0, ":num"),
       (scene_prop_get_instance, ":instance", kind, ":k"),
       (prop_instance_get_starting_position, pos1, ":instance"),
       (copy_position, pos2, pos1),
       (position_move_z, pos2, LADDER_LENGTH[kind] * 100),
       (call_script, "script_coop_mp_add_way", 0, ":instance"),
     (try_end),
     ]] + [op for body, bridge in BELFRIES for op in [
     (scene_prop_get_num_instances, ":num", body),
     (scene_prop_get_num_instances, ":bridges", bridge),
     (try_for_range, ":k", 0, ":num"),
       (scene_prop_get_instance, ":instance", body, ":k"),
       (prop_instance_get_starting_position, pos1, ":instance"),
       (copy_position, pos2, pos1),
       (position_move_y, pos1, -900),
       (position_move_y, pos2, 500),
       (try_begin),
         (lt, ":k", ":bridges"),
         (scene_prop_get_instance, ":bridge", bridge, ":k"),
         (prop_instance_get_starting_position, pos3, ":bridge"),
         (position_get_z, ":bridge_z", pos3),
         (position_set_z, pos2, ":bridge_z"),
       (try_end),
       (call_script, "script_coop_mp_add_way", 1, ":instance"),
     (try_end),
     ]] + [
    ]),

  # script_coop_mp_add_way: arg1 = kind (0 a ladder, 1 a siege tower), arg2 = its scene prop; pos1 its foot,
  # pos2 its top
  ("coop_mp_add_way",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":instance", 2),
     (set_fixed_point_multiplier, 100),
     (try_begin),
       (lt, "$coop_mp_ways", coop_mp_max_ways),
       (store_mul, ":slot", "$coop_mp_ways", 8),
       (val_add, ":slot", coop_mp_ways_slot),
       (troop_set_slot, MP_ARR, ":slot", ":kind"),
       (val_add, ":slot", 1),
       (troop_set_slot, MP_ARR, ":slot", ":instance"),
       ] + [op for pos in (pos1, pos2) for get in (position_get_x, position_get_y, position_get_z) for op in [
       (get, ":v", pos),
       (val_add, ":slot", 1),
       (troop_set_slot, MP_ARR, ":slot", ":v"),
       ]] + [
       (val_add, "$coop_mp_ways", 1),
     (try_end),
    ]),

  # script_cf_coop_mp_way_up: arg1 = a way up the walls. Succeeds while it can be climbed: a siege tower
  # always, a ladder while it stands raised
  ("cf_coop_mp_way_up",
   [
     (store_script_param, ":way", 1),
     (store_mul, ":slot", ":way", 8),
     (val_add, ":slot", coop_mp_ways_slot),
     (troop_get_slot, ":kind", MP_ARR, ":slot"),
     (val_add, ":slot", 1),
     (troop_get_slot, ":instance", MP_ARR, ":slot"),
     (this_or_next|eq, ":kind", 1),
     (scene_prop_slot_eq, ":instance", scene_prop_open_or_close_slot, 1),
    ]),

  # script_coop_mp_pick_way: arg1 = a storming bot; reg0 = the way up it goes to, -1 if none can be
  # climbed: the nearest, a crowded one counting farther; not the one it went last, while another stands
  ("coop_mp_pick_way",
   [
     (store_script_param, ":agent_no", 1),
     (set_fixed_point_multiplier, 100),
     (agent_get_position, pos4, ":agent_no"),
     (agent_get_slot, ":last", ":agent_no", slot_agent_coop_ladder),
     (val_sub, ":last", 1),
     (assign, ":up", 0),
     (try_for_range, ":k", 0, "$coop_mp_ways"),
       (call_script, "script_cf_coop_mp_way_up", ":k"),
       (val_add, ":up", 1),
     (try_end),
     (assign, ":best", -1),
     (assign, ":best_dist", 0),
     (try_for_range, ":k", 0, "$coop_mp_ways"),
       (call_script, "script_cf_coop_mp_way_up", ":k"),
       (this_or_next|neq, ":k", ":last"),
       (eq, ":up", 1),
       ] + way_pos(":k", WAY_FOOT, pos5) + [
       (get_distance_between_positions, ":dist", pos4, pos5),
       (store_add, ":slot", coop_mp_crowd_slot, ":k"),
       (troop_get_slot, ":crowd", MP_ARR, ":slot"),
       # past its cap a way counts much farther: a crowd stood at one tower while a ladder stood free (11-05)
       ] + way_kind(":k", ":kind") + [
       (assign, ":cap", coop_mp_ladder_cap),
       (try_begin),
         (eq, ":kind", 1),
         (assign, ":cap", coop_mp_tower_cap),
       (try_end),
       (store_sub, ":over", ":crowd", ":cap"),
       (val_max, ":over", 0),
       (val_mul, ":over", coop_mp_way_full),
       (val_add, ":dist", ":over"),
       (val_mul, ":crowd", coop_mp_way_crowd),
       (val_add, ":dist", ":crowd"),
       (this_or_next|lt, ":best", 0),
       (lt, ":dist", ":best_dist"),
       (assign, ":best", ":k"),
       (assign, ":best_dist", ":dist"),
     (try_end),
     (assign, reg0, ":best"),
     (try_begin),
       (ge, ":best", 0),
       (store_add, ":slot", coop_mp_crowd_slot, ":best"),
       (troop_get_slot, ":crowd", MP_ARR, ":slot"),
       (val_add, ":crowd", 1),
       (troop_set_slot, MP_ARR, ":slot", ":crowd"),
     (try_end),
    ]),

  # script_coop_mp_storm: the storming bots of a siege (team 1), every 2 s. Their own AI walks the AI mesh
  # to the nearest defender, and that path ran through the shut gate: they stood under the walls. So each
  # is sent up a way (stage 1 to its foot, 2 up it); on the walls (3) its AI leads it again, and one that
  # stands there idle goes to the flag (4). A fight on its level comes first (bot_fight); an archer shoots
  # from where it stands for coop_mp_storm_shoot_s before it climbs too. A way that went down (a ladder
  # pushed off the wall), or was not got up in time, is left for another.
  ("coop_mp_storm",
   [
     (set_fixed_point_multiplier, 100),
     (try_for_range, ":k", 0, "$coop_mp_ways"),
       (store_add, ":slot", coop_mp_crowd_slot, ":k"),
       (troop_set_slot, MP_ARR, ":slot", 0),
     (try_end),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
       (agent_get_slot, ":stage", ":agent_no", slot_agent_coop_stage),
       (is_between, ":stage", 1, 3),
       (agent_get_slot, ":slot", ":agent_no", slot_agent_coop_ladder),
       (gt, ":slot", 0),
       (val_add, ":slot", coop_mp_crowd_slot - 1),
       (troop_get_slot, ":crowd", MP_ARR, ":slot"),
       (val_add, ":crowd", 1),
       (troop_set_slot, MP_ARR, ":slot", ":crowd"),
     (try_end),
     (entry_point_get_position, pos6, multi_siege_flag_point),
     (assign, ":team", 1),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_is_human, ":agent_no"),
       (agent_is_non_player, ":agent_no"),
       (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
       (agent_get_team, ":agent_team", ":agent_no"),
       (eq, ":agent_team", ":team"),
       ] + led_by_orders() + bot_look() + bot_fight(coop_mp_fight_near) + [
       (agent_get_slot, ":stage", ":agent_no", slot_agent_coop_stage),
       (try_begin),
         (eq, ":fight", 0),
         (agent_get_slot, ":way", ":agent_no", slot_agent_coop_ladder),
         (val_sub, ":way", 1),
         (assign, ":up", 0),
         (try_begin),
           (ge, ":way", 0),
           (call_script, "script_cf_coop_mp_way_up", ":way"),
           (assign, ":up", 1),
         (try_end),
         (try_begin),
           (is_between, ":stage", 1, 3),
           (eq, ":up", 0),
           ] + storm_back() + [
         (try_end),
         (try_begin),
           (eq, ":stage", 0),
           (assign, ":ranged", 0),
           (try_begin),
             (agent_get_wielded_item, ":item", ":agent_no", 0),
             (ge, ":item", 0),
             (item_get_type, ":type", ":item"),
             (this_or_next|eq, ":type", itp_type_bow),
             (this_or_next|eq, ":type", itp_type_crossbow),
             (eq, ":type", itp_type_thrown),
             (assign, ":ranged", 1),
           (try_end),
           (try_begin),
             (eq, ":ranged", 1),
             (lt, ":still", coop_mp_storm_shoot_s),
             (val_add, ":still", 2),
           (else_try),
             (call_script, "script_coop_mp_pick_way", ":agent_no"),
             (ge, reg0, 0),
             (assign, ":way", reg0),
             (store_add, ":tag", ":way", 1),
             (agent_set_slot, ":agent_no", slot_agent_coop_ladder, ":tag"),
             (assign, ":stage", 1),
             (assign, ":sent", 0),
           (try_end),
         (try_end),
         # a siege tower takes its crowd up its stairs one by one: a bot near its foot goes up (the crowd at
         # the foot waited there for good, 11-05), and has longer for it
         (assign, ":foot_near", 300),
         (assign, ":climb_s", coop_mp_storm_climb_s),
         (try_begin),
           (ge, ":way", 0),
           ] + way_kind(":way", ":kind") + [
           (eq, ":kind", 1),
           (assign, ":foot_near", coop_mp_tower_foot),
           (assign, ":climb_s", coop_mp_tower_climb_s),
         (try_end),
         (try_begin),
           (eq, ":stage", 1), #to the foot of its way up
           ] + way_pos(":way", WAY_FOOT, pos3) + [
           (copy_position, pos4, pos3),
           (position_set_z, pos4, ":z"),
           (get_distance_between_positions, ":dist", pos1, pos4), #along the ground
           (try_begin),
             (lt, ":dist", ":foot_near"),
             (assign, ":stage", 2),
             (assign, ":sent", 0),
           (else_try),
             (eq, ":sent", 0),
             (agent_set_scripted_destination, ":agent_no", pos3, 1),
             (assign, ":sent", 1),
             (assign, ":still", 0),
             (agent_set_slot, ":agent_no", slot_agent_coop_stuck, 0),
           (else_try),
             (val_add, ":still", 2),
             ] + stuck_nudge(pos3, 1) + [
             (ge, ":still", coop_mp_storm_walk_s),
             ] + storm_back() + [
           (try_end),
         (try_end),
         (try_begin),
           (eq, ":stage", 2), #up it, to the wall walk
           ] + way_pos(":way", WAY_TOP, pos3) + [
           (position_get_z, ":top_z", pos3),
           (val_sub, ":top_z", 150),
           (get_distance_between_positions, ":dist", pos1, pos3),
           (try_begin),
             (this_or_next|lt, ":dist", 300),
             (ge, ":z", ":top_z"),
             (try_begin),
               (eq, ":sent", 1),
               (agent_clear_scripted_mode, ":agent_no"),
             (try_end),
             (assign, ":sent", 0),
             (assign, ":stage", 3),
             (assign, ":still", 0),
           (else_try),
             (eq, ":sent", 0),
             (agent_set_scripted_destination, ":agent_no", pos3, 0),
             (assign, ":sent", 1),
             (assign, ":still", 0),
             (agent_set_slot, ":agent_no", slot_agent_coop_stuck, 0),
           (else_try),
             (val_add, ":still", 2),
             ] + stuck_nudge(pos3, 0) + [
             (ge, ":still", ":climb_s"),
             ] + storm_back() + [
           (try_end),
         (try_end),
         (try_begin),
           (eq, ":stage", 3), #on the walls: its AI leads it, to the flag if it stands idle
           (try_begin),
             (lt, ":moved", 100),
             (val_add, ":still", 2),
           (else_try),
             (assign, ":still", 0),
           (try_end),
           (ge, ":still", coop_mp_storm_still_s),
           (assign, ":stage", 4),
           (assign, ":sent", 0),
         (try_end),
         (try_begin),
           (eq, ":stage", 4), #to the flag; one that does not get there is under the walls still
           (get_distance_between_positions, ":dist", pos1, pos6),
           (try_begin),
             (lt, ":dist", 300),
             (try_begin),
               (eq, ":sent", 1),
               (agent_clear_scripted_mode, ":agent_no"),
             (try_end),
             (assign, ":sent", 0),
             (assign, ":stage", 3),
             (assign, ":still", 0),
           (else_try),
             (eq, ":sent", 0),
             (agent_set_scripted_destination, ":agent_no", pos6, 0),
             (assign, ":sent", 1),
             (assign, ":still", 0),
           (else_try),
             (val_add, ":still", 2),
             (ge, ":still", coop_mp_storm_walk_s),
             ] + storm_back() + [
           (try_end),
         (try_end),
       (try_end),
       (agent_set_slot, ":agent_no", slot_agent_coop_stage, ":stage"),
       ] + bot_save() + [
     (try_end),
    ]),

  # script_coop_mp_hold: the garrison's bots (team 0), every 2 s. Their own AI went for the nearest attacker
  # by the AI mesh, to the shut gate or down a ladder, and stood under the walls. Each fights an enemy on its
  # level (within coop_mp_hold_near), else it holds its post: the top of a way up (by its agent number, in
  # turn), or the flag.
  ("coop_mp_hold",
   [
     (set_fixed_point_multiplier, 100),
     (store_add, ":posts", "$coop_mp_ways", 1),
     (assign, ":team", 0),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_is_human, ":agent_no"),
       (agent_is_non_player, ":agent_no"),
       (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
       (agent_get_team, ":agent_team", ":agent_no"),
       (eq, ":agent_team", ":team"),
       (agent_get_horse, ":horse", ":agent_no"),
       (lt, ":horse", 0), #a horseman of the garrison fights in the open (11-07)
       ] + led_by_orders() + bot_look() + bot_fight(coop_mp_hold_near) + [
       (try_begin),
         (eq, ":fight", 0),
         (eq, ":sent", 0),
         (store_mod, ":post", ":agent_no", ":posts"),
         (try_begin),
           (lt, ":post", "$coop_mp_ways"),
           ] + way_pos(":post", WAY_TOP, pos3) + [
         (else_try),
           (entry_point_get_position, pos3, multi_siege_flag_point),
         (try_end),
         (agent_set_scripted_destination, ":agent_no", pos3, 0),
         (assign, ":sent", 1),
         (assign, ":still", 0),
       (try_end),
       ] + bot_save() + [
     (try_end),
    ]),

  # script_coop_mp_field_shares: each side's place on the field of a campaign battle ($coop_mp_share_0, _1):
  # all its men while both sides together are coop_mp_field_bots at most, else its share of that (never under
  # coop_mp_field_least, or all it has). The first wave of each side comes now.
  ("coop_mp_field_shares",
   [
     (assign, ":n_0", 0),
     (assign, ":n_1", 0),
     (try_for_range, ":i", 0, "$coop_mp_n"),
       ] + stack_slot(S_TEAM) + [
       (troop_get_slot, ":team", MP_ARR, ":slot"),
       ] + stack_slot(S_COUNT) + [
       (troop_get_slot, ":count", MP_ARR, ":slot"),
       (try_begin),
         (eq, ":team", 0),
         (val_add, ":n_0", ":count"),
       (else_try),
         (eq, ":team", 1),
         (val_add, ":n_1", ":count"),
       (try_end),
     (try_end),
     (assign, ":share_0", ":n_0"),
     (assign, ":share_1", ":n_1"),
     (store_add, ":total", ":n_0", ":n_1"),
     (try_begin),
       (gt, ":total", coop_mp_field_bots),
       ] + [op for t in (0, 1) for op in [
       (store_mul, f":share_{t}", f":n_{t}", coop_mp_field_bots),
       (val_div, f":share_{t}", ":total"),
       (assign, f":least_{t}", f":n_{t}"),
       (val_min, f":least_{t}", coop_mp_field_least),
       (val_max, f":share_{t}", f":least_{t}"),
       ]] + [
       (store_add, ":sum", ":share_0", ":share_1"),
       (gt, ":sum", coop_mp_field_bots), #a small side kept its least: the big one gives way
       (store_sub, ":over", ":sum", coop_mp_field_bots),
       (try_begin),
         (ge, ":share_0", ":share_1"),
         (val_sub, ":share_0", ":over"),
         (val_max, ":share_0", ":least_0"),
       (else_try),
         (val_sub, ":share_1", ":over"),
         (val_max, ":share_1", ":least_1"),
       (try_end),
     (try_end),
     ] + [op for t in (0, 1) for op in [
     (assign, f"$coop_mp_share_{t}", f":share_{t}"),
     (assign, f"$coop_mp_field_{t}", 0),
     (assign, f"$coop_mp_wave_{t}", 1),
     (assign, f"$coop_mp_cursor_{t}", 0),
     (assign, f"$coop_mp_wave_told_{t}", -coop_mp_wave_tell_s), #the first wave is told
     ]] + [
    ]),

  # script_coop_mp_reserves: reg0, reg1 = the men of teams 0 and 1 still to come to the field
  ("coop_mp_reserves",
   [
     (assign, ":left_0", 0),
     (assign, ":left_1", 0),
     (try_for_range, ":i", 0, "$coop_mp_n"),
       ] + stack_slot(S_COUNT) + [
       (troop_get_slot, ":left", MP_ARR, ":slot"),
       ] + stack_slot(S_SPAWNED) + [
       (troop_get_slot, ":spawned", MP_ARR, ":slot"),
       (val_sub, ":left", ":spawned"),
       (gt, ":left", 0),
       ] + stack_slot(S_TEAM) + [
       (troop_get_slot, ":team", MP_ARR, ":slot"),
       (try_begin),
         (eq, ":team", 0),
         (val_add, ":left_0", ":left"),
       (else_try),
         (eq, ":team", 1),
         (val_add, ":left_1", ":left"),
       (try_end),
     (try_end),
     (assign, reg0, ":left_0"),
     (assign, reg1, ":left_1"),
    ]),

  # script_coop_mp_standing: reg0, reg1 = who of teams 0 and 1 stands: the campaign's bots and the players'
  # heroes (Siege brings players back, but a fallen hero stays out)
  ("coop_mp_standing",
   [
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
     (assign, reg0, ":alive_0"),
     (assign, reg1, ":alive_1"),
    ]),

  # script_coop_mp_fallen: reg0, reg1 = the fallen of teams 0 and 1 so far: bots and heroes
  ("coop_mp_fallen",
   [
     (assign, ":fell_0", 0),
     (assign, ":fell_1", 0),
     (try_for_range, ":i", 0, "$coop_mp_n"),
       ] + stack_slot(S_FALLEN) + [
       (troop_get_slot, ":fell", MP_ARR, ":slot"),
       ] + stack_slot(S_TEAM) + [
       (troop_get_slot, ":team", MP_ARR, ":slot"),
       (try_begin),
         (eq, ":team", 0),
         (val_add, ":fell_0", ":fell"),
       (else_try),
         (eq, ":team", 1),
         (val_add, ":fell_1", ":fell"),
       (try_end),
     (try_end),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 0, ":num_players"),
       (player_is_active, ":player_no"),
       (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
       (player_slot_eq, ":player_no", slot_player_coop_fallen, 1),
       (player_get_team_no, ":team", ":player_no"),
       (try_begin),
         (eq, ":team", 0),
         (val_add, ":fell_0", 1),
       (else_try),
         (eq, ":team", 1),
         (val_add, ":fell_1", 1),
       (try_end),
     (try_end),
     (assign, reg0, ":fell_0"),
     (assign, reg1, ":fell_1"),
    ]),

  # script_cf_coop_mp_may_end: Battle ends a round when a team has nobody alive; in a campaign battle a
  # side with men still to come is not beaten yet (the field battle's own end counts them)
  ("cf_coop_mp_may_end",
   [
     (assign, ":may", 1),
     (try_begin),
       (multiplayer_is_server),
       (is_between, "$coop_mp_phase", 2, 4),
       (lt, "$coop_mp_mode", coop_mp_mode_arena),
       (call_script, "script_coop_mp_reserves"),
       (store_add, ":left", reg0, reg1),
       (gt, ":left", 0),
       (assign, ":may", 0),
     (try_end),
     (eq, ":may", 1),
    ]),

  # script_coop_mp_next_stack: arg1 = team; reg0 = its next stack with men still to come, the stacks in
  # turn (a wave brings some of each), -1 none
  ("coop_mp_next_stack",
   [
     (store_script_param, ":want", 1),
     (assign, ":cursor", "$coop_mp_cursor_0"),
     (try_begin),
       (eq, ":want", 1),
       (assign, ":cursor", "$coop_mp_cursor_1"),
     (try_end),
     (assign, ":found", -1),
     (try_for_range, ":k", 0, "$coop_mp_n"),
       (eq, ":found", -1),
       (store_add, ":i", ":cursor", ":k"),
       (val_mod, ":i", "$coop_mp_n"),
       ] + stack_slot(S_TEAM) + [
       (troop_slot_eq, MP_ARR, ":slot", ":want"),
       ] + stack_slot(S_SPAWNED) + [
       (troop_get_slot, ":spawned", MP_ARR, ":slot"),
       ] + stack_slot(S_COUNT) + [
       (troop_get_slot, ":count", MP_ARR, ":slot"),
       (lt, ":spawned", ":count"),
       (assign, ":found", ":i"),
     (try_end),
     (try_begin),
       (ge, ":found", 0),
       (store_add, ":cursor", ":found", 1),
       (try_begin),
         (eq, ":want", 1),
         (assign, "$coop_mp_cursor_1", ":cursor"),
       (else_try),
         (assign, "$coop_mp_cursor_0", ":cursor"),
       (try_end),
     (try_end),
     (assign, reg0, ":found"),
    ]),

  # script_coop_mp_send_bot: arg1 = stack; one bot of it is asked for (it comes in ti_on_agent_spawn)
  ("coop_mp_send_bot",
   [
     (store_script_param, ":i", 1),
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
     (try_begin), #the AI's men of the starter's side (world parties, a lord's) obey the player who started it (11-07)
       (eq, ":group", -1),
       (lt, "$coop_mp_mode", coop_mp_mode_arena),
       (ge, "$coop_mp_starter", 0),
       (eq, ":team", "$coop_mp_starter_team"),
       (player_is_active, "$coop_mp_starter"),
       (player_get_team_no, ":starter_team", "$coop_mp_starter"),
       (eq, ":starter_team", ":team"),
       (assign, ":group", "$coop_mp_starter"),
     (try_end),
     # the garrison's horse spawns (11-07): a third of its horsemen ride out mounted; in a Khergit town two of three of
     # all its men, a third holds the walls
     (assign, ":rider", 0),
     (try_begin),
       (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
       (eq, ":team", 0),
       (gt, "$coop_mp_cav_n", 0),
       (try_begin),
         (eq, "$coop_mp_steppe", 1),
         (val_add, "$coop_mp_def_turn", 1),
         (store_mod, ":third", "$coop_mp_def_turn", 3),
         (neq, ":third", 0),
         (assign, ":rider", 1),
       (else_try),
         (eq, "$coop_mp_steppe", 0),
         (troop_is_guarantee_horse, ":troop"),
         (val_add, "$coop_mp_cav_turn", 1),
         (store_mod, ":third", "$coop_mp_cav_turn", 3),
         (eq, ":third", 1),
         (assign, ":rider", 1),
       (try_end),
     (else_try), #a third of the storming horsemen ride up to the walls (11-07)
       (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
       (eq, ":team", 1),
       (gt, "$coop_mp_acav_n", 0),
       (troop_is_guarantee_horse, ":troop"),
       (val_add, "$coop_mp_acav_turn", 1),
       (store_mod, ":third", "$coop_mp_acav_turn", 3),
       (eq, ":third", 1),
       (assign, ":rider", 2),
     (try_end),
     (try_begin),
       (eq, ":rider", 1),
       (store_random_in_range, ":slot", 0, "$coop_mp_cav_n"),
       (val_add, ":slot", coop_mp_cav_slot),
       (troop_get_slot, ":entry", MP_ARR, ":slot"),
     (else_try),
       (eq, ":rider", 2),
       (store_random_in_range, ":slot", 0, "$coop_mp_acav_n"),
       (val_add, ":slot", coop_mp_acav_slot),
       (troop_get_slot, ":entry", MP_ARR, ":slot"),
     (else_try),
       (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
       (eq, ":team", 0), #the garrison: at a point inside the walls the attackers reach
       (gt, "$coop_mp_entries_n", 0),
       (store_random_in_range, ":slot", 0, "$coop_mp_entries_n"),
       (val_add, ":slot", coop_mp_entries_slot),
       (troop_get_slot, ":entry", MP_ARR, ":slot"),
     (else_try),
       (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
       (eq, ":team", 0), #a map not in DEFENDER_ENTRIES: where Siege puts its defenders
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
       (try_begin),
         (gt, ":rider", 0),
         (mission_tpl_entry_set_override_flags, "mt_multiplayer_sg", ":entry", 0), #its horse comes with it
       (else_try),
         (mission_tpl_entry_set_override_flags, "mt_multiplayer_sg", ":entry", af_override_horse), #on foot
       (try_end),
     (try_end),
     (assign, "$coop_mp_spawning_rider", ":rider"),
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
     (try_begin),
       (eq, ":team", 0),
       (val_add, "$coop_mp_field_0", 1),
     (else_try),
       (eq, ":team", 1),
       (val_add, "$coop_mp_field_1", 1),
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
  # every game: a siege's retreat is offered only once the server tells of a campaign siege (a game that left
  # one midway would offer it still)
  (ti_before_mission_start, 0, 0, [], [(assign, "$coop_mp_campaign_on", 0), (assign, "$coop_mp_hud_foes", -1), (assign, "$coop_mp_hud_kind", 0)]),

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

  # a siege ends when one side has nobody standing and no men to come, bots and heroes (Siege brings
  # players back, but a fallen hero stays out)
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
     (call_script, "script_coop_mp_standing"),
     (assign, ":alive_0", reg0),
     (assign, ":alive_1", reg1),
     (call_script, "script_coop_mp_reserves"), #the reinforcements still to come stand too
     (val_add, ":alive_0", reg0),
     (val_add, ":alive_1", reg1),
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

  # a field battle of the campaign ends when one side has nobody standing and no men to come: Battle's own
  # count waits while reinforcements are to come (script_cf_coop_mp_may_end). A side that has lost nobody
  # yet is not beaten (its heroes may still be on their way to the field).
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (eq, "$coop_mp_mode", 0),
     (eq, "$g_round_ended", 0),
   ],
   [
     (call_script, "script_coop_mp_standing"),
     (assign, ":stand_0", reg0),
     (assign, ":stand_1", reg1),
     (call_script, "script_coop_mp_reserves"),
     (val_add, ":stand_0", reg0),
     (val_add, ":stand_1", reg1),
     (call_script, "script_coop_mp_fallen"),
     (assign, ":winner", -1),
     (try_begin),
       (eq, ":stand_0", 0),
       (gt, reg0, 0),
       (assign, ":winner", 1),
     (else_try),
       (eq, ":stand_1", 0),
       (gt, reg1, 0),
       (assign, ":winner", 0),
     (try_end),
     (ge, ":winner", 0),
     (assign, "$g_winner_team", ":winner"),
     (store_mission_timer_a, "$g_round_finish_time"),
     (assign, "$g_round_ended", 1),
    ]),

  # a campaign battle's reinforcements: a side that has lost coop_mp_wave_pct of its place on the field gets
  # a wave from its men still to come (the spawn trigger brings it up to its place again)
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (lt, "$coop_mp_mode", coop_mp_mode_arena),
     (eq, "$g_round_ended", 0),
   ],
   [
     (call_script, "script_coop_mp_reserves"),
     (assign, ":left_0", reg0),
     (assign, ":left_1", reg1),
     ] + [op for t in (0, 1) for op in [
     (try_begin),
       (eq, f"$coop_mp_wave_{t}", 0),
       (gt, f":left_{t}", 0),
       (store_mul, ":field", f"$coop_mp_field_{t}", 100),
       (store_mul, ":least", f"$coop_mp_share_{t}", 100 - coop_mp_wave_pct),
       (le, ":field", ":least"),
       (assign, f"$coop_mp_wave_{t}", 1),
       # told now and then: a big battle has a wave every few seconds
       (store_mission_timer_a, ":now"),
       (store_sub, ":since", ":now", f"$coop_mp_wave_told_{t}"),
       (this_or_next|ge, ":since", coop_mp_wave_tell_s),
       (lt, ":since", 0), #a new round's clock
       (assign, f"$coop_mp_wave_told_{t}", ":now"),
       (assign, reg20, t + 1),
       (assign, reg21, f":left_{t}"),
       (str_store_string, s0, "@CoopWorld: reinforcements come for team {reg20} ({reg21} still in reserve)."),
       (call_script, "script_coop_mp_tell_all"),
     (try_end),
     ]] + [
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
  # every battle but a duel: each player sees how many still stand - a joint event's opponents, or a campaign battle's
  # two sides with their reserves - and how many it beat itself (11-06, 11-07: the user's ask)
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (is_between, "$coop_mp_phase", 2, 4), #from the first bot: an event's phase 3 begins only once the last is in
     (neq, "$coop_mp_mode", coop_mp_mode_duel),
     (eq, "$g_round_ended", 0),
   ],
   [
     (assign, ":foes", 0),
     (try_for_range, ":i", 0, "$coop_mp_n"),
       ] + stack_slot(S_TEAM) + [
       (neg|troop_slot_eq, MP_ARR, ":slot", 0), #the players' side is team 0
       ] + stack_slot(S_COUNT) + [
       (troop_get_slot, ":count", MP_ARR, ":slot"),
       ] + stack_slot(S_FALLEN) + [
       (troop_get_slot, ":fallen", MP_ARR, ":slot"),
       (val_sub, ":count", ":fallen"),
       (val_max, ":count", 0),
       (val_add, ":foes", ":count"),
     (try_end),
     (assign, ":campaign", 0),
     (assign, ":alive_0", 0),
     (assign, ":alive_1", 0),
     (assign, ":reserve_0", 0),
     (assign, ":reserve_1", 0),
     (try_begin),
       (lt, "$coop_mp_mode", coop_mp_mode_arena),
       (assign, ":campaign", 1),
       (call_script, "script_coop_mp_standing"),
       (assign, ":alive_0", reg0),
       (assign, ":alive_1", reg1),
       (call_script, "script_coop_mp_reserves"),
       (assign, ":reserve_0", reg0),
       (assign, ":reserve_1", reg1),
     (try_end),
     (multiplayer_get_my_player, ":me"),
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 0, ":num_players"),
       (player_is_active, ":player_no"),
       (player_get_slot, ":kills", ":player_no", slot_player_coop_kills),
       (assign, ":own", ":alive_0"), #team 0, or a spectator: as the first side sees it
       (assign, ":own_reserve", ":reserve_0"),
       (assign, ":enemy", ":alive_1"),
       (assign, ":enemy_reserve", ":reserve_1"),
       (try_begin),
         (eq, ":campaign", 1),
         (player_get_team_no, ":team", ":player_no"),
         (try_begin),
           (eq, ":team", 1),
           (assign, ":own", ":alive_1"),
           (assign, ":own_reserve", ":reserve_1"),
           (assign, ":enemy", ":alive_0"),
           (assign, ":enemy_reserve", ":reserve_0"),
         (try_end),
         (store_add, ":foes", ":enemy", ":enemy_reserve"),
       (try_end),
       (try_begin),
         (eq, ":player_no", ":me"), #the server's own player: here at once
         (try_begin),
           (eq, ":campaign", 1),
           (call_script, "script_coop_mp_hero_stat", ":own", coop_mp_stat_own_side, ":own_reserve"),
           (call_script, "script_coop_mp_hero_stat", ":enemy", coop_mp_stat_enemy_side, ":enemy_reserve"),
         (try_end),
         (call_script, "script_coop_mp_hero_stat", 0, coop_mp_stat_kills, ":kills"),
         (call_script, "script_coop_mp_hero_stat", 0, coop_mp_stat_foes, ":foes"),
       (else_try),
         (neq, ":player_no", 0),
         (try_begin),
           (eq, ":campaign", 1),
           (multiplayer_send_3_int_to_player, ":player_no", coop_mp_event_hero_stat, ":own", coop_mp_stat_own_side, ":own_reserve"),
           (multiplayer_send_3_int_to_player, ":player_no", coop_mp_event_hero_stat, ":enemy", coop_mp_stat_enemy_side, ":enemy_reserve"),
         (try_end),
         (multiplayer_send_3_int_to_player, ":player_no", coop_mp_event_hero_stat, 0, coop_mp_stat_kills, ":kills"),
         (multiplayer_send_3_int_to_player, ":player_no", coop_mp_event_hero_stat, 0, coop_mp_stat_foes, ":foes"),
       (try_end),
     (try_end),
    ]),

  (ti_on_agent_killed_or_wounded, 0, 0,
   [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4)],
   [
     (store_trigger_param_1, ":agent_no"),
     (agent_is_human, ":agent_no"),
     (neg|agent_is_non_player, ":agent_no"),
     (agent_get_player_id, ":player_no", ":agent_no"),
     (ge, ":player_no", 0),
     (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
     (player_slot_eq, ":player_no", slot_player_coop_fallen, 0), #not a soldier it took over after
     (player_set_slot, ":player_no", slot_player_coop_fallen, 1),
     (str_store_player_username, s1, ":player_no"),
     (str_store_string, s0, "@CoopWorld: {s1}'s hero has fallen and does not come back to this battle."),
     (call_script, "script_coop_mp_tell_all"),
    ]),

  # the opponents a hero beats count for that player: a joint event's prize goes by them, and every battle's counter
  # shows them (a player who took over a soldier counts its blows too)
  (ti_on_agent_killed_or_wounded, 0, 0,
   [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4)],
   [
     (store_trigger_param_1, ":agent_no"),
     (store_trigger_param_2, ":killer"),
     (ge, ":killer", 0),
     (agent_is_human, ":agent_no"),
     (agent_is_non_player, ":agent_no"),
     (agent_is_human, ":killer"),
     (neg|agent_is_non_player, ":killer"),
     (agent_get_team, ":victim_team", ":agent_no"),
     (agent_get_team, ":killer_team", ":killer"),
     (this_or_next|neq, ":victim_team", ":killer_team"),
     (eq, "$coop_mp_mode", coop_mp_mode_arena), #an arena's fighters of team 1 fight each other
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
   [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4), (eq, "$g_multiplayer_ready_for_spawning_agent", 0)],
   [
     (val_add, "$coop_mp_spawn_wait", 1),
     (ge, "$coop_mp_spawn_wait", coop_mp_spawn_wait_s),
     (assign, "$coop_mp_spawn_wait", 0),
     (assign, "$g_multiplayer_ready_for_spawning_agent", 1),
     (assign, ":i", "$coop_mp_spawning_stack"), #it is not on the field
     ] + stack_slot(S_TEAM) + [
     (try_begin),
       (troop_slot_eq, MP_ARR, ":slot", 0),
       (val_sub, "$coop_mp_field_0", 1),
     (else_try),
       (troop_slot_eq, MP_ARR, ":slot", 1),
       (val_sub, "$coop_mp_field_1", 1),
     (try_end),
     (display_message, "@CoopWorld: a fighter did not come, the next one goes on.", 0xFFDD66),
    ]),

  # phase 2 of a joint event: one bot a frame, as Native spawns bots
  (0, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 2),
     (ge, "$coop_mp_mode", coop_mp_mode_arena),
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
     (else_try),
       (assign, "$coop_mp_spawn_i", ":found"),
       (call_script, "script_coop_mp_send_bot", ":found"),
     (try_end),
    ]),

  # a campaign battle: one bot a frame, as Native spawns bots, each side up to its place on the field
  # (script_coop_mp_field_shares) while its wave is open; the side further from its place first. Phase 2
  # brings the first waves; once they are in, the battle runs (phase 3) and the waves of reinforcements
  # come by the trigger above.
  (0, 0, 0,
   [
     (multiplayer_is_server),
     (is_between, "$coop_mp_phase", 2, 4),
     (lt, "$coop_mp_mode", coop_mp_mode_arena),
     (eq, "$g_multiplayer_ready_for_spawning_agent", 1),
     (eq, "$g_round_ended", 0),
   ],
   [
     (call_script, "script_coop_mp_reserves"),
     (assign, ":left_0", reg0),
     (assign, ":left_1", reg1),
     ] + [op for t in (0, 1) for op in [
     (assign, f":gap_{t}", 0),
     (try_begin),
       (eq, f"$coop_mp_wave_{t}", 1),
       (store_sub, f":gap_{t}", f"$coop_mp_share_{t}", f"$coop_mp_field_{t}"),
       (this_or_next|le, f":gap_{t}", 0),
       (le, f":left_{t}", 0),
       (assign, f"$coop_mp_wave_{t}", 0), #this wave is in
       (assign, f":gap_{t}", 0),
     (try_end),
     ]] + [
     (try_begin),
       (this_or_next|gt, ":gap_0", 0),
       (gt, ":gap_1", 0),
       (assign, ":team", 0),
       (try_begin),
         (gt, ":gap_1", ":gap_0"),
         (assign, ":team", 1),
       (try_end),
       (call_script, "script_coop_mp_next_stack", ":team"),
       (ge, reg0, 0),
       (call_script, "script_coop_mp_send_bot", reg0),
     (else_try),
       (eq, "$coop_mp_phase", 2),
       (assign, "$coop_mp_phase", 3),
       (store_add, ":left", ":left_0", ":left_1"),
       (try_begin),
         (gt, ":left", 0),
         (assign, reg20, ":left_0"),
         (assign, reg21, ":left_1"),
         (str_store_string, s0, "@CoopWorld: the first troops are on the field, the others come as they fall (in reserve: team 1 {reg20}, team 2 {reg21}). To battle!"),
       (else_try),
         (str_store_string, s0, "@CoopWorld: all troops are on the field. To battle!"),
       (try_end),
       (call_script, "script_coop_mp_tell_all"),
       (call_script, "script_coop_mp_hero_stat_to_all", 0, coop_mp_stat_campaign, 1),
       (str_store_string, s0, "@CoopWorld: Esc - Retreat ends the battle: nobody is taken prisoner, the men still standing get away."),
       (call_script, "script_coop_mp_tell_all"),
       (try_begin),
         (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
         (call_script, "script_coop_mp_open_doors"),
         (call_script, "script_coop_mp_raise_ladders"),
         (call_script, "script_coop_mp_place_belfries"),
         (assign, "$coop_mp_ladders_s", 0),
         (get_max_players, ":num_players"),
         (try_for_range, ":player_no", 0, ":num_players"),
           (player_is_active, ":player_no"),
           (player_set_slot, ":player_no", slot_player_coop_orders, 0),
         (try_end),
         (str_store_string, s0, "@CoopWorld: a fallen hero takes over one of its own soldiers. Orders lead your men yourself; a charge sends them up the walls again."),
         (call_script, "script_coop_mp_tell_all"),
         # the bots storm and hold the walls on foot: a horse that came all the same is told
         (assign, ":mounted", 0),
         (try_for_agents, ":agent_no"),
           (agent_is_human, ":agent_no"),
           (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
           (agent_slot_eq, ":agent_no", slot_agent_coop_rider, 0), #not one of the garrison's horsemen (11-07)
           (agent_get_horse, ":horse", ":agent_no"),
           (ge, ":horse", 0),
           (val_add, ":mounted", 1),
         (try_end),
         (gt, ":mounted", 0),
         (assign, reg20, ":mounted"),
         (str_store_string, s0, "@CoopWorld: {reg20} bots came on horses all the same."),
         (call_script, "script_coop_mp_tell_all"),
       (try_end),
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
     (player_slot_eq, ":player_no", slot_player_coop_fallen, 0), #a soldier taken over teaches the hero nothing
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

  # which stack a bot belongs to (the first waves in phase 2, the reinforcements in phase 3)
  (ti_on_agent_spawn, 0, 0, [(multiplayer_is_server), (is_between, "$coop_mp_phase", 2, 4)],
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
           slot_agent_coop_calm, slot_agent_coop_stage, slot_agent_coop_sent, slot_agent_coop_kite)] + [
     (agent_set_slot, ":agent_no", slot_agent_coop_rider, "$coop_mp_spawning_rider"),
     (assign, "$coop_mp_spawning_rider", 0),
     (try_begin), #a Khergit town: the storming bots start at the far edge of the map, the horsemen have room
       (eq, "$coop_mp_steppe", 1),
       (eq, ":team", 1),
       (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
       (store_mod, ":spot", ":agent_no", len(STEPPE_FAR_SPOTS)),
       (set_fixed_point_multiplier, 100),
       (agent_get_position, pos1, ":agent_no"),
       ] + [op for k, (x, y, z) in enumerate(STEPPE_FAR_SPOTS) for op in [
       (try_begin),
         (eq, ":spot", k),
         (position_set_x, pos1, x),
         (position_set_y, pos1, y),
         (position_set_z, pos1, z),
       (try_end),
       ]] + [
       (store_random_in_range, ":dx", -600, 600),
       (store_random_in_range, ":dy", -600, 600),
       (position_move_x, pos1, ":dx"),
       (position_move_y, pos1, ":dy"),
       (position_set_z_to_ground_level, pos1),
       (agent_get_horse, ":horse", ":agent_no"),
       (try_begin),
         (ge, ":horse", 0),
         (agent_set_position, ":horse", pos1), #its rider sits on it
       (else_try),
         (agent_set_position, ":agent_no", pos1),
       (try_end),
     (try_end),
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

  # a siege: a ladder pushed off the wall goes up again after a while, a door shut again (by a player)
  # opens again
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
     (call_script, "script_coop_mp_open_doors"),
    ]),

  # a siege: the storming bots go up the walls, the garrison holds them
  (2, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
     (eq, "$g_round_ended", 0),
   ],
   [
     (call_script, "script_coop_mp_storm"),
     (call_script, "script_coop_mp_hold"),
    ]),

  # a siege: a storming horseman gets off its horse a few metres before a way up the walls (a ladder's or a siege
  # tower's foot) or near the flag, and storms on foot (11-07, the user's ask). No operation sets a rider down: its
  # horse falls under it (its body does not stand in the way, as a living horse would), the rider gets up and goes on.
  (0.5, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
     (eq, "$g_round_ended", 0),
   ],
   [
     (set_fixed_point_multiplier, 100),
     (entry_point_get_position, pos6, multi_siege_flag_point),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_is_human, ":agent_no"),
       (agent_slot_eq, ":agent_no", slot_agent_coop_rider, 2),
       (agent_get_horse, ":horse", ":agent_no"),
       (ge, ":horse", 0),
       (agent_get_position, pos1, ":agent_no"),
       (get_distance_between_positions, ":near", pos1, pos6),
       (try_for_range, ":k", 0, "$coop_mp_ways"),
         ] + way_pos(":k", WAY_FOOT, pos2) + [
         (get_distance_between_positions, ":distance", pos1, pos2),
         (val_min, ":near", ":distance"),
       (try_end),
       (this_or_next|lt, ":near", coop_mp_dismount_near),
       (agent_slot_ge, ":agent_no", slot_agent_coop_stage, 2), #already on its way up
       (agent_deliver_damage_to_agent, ":agent_no", ":horse", 1000),
       (agent_set_slot, ":agent_no", slot_agent_coop_sent, 0), #on foot: sent on its way again
     (try_end),
    ]),

  # a campaign battle: a horse archer with arrows keeps its distance (11-07, the user's ask): an enemy closer than
  # coop_mp_ha_near sends it riding away (it shoots on the way, as Native's AI does when its target is in range); with
  # no arrows left, or nobody near, Native's AI has it again, and charges once the quiver is empty
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (lt, "$coop_mp_mode", coop_mp_mode_arena),
     (eq, "$g_round_ended", 0),
   ],
   [
     (set_fixed_point_multiplier, 100),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_is_human, ":agent_no"),
       (agent_is_non_player, ":agent_no"),
       (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
       (neg|agent_slot_eq, ":agent_no", slot_agent_coop_rider, 2), #a storming horseman rides to the walls
       (agent_get_horse, ":horse", ":agent_no"),
       (assign, ":ammo", 0),
       (try_begin),
         (ge, ":horse", 0),
         (agent_get_ammo, ":ammo", ":agent_no", 0),
       (try_end),
       (assign, ":led", 0),
       (try_begin),
         (agent_get_group, ":group", ":agent_no"),
         (ge, ":group", 0),
         (player_is_active, ":group"),
         (player_slot_eq, ":group", slot_player_coop_orders, 1), #its player leads it by orders
         (assign, ":led", 1),
       (try_end),
       (try_begin),
         (gt, ":ammo", 0),
         (eq, ":led", 0),
         (agent_get_team, ":team", ":agent_no"),
         (agent_get_position, pos1, ":agent_no"),
         (assign, ":best", coop_mp_ha_near),
         (assign, ":foe", -1),
         (try_for_agents, ":other"),
           (agent_is_alive, ":other"),
           (agent_is_human, ":other"),
           (agent_get_team, ":other_team", ":other"),
           (neq, ":other_team", ":team"),
           (agent_get_position, pos2, ":other"),
           (get_distance_between_positions, ":distance", pos1, pos2),
           (lt, ":distance", ":best"),
           (assign, ":best", ":distance"),
           (assign, ":foe", ":other"),
         (try_end),
         (ge, ":foe", 0),
         (agent_get_position, pos2, ":foe"),
         (position_get_x, ":x", pos1),
         (position_get_y, ":y", pos1),
         (position_get_x, ":fx", pos2),
         (position_get_y, ":fy", pos2),
         (store_sub, ":dx", ":x", ":fx"),
         (store_sub, ":dy", ":y", ":fy"),
         (val_max, ":best", 100),
         (val_mul, ":dx", coop_mp_ha_away),
         (val_div, ":dx", ":best"),
         (val_mul, ":dy", coop_mp_ha_away),
         (val_div, ":dy", ":best"),
         (val_add, ":x", ":dx"),
         (val_add, ":y", ":dy"),
         (copy_position, pos3, pos1),
         (position_set_x, pos3, ":x"),
         (position_set_y, pos3, ":y"),
         (agent_set_scripted_destination, ":agent_no", pos3, 1),
         (agent_set_slot, ":agent_no", slot_agent_coop_kite, 1),
       (else_try),
         (agent_slot_eq, ":agent_no", slot_agent_coop_kite, 1),
         (agent_set_slot, ":agent_no", slot_agent_coop_kite, 0),
         (agent_clear_scripted_mode, ":agent_no"), #nobody near any more, or out of arrows: Native's AI again
       (try_end),
     (try_end),
    ]),

  # a campaign battle with a lord on a side the AI leads (11-07, the user's ask): his men fight as a single player game
  # army does - the archers hold their ground and shoot, the horsemen charge, the infantry holds by the archers until
  # the enemy comes near or a minute has gone, then charges. Without a lord standing they charge as before.
  (2, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (lt, "$coop_mp_mode", coop_mp_mode_arena),
     (eq, "$g_round_ended", 0),
     (eq, "$g_multiplayer_game_type", multiplayer_game_type_battle),
   ],
   [
     (val_add, "$coop_mp_lord_s", 2),
     (set_fixed_point_multiplier, 100),
     (try_for_range, ":team", 0, 2),
       (assign, ":lord", -1),
       (try_for_agents, ":agent_no"),
         (eq, ":lord", -1),
         (agent_is_alive, ":agent_no"),
         (agent_is_human, ":agent_no"),
         (agent_is_non_player, ":agent_no"),
         (agent_get_team, ":agent_team", ":agent_no"),
         (eq, ":agent_team", ":team"),
         (agent_get_troop_id, ":troop", ":agent_no"),
         (is_between, ":troop", kings_begin, lords_end),
         (assign, ":lord", ":agent_no"),
       (try_end),
       (ge, ":lord", 0),
       (this_or_next|neq, ":team", "$coop_mp_starter_team"), #the starter's side obeys the starter
       (neg|player_is_active, "$coop_mp_starter"),
       (team_give_order, ":team", grc_archers, mordr_hold),
       (team_give_order, ":team", grc_cavalry, mordr_charge),
       (assign, ":charge", 0),
       (try_begin),
         (ge, "$coop_mp_lord_s", coop_mp_lord_wait_s),
         (assign, ":charge", 1),
       (else_try),
         (try_for_agents, ":agent_no"), #an enemy near the held infantry
           (eq, ":charge", 0),
           (agent_is_alive, ":agent_no"),
           (agent_is_human, ":agent_no"),
           (agent_get_team, ":agent_team", ":agent_no"),
           (eq, ":agent_team", ":team"),
           (agent_get_division, ":division", ":agent_no"),
           (eq, ":division", grc_infantry),
           (agent_get_position, pos1, ":agent_no"),
           (try_for_agents, ":other"),
             (eq, ":charge", 0),
             (agent_is_alive, ":other"),
             (agent_is_human, ":other"),
             (agent_get_team, ":other_team", ":other"),
             (neq, ":other_team", ":team"),
             (agent_get_position, pos2, ":other"),
             (get_distance_between_positions, ":distance", pos1, pos2),
             (lt, ":distance", coop_mp_lord_near),
             (assign, ":charge", 1),
           (try_end),
         (try_end),
       (try_end),
       (try_begin),
         (eq, ":charge", 1),
         (team_give_order, ":team", grc_infantry, mordr_charge),
       (else_try),
         (team_give_order, ":team", grc_infantry, mordr_hold),
       (try_end),
     (try_end),
    ]),

  # a campaign battle, field or siege: a player whose hero fell takes over a soldier of its side after Native's
  # respawn time, and another when that one falls (Native's respawn as a bot, the same server option): its own
  # first, then the AI's, then a friend's. Siege itself only spawns players anew and a fallen hero does not come
  # back (11-05); Battle's own respawn takes only the player's own men (11-07: a friend without them stayed out).
  (1, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (lt, "$coop_mp_mode", coop_mp_mode_arena),
     (eq, "$g_round_ended", 0),
     (eq, "$g_multiplayer_player_respawn_as_bot", 1),
   ],
   [
     (get_max_players, ":num_players"),
     (try_for_range, ":player_no", 0, ":num_players"),
       (player_is_active, ":player_no"),
       (player_slot_ge, ":player_no", slot_player_coop_hero, 1),
       (player_slot_eq, ":player_no", slot_player_coop_fallen, 1),
       (player_get_team_no, ":team", ":player_no"),
       (lt, ":team", multi_team_spectator),
       (player_get_agent_id, ":agent_no", ":player_no"),
       (ge, ":agent_no", 0),
       (neg|agent_is_alive, ":agent_no"),
       (agent_get_time_elapsed_since_removed, ":elapsed", ":agent_no"),
       (gt, ":elapsed", "$g_multiplayer_respawn_period"),
       (call_script, "script_coop_mp_bot_to_take", ":player_no", ":agent_no"),
       (ge, reg0, 0),
       (assign, ":bot", reg0),
       (agent_clear_scripted_mode, ":bot"),
       (agent_set_slot, ":bot", slot_agent_coop_sent, 0),
       (player_control_agent, ":player_no", ":bot"),
     (try_end),
    ]),

  # a campaign siege: a player who gives its men a movement order leads them itself, and the storm and the
  # hold leave them be (they overrode every order, 11-05); a charge gives them back to the storm or the hold
  (ti_on_order_issued, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (eq, "$g_multiplayer_game_type", multiplayer_game_type_siege),
     (lt, "$coop_mp_mode", coop_mp_mode_arena),
   ],
   [
     (store_trigger_param_1, ":order"),
     (store_trigger_param_2, ":commander"),
     (ge, ":commander", 0),
     (agent_is_human, ":commander"),
     (neg|agent_is_non_player, ":commander"),
     (agent_get_player_id, ":player_no", ":commander"),
     (ge, ":player_no", 0),
     (try_begin),
       (eq, ":order", mordr_charge),
       (player_slot_eq, ":player_no", slot_player_coop_orders, 1),
       (player_set_slot, ":player_no", slot_player_coop_orders, 0),
       (str_store_string, s0, "@CoopWorld: your men go back to the storm (or to holding the walls)."),
       (call_script, "script_coop_mp_tell_player", ":player_no"),
     (else_try),
       ] + [op for k, order in enumerate((mordr_hold, mordr_follow, mordr_advance, mordr_fall_back,
                                          mordr_stand_closer, mordr_spread_out, mordr_stand_ground, mordr_retreat))
            for op in [(this_or_next|eq, ":order", order) if k < 7 else (eq, ":order", order)]] + [
       (try_begin),
         (player_slot_eq, ":player_no", slot_player_coop_orders, 0),
         (str_store_string, s0, "@CoopWorld: your men follow your orders now; order a charge to send them back to the storm."),
         (call_script, "script_coop_mp_tell_player", ":player_no"),
       (try_end),
       (player_set_slot, ":player_no", slot_player_coop_orders, 1),
       (try_for_agents, ":agent_no"),
         (agent_is_alive, ":agent_no"),
         (agent_is_non_player, ":agent_no"),
         (agent_get_group, ":group", ":agent_no"),
         (eq, ":group", ":player_no"),
         (agent_slot_eq, ":agent_no", slot_agent_coop_sent, 1),
         (agent_clear_scripted_mode, ":agent_no"),
         (agent_set_slot, ":agent_no", slot_agent_coop_sent, 0),
       (try_end),
     (try_end),
    ]),

  # a player who came during a campaign battle learns of it too (the escape menu's retreat), and a word lost on
  # the way comes again
  (5, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 3),
     (lt, "$coop_mp_mode", coop_mp_mode_arena),
     (eq, "$g_round_ended", 0),
   ],
   [
     (call_script, "script_coop_mp_hero_stat_to_all", 0, coop_mp_stat_campaign, 1),
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
     ] + stack_slot(S_TEAM) + [ #its side has one place on the field more for its reinforcements
     (try_begin),
       (troop_slot_eq, MP_ARR, ":slot", 0),
       (val_sub, "$coop_mp_field_0", 1),
     (else_try),
       (troop_slot_eq, MP_ARR, ":slot", 1),
       (val_sub, "$coop_mp_field_1", 1),
     (try_end),
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
       # the hero's wounds go back to the campaign: health in percent, 0 if the hero fell (the soldier it
       # took over after is not the hero)
       (assign, ":health", 0),
       (try_begin),
         (player_slot_eq, ":player_no", slot_player_coop_fallen, 0),
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
     (try_for_range, ":player_no", 0, ":num_players"),
       (player_is_active, ":player_no"),
       (player_set_slot, ":player_no", slot_player_coop_orders, 0),
     (try_end),
     (call_script, "script_coop_mp_hero_stat_to_all", 0, coop_mp_stat_campaign, 0),
     (call_script, "script_coop_mp_hero_stat_to_all", 0, coop_mp_stat_foes, -1), #the counter goes
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
    (try_begin),  # the escape menu's retreat of a client (the server's own player calls the script itself)
      (multiplayer_is_server),
      (store_script_param, ":coop_event", 2),
      (eq, ":coop_event", coop_mp_event_retreat),
      (store_script_param, ":coop_player", 1),
      (call_script, "script_coop_mp_retreat", ":coop_player"),
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
          block[i:i] = [  # and "a field battle of the campaign ends": its reinforcements may still come
            (eq, "$coop_mp_team_event", 0),
            (call_script, "script_cf_coop_mp_may_end"),
          ]
          counts += 1
          i += 2
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


# A joint event's counter at the top of the battle window: the opponents still standing, and those this player beat
# (codes coop_mp_stat_foes and _kills from the server), made anew with each new value (script_coop_mp_hud_show).
# It closes itself when the server sends -1, or with the mission.
mp_presentations = [
  ("coop_mp_hud", prsntf_read_only|prsntf_manual_end_only, 0,
   [
     (ti_on_presentation_load,
      [
        (set_fixed_point_multiplier, 1000),
        (assign, "$coop_mp_hud_dirty", 0),
        (call_script, "script_coop_mp_hud_text"),
        (create_text_overlay, "$coop_mp_hud_text", s0, tf_center_justify|tf_single_line|tf_with_outline),
        (overlay_set_color, "$coop_mp_hud_text", 0xFFFFFF),
        (position_set_x, pos1, 500),
        (position_set_y, pos1, 650),
        (overlay_set_position, "$coop_mp_hud_text", pos1),
        (assign, ":size", 1400),
        (try_begin),
          (eq, "$coop_mp_hud_kind", 1), #a campaign battle's longer line: smaller, to stay within the screen
          (assign, ":size", 1000),
        (try_end),
        (position_set_x, pos1, ":size"),
        (position_set_y, pos1, ":size"),
        (overlay_set_size, "$coop_mp_hud_text", pos1),
        (presentation_set_duration, 999999),
      ]),
     (ti_on_presentation_run,
      [
        (try_begin),
          (lt, "$coop_mp_hud_foes", 0),
          (presentation_set_duration, 0),
        (else_try),
          # a value not made anew yet (a window of the player's open over it): the text at least
          (eq, "$coop_mp_hud_dirty", 1),
          (assign, "$coop_mp_hud_dirty", 0),
          (call_script, "script_coop_mp_hud_text"),
          (overlay_set_text, "$coop_mp_hud_text", s0),
        (try_end),
      ]),
   ]),
]
