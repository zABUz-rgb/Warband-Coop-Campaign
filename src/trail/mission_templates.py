from header_triggers import ti_before_mission_start
from trail.marks import *


def merge(mission_templates, **extra):
  started = Marker(MISSION)
  for mt in mission_templates:
    if not mt[0].startswith("multiplayer"):  # the battle server has trace.log
      block = []
      started(block)
      mt[5].append((ti_before_mission_start, 0, 0, [], block))
