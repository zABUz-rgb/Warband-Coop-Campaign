from trail.marks import *


def merge(menus, **extra):
  loads, options = Marker(MENU), Marker(OPTION)
  for m in menus:
    loads(m[4])
    for o in m[5]:
      options(o[3])
