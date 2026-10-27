from header_common import *
from header_operations import *
from header_mission_templates import *
from header_triggers import *
from module_constants import *
from coop.constants import *

# Joint battles: a campaign battle is fought on a Warband multiplayer server, so every player
# fights it in person. The server is this module's "Battle" game type, hosted on the host's PC;
# it asks the bridge (tools/coop_bridge.py, /mp requests) whether a battle is waiting.
#
# Phases ($coop_mp_phase): 0 an ordinary round, nothing from the campaign
#   1 a battle arrived: the round restarts      2 the armies spawn, one bot a frame
#   3 the battle runs                            4 over: the losses go to the bridge until it acks
# Stacks are kept on trp_temp_array_a, COOP_MP_STRIDE slots each (troop, team, group = the MP
# player who commands them or -1, count, fallen, spawned); trp_temp_array_b holds the last reply.

MP_ARR = "trp_temp_array_a"
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
       (eq, ":kind", 1),
       (eq, "$coop_mp_phase", 0),
       (assign, "$coop_mp_battle", ":bid"),
       (troop_get_slot, "$coop_mp_n", MP_BUF, 3),
       (val_min, "$coop_mp_n", coop_mp_max_stacks),
       # the players of the campaign onto their sides
       (troop_get_slot, ":n", MP_BUF, 4),
       (try_for_range, ":k", 0, ":n"),
         (store_mul, ":src", ":k", 2),
         (val_add, ":src", 5),
         (troop_get_slot, ":player_no", MP_BUF, ":src"),
         (val_add, ":src", 1),
         (troop_get_slot, ":team", MP_BUF, ":src"),
         (player_is_active, ":player_no"),
         (player_get_team_no, ":old_team", ":player_no"),
         (neq, ":old_team", ":team"),
         (player_set_troop_id, ":player_no", -1),
         (player_set_team_no, ":player_no", ":team"),
         (multiplayer_send_message_to_player, ":player_no", multiplayer_event_force_start_team_selection),
       (try_end),
       # one long round: no time limit and no flags while the campaign battle lasts
       (assign, "$coop_mp_old_round_seconds", "$g_multiplayer_round_max_seconds"),
       (assign, "$g_multiplayer_round_max_seconds", coop_mp_round_seconds),
       (assign, "$g_round_ended", 1),
       (assign, "$g_round_finish_time", -100000), #the next round starts at once
       (assign, "$coop_mp_phase", 1),
       (str_store_string, s0, "@CoopWorld: a battle of the campaign begins!"),
       (call_script, "script_coop_mp_tell_all"),
     (else_try),
       (eq, ":kind", 4),
       (eq, "$coop_mp_phase", 4),
       (eq, ":bid", "$coop_mp_battle"),
       (assign, "$coop_mp_phase", 0),
       (assign, "$coop_mp_battle", 0),
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
         (eq, ":team", 0),
         (assign, ":entry", 0),
       (else_try),
         (assign, ":entry", 32),
       (try_end),
       (assign, "$coop_mp_spawning_stack", ":i"),
       (store_current_scene, ":cur_scene"),
       (modify_visitors_at_site, ":cur_scene"),
       (add_visitors_to_current_scene, ":entry", ":troop", 1, ":team", ":group"),
       (assign, "$g_multiplayer_ready_for_spawning_agent", 0),
     (try_end),
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
     (assign, "$coop_mp_phase", 4),
     (assign, "$coop_mp_pending", 0), #report at once
     (str_store_string, s0, "@CoopWorld: the battle is over. The outcome goes back to the campaign."),
     (call_script, "script_coop_mp_tell_all"),
    ]),
]
