from coop_merge import MergeError
from header_operations import *
from trail.marks import *


def merge(triggers, **extra):
  fired = Marker(TRIGGER)
  for t in triggers:
    if t[0] > 0:  # one looking each frame would drown everything else
      fired(t[4], past_tests(t[4]))
  # the map sends once a frame, from the head of a trigger that looks each frame: a trigger more would
  # shift the timers a save keeps for them, and a debug build plays the same saves as a plain one
  if triggers[0][0] != 0 or "script_cf_custom_word_send" not in repr(triggers[0][3]):
    raise MergeError("trail: the first map trigger is not the one looking each frame")
  triggers[0][3][0:0] = [(call_script, "script_coop_trail_flush")]
