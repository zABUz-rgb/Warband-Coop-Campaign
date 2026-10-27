from header_common import *
from header_operations import *
from module_constants import *
from coop.constants import *

scripts = [
  # script_game_get_party_speed_multiplier
  # Called by the engine for party speed (commented out in Native). Output: trigger_result in percent.
  # CoopWorld: the whole world moves at coop_world_speed_percent.
  ("game_get_party_speed_multiplier",
   [
     (store_script_param, ":party_no", 1),
     (assign, ":unused", ":party_no"),
     (set_trigger_result, coop_world_speed_percent),
     # shows once per campaign (globals are saved) that the engine really calls this hook
     (try_begin),
       (eq, "$coop_speed_hook_seen", 0),
       (assign, "$coop_speed_hook_seen", 1),
       (assign, reg1, coop_world_speed_percent),
       (display_message, "@CoopWorld: world speed {reg1}%", 0x66CCFF),
     (try_end),
    ]),

  # script_coop_battle_ceasefire
  # Input: arg1 = 1 to make the two sides of a field battle neutral, 0 to make them enemies again.
  # Field battles use teams 0 and 1, with allies of each side on 2 and 3 (Native agent_reassign_team).
  # Called before mission start for 1, so the AI never picks targets; agents rethink when it ends.
  ("coop_battle_ceasefire",
   [
     (store_script_param, ":on", 1),
     (store_sub, ":relation", ":on", 1), #1 -> 0 (neutral), 0 -> -1 (enemy)
     (team_set_relation, 0, 1, ":relation"),
     (team_set_relation, 0, 3, ":relation"),
     (team_set_relation, 2, 1, ":relation"),
     (team_set_relation, 2, 3, ":relation"),
    ]),

  # script_coop_end_battle_prep: ends the preparation phase early or on time.
  ("coop_end_battle_prep",
   [
     (try_begin),
       (eq, "$coop_prep_seconds_left", 0), #keeps the call idempotent: only runs once
       (assign, "$coop_prep_seconds_left", -1),
       (call_script, "script_coop_battle_ceasefire", 0),
       (try_for_agents, ":agent_no"),
         (agent_is_alive, ":agent_no"),
         (agent_set_speed_limit, ":agent_no", 100),
         (agent_force_rethink, ":agent_no"),
       (try_end),
       (display_message, "@To battle!", 0xFF4444),
     (try_end),
    ]),

  # script_coop_evict_from_town
  # The player cannot pay for the night: stop resting and close this center's gates until dawn.
  ("coop_evict_from_town",
   [
     (assign, "$coop_ban_center", "$g_last_rest_center"),
     (store_time_of_day, ":hour"),
     (try_begin),
       (lt, ":hour", coop_dawn_hour),
       (store_sub, ":hours_to_dawn", coop_dawn_hour, ":hour"),
     (else_try),
       (store_sub, ":hours_to_dawn", 24 + coop_dawn_hour, ":hour"),
     (try_end),
     (store_current_hours, ":now"),
     (store_add, "$coop_ban_until", ":now", ":hours_to_dawn"),
     (str_store_party_name, s1, "$g_last_rest_center"),
     (display_message, "@You cannot pay for your lodgings in {s1}. The guards turn you out until dawn.", 0xFF6666),
     (assign, "$g_last_rest_center", -1),
     (assign, "$auto_enter_town", 0),
     (rest_for_hours, 0, 0, 0), #stop resting
    ]),
]


def merge(orig_scripts):
  from coop_merge import script_block, insert_after
  from coop.net import net_scripts, net_reply_handler
  from coop.triggers import first_dynamic_party
  # the engine hook is commented out in Native, so it is simply added
  orig_scripts.extend(scripts)
  orig_scripts.extend(net_scripts(first_dynamic_party()))
  # the unattended world server opens no dialog boxes
  from coop.quiet import quiet_block, BOX_OPS
  for s in orig_scripts:
    quiet_block(s[1], BOX_OPS)
  # co-op network replies (wire format in tools/coop_bridge.py)
  script_block(orig_scripts, "game_receive_url_response").extend(net_reply_handler())
  # a new arrival (not the automatic return after resting) starts a new stay
  insert_after(script_block(orig_scripts, "game_event_party_encounter"),
               (assign, "$new_encounter", 1), [
      (try_begin),
        (neq, "$auto_enter_town", "$g_encountered_party"),
        (assign, "$coop_lodging_started", 0),
      (try_end),
      # a client meeting a party of the shared world (not a town): pause the world, note the mirrors
      (try_begin),
        (eq, "$coop_role", coop_role_client),
        (ge, "$g_encountered_party", first_dynamic_party()),
        (call_script, "script_coop_client_encounter_start"),
      (try_end),
  ])
  # the server never auto-resolves a fight of the client's puppet: the client fights it itself
  block = script_block(orig_scripts, "game_event_simulate_battle")
  params = [(store_script_param_1, ":root_defender_party"), (store_script_param_2, ":root_attacker_party")]
  if [tuple(op) for op in block[:2]] != params:
    from coop_merge import MergeError
    raise MergeError("game_event_simulate_battle: expected the two parameter reads first")
  block[:] = block[:2] + [
      (assign, ":coop_puppet_fight", 0),
      (try_begin),
        (eq, "$coop_role", coop_role_server),
        (this_or_next|eq, ":root_defender_party", "p_coop_puppet_1"),
        (eq, ":root_attacker_party", "p_coop_puppet_1"),
        (assign, ":coop_puppet_fight", 1),
        (set_trigger_result, 1), #end this battle
      (try_end),
      (try_begin),
        (eq, ":coop_puppet_fight", 0),
  ] + block[2:] + [
      (try_end),
  ]
