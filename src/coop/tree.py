from header_common import *
from header_operations import *
from header_presentations import *
from header_triggers import *
from header_troops import *
from module_constants import *
from coop.constants import *

# The troop tree (Camp - CoopWorld): the branches on the left, a branch's troops in the middle, each
# under the troop it grows from, and what a clicked troop can do and carries on the right. The tree is
# laid out here from module_troops' upgrade paths, so it stays true to the troops of the build.
# A troop that grows from two others (a watchman) stands under the first of them, and a path into
# another branch (a looter's into a kingdom) is named on the right, not drawn.
# $coop_tree_branch: the branch shown. $coop_tree_troop: the troop looked at, 0 none.
# trp_temp_array_a holds what each overlay stands for while the window is up: a troop, or -1 - a branch.

MAP = "trp_temp_array_a"
MAP_SLOTS = 600

# (the branch's name: a faction's, or a string; the troops it starts from)
BRANCHES = [
  ("fac_kingdom_1", ["swadian_recruit"]),
  ("fac_kingdom_2", ["vaegir_recruit"]),
  ("fac_kingdom_3", ["khergit_tribesman"]),
  ("fac_kingdom_4", ["nord_recruit"]),
  ("fac_kingdom_5", ["rhodok_tribesman"]),
  ("fac_kingdom_6", ["sarranid_recruit"]),
  ("@Townsfolk and mercenaries", ["farmer", "townsman", "caravan_guard"]),
  ("@Women", ["refugee", "peasant_woman"]),
  ("@Outlaws", ["looter", "steppe_bandit", "taiga_bandit", "sea_raider", "desert_bandit", "bandit", "manhunter"]),
]
# The troops of this mod still being made: their ids go here, they show under "In development". A new
# troop changes what a save holds, so none is in the game yet: they come together, with a new campaign.
DEVELOPMENT_TROOPS = []
DEVELOPMENT = "@In development"
DEVELOPMENT_TEXT = ["Troops still being made for this mod will stand here.",
                    "None is ready yet: a new troop changes what a save holds,",
                    "so they come together, with a new campaign."]

ROW_HEIGHT = 30
ROW_INDENT = 24
TREE_X = 170          # the branch's box
TREE_Y = 80
TREE_WIDTH = 440
TREE_HEIGHT = 600
TEXT_WIDTH = 8        # about what a letter of a troop's name takes at TREE_TEXT_SIZE
TREE_TEXT_SIZE = 850
DETAIL_X = 640        # the panel of the troop looked at
DETAIL_ROW = 26
ITEM_ROW = 46
LINE_COLOR = 0x505050
PICKED_COLOR = 0xAA1111

SKILLS = [("Ironflesh", "skl_ironflesh"), ("Power Strike", "skl_power_strike"), ("Power Throw", "skl_power_throw"),
          ("Power Draw", "skl_power_draw"), ("Weapon Master", "skl_weapon_master"), ("Shield", "skl_shield"),
          ("Athletics", "skl_athletics"), ("Riding", "skl_riding"), ("Horse Archery", "skl_horse_archery")]
PROFICIENCIES = [("One Handed Weapons", wpt_one_handed_weapon), ("Two Handed Weapons", wpt_two_handed_weapon),
                 ("Polearms", wpt_polearm), ("Archery", wpt_archery), ("Crossbows", wpt_crossbow),
                 ("Throwing", wpt_throwing)]


def upgrades_of(troop, troops):
  """The troops this one grows into, by id (header_troops.upgrade keeps them at 14 and 15)."""
  return [troops[n][0] for n in troop[14:16] if n > 0]


def branch_rows(roots, troops, taken):
  """[(troop id, depth, the row of the troop it grows from or -1)], a troop under the one it grows from.
  taken: the troops the branches before this one hold already."""
  by_id = {t[0]: t for t in troops}
  rows = []

  def walk(troop_id, depth, parent):
    if troop_id in taken:
      return
    taken.add(troop_id)
    at = len(rows)
    rows.append((troop_id, depth, parent))
    for child in upgrades_of(by_id[troop_id], troops):
      walk(child, depth + 1, at)

  for root in roots:
    walk(root, 0, -1)
  return rows


def layout():
  """Every branch's rows, the last one "In development"."""
  from module_troops import troops
  taken = set()
  rows = [branch_rows(roots, troops, taken) for _, roots in BRANCHES]
  return rows + [branch_rows(DEVELOPMENT_TROOPS, troops, taken)]


def branch_name_to_s0(name):
  if name.startswith("fac_"):
    return [(str_store_faction_name, s0, name)]
  return [(str_store_string, s0, name)]


def text_line(y):
  """Ops: s0 as a line of the troop's list at height y (a local)."""
  return [(call_script, "script_coop_tree_text", 0, y), (val_sub, y, DETAIL_ROW)]


def rows_ops():
  """Ops for script_coop_tree_rows: the rows of the branch shown."""
  ops = []
  for i, rows in enumerate(layout()):
    ops += [(eq, "$coop_tree_branch", i)] if not ops else [(else_try), (eq, "$coop_tree_branch", i)]
    # a box counts from its bottom: a short branch counted to the box's own height starts at its top
    high = max(len(rows), TREE_HEIGHT // ROW_HEIGHT)
    ops += [(call_script, "script_coop_tree_row", "trp_" + troop, depth, row, parent, high)
            for row, (troop, depth, parent) in enumerate(rows)]
  return [(try_begin)] + ops + [(try_end)]


def skill_ops():
  ops = []
  for name, skill in SKILLS:
    ops += [
      (try_begin),
        (store_skill_level, reg1, skill, ":troop"),
        (gt, reg1, 0),
        (str_store_string, s0, "@" + name + ": {reg1}"),
        ] + text_line(":y") + [
      (try_end),
    ]
  return ops


def proficiency_ops():
  ops = []
  for name, wpt in PROFICIENCIES:
    ops += [
      (store_proficiency_level, reg1, ":troop", wpt),
      (str_store_string, s0, "@" + name + ": {reg1}"),
      ] + text_line(":y")
  return ops


tree_scripts = [
  # script_coop_tree_plane: arg1, arg2 = where, arg3, arg4 = how wide and high: a line of the tree
  ("coop_tree_plane",
   [
     (store_script_param, ":x", 1),
     (store_script_param, ":y", 2),
     (store_script_param, ":width", 3),
     (store_script_param, ":height", 4),
     (create_mesh_overlay, reg0, "mesh_white_plane"),
     (overlay_set_color, reg0, LINE_COLOR),
     (position_set_x, pos1, ":x"),
     (position_set_y, pos1, ":y"),
     (overlay_set_position, reg0, pos1),
     (store_mul, ":size_x", ":width", 20), #the mesh is 50 wide at size 1000
     (store_mul, ":size_y", ":height", 20),
     (position_set_x, pos1, ":size_x"),
     (position_set_y, pos1, ":size_y"),
     (overlay_set_size, reg0, pos1),
    ]),

  # script_coop_tree_row: arg1 = troop, arg2 = depth, arg3 = row, arg4 = the row it grows from or -1,
  # arg5 = rows of the branch. The lines first: a click must find the button on top.
  ("coop_tree_row",
   [
     (store_script_param, ":troop", 1),
     (store_script_param, ":depth", 2),
     (store_script_param, ":row", 3),
     (store_script_param, ":parent", 4),
     (store_script_param, ":rows", 5),
     (store_sub, ":y", ":rows", ":row"),
     (val_sub, ":y", 1),
     (val_mul, ":y", ROW_HEIGHT),
     (val_add, ":y", 6),
     (store_mul, ":x", ":depth", ROW_INDENT),
     (val_add, ":x", 6),
     (try_begin),
       (ge, ":parent", 0),
       (store_sub, ":trunk", ":x", ROW_INDENT - 10),
       (store_add, ":line_y", ":y", 10),
       (store_sub, ":high", ":row", ":parent"),
       (val_mul, ":high", ROW_HEIGHT),
       (val_sub, ":high", 16),
       (call_script, "script_coop_tree_plane", ":trunk", ":line_y", 2, ":high"),
       (call_script, "script_coop_tree_plane", ":trunk", ":line_y", ROW_INDENT - 14, 2),
     (try_end),
     (str_store_troop_name, s0, ":troop"),
     (create_button_overlay, reg0, s0, 0),
     (position_set_x, pos1, ":x"),
     (position_set_y, pos1, ":y"),
     (overlay_set_position, reg0, pos1),
     (position_set_x, pos1, TREE_TEXT_SIZE),
     (position_set_y, pos1, TREE_TEXT_SIZE),
     (overlay_set_size, reg0, pos1),
     (troop_set_slot, MAP, reg0, ":troop"),
     (try_begin),
       (eq, ":troop", "$coop_tree_troop"),
       (overlay_set_color, reg0, PICKED_COLOR),
     (try_end),
    ]),

  # script_coop_tree_rows: the rows of the branch shown
  ("coop_tree_rows", rows_ops()),

  # script_coop_tree_text: arg1 = x, arg2 = y: s0, as one line (a text of several lines would go by
  # the engine's own idea of where it starts)
  ("coop_tree_text",
   [
     (store_script_param, ":x", 1),
     (store_script_param, ":y", 2),
     (create_text_overlay, reg0, s0, 0),
     (position_set_x, pos1, ":x"),
     (position_set_y, pos1, ":y"),
     (overlay_set_position, reg0, pos1),
     (position_set_x, pos1, 800),
     (position_set_y, pos1, 800),
     (overlay_set_size, reg0, pos1),
    ]),

  # script_coop_tree_troop: the panel of the troop looked at
  ("coop_tree_troop",
   [
     (assign, ":troop", "$coop_tree_troop"),
     (try_begin),
       (le, ":troop", 0),
       (str_store_string, s0, "@Click a troop to see what it can do and what it carries."),
       (call_script, "script_coop_tree_text", DETAIL_X, 640),
     (else_try),
       (store_mul, ":with_weapons", ":troop", 2),
       (create_mesh_overlay_with_tableau_material, reg0, -1, "tableau_game_party_window", ":with_weapons"),
       (position_set_x, pos1, DETAIL_X),
       (position_set_y, pos1, 470),
       (overlay_set_position, reg0, pos1),
       (position_set_x, pos1, 800),
       (position_set_y, pos1, 800),
       (overlay_set_size, reg0, pos1),
       (str_store_troop_name, s0, ":troop"),
       (call_script, "script_coop_tree_text", DETAIL_X, 680),
       (store_character_level, reg1, ":troop"),
       (str_store_string, s0, "@Level: {reg1}"),
       (call_script, "script_coop_tree_text", 790, 640),
       (store_attribute_level, ":strength", ":troop", ca_strength),
       (store_skill_level, ":ironflesh", "skl_ironflesh", ":troop"),
       (store_mul, reg1, ":ironflesh", 2),
       (val_add, reg1, ":strength"),
       (val_add, reg1, 35), #as the engine counts it
       (str_store_string, s0, "@Hit points: {reg1}"),
       (call_script, "script_coop_tree_text", 790, 614),
       (assign, reg1, ":strength"),
       (str_store_string, s0, "@Strength: {reg1}"),
       (call_script, "script_coop_tree_text", 790, 588),
       (store_attribute_level, reg1, ":troop", ca_agility),
       (str_store_string, s0, "@Agility: {reg1}"),
       (call_script, "script_coop_tree_text", 790, 562),
       (store_attribute_level, reg1, ":troop", ca_intelligence),
       (str_store_string, s0, "@Intelligence: {reg1}"),
       (call_script, "script_coop_tree_text", 790, 536),
       (store_attribute_level, reg1, ":troop", ca_charisma),
       (str_store_string, s0, "@Charisma: {reg1}"),
       (call_script, "script_coop_tree_text", 790, 510),
       (call_script, "script_game_get_troop_wage", ":troop", 0),
       (assign, reg1, reg0),
       (set_fixed_point_multiplier, 1000), #whatever that script used: the positions below count on it
       (str_store_string, s0, "@Wage: {reg1} denars a week"),
       (call_script, "script_coop_tree_text", 790, 484),
       # the rest scrolls: skills, proficiencies, what it grows into, its gear
       (assign, ":items", 0),
       (troop_get_inventory_capacity, ":capacity", ":troop"),
       (try_for_range, ":slot", 0, ":capacity"),
         (troop_get_inventory_slot, ":item", ":troop", ":slot"),
         (ge, ":item", 0),
         (val_add, ":items", 1),
       (try_end),
       (str_clear, s0),
       (create_text_overlay, "$coop_tree_detail", s0, tf_scrollable_style_2),
       (position_set_x, pos1, DETAIL_X),
       (position_set_y, pos1, 80),
       (overlay_set_position, "$coop_tree_detail", pos1),
       (position_set_x, pos1, 340),
       (position_set_y, pos1, 380),
       (overlay_set_area_size, "$coop_tree_detail", pos1),
       (set_container_overlay, "$coop_tree_detail"),
       (assign, ":lines", len(SKILLS) + len(PROFICIENCIES) + 6), #every title and upgrade counted
       (store_mul, ":y", ":lines", DETAIL_ROW),
       (store_mul, ":gear", ":items", ITEM_ROW),
       (val_add, ":y", ":gear"),
       (val_max, ":y", 350), #a short list starts at the box's top
       (str_store_string, s0, "@Skills"),
       ] + text_line(":y") + skill_ops() + [
       (str_store_string, s0, "@Weapon proficiencies"),
       ] + text_line(":y") + proficiency_ops() + [
       (try_for_range, ":path", 0, 2),
         (troop_get_upgrade_troop, ":next", ":troop", ":path"),
         (gt, ":next", 0),
         (str_store_troop_name, s1, ":next"),
         (str_store_string, s0, "@Grows into: {s1}"),
         ] + text_line(":y") + [
       (try_end),
       (str_store_string, s0, "@Equipment"),
       ] + text_line(":y") + [
       (val_sub, ":y", ITEM_ROW - DETAIL_ROW),
       (try_for_range, ":slot", 0, ":capacity"),
         (troop_get_inventory_slot, ":item", ":troop", ":slot"),
         (ge, ":item", 0),
         (create_mesh_overlay_with_item_id, reg0, ":item"),
         (store_add, ":icon_y", ":y", ITEM_ROW // 2),
         (position_set_x, pos1, 26),
         (position_set_y, pos1, ":icon_y"),
         (overlay_set_position, reg0, pos1),
         (position_set_x, pos1, 500),
         (position_set_y, pos1, 500),
         (overlay_set_size, reg0, pos1),
         (str_store_item_name, s0, ":item"),
         (store_add, ":text_y", ":y", 14),
         (call_script, "script_coop_tree_text", 56, ":text_y"),
         (val_sub, ":y", ITEM_ROW),
       (try_end),
       (set_container_overlay, -1),
     (try_end),
    ]),
]


def branch_buttons():
  """Ops: the branches' buttons down the left side."""
  ops = []
  names = [name for name, _ in BRANCHES] + [DEVELOPMENT]
  for i, name in enumerate(names):
    ops += branch_name_to_s0(name) + [
      (create_button_overlay, reg0, s0, 0),
      (position_set_x, pos1, 24),
      (position_set_y, pos1, 660 - i * 52),
      (overlay_set_position, reg0, pos1),
      (position_set_x, pos1, 800),
      (position_set_y, pos1, 800),
      (overlay_set_size, reg0, pos1),
      (troop_set_slot, MAP, reg0, -1 - i),
      (try_begin),
        (eq, "$coop_tree_branch", i),
        (overlay_set_color, reg0, PICKED_COLOR),
      (try_end),
    ]
  return ops


def development_text():
  """Ops: what "In development" says while it holds no troop."""
  ops = []
  if not DEVELOPMENT_TROOPS:
    ops = [(try_begin), (eq, "$coop_tree_branch", len(BRANCHES))]
    for k, line in enumerate(DEVELOPMENT_TEXT):
      ops += [(str_store_string, s0, "@" + line), (call_script, "script_coop_tree_text", TREE_X + 10, 620 - k * DETAIL_ROW)]
    ops += [(try_end)]
  return ops


tree_presentations = [
  ("coop_troop_tree", prsntf_manual_end_only, 0,
   [
     (ti_on_presentation_load,
      [
        (set_fixed_point_multiplier, 1000),
        (presentation_set_duration, 999999),
        (create_mesh_overlay, reg0, "mesh_load_window"),
        (position_set_x, pos1, 0),
        (position_set_y, pos1, 0),
        (overlay_set_position, reg0, pos1),
        (try_for_range, ":k", 0, MAP_SLOTS),
          (troop_set_slot, MAP, ":k", 0),
        (try_end),
        (str_store_string, s0, "@Troop tree"),
        (call_script, "script_coop_tree_text", 24, 710),
        ] + branch_buttons() + [
        (str_clear, s0),
        (create_text_overlay, "$coop_tree_box", s0, tf_scrollable_style_2),
        (position_set_x, pos1, TREE_X),
        (position_set_y, pos1, TREE_Y),
        (overlay_set_position, "$coop_tree_box", pos1),
        (position_set_x, pos1, TREE_WIDTH),
        (position_set_y, pos1, TREE_HEIGHT),
        (overlay_set_area_size, "$coop_tree_box", pos1),
        (set_container_overlay, "$coop_tree_box"),
        (call_script, "script_coop_tree_rows"),
        (set_container_overlay, -1),
        ] + development_text() + [
        (call_script, "script_coop_tree_troop"),
        (create_game_button_overlay, "$coop_tree_close", "@Close"),
        (position_set_x, pos1, 830),
        (position_set_y, pos1, 30),
        (overlay_set_position, "$coop_tree_close", pos1),
      ]),
     (ti_on_presentation_run,
      [
        (store_trigger_param_1, ":now"),
        (try_begin),
          (gt, ":now", 200), #the key that opened nothing here must not close it at once
          (key_clicked, key_escape),
          (presentation_set_duration, 0),
        (try_end),
      ]),
     (ti_on_presentation_event_state_change,
      [
        (store_trigger_param_1, ":object"),
        (try_begin),
          (eq, ":object", "$coop_tree_close"),
          (presentation_set_duration, 0),
        (else_try),
          (is_between, ":object", 0, MAP_SLOTS),
          (troop_get_slot, ":what", MAP, ":object"),
          (neq, ":what", 0),
          (try_begin),
            (gt, ":what", 0),
            (assign, "$coop_tree_troop", ":what"),
            (call_script, "script_coop_note", coop_note_tree, ":what", 0, 0),
          (else_try),
            (store_sub, "$coop_tree_branch", -1, ":what"),
            (assign, "$coop_tree_troop", 0),
          (try_end),
          (presentation_set_duration, 0),
          (start_presentation, "prsnt_coop_troop_tree"),
        (try_end),
      ]),
   ]),
]
