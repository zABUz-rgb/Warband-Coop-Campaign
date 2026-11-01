from header_common import *
from header_items import *
from header_operations import *
from header_presentations import *
from header_triggers import *
from module_constants import *
from coop.tree import MAP, MAP_SLOTS, window_ops
from custom_troops.constants import *

# John Blackborn's two screens, each drawn anew after every click, as the troop tree is.
# custom_shop: what a soldier may be given on the left, what he has on the right. $custom_kind is the soldier,
# picked in John's conversation, $custom_category the sort of item. In MAP an overlay stands for item + 1 to buy,
# -(item + 1) to sell.
# custom_names: the army's common name and the units' own, as $custom_names_shown says. In MAP a text box stands for
# 1 + what it names.

# (what the list says, the sort of item); horses last: only riders get them
CATEGORIES = [("One-handed weapons", itp_type_one_handed_wpn), ("Two-handed weapons", itp_type_two_handed_wpn),
              ("Polearms", itp_type_polearm), ("Bows", itp_type_bow), ("Crossbows", itp_type_crossbow),
              ("Throwing weapons", itp_type_thrown), ("Arrows", itp_type_arrows), ("Bolts", itp_type_bolts),
              ("Shields", itp_type_shield), ("Helmets", itp_type_head_armor), ("Armor", itp_type_body_armor),
              ("Boots", itp_type_foot_armor), ("Gloves", itp_type_hand_armor), ("Horses", itp_type_horse)]
FOOT_CATEGORIES = len(CATEGORIES) - 1
RIDERS_FROM = 1 + 2 * len(TIERS)    # the first kind of the riders' branch

LEFT_X = 20
RIGHT_X = 530
BOX_Y = 60
BOX_WIDTH = 450
BOX_HEIGHT = 560
ROW = 46
ICON_X = 26
TEXT_X = 56
HEAD_Y = 625
DETAILS_X = 330     # where an item's window opens: over the other list
DETAILS_Y = 260

NAME_TOP = 670
NAME_ROW = 44
NAME_LABEL_X = 150
NAME_BOX_X = 480


def category_options():
  ops = []
  for name, _ in CATEGORIES:
    ops += [(str_store_string, s0, "@" + name), (try_begin), (lt, ":added", ":categories"),
            (overlay_add_item, "$custom_combo_category", s0), (val_add, ":added", 1), (try_end)]
  return ops


def category_type():
  """Ops: :type, the item sort of $custom_category."""
  ops = []
  for k, (_, item_type) in enumerate(CATEGORIES):
    ops += [(try_begin), (eq, "$custom_category", k), (assign, ":type", item_type), (try_end)]
  return ops


def name_rows():
  ops = []
  labels = ["The army"] + custom_kind_labels
  for index, label in enumerate(labels):
    y = NAME_TOP - index * NAME_ROW
    ops += [
      (try_begin),
      (neq, "$custom_names_shown", custom_screen_army if index else custom_screen_soldiers),
      (str_store_string, s0, "@" + label),
      (call_script, "script_coop_tree_text", NAME_LABEL_X, y + 8),
      (create_simple_text_box_overlay, reg0),
      (position_set_x, pos1, NAME_BOX_X),
      (position_set_y, pos1, y),
      (overlay_set_position, reg0, pos1),
      (troop_set_slot, MAP, reg0, index + 1),
      (call_script, "script_custom_name_to_s0", index),
      (overlay_set_text, reg0, s0),
      (try_end),
    ]
  return ops


scripts = [
  # script_custom_name_to_s0: arg1 = 0 the army, 1 + kind a soldier: its name. reg0 stays as it was
  ("custom_name_to_s0",
   [
     (store_script_param, ":index", 1),
     (assign, ":keep", reg0),
     (try_begin),
       (eq, ":index", 0),
       (str_store_troop_name, s0, custom_holder),
     (else_try),
       (store_sub, ":kind", ":index", 1),
       (call_script, "script_custom_troop", ":kind", 1),
       (str_store_troop_name, s0, reg0),
     (try_end),
     (assign, reg0, ":keep"),
    ]),

  # script_custom_shop_row: arg1 = item, arg2 = y in the box, arg3 = what a click means: s0 as a button
  # with the item's picture
  ("custom_shop_row",
   [
     (store_script_param, ":item", 1),
     (store_script_param, ":y", 2),
     (store_script_param, ":means", 3),
     (create_mesh_overlay_with_item_id, reg0, ":item"),
     (store_add, ":icon_y", ":y", ROW // 2),
     (position_set_x, pos1, ICON_X),
     (position_set_y, pos1, ":icon_y"),
     (overlay_set_position, reg0, pos1),
     (position_set_x, pos1, 500),
     (position_set_y, pos1, 500),
     (overlay_set_size, reg0, pos1),
     (create_button_overlay, reg0, s0, 0),
     (store_add, ":text_y", ":y", 14),
     (position_set_x, pos1, TEXT_X),
     (position_set_y, pos1, ":text_y"),
     (overlay_set_position, reg0, pos1),
     (position_set_x, pos1, 800),
     (position_set_y, pos1, 800),
     (overlay_set_size, reg0, pos1),
     (troop_set_slot, MAP, reg0, ":means"),
    ]),

  # script_custom_shop_lists: both lists of the soldier $custom_kind
  ("custom_shop_lists",
   [
     (call_script, "script_custom_tier", "$custom_kind"),
     (assign, ":tier", reg0),
     (call_script, "script_custom_troop", "$custom_kind", 1),
     (assign, ":troop", reg0),
     ] + category_type() + [
     # what may be bought: not what he has already
     (assign, ":rows", 0),
     (try_for_range, ":item", 0, "itm_ccoop_new_items_end"),
       (item_get_slot, ":needs", ":item", slot_item_custom_tier),
       (gt, ":needs", 0),
       (le, ":needs", ":tier"),
       (item_get_type, ":item_type", ":item"),
       (eq, ":item_type", ":type"),
       (call_script, "script_custom_has_item", ":troop", ":item"),
       (eq, reg0, -1),
       (val_add, ":rows", 1),
     (try_end),
     (str_clear, s0),
     (create_text_overlay, ":box", s0, tf_scrollable_style_2),
     (position_set_x, pos1, LEFT_X),
     (position_set_y, pos1, BOX_Y),
     (overlay_set_position, ":box", pos1),
     (position_set_x, pos1, BOX_WIDTH),
     (position_set_y, pos1, BOX_HEIGHT),
     (overlay_set_area_size, ":box", pos1),
     (set_container_overlay, ":box"),
     (store_mul, ":y", ":rows", ROW),
     (val_max, ":y", BOX_HEIGHT - 10), #a short list starts at the box's top
     (val_sub, ":y", ROW),
     (try_for_range, ":item", 0, "itm_ccoop_new_items_end"),
       (item_get_slot, ":needs", ":item", slot_item_custom_tier),
       (gt, ":needs", 0),
       (le, ":needs", ":tier"),
       (item_get_type, ":item_type", ":item"),
       (eq, ":item_type", ":type"),
       (call_script, "script_custom_has_item", ":troop", ":item"),
       (eq, reg0, -1),
       (call_script, "script_custom_prices", ":item"),
       (assign, reg1, reg0),
       (str_store_item_name, s1, ":item"),
       (str_store_string, s0, "@{s1}: {reg1} dinars"),
       (set_fixed_point_multiplier, 1000), #whatever the price's script used: the positions count on it
       (store_add, ":means", ":item", 1),
       (call_script, "script_custom_shop_row", ":item", ":y", ":means"),
       (val_sub, ":y", ROW),
     (try_end),
     (set_container_overlay, -1),
     # what he has
     (call_script, "script_custom_gear_count", "$custom_kind"),
     (assign, ":rows", reg0),
     (str_clear, s0),
     (create_text_overlay, ":box", s0, tf_scrollable_style_2),
     (position_set_x, pos1, RIGHT_X),
     (position_set_y, pos1, BOX_Y),
     (overlay_set_position, ":box", pos1),
     (position_set_x, pos1, BOX_WIDTH),
     (position_set_y, pos1, BOX_HEIGHT),
     (overlay_set_area_size, ":box", pos1),
     (set_container_overlay, ":box"),
     (store_mul, ":y", ":rows", ROW),
     (val_max, ":y", BOX_HEIGHT - 10),
     (val_sub, ":y", ROW),
     (troop_get_inventory_capacity, ":capacity", ":troop"),
     (try_for_range, ":slot", 0, ":capacity"),
       (troop_get_inventory_slot, ":item", ":troop", ":slot"),
       (ge, ":item", 0),
       (call_script, "script_custom_prices", ":item"),
       (item_get_slot, ":paid", ":item", slot_item_custom_paid),
       (try_begin),
         (eq, ":paid", 0), #it came with him: it brings nothing back
         (assign, reg1, 0),
       (try_end),
       (str_store_item_name, s1, ":item"),
       (str_store_string, s0, "@{s1}: sell for {reg1} dinars"),
       (set_fixed_point_multiplier, 1000),
       (store_sub, ":means", -1, ":item"),
       (call_script, "script_custom_shop_row", ":item", ":y", ":means"),
       (val_sub, ":y", ROW),
     (try_end),
     (set_container_overlay, -1),
    ]),
]

presentations = [
  ("custom_shop", prsntf_manual_end_only, 0,
   [
     (ti_on_presentation_load,
      window_ops() + [
        (try_for_range, ":k", 0, MAP_SLOTS),
          (troop_set_slot, MAP, ":k", 0),
        (try_end),
        # riders alone get horses
        (assign, ":categories", FOOT_CATEGORIES),
        (try_begin),
          (ge, "$custom_kind", RIDERS_FROM),
          (assign, ":categories", len(CATEGORIES)),
        (try_end),
        (try_begin),
          (ge, "$custom_category", ":categories"),
          (assign, "$custom_category", 0),
        (try_end),
        (store_add, ":index", "$custom_kind", 1),
        (call_script, "script_custom_name_to_s0", ":index"),
        (str_store_string, s1, s0),
        (str_store_string, s0, "@Soldier: {s1}"),
        (call_script, "script_coop_tree_text", LEFT_X, 700),
        (str_store_string, s0, "@Items:"),
        (call_script, "script_coop_tree_text", LEFT_X, 655),
        (create_combo_button_overlay, "$custom_combo_category"),
        (position_set_x, pos1, 800),
        (position_set_y, pos1, 800),
        (overlay_set_size, "$custom_combo_category", pos1),
        (position_set_x, pos1, 220),
        (position_set_y, pos1, 650),
        (overlay_set_position, "$custom_combo_category", pos1),
        (assign, ":added", 0),
        ] + category_options() + [
        (overlay_set_val, "$custom_combo_category", "$custom_category"),
        (call_script, "script_custom_tier", "$custom_kind"),
        (assign, reg1, reg0),
        (store_troop_gold, reg2, "trp_player"),
        (str_store_string, s0, "@Tier {reg1}. You have {reg2} dinars."),
        (call_script, "script_coop_tree_text", RIGHT_X, 700),
        (str_store_string, s0, "@A click on the left buys, a click on the right sells."),
        (call_script, "script_coop_tree_text", RIGHT_X, 655),
        (call_script, "script_custom_shop_lists"),
        (create_game_button_overlay, "$custom_close", "@Close"),
        (position_set_x, pos1, 830),
        (position_set_y, pos1, 16),
        (overlay_set_position, "$custom_close", pos1),
      ]),
     (ti_on_presentation_run,
      [
        (store_trigger_param_1, ":now"),
        (try_begin),
          (gt, ":now", 200), #the key that opened nothing here must not close it at once
          (key_clicked, key_escape),
          (close_item_details),
          (presentation_set_duration, 0),
        (try_end),
      ]),
     (ti_on_presentation_mouse_enter_leave,
      [
        (store_trigger_param_1, ":object"),
        (store_trigger_param_2, ":leaving"),
        (try_begin),
          (eq, ":leaving", 0),
          (is_between, ":object", 0, MAP_SLOTS),
          (troop_get_slot, ":what", MAP, ":object"),
          (neq, ":what", 0),
          (try_begin),
            (gt, ":what", 0),
            (store_sub, ":item", ":what", 1),
          (else_try),
            (store_sub, ":item", -1, ":what"),
          (try_end),
          (set_fixed_point_multiplier, 1000),
          (position_set_x, pos0, DETAILS_X),
          (position_set_y, pos0, DETAILS_Y),
          (show_item_details, ":item", pos0, 100),
        (else_try),
          (eq, ":leaving", 1),
          (close_item_details),
        (try_end),
      ]),
     (ti_on_presentation_event_state_change,
      [
        (store_trigger_param_1, ":object"),
        (store_trigger_param_2, ":value"),
        (try_begin),
          (eq, ":object", "$custom_close"),
          (close_item_details),
          (presentation_set_duration, 0),
        (else_try),
          (eq, ":object", "$custom_combo_category"),
          (assign, "$custom_category", ":value"),
          (start_presentation, "prsnt_custom_shop"),
        (else_try),
          (is_between, ":object", 0, MAP_SLOTS),
          (troop_get_slot, ":what", MAP, ":object"),
          (neq, ":what", 0),
          (close_item_details),
          (try_begin),
            (gt, ":what", 0),
            (store_sub, ":item", ":what", 1),
            (call_script, "script_custom_buy", "$custom_kind", ":item"),
          (else_try),
            (store_sub, ":item", -1, ":what"),
            (call_script, "script_custom_sell", "$custom_kind", ":item"),
          (try_end),
          (start_presentation, "prsnt_custom_shop"),
        (try_end),
      ]),
   ]),

  ("custom_names", prsntf_manual_end_only, 0,
   [
     (ti_on_presentation_load,
      window_ops() + [
        (try_for_range, ":k", 0, MAP_SLOTS),
          (troop_set_slot, MAP, ":k", 0),
        (try_end),
        (str_store_string, s0, "@Names: leave a box as it is to keep the name."),
        (call_script, "script_coop_tree_text", NAME_LABEL_X, 712),
        ] + name_rows() + [
        (create_game_button_overlay, "$custom_close", "@Done"),
        (position_set_x, pos1, 830),
        (position_set_y, pos1, 16),
        (overlay_set_position, "$custom_close", pos1),
      ]),
     (ti_on_presentation_event_state_change,
      [
        (store_trigger_param_1, ":object"),
        (try_begin),
          (eq, ":object", "$custom_close"),
          (try_begin),
            (eq, "$custom_army_made", 0),
            (call_script, "script_custom_army_make"),
          (try_end),
          (presentation_set_duration, 0),
        (else_try),
          (is_between, ":object", 0, MAP_SLOTS),
          (troop_get_slot, ":what", MAP, ":object"),
          (gt, ":what", 0),
          (store_sub, ":index", ":what", 1),
          (call_script, "script_custom_name_set", ":index"), #the box's text is in s0
          (store_add, ":slot", custom_slot_name, ":index"),
          (troop_set_slot, custom_holder, ":slot", custom_word_change),
        (try_end),
      ]),
   ]),
]


def merge(orig_presentations):
  orig_presentations += presentations
