"""Stand-in for the W.R.E.C.K. compiler's `compiler` module, which the Diplomacy source imports.

W.R.E.C.K. gave every module file all the headers and let it name any game object bare
(skl_trade, itm_sword, trp_player). Here the standard module system builds Diplomacy, so the
headers are imported here, and the bare names come from the ID_*.py files it writes (the first
build starts from Diplomacy's own; build.py builds again when they change).
"""
from header_animations import *
from header_common import *
from header_dialogs import *
from header_factions import *
from header_game_menus import *
from header_ground_types import *
from header_item_modifiers import *
from header_items import *
from header_map_icons import *
from header_meshes import *
from header_mission_templates import *
from header_mission_types import *
from header_music import *
from header_operations import *
from header_particle_systems import *
from header_parties import *
from header_postfx import *
from header_presentations import *
from header_quests import *
from header_scene_props import *
from header_scenes import *
from header_skills import *
from header_skins import *
from header_sounds import *
from header_strings import *
from header_tableau_materials import *
from header_terrain_types import *
from header_triggers import *
from header_troops import *
from ID_animations import *
from ID_factions import *
from ID_info_pages import *
from ID_items import *
from ID_map_icons import *
from ID_menus import *
from ID_meshes import *
from ID_mission_templates import *
from ID_music import *
from ID_particle_systems import *
from ID_parties import *
from ID_party_templates import *
from ID_postfx import *
from ID_postfx_params import *
from ID_presentations import *
from ID_quests import *
from ID_scene_props import *
from ID_scenes import *
from ID_scripts import *
from ID_skills import *
from ID_sounds import *
from ID_strings import *
from ID_tableau_materials import *
from ID_troops import *
