from header_common import *
from header_operations import *
from header_game_menus import *
from header_items import *
from module_constants import *

# The smith of every town (1.2.0): whatever arms and armour the shops of Calradia sell, made to order for a fifth more
# than they ask, so nobody rides from town to town after one helmet. The goods are Native's merchandise, read from
# module_items when the module is built, by kind and price, in pages the trade screen holds. They lie in
# trp_temp_troop's inventory (as the loot of a battle does) only while the screen is open; the smith has no money,
# so he buys nothing.

SMITH = "trp_temp_troop"
PAGE = 40          # goods on one page of the trade screen
MARKUP = 120       # per cent of the shops' price
KINDS = [          # what the smith offers, by Native's item types
  ("One-handed weapons", (itp_type_one_handed_wpn,)),
  ("Two-handed weapons", (itp_type_two_handed_wpn,)),
  ("Polearms", (itp_type_polearm,)),
  ("Bows and arrows", (itp_type_bow, itp_type_arrows)),
  ("Crossbows and bolts", (itp_type_crossbow, itp_type_bolts)),
  ("Throwing weapons", (itp_type_thrown,)),
  ("Shields", (itp_type_shield,)),
  ("Helmets", (itp_type_head_armor,)),
  ("Body armour", (itp_type_body_armor,)),
  ("Boots and gloves", (itp_type_foot_armor, itp_type_hand_armor)),
]


def pages():
  """[(label, [item ids])]: each kind's goods, cheapest first, PAGE at a time."""
  import module_items
  out = []
  for label, types in KINDS:
    goods = sorted((item[5], "itm_" + item[0]) for item in module_items.items
                   if item[3] & itp_merchandise and item[3] & 0xff in types)
    parts = [goods[k:k + PAGE] for k in range(0, len(goods), PAGE)]
    for part in parts:
      text = label if len(parts) == 1 else "%s, %d to %d denars" % (label, part[0][0], part[-1][0])
      out.append((text, [name for _, name in part]))
  return out


def fill_ops():
  ops = []
  for k, (_, names) in enumerate(pages()):
    ops += [(try_begin), (eq, "$coop_smith_page", k)] + [(troop_add_item, SMITH, name) for name in names] + [(try_end)]
  return ops


def price_ops():
  """Ops for game_get_item_buy_price_factor, before its result: the smith's price."""
  return [
    (try_begin),
      (eq, "$coop_smith_on", 1),
      (val_mul, ":price_factor", MARKUP),
      (val_div, ":price_factor", 100),
    (try_end),
  ]


def town_option():
  return ("coop_smith",
          [(party_slot_eq, "$current_town", slot_party_type, spt_town)],
          "Visit the smith: any arms and armour made to order (a fifth dearer than the shops).",
          [(jump_to_menu, "mnu_coop_smith")])


smith_scripts = [
  # script_coop_smith_close: the trade screen closed, or never opened: the smith's goods go
  ("coop_smith_close",
   [
     (assign, "$coop_smith_on", 0),
     (assign, "$coop_smith_step", 0),
     (troop_clear_inventory, SMITH),
     (troop_set_name, SMITH, "@Temp Troop"),
    ]),

  # script_coop_smith_open: the goods of $coop_smith_page on the trade screen
  ("coop_smith_open",
   [
     (troop_clear_inventory, SMITH),
     (store_troop_gold, ":gold", SMITH),
     (troop_remove_gold, SMITH, ":gold"),
     ] + fill_ops() + [
     (str_store_party_name, s1, "$current_town"),
     (troop_set_name, SMITH, "@The smith of {s1}"),
     (assign, "$coop_smith_on", 1),
     (change_screen_trade, SMITH),
    ]),
]


smith_menus = [
  ("coop_smith", 0,
   "The smith of {s1}.^^Whatever arms and armour the shops of Calradia sell, the smith makes to order, for a fifth more than they ask: no need to ride from town to town after one helmet. What do you need?^^You carry {reg1} denars.",
   "none",
   [
     (set_background_mesh, "mesh_pic_town1"),
     (str_store_party_name, s1, "$current_town"),
     (store_troop_gold, reg1, "trp_player"),
   ],
   [("coop_smith_%d" % k, [], text, [(assign, "$coop_smith_page", k), (assign, "$coop_smith_step", 1),
                                     (jump_to_menu, "mnu_coop_smith_shop")])
    for k, (text, _) in enumerate(pages())] + [
     ("coop_smith_back", [], "Back to the town.", [(call_script, "script_coop_smith_close"), (jump_to_menu, "mnu_town")]),
   ]),

  # the trade screen from the menu's own code; when it closes the code runs again and the goods go
  ("coop_smith_shop", 0,
   "The smith of {s1}.",
   "none",
   [
     (str_store_party_name, s1, "$current_town"),
     (try_begin),
       (eq, "$coop_smith_step", 1),
       (assign, "$coop_smith_step", 2),
       (call_script, "script_coop_smith_open"),
     (else_try),
       (eq, "$coop_smith_step", 2),
       (call_script, "script_coop_smith_close"),
       (jump_to_menu, "mnu_coop_smith"),
     (try_end),
   ],
   [
     ("coop_smith_shop_back", [], "Back to the smith.",
      [(call_script, "script_coop_smith_close"), (jump_to_menu, "mnu_coop_smith")]),
   ]),
]
