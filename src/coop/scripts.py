from header_common import *
from header_operations import *
from module_constants import *
from coop.constants import *

scripts = [
  # script_game_get_party_speed_multiplier
  # Called by the engine for party speed. Output: trigger_result in percent. The base module's own
  # speed (Diplomacy: pathfinding, fast travel) comes from script_coop_base_party_speed (see merge);
  # CoopWorld: the whole world moves at coop_world_speed_percent of it.
  ("game_get_party_speed_multiplier",
   [
     (store_script_param, ":party_no", 1),
     (assign, reg0, 100),
     (call_script, "script_coop_base_party_speed", ":party_no"),
     (assign, ":speed", reg0),
     (val_mul, ":speed", coop_world_speed_percent),
     (val_div, ":speed", 100),
     (try_begin),
       # another player is in battle or a menu: the world stands still for everyone, so here too
       (eq, "$coop_role", coop_role_client),
       (eq, "$coop_world_paused", 1),
       (set_trigger_result, coop_paused_speed_percent),
     (else_try),
       (eq, "$coop_role", coop_role_server),
       (eq, "$coop_srv_player", 1), #the host plays on the server: same for the host
       (eq, "$coop_srv_paused", 1),
       (set_trigger_result, coop_paused_speed_percent),
     (else_try),
       (set_trigger_result, ":speed"),
     (try_end),
     # shows once per campaign (globals are saved) that the engine really calls this hook
     (try_begin),
       (eq, "$coop_speed_hook_seen", 0),
       (assign, "$coop_speed_hook_seen", 1),
       (assign, reg1, coop_world_speed_percent),
       (display_message, "@CoopWorld: world speed {reg1}%", 0x66CCFF),
     (try_end),
    ]),

  # script_coop_rest_interactive: arg1 = hours, arg2 = time speed, arg3 = attackable. A rest of a
  # co-op player (the host on the server, a client) runs at the world's time speed, faster while the
  # player's clock is behind the world's, and not at all while the world stands still. Freelancer's
  # own rests (speed 4 and 5) ran a soldier's clock ahead of everyone else's.
  ("coop_rest_interactive",
   [
     (store_script_param, ":hours", 1),
     (store_script_param, ":speed", 2),
     (store_script_param, ":attackable", 3),
     (try_begin),
       (this_or_next|eq, "$coop_role", coop_role_client),
       (eq, "$coop_srv_player", 1),
       (assign, ":speed", coop_world_time_speed),
       (try_begin),
         (eq, "$coop_role", coop_role_client),
         (eq, "$coop_time_behind", 1),
         (assign, ":speed", coop_catch_up_time_speed),
       (try_end),
       (try_begin),
         (eq, "$coop_role", coop_role_client),
         (eq, "$coop_world_paused", 1),
         (assign, ":hours", 0),
       (else_try),
         (eq, "$coop_role", coop_role_server),
         (eq, "$coop_srv_paused", 1),
         (assign, ":hours", 0),
       (try_end),
     (try_end),
     (try_begin),
       (gt, ":hours", 0),
       (rest_for_hours_interactive, ":hours", ":speed", ":attackable"),
       (eq, "$coop_role", coop_role_client),
       (assign, "$coop_menu_hours", -2), #our own rest: time flows, it is not a menu
       (assign, "$coop_rest_frame", 1),
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


# Diplomacy's scripts that change the shared world on a player's word (absent from Native: skipped)
DIPLOMACY_WORLD_ACTS = (
  "dplmc_start_alliance_between_kingdoms", "dplmc_start_defensive_between_kingdoms",
  "dplmc_start_trade_between_kingdoms", "dplmc_start_nonaggression_between_kingdoms",
  "dplmc_send_messenger_to_troop", "dplmc_send_messenger_to_party", "dplmc_send_gift",
  "dplmc_send_gift_to_center", "dplmc_send_patrol", "dplmc_send_patrol_party", "dplmc_send_scout_party",
  "dplmc_send_recruiter",
)


def merge(orig_scripts):
  from coop_merge import script_block, insert_after
  from coop.net import net_scripts, net_reply_handler
  from coop.triggers import first_dynamic_party
  # the engine's speed hook: Native has it commented out, Diplomacy has its own. The engine calls the
  # first script of that name, so the base module's one becomes script_coop_base_party_speed (its
  # result in reg0) and CoopWorld's hook, which calls it, takes the name.
  from header_operations import set_trigger_result, store_script_param, assign
  from header_common import reg0 as _reg0
  base = [s for s in orig_scripts if s[0] == "game_get_party_speed_multiplier"]
  for s in base:
    orig_scripts.remove(s)
  body = [(store_script_param, ":party_no", 1), (assign, _reg0, 100)]
  if base:
    body = []
    for op in base[0][1]:
      if isinstance(op, (list, tuple)) and op[0] == set_trigger_result:
        body.append((assign, _reg0, op[1]))
      else:
        body.append(op)
  orig_scripts.append(("coop_base_party_speed", body))
  orig_scripts.extend(scripts)
  orig_scripts.extend(net_scripts(first_dynamic_party()))
  # the unattended world server opens no dialog boxes
  from coop.quiet import quiet_block, BOX_OPS
  for s in orig_scripts:
    quiet_block(s[1], BOX_OPS)
  # co-op network replies (wire format in tools/coop_bridge.py)
  response = script_block(orig_scripts, "game_receive_url_response")
  response.extend(net_reply_handler())
  # joint battles: replies on the multiplayer server
  from coop.mp import mp_scripts, mp_reply_hook, mp_network_hook
  from coop.mp_campaign import mp_campaign_scripts
  orig_scripts.extend(mp_scripts)
  orig_scripts.extend(mp_campaign_scripts)
  from coop.profile import profile_scripts
  orig_scripts.extend(profile_scripts)
  from coop.players import players_scripts
  orig_scripts.extend(players_scripts)
  response[:0] = mp_reply_hook()
  script_block(orig_scripts, "game_receive_network_message")[:0] = mp_network_hook()
  # Diplomacy's own acts on the world (treaties, envoys, gifts, patrols, recruiters, scouts) would
  # happen in a client's game only: on a client they are refused (the world server and the host
  # keep them, and the world's kingdoms still use them)
  diplomacy_acts = [s for s in DIPLOMACY_WORLD_ACTS if any(r[0] == s for r in orig_scripts)]
  for script_id in diplomacy_acts:
    block = script_block(orig_scripts, script_id)
    block[:] = [
        (assign, ":coop_refused", 0),
        (try_begin),
          (eq, "$coop_role", coop_role_client),
          (assign, ":coop_refused", 1),
          (display_message, "@CoopWorld: in co-op only the host deals with kingdoms for now (treaties, envoys, gifts, patrols, recruiters).", 0xFFDD66),
        (try_end),
        (try_begin),
          (eq, ":coop_refused", 0),
    ] + block + [
        (try_end),
    ]
  # a client's fief would exist in its own game only: the world server's center keeps its lord
  block = script_block(orig_scripts, "give_center_to_lord")
  if [op[0] for op in block[:3]] != [store_script_param] * 3:
    from coop_merge import MergeError
    raise MergeError("give_center_to_lord: expected its three parameter reads first")
  block[:] = block[:3] + [
      (assign, ":coop_fief_refused", 0),
      (try_begin),
        (eq, "$coop_role", coop_role_client),
        (eq, ":lord_troop_id", "trp_player"),
        (assign, ":coop_fief_refused", 1),
        (str_store_party_name, s1, ":center_no"),
        (display_message, "@CoopWorld: in co-op only the host holds fiefs for now. {s1} stays with its lord in the shared world; your oath, rank and relations stay yours.", 0xFFDD66),
      (try_end),
      (try_begin),
        (eq, ":coop_fief_refused", 0),
  ] + block[3:] + [
      (try_end),
  ]
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
  from coop.triggers import puppet_range
  puppets_end = puppet_range()[1]
  block = script_block(orig_scripts, "game_event_simulate_battle")
  params = [(store_script_param_1, ":root_defender_party"), (store_script_param_2, ":root_attacker_party")]
  if [tuple(op) for op in block[:2]] != params:
    from coop_merge import MergeError
    raise MergeError("game_event_simulate_battle: expected the two parameter reads first")
  block[:] = block[:2] + [
      (assign, ":coop_puppet_fight", 0),
      (try_begin),
        (eq, "$coop_role", coop_role_server),
        (this_or_next|is_between, ":root_defender_party", "p_coop_puppet_1", puppets_end),
        (is_between, ":root_attacker_party", "p_coop_puppet_1", puppets_end),
        (assign, ":coop_puppet_fight", 1),
        (set_trigger_result, 1), #end this battle
      (try_end),
      (try_begin),
        (eq, ":coop_puppet_fight", 0),
  ] + block[2:] + [
      (try_end),
  ]
