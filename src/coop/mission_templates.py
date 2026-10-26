from header_common import *
from header_operations import *
from header_mission_templates import *
from header_triggers import *
from module_constants import *
from coop.constants import *

# Field-battle preparation: for coop_battle_prep_seconds every hostile team pair is neutral,
# so the player sees the battlefield and the enemy before anyone strikes.
# A hit by anyone during the preparation starts the battle at once.
battle_prep_triggers = [
  (ti_after_mission_start, 0, 0, [],
   [
     (assign, "$coop_prep_seconds_left", coop_battle_prep_seconds),
     (call_script, "script_coop_battle_ceasefire", 1),
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


def merge(mission_templates, **unused):
  from coop_merge import get_by_id
  for mt_id in coop_prep_mission_templates:
    get_by_id(mission_templates, mt_id)[5].extend(battle_prep_triggers)
