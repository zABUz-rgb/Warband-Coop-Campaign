from header_common import *
from header_operations import *

# A word about the army goes out as a request of its own: first of the map's triggers, while none is out
triggers = [
  (0, 0, 0, [(eq, "$coop_net_pending", 0), (call_script, "script_cf_custom_word_send")], []),
]


def merge(orig_triggers):
  orig_triggers[0:0] = triggers
