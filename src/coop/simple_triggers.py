from header_common import *
from header_operations import *
from module_constants import *


# Simple triggers a client keeps: they act on the player, not on the world.
CLIENT_KEEPS = ("$g_check_autos_at_hour", "script_consume_food", "@You pay for accommodation.")


def gate_world_triggers(orig_simple_triggers):
  """A client shows the server's world, so its own world simulation stays off."""
  from coop.constants import coop_role_client
  kept = 0
  for t in orig_simple_triggers:
    text = repr(t[1])
    if any(k in text for k in CLIENT_KEEPS):
      kept += 1
      continue
    t[1][0:0] = [(neq, "$coop_role", coop_role_client)]
  if kept != len(CLIENT_KEEPS):
    from coop_merge import MergeError
    raise MergeError(f"client keeps {kept} simple triggers, expected {len(CLIENT_KEEPS)}")


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
  gate_world_triggers(orig_simple_triggers)
  # the unattended world server opens no windows (weekly report, budget, notifications)
  from coop.quiet import quiet_block
  quieted = sum(quiet_block(t[1]) for t in orig_simple_triggers)
  if quieted == 0:
    raise MergeError("no window operations found in the simple triggers")
