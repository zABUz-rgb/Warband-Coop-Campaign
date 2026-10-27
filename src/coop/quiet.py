"""The world server runs unattended: nothing may stop its rest with a window.

Every operation that opens a window (dialog and tutorial boxes, presentations such as the weekly
budget, menus such as the war and notification menus) is wrapped so that it only runs when this
game is not the world server.
"""
from header_operations import (try_begin, try_end, neq, dialog_box, tutorial_box, start_presentation,
                               jump_to_menu)
from coop.constants import coop_role_server

WINDOW_OPS = {dialog_box, tutorial_box, start_presentation, jump_to_menu}
BOX_OPS = {dialog_box, tutorial_box}


def opcode(op):
  if isinstance(op, (tuple, list)):
    return op[0]
  return op


def quiet_block(block, ops=WINDOW_OPS):
  """Wraps the window operations of an operation block in place; returns how many."""
  count = 0
  i = 0
  while i < len(block):
    if opcode(block[i]) in ops:
      block[i:i + 1] = [(try_begin), (neq, "$coop_role", coop_role_server), block[i], (try_end)]
      i += 4
      count += 1
    else:
      i += 1
  return count
