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
# stands; the defenders when no attacker bot stands.
# Stacks are kept on trp_temp_array_a, COOP_MP_STRIDE slots each (troop, team, group = the MP
# player who commands them or -1, count, fallen, spawned); trp_temp_array_b holds the last reply.
#
# The players' heroes: up to four players fight as their campaign hero, with its equipment,
# attributes, combat skills and proficiencies. The battle server borrows the four tutorial
# students for them (never used in multiplayer; new troops would change the campaign's saves),
# and tells every game the stats it gave them (network event coop_mp_event_hero_stat).

MP_ARR = "trp_temp_array_a"
HERO_TROOPS = "trp_tutorial_student_1"  # .. _4
SIEGE_SCENES = ["scn_multi_scene_3", "scn_multi_scene_8", "scn_multi_scene_10", "scn_multi_scene_13",
                "scn_multi_scene_15", "scn_multi_scene_16"]  # Native's Siege maps
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
  # kind 1: start              bid|stacks|n|(player, team)*n
  # kind 4: the losses arrived bid
  # kind 3: tell one player s0 (an invitation waits in that player's campaign window)
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
         (get_max_players, ":num_players"),
         (try_for_range, ":player_no", 0, ":num_players"),
           (player_set_slot, ":player_no", slot_player_coop_hero, 0),
           (player_set_slot, ":player_no", slot_player_coop_health, 0),
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
       (eq, "$coop_mp_phase", 0),
       (troop_get_slot, ":player_no", MP_BUF, 3),
       (player_is_active, ":player_no"),
       (lt, "$coop_mp_heroes", 4),
       (store_add, ":troop", HERO_TROOPS, "$coop_mp_heroes"),
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
     (else_try),
       # start: bid|stacks|mode|scene hint|n|(player, team)*n
       (eq, ":kind", 1),
       (eq, "$coop_mp_phase", 0),
       (assign, "$coop_mp_battle", ":bid"),
       (troop_get_slot, "$coop_mp_n", MP_BUF, 3),
       (val_min, "$coop_mp_n", coop_mp_max_stacks),
       (troop_get_slot, "$coop_mp_mode", MP_BUF, 4),
       (troop_get_slot, ":hint", MP_BUF, 5),
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
       (try_begin),
         (eq, "$coop_mp_mode", 1),
         (str_store_string, s0, "@CoopWorld: a siege of the campaign begins! Team 1 holds the walls, team 2 storms them."),
       (else_try),
         (str_store_string, s0, "@CoopWorld: a battle of the campaign begins!"),
       (try_end),
       (call_script, "script_coop_mp_tell_all"),
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
     (try_for_range, ":ek", 0, coop_hero_items),
       (troop_get_inventory_slot, ":item", ":troop", ":ek"),
       (ge, ":item", 0),
       (player_add_spawn_item, ":player_no", ":ek", ":item"),
     (try_end),
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
       (player_get_team_no, ":old_team", ":player_no"),
       (neq, ":old_team", ":team"),
       (player_set_troop_id, ":player_no", -1),
       (player_set_team_no, ":player_no", ":team"),
       (multiplayer_send_message_to_player, ":player_no", multiplayer_event_force_start_team_selection),
     (try_end),
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

  # script_coop_mp_request: s10 = the next /mp request
  # st: the phase; pl: the players by number and name; w, r: the outcome (phase 4)
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
     (assign, "$g_multiplayer_num_bots_required_team_1", 0),
     (assign, "$g_multiplayer_num_bots_required_team_2", 0),
     (assign, "$coop_mp_spawn_i", 0),
     (assign, "$coop_mp_phase", 2),
    ]),

  # a siege ends when one side has no bot standing (players come back in Siege, bots do not)
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
     (assign, ":alive_0", 0),
     (assign, ":alive_1", 0),
     (try_for_agents, ":agent_no"),
       (agent_is_alive, ":agent_no"),
       (agent_is_human, ":agent_no"),
       (agent_slot_ge, ":agent_no", slot_agent_coop_stack, 1),
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
     (assign, "$g_multiplayer_num_bots_required_team_1", 0), #only the campaign's armies
     (assign, "$g_multiplayer_num_bots_required_team_2", 0),
     (assign, "$coop_mp_spawn_i", 0),
     (assign, "$coop_mp_phase", 2),
    ]),

  # phase 2: one bot a frame, as Native spawns bots
  (0, 0, 0,
   [
     (multiplayer_is_server),
     (eq, "$coop_mp_phase", 2),
     (eq, "$g_multiplayer_ready_for_spawning_agent", 1),
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
       (str_store_string, s0, "@CoopWorld: all troops are on the field. To battle!"),
       (call_script, "script_coop_mp_tell_all"),
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
       (assign, "$coop_mp_spawning_stack", ":i"),
       (store_current_scene, ":cur_scene"),
       (modify_visitors_at_site, ":cur_scene"),
       (add_visitors_to_current_scene, ":entry", ":troop", 1, ":team", ":group"),
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
     (store_add, ":tag", "$coop_mp_spawning_stack", 1),
     (agent_set_slot, ":agent_no", slot_agent_coop_stack, ":tag"),
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
       (player_set_troop_id, ":player_no", -1), #picks a class of the ordinary game again
       (multiplayer_send_message_to_player, ":player_no", multiplayer_event_force_start_team_selection),
     (try_end),
     (assign, "$coop_mp_phase", 4),
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
  for template_id in ("multiplayer_bt", "multiplayer_sg"):
    template_triggers = get_by_id(mission_templates, template_id)[5]
    found = 0
    for trigger in template_triggers:
      block = trigger[4]
      i = 0
      while i < len(block):
        op = block[i]
        if op == buy:  # the player is about to spawn (Siege picks the spawn point in between)
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
    template_triggers.extend(mp_battle_triggers)
