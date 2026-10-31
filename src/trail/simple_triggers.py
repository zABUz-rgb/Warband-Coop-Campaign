from trail.marks import *


def merge(simple_triggers, **extra):
  fired = Marker(SIMPLE)
  for t in simple_triggers:
    if t[0] > 0:
      fired(t[1], past_tests(t[1]))
