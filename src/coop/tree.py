from header_common import *
from header_operations import *
from header_presentations import *
from header_triggers import *
from header_troops import *
from module_constants import *
from coop.constants import *
from custom_troops.constants import BRANCH_NAMES, LEVELS, TIERS, custom_first, custom_holder, kind_of, troop_id

# The troop tree (Camp - CoopWorld): the branches on the left and the branch shown as a tree of portraits,
# growing to the right, each troop halfway between those it grows into. A click on a portrait opens the
# troop's card: what it can do and what it carries. The tree is laid out here, at build time, from
# module_troops' upgrade paths, so it stays true to the troops of the build.
# A troop that grows from two others (a watchman) stands behind the first of them, and a path into
# another branch (a looter's into a kingdom) is named on the card, not drawn.
# $coop_tree_branch: the branch shown. $coop_tree_troop: the troop of the card.
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
# The last branch is the player's own army (src/custom_troops), under the name the player gave it: one
# portrait for each kind of soldier, at the highest level of stats the player has.
ARMY_TEXT = ["You have no company of your own yet.",
             "John Blackborn raises it, at the company's camp or in a town or castle of yours.",
             "In a co-op game the host raises it, and it is the same for all the players."]

TREE_X = 170          # the branch's box
TREE_Y = 60
TREE_WIDTH = 815
TREE_HEIGHT = 630
COLUMN = 130          # a step of the tree to the right
ROW = 165             # and a row of it: a portrait with the name under it
FIRST_X = 62          # the first column's portraits, by their middle
PORTRAIT = 120        # how much of the screen a portrait takes
PORTRAIT_SIZE_X = 360 # the overlay's size for that: the tableau is 3 by 4
PORTRAIT_SIZE_Y = 480
REACH = 35            # a line goes this close to a portrait's middle, behind its empty sides
NAME_HEIGHT = 45
NAME_TEXT_SIZE = 750
LINE = 2
LINE_COLOR = 0x505050
PICKED_COLOR = 0xAA1111

CARD_X = 50           # the troop's card: portrait and numbers, then skills, then gear
CARD_SKILLS_X = 330
CARD_GEAR_X = 640
CARD_TOP = 690
CARD_ROW = 26
GEAR_HEIGHT = 590
ITEM_ROW = 46

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
  """[(troop id, depth, the row of the troop it grows from or -1)], a troop after the one it grows from.
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


def army_rows():
  """The army's rows: the recruit, then each branch's tiers (a row's number is its kind of soldier). The riders
  grow from the militia: a row has one parent, so ARMY_ALSO gives them the second."""
  rows = [(troop_id(0, 1), 0, -1)]
  for branch in BRANCH_NAMES:
    parent = kind_of("inf", TIERS[0]) if branch == "cav" else 0
    for tier in TIERS:
      rows.append((troop_id(kind_of(branch, tier), 1), rows[parent][1] + 1, parent))
      parent = len(rows) - 1
  return rows


ARMY_ALSO = [(kind_of("arc", TIERS[0]), kind_of("cav", TIERS[0]))]  # (the row, the row it grows into as well)


def layout():
  """Every branch's rows, the last one the player's army."""
  from module_troops import troops
  taken = set()
  rows = [branch_rows(roots, troops, taken) for _, roots in BRANCHES]
  return rows + [army_rows()]


def place(rows):
  """[(x, y)]: the middle of each row's portrait in the box. The last troops of the tree take the rows,
  one under the other, and each troop stands halfway between those it grows into."""
  grown = {i: [k for k, row in enumerate(rows) if row[2] == i] for i in range(len(rows))}
  down = {}  # how far under the top
  rows_taken = [0]

  def walk(i):
    if grown[i]:
      for k in grown[i]:
        walk(k)
      down[i] = (down[grown[i][0]] + down[grown[i][-1]]) // 2
    else:
      down[i] = rows_taken[0] * ROW
      rows_taken[0] += 1

  for i, row in enumerate(rows):
    if row[2] < 0:
      walk(i)
  # a box counts from its bottom: a short branch counted to the box's own height starts at its top
  high = max(rows_taken[0] * ROW + 10, TREE_HEIGHT)
  return [(FIRST_X + row[1] * COLUMN, high - 10 - PORTRAIT // 2 - down[i]) for i, row in enumerate(rows)]


def links(rows, at, also=()):
  """[(x, y, width, height)]: the lines from each troop to those it grows into."""
  lines = []
  for i, (x, y) in enumerate(at):
    grown = [at[k] for k, row in enumerate(rows) if row[2] == i] + [at[k] for parent, k in also if parent == i]
    if not grown:
      continue
    if len(grown) == 1 and grown[0][1] == y:
      lines.append((x + REACH, y, grown[0][0] - REACH - x - REACH, LINE))
      continue
    fork = x + COLUMN // 2
    lines.append((x + REACH, y, fork - x - REACH, LINE))
    low = min(g[1] for g in grown + [(x, y)])
    high = max(g[1] for g in grown + [(x, y)])
    lines.append((fork, low, LINE, high - low + LINE))
    lines += [(fork, g[1], g[0] - REACH - fork, LINE) for g in grown]
  return lines


def branch_name_to_s0(name):
  if name.startswith("fac_"):
    return [(str_store_faction_name, s0, name)]
  if name.startswith("trp_"):
    return [(str_store_troop_name, s0, name)]
  return [(str_store_string, s0, name)]


def text_line(y, x=CARD_SKILLS_X):
  """Ops: s0 as a line of the card at height y (a local)."""
  return [(call_script, "script_coop_tree_text", x, y), (val_sub, y, CARD_ROW)]


def rows_ops():
  """Ops for script_coop_tree_rows: the tree of the branch shown. The lines first: a click must find the
  button on top."""
  ops = []
  for i, rows in enumerate(layout()):
    ops += [(eq, "$coop_tree_branch", i)] if not ops else [(else_try), (eq, "$coop_tree_branch", i)]
    at = place(rows)
    if i == len(BRANCHES):
      ops += [(eq, "$custom_army_made", 1)]
    also = ARMY_ALSO if i == len(BRANCHES) else ()
    ops += [(call_script, "script_coop_tree_plane", *line) for line in links(rows, at, also)]
    if i == len(BRANCHES):
      for kind, (x, y) in enumerate(at):
        ops += [(call_script, "script_custom_shown", kind), (call_script, "script_coop_tree_node", reg0, x, y)]
    else:
      ops += [(call_script, "script_coop_tree_node", "trp_" + row[0], x, y) for row, (x, y) in zip(rows, at)]
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

  # script_coop_tree_node: arg1 = troop, arg2, arg3 = the middle of its portrait: the portrait, a button,
  # and the name under it (in a little box of its own: only such a text breaks its lines)
  ("coop_tree_node",
   [
     (store_script_param, ":troop", 1),
     (store_script_param, ":x", 2),
     (store_script_param, ":y", 3),
     (store_mul, ":with_weapons", ":troop", 2),
     (create_image_button_overlay_with_tableau_material, reg0, -1, "tableau_game_party_window", ":with_weapons"),
     (store_sub, ":left", ":x", PORTRAIT // 2),
     (store_sub, ":bottom", ":y", PORTRAIT // 2),
     (position_set_x, pos1, ":left"),
     (position_set_y, pos1, ":bottom"),
     (overlay_set_position, reg0, pos1),
     (position_set_x, pos1, PORTRAIT_SIZE_X),
     (position_set_y, pos1, PORTRAIT_SIZE_Y),
     (overlay_set_size, reg0, pos1),
     (troop_set_slot, MAP, reg0, ":troop"),
     (str_store_troop_name, s0, ":troop"),
     (create_text_overlay, reg0, s0, tf_center_justify|tf_vertical_align_center|tf_scrollable),
     (val_sub, ":bottom", NAME_HEIGHT),
     (position_set_x, pos1, ":left"),
     (position_set_y, pos1, ":bottom"),
     (overlay_set_position, reg0, pos1),
     (position_set_x, pos1, PORTRAIT),
     (position_set_y, pos1, NAME_HEIGHT),
     (overlay_set_area_size, reg0, pos1),
     (position_set_x, pos1, NAME_TEXT_SIZE),
     (position_set_y, pos1, NAME_TEXT_SIZE),
     (overlay_set_size, reg0, pos1),
    ]),

  # script_coop_tree_rows: the tree of the branch shown
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

  # script_coop_tree_troop: the card of the troop $coop_tree_troop
  ("coop_tree_troop",
   [
     (assign, ":troop", "$coop_tree_troop"),
     (str_store_troop_name, s0, ":troop"),
     (call_script, "script_coop_tree_text", CARD_X, CARD_TOP),
     (store_mul, ":with_weapons", ":troop", 2),
     (create_mesh_overlay_with_tableau_material, reg0, -1, "tableau_game_party_window", ":with_weapons"),
     (position_set_x, pos1, CARD_X - 40),
     (position_set_y, pos1, 400),
     (overlay_set_position, reg0, pos1),
     (position_set_x, pos1, 600),
     (position_set_y, pos1, 800),
     (overlay_set_size, reg0, pos1),
     # the numbers under the portrait
     (assign, ":y", 370),
     (try_begin),
       (is_between, ":troop", custom_first, custom_holder), #the army: a level there is the stats John sells
       (store_sub, ":index", ":troop", custom_first),
       (store_div, ":kind", ":index", len(LEVELS)),
       (store_mod, reg2, ":index", len(LEVELS)),
       (val_add, reg2, 1),
       (call_script, "script_custom_tier", ":kind"),
       (assign, reg1, reg0),
       (str_store_string, s0, "@Tier {reg1}, level {reg2} of 3"),
     (else_try),
       (store_character_level, reg1, ":troop"),
       (str_store_string, s0, "@Level: {reg1}"),
     (try_end),
     ] + text_line(":y", CARD_X) + [
     (store_attribute_level, ":strength", ":troop", ca_strength),
     (store_skill_level, ":ironflesh", "skl_ironflesh", ":troop"),
     (store_mul, reg1, ":ironflesh", 2),
     (val_add, reg1, ":strength"),
     (val_add, reg1, 35), #as the engine counts it
     (str_store_string, s0, "@Hit points: {reg1}"),
     ] + text_line(":y", CARD_X) + [
     (assign, reg1, ":strength"),
     (str_store_string, s0, "@Strength: {reg1}"),
     ] + text_line(":y", CARD_X) + [
     (store_attribute_level, reg1, ":troop", ca_agility),
     (str_store_string, s0, "@Agility: {reg1}"),
     ] + text_line(":y", CARD_X) + [
     (store_attribute_level, reg1, ":troop", ca_intelligence),
     (str_store_string, s0, "@Intelligence: {reg1}"),
     ] + text_line(":y", CARD_X) + [
     (store_attribute_level, reg1, ":troop", ca_charisma),
     (str_store_string, s0, "@Charisma: {reg1}"),
     ] + text_line(":y", CARD_X) + [
     (call_script, "script_game_get_troop_wage", ":troop", 0),
     (assign, reg1, reg0),
     (set_fixed_point_multiplier, 1000), #whatever that script used: the positions below count on it
     (str_store_string, s0, "@Wage: {reg1} denars a week"),
     ] + text_line(":y", CARD_X) + [
     (try_for_range, ":path", 0, 2),
       (troop_get_upgrade_troop, ":next", ":troop", ":path"),
       (gt, ":next", 0),
       (str_store_troop_name, s1, ":next"),
       (str_store_string, s0, "@Grows into: {s1}"),
       ] + text_line(":y", CARD_X) + [
     (try_end),
     # what it can do
     (assign, ":y", CARD_TOP),
     (str_store_string, s0, "@Skills"),
     ] + text_line(":y") + skill_ops() + [
     (val_sub, ":y", CARD_ROW // 2),
     (str_store_string, s0, "@Weapon proficiencies"),
     ] + text_line(":y") + proficiency_ops() + [
     # what it carries: it may be a long list
     (str_store_string, s0, "@Equipment"),
     (call_script, "script_coop_tree_text", CARD_GEAR_X, CARD_TOP),
     (assign, ":items", 0),
     (troop_get_inventory_capacity, ":capacity", ":troop"),
     (try_for_range, ":slot", 0, ":capacity"),
       (troop_get_inventory_slot, ":item", ":troop", ":slot"),
       (ge, ":item", 0),
       (val_add, ":items", 1),
     (try_end),
     (str_clear, s0),
     (create_text_overlay, ":box", s0, tf_scrollable_style_2),
     (position_set_x, pos1, CARD_GEAR_X),
     (position_set_y, pos1, CARD_TOP - GEAR_HEIGHT - 10),
     (overlay_set_position, ":box", pos1),
     (position_set_x, pos1, 340),
     (position_set_y, pos1, GEAR_HEIGHT),
     (overlay_set_area_size, ":box", pos1),
     (set_container_overlay, ":box"),
     (store_mul, ":y", ":items", ITEM_ROW),
     (val_max, ":y", GEAR_HEIGHT - 10), #a short list starts at the box's top
     (val_sub, ":y", ITEM_ROW),
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
    ]),
]


def branch_buttons():
  """Ops: the branches' buttons down the left side."""
  ops = []
  names = [name for name, _ in BRANCHES] + [custom_holder]
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


def army_text():
  """Ops: what the army's branch says while there is no army."""
  ops = [(try_begin), (eq, "$coop_tree_branch", len(BRANCHES)), (eq, "$custom_army_made", 0)]
  for k, line in enumerate(ARMY_TEXT):
    ops += [(str_store_string, s0, "@" + line), (call_script, "script_coop_tree_text", TREE_X + 10, 620 - k * CARD_ROW)]
  return ops + [(try_end)]


def window_ops():
  """Ops: the window of the tree and of a card."""
  return [
    (set_fixed_point_multiplier, 1000),
    (presentation_set_duration, 999999),
    (create_mesh_overlay, reg0, "mesh_load_window"),
    (position_set_x, pos1, 0),
    (position_set_y, pos1, 0),
    (overlay_set_position, reg0, pos1),
  ]


tree_presentations = [
  ("coop_troop_tree", prsntf_manual_end_only, 0,
   [
     (ti_on_presentation_load,
      window_ops() + [
        (try_for_range, ":k", 0, MAP_SLOTS),
          (troop_set_slot, MAP, ":k", 0),
        (try_end),
        (str_store_string, s0, "@Troop tree"),
        (call_script, "script_coop_tree_text", 24, 710),
        (str_store_string, s0, "@Click a troop to see what it can do and what it carries."),
        (call_script, "script_coop_tree_text", TREE_X + 10, 710),
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
        ] + army_text() + [
        (create_game_button_overlay, "$coop_tree_close", "@Close"),
        (position_set_x, pos1, 830),
        (position_set_y, pos1, 16),
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
            (start_presentation, "prsnt_coop_troop_card"),
          (else_try),
            (store_sub, "$coop_tree_branch", -1, ":what"),
            (start_presentation, "prsnt_coop_troop_tree"),
          (try_end),
        (try_end),
      ]),
   ]),

  # a troop's card: back to the tree it was opened from
  ("coop_troop_card", prsntf_manual_end_only, 0,
   [
     (ti_on_presentation_load,
      window_ops() + [
        (call_script, "script_coop_tree_troop"),
        (create_game_button_overlay, "$coop_tree_close", "@Back"),
        (position_set_x, pos1, 830),
        (position_set_y, pos1, 16),
        (overlay_set_position, "$coop_tree_close", pos1),
      ]),
     (ti_on_presentation_run,
      [
        (store_trigger_param_1, ":now"),
        (try_begin),
          (gt, ":now", 200),
          (key_clicked, key_escape),
          (start_presentation, "prsnt_coop_troop_tree"),
        (try_end),
      ]),
     (ti_on_presentation_event_state_change,
      [
        (store_trigger_param_1, ":object"),
        (eq, ":object", "$coop_tree_close"),
        (start_presentation, "prsnt_coop_troop_tree"),
      ]),
   ]),
]
