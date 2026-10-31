from trail.marks import *


def merge(dialogs, **extra):
  lines = Marker(LINE)
  for d in dialogs:
    lines(d[5])
