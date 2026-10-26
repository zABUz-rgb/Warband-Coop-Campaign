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
    ]),

  # script_coop_battle_ceasefire
  # Input: arg1 = 1 to make all hostile team pairs neutral, 0 to restore the pairs made neutral before.
  # The pairs are remembered as bits in $coop_ceasefire_pairs (bit = team_a * 4 + team_b).
  ("coop_battle_ceasefire",
   [
     (store_script_param, ":on", 1),
     (try_begin),
       (eq, ":on", 1),
       (assign, "$coop_ceasefire_pairs", 0),
       (try_for_range, ":team_a", 0, 4),
         (store_add, ":first_b", ":team_a", 1),
         (try_for_range, ":team_b", ":first_b", 4),
           (teams_are_enemies, ":team_a", ":team_b"),
           (team_set_relation, ":team_a", ":team_b", 0),
           (team_set_relation, ":team_b", ":team_a", 0),
           (store_mul, ":bit_no", ":team_a", 4),
           (val_add, ":bit_no", ":team_b"),
           (assign, ":bit", 1),
           (val_lshift, ":bit", ":bit_no"),
           (val_or, "$coop_ceasefire_pairs", ":bit"),
         (try_end),
       (try_end),
     (else_try),
       (try_for_range, ":team_a", 0, 4),
         (store_add, ":first_b", ":team_a", 1),
         (try_for_range, ":team_b", ":first_b", 4),
           (store_mul, ":bit_no", ":team_a", 4),
           (val_add, ":bit_no", ":team_b"),
           (assign, ":bit", 1),
           (val_lshift, ":bit", ":bit_no"),
           (store_and, ":is_set", "$coop_ceasefire_pairs", ":bit"),
           (neq, ":is_set", 0),
           (team_set_relation, ":team_a", ":team_b", -1),
           (team_set_relation, ":team_b", ":team_a", -1),
         (try_end),
       (try_end),
       (assign, "$coop_ceasefire_pairs", 0),
     (try_end),
    ]),

  # script_coop_end_battle_prep: ends the preparation phase early or on time.
  ("coop_end_battle_prep",
   [
     (try_begin),
       (eq, "$coop_prep_seconds_left", 0), #keeps the call idempotent: only runs once
       (assign, "$coop_prep_seconds_left", -1),
       (call_script, "script_coop_battle_ceasefire", 0),
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
  from coop_merge import find_by_id, script_block, insert_after
  # the engine hook is commented out in Native, so it is simply added
  orig_scripts.extend(scripts)
  # a new arrival (not the automatic return after resting) starts a new stay
  insert_after(script_block(orig_scripts, "game_event_party_encounter"),
               (assign, "$new_encounter", 1), [
      (try_begin),
        (neq, "$auto_enter_town", "$g_encountered_party"),
        (assign, "$coop_lodging_started", 0),
      (try_end),
  ])
