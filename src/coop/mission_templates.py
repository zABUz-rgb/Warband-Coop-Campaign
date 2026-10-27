from header_common import *
from header_operations import *
from header_mission_templates import *
from header_triggers import *
from module_constants import *
from coop.constants import *

# Field-battle preparation: for coop_battle_prep_seconds the two sides are neutral and the AI
# stands still, so the player sees the battlefield and the enemy before anyone strikes.
# The ceasefire is set before mission start (AI agents never pick targets); when it ends every
# agent rethinks, as Native does after changing team relations mid-mission.
# A hit by anyone during the preparation starts the battle at once.
battle_prep_triggers = [
  (ti_before_mission_start, 0, 0, [],
   [
     (assign, "$coop_prep_seconds_left", coop_battle_prep_seconds),
     (call_script, "script_coop_battle_ceasefire", 1),
    ]),

  (ti_on_agent_spawn, 0, 0,
   [
     (gt, "$coop_prep_seconds_left", 0),
   ],
   [
     (store_trigger_param_1, ":agent_no"),
     (agent_set_speed_limit, ":agent_no", 0), #AI only: the player still moves
    ]),

  (ti_after_mission_start, 0, 0, [],
   [
     (assign, reg1, coop_battle_prep_seconds),
     (display_message, "@The enemy is forming up. You have {reg1} seconds to prepare!", 0xFFDD66),
    ]),

  (1, 0, 0,
   [
     (gt, "$coop_prep_seconds_left", 0),
   ],
   [
     (val_sub, "$coop_prep_seconds_left", 1),
     (try_begin),
       (eq, "$coop_prep_seconds_left", 0),
       (call_script, "script_coop_end_battle_prep"),
     (else_try),
       (le, "$coop_prep_seconds_left", 3),
       (assign, reg1, "$coop_prep_seconds_left"),
       (display_message, "@{reg1}...", 0xFFDD66),
     (try_end),
    ]),

  (ti_on_agent_hit, 0, 0,
   [
     (gt, "$coop_prep_seconds_left", 0),
   ],
   [
     (assign, "$coop_prep_seconds_left", 0),
     (call_script, "script_coop_end_battle_prep"),
    ]),
]


VICTORY_OPS = (all_enemies_defeated, num_active_teams_le)


def checks_victory(trigger):
  ops = list(trigger[3]) + list(trigger[4])
  return any(isinstance(op, (tuple, list)) and op[0] in VICTORY_OPS for op in ops)


def merge(mission_templates, **unused):
  from coop_merge import get_by_id, MergeError
  for mt_id in coop_prep_mission_templates:
    template_triggers = get_by_id(mission_templates, mt_id)[5]
    # While the sides are neutral nobody counts as an enemy, so Native's "all enemies defeated"
    # was true and the battle was won the moment the 10 s were up. The victory checks of these
    # battles wait until the preparation is over (-1). Copies: other battles share these triggers.
    guarded = 0
    for i, t in enumerate(template_triggers):
      if checks_victory(t):
        template_triggers[i] = (t[0], t[1], t[2], [(lt, "$coop_prep_seconds_left", 0)] + list(t[3])) + tuple(t[4:])
        guarded += 1
    if guarded == 0:
      raise MergeError(f"{mt_id}: no victory check found to hold during the preparation")
    template_triggers.extend(battle_prep_triggers)
  from coop.mp import merge_battle_template
  merge_battle_template(mission_templates)
