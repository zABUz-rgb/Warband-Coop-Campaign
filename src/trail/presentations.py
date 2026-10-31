from header_triggers import ti_on_presentation_event_state_change, ti_on_presentation_load
from trail.marks import *

SEEN = (ti_on_presentation_load, ti_on_presentation_event_state_change)  # not each frame, not each hover
BATTLE_SERVER = ("multiplayer_", "game_multiplayer_")


def merge(presentations, **extra):
  screens = Marker(SCREEN)
  for p in presentations:
    if not p[0].startswith(BATTLE_SERVER):
      for event in p[3]:
        if event[0] in SEEN:
          screens(event[1])
