from header_operations import *

trail_holder = "trp_tutorial_student_3"  # with the notes, which end at slot 64 (coop/together.py)
trail_slot_seq = 100                     # entries so far
trail_slot_sent = 101                    # entries gone to the bridge
trail_slot_last = 102                    # the newest: the same again adds nothing
trail_slot_ring = 110                    # the entries
trail_ring = 256
trail_part = 12                          # entries a request carries
trail_step = 100000                      # an entry is kind * this + index
trail_ack = 7779                         # first number of the bridge's reply, as TRAIL_ACK in tools/coop_bridge.py

MENU, OPTION, LINE, SCREEN, TRIGGER, SIMPLE, MISSION, SCRIPT = range(1, 9)


def mark(kind, index):
  return (call_script, "script_coop_trail", kind * trail_step + index)


def past_tests(block):
  """Where the tests at the head of a block end: marked there, a trigger ran, it did not only look."""
  for i, op in enumerate(block):
    code = op[0] if isinstance(op, (list, tuple)) else op
    if code & ~(neg | this_or_next) not in can_fail_operations:
      return i
  return len(block)


class Marker:
  """Numbers the blocks of one list. Two records may share a list: it gets one mark."""

  def __init__(self, kind):
    self.kind, self.index, self.seen = kind, 0, set()

  def __call__(self, block, at=0):
    if id(block) not in self.seen:
      self.seen.add(id(block))
      block[at:at] = [mark(self.kind, self.index)]
      self.index += 1
