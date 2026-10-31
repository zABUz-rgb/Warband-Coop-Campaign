from header_common import *
from header_game_menus import *
from header_operations import *
from module_constants import *
from coop_merge import find_by_id, menu_options
from custom_troops.constants import *

# What John Blackborn's conversation leaves open. A dialog cannot show a screen by itself: its last line
# jumps here, and this menu's load opens what was asked for ($custom_screen). When the screen closes the
# menu stands: a word with John again, or back to where the player was ($custom_back_menu).


def train_options():
  options = []
  for kind in range(custom_kinds):
    for level in LEVELS[:-1]:
      options.append(("custom_train_%d_%d" % (kind, level),
        [
          (call_script, "script_cf_custom_train_text", kind, level),
          (try_begin),
            (store_troop_gold, ":gold", "trp_player"),
            (lt, ":gold", reg4),
            (disable_menu_option),
          (try_end),
        ],
        "{s1}: to level {reg2} ({reg3} men): {reg4} dinars.",
        [
          (call_script, "script_custom_train", kind, level),
          (jump_to_menu, "mnu_custom_train"),
        ]))
  return options


game_menus = [
  ("custom_screen", 0,
   "John Blackborn waits for your word.", "none",
   [
     (call_script, "script_coop_ping_kick"),
     (assign, ":screen", "$custom_screen"),
     (assign, "$custom_screen", 0), #the menu loads again when a screen closes
     (try_begin),
       (eq, ":screen", custom_screen_shop),
       (call_script, "script_custom_items_init"),
       (assign, "$custom_kind", -1),
       (start_presentation, "prsnt_custom_shop"),
     (else_try),
       (eq, ":screen", custom_screen_names),
       (start_presentation, "prsnt_custom_names"),
     (else_try),
       (eq, ":screen", custom_screen_train),
       (jump_to_menu, "mnu_custom_train"),
     (try_end),
   ],
   [
     ("custom_screen_talk", [], "Talk to John Blackborn.", [(call_script, "script_coop_blackborn_talk")]),
     ("custom_screen_back", [], "Back.", [(jump_to_menu, "$custom_back_menu")]),
   ]),

  ("custom_train", 0,
   "John Blackborn looks your men over. Training raises only their level of stats. Their tier stays as it is: it grows\
 in battles and at the training field. The price is one for all the men of a kind who stand at a level. The game cannot\
 carry their experience across, so what they have gathered towards the next tier is lost: promote those who are ready\
 first.^^You have {reg10} dinars.", "none",
   [
     (call_script, "script_coop_ping_kick"),
     (store_troop_gold, reg10, "trp_player"),
   ],
   train_options() + [
     ("custom_train_back", [], "That is all.", [(jump_to_menu, "mnu_custom_screen")]),
   ]),
]


def merge(orig_game_menus):
  orig_game_menus += game_menus
  # at the company's camp, and in whatever town or castle the player holds
  options = menu_options(orig_game_menus, "coop_shared")
  for i, option in enumerate(options):
    if option[0] == "coop_blackborn":
      options[i] = (option[0], option[1], option[2], [(assign, "$custom_back_menu", "mnu_coop_shared")] + list(option[3]))
  town = menu_options(orig_game_menus, "town")
  at = find_by_id(town, "town_leave")
  town[at:at] = [
    ("custom_blackborn", [(party_slot_eq, "$current_town", slot_town_lord, "trp_player")], "Talk to John Blackborn.",
     [
       (assign, "$custom_back_menu", "mnu_town"),
       (call_script, "script_coop_blackborn_talk"),
     ]),
  ]
