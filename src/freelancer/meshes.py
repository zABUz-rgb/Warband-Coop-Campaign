# Freelancer (1.3) by Taragoth
# Released 11 July 2011
# Edits by Caba'drin 14 Dec 2011
# Mod-Merger'd by Windyplains, Monnikje and Caba'drin
from freelancer.constants import *

from header_meshes import *

####################################################################################################################
#  Each mesh record contains the following fields:
#  1) Mesh id: used for referencing meshes in other files. The prefix mesh_ is automatically added before each mesh id.
#  2) Mesh flags. See header_meshes.py for a list of available flags
#  3) Mesh resource name: Resource name of the mesh
#  4) Mesh translation on x axis: Will be done automatically when the mesh is loaded
#  5) Mesh translation on y axis: Will be done automatically when the mesh is loaded
#  6) Mesh translation on z axis: Will be done automatically when the mesh is loaded
#  7) Mesh rotation angle over x axis: Will be done automatically when the mesh is loaded
#  8) Mesh rotation angle over y axis: Will be done automatically when the mesh is loaded
#  9) Mesh rotation angle over z axis: Will be done automatically when the mesh is loaded
#  10) Mesh x scale: Will be done automatically when the mesh is loaded
#  11) Mesh y scale: Will be done automatically when the mesh is loaded
#  12) Mesh z scale: Will be done automatically when the mesh is loaded
####################################################################################################################

meshes = [
#+freelancer begin
#CoopWorld: the original pic_soldier_* art is not in the source release, reuse Native pictures
  ("pic_soldier_world_map", 0, "pic_recruits", 0, 0, 0, 0, 0, 0, 1, 1, 1),
  ("pic_soldier_rebel", 0, "pic_charge", 0, 0, 0, 0, 0, 0, 1, 1, 1),
  ("pic_soldier_desert", 0, "pic_deserters", 0, 0, 0, 0, 0, 0, 1, 1, 1),
#+freelancer end
]


def merge(orig_meshes):
  orig_meshes.extend(meshes)
