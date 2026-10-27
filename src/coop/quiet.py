"""The world server runs unattended: nothing may stop its rest with a window.

Every operation that opens a window (dialog and tutorial boxes, presentations such as the weekly
budget, menus such as the war and notification menus) is wrapped so that it only runs when this
game is not the world server. The host playing in it gets a box's text as a message instead (a
window would stop the world for everybody); its menus and presentations are held back for later
(coop/simple_triggers.py) or close by themselves (the weekly budget, coop/presentations.py).
"""
from header_operations import (try_begin, try_end, else_try, neq, eq, this_or_next, dialog_box, tutorial_box,
                               start_presentation, jump_to_menu, display_message)
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
    op = block[i]
    if opcode(op) in ops and opcode(op) in BOX_OPS:
      # (dialog_box, text[, title]) and (tutorial_box, text[, title]): the host reads the text
      block[i:i + 1] = [(try_begin), (neq, "$coop_role", coop_role_server), op,
                        (else_try), (eq, "$coop_srv_player", 1), (display_message, op[1], 0xFFEECC),
                        (try_end)]
      i += 7
      count += 1
    elif opcode(op) in ops:
      block[i:i + 1] = [(try_begin), (this_or_next | neq, "$coop_role", coop_role_server),
                        (eq, "$coop_srv_player", 1), op, (try_end)]
      i += 5
      count += 1
    else:
      i += 1
  return count
