from header_common import *
from header_operations import *
from module_constants import *


def merge(orig_simple_triggers):
  """Native's nightly accommodation trigger takes the last coins when the player cannot pay;
  CoopWorld turns the player out until dawn instead."""
  from coop_merge import find_line, MergeError
  paying = [t for t in orig_simple_triggers
            if any(op == (display_message, "@You pay for accommodation.") for op in t[1])]
  if len(paying) != 1:
    raise MergeError(f"expected one accommodation trigger, found {len(paying)}")
  block = paying[0][1]
  pos = find_line(block, (gt, ":gold", 0))
  if block[pos + 1] != (troop_remove_gold, "trp_player", ":gold"):
    raise MergeError("accommodation trigger: unexpected code after (gt, :gold, 0)")
  block[pos:pos + 2] = [(call_script, "script_coop_evict_from_town")]
