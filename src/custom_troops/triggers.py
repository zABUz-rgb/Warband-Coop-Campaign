from header_common import *
from header_operations import *
from custom_troops.constants import custom_levels_period

# A word about the army goes out as a request of its own: first of the map's triggers, while none is out.
# Men promoted or hired since the last look take their kind's level.
triggers = [
  (0, 0, 0, [(eq, "$coop_net_pending", 0), (call_script, "script_cf_custom_word_send")], []),
  (0, 0, 0,
   [
     (val_add, "$custom_levels_wait", 1),
     (ge, "$custom_levels_wait", custom_levels_period),
     (assign, "$custom_levels_wait", 0),
     (call_script, "script_custom_levels_apply"),
   ], []),
]


def merge(orig_triggers):
  orig_triggers[0:0] = triggers
