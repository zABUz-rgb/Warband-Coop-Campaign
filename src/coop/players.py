from header_common import *
from header_operations import *
from header_game_menus import *
from module_constants import *
from coop.constants import *

# Players together on the map: one player joins another's party (asks, the other accepts or
# declines; then follows the leader and is called into the leader's joint battles), and players
# trade: troops (chosen on the exchange screen), items (on the loot screen) and denars go in one offer, the
# receiver accepts or declines it; a declined offer goes back (11-07: items and denars too). An entry is
# (code, value): see coop_trade_gold and coop_trade_item. Requests go out with the next map request (s17),
# answers come back as replies:
#   15 an offer id|from slot|n|(code, value)*n               16 how the offer went id|accepted|n|...
#   17 a player asks to join this one: from slot              18 the answer: leader slot|accepted
#   19 to the leader: slot|joined (1) or left (0)             20 the leader let this player go: leader slot
# Player slots are kept + 1, so that 0 (a new game's globals) means none.
# trp_tutorial_student_2 keeps an offer while its menu is open; p_temp_party_2 the troops chosen for one,
# trp_temp_array_a's inventory the items (nothing else keeps items there; a hero's inventory is in the save).

OFFER = "trp_tutorial_student_2"
GIFT = "p_temp_party_2"
BOX = "trp_temp_array_a"


def puppet_end():
  from coop.triggers import puppet_range
  return puppet_range()[1]


def player_name_to_s1(slot_plus_one):
  """Ops: s1 = the name of the player in slot (kept + 1)."""
  return [
    (str_store_string, s1, "@another player"),
    (try_begin),
      (gt, slot_plus_one, 0),
      (store_add, ":puppet", "p_coop_puppet_1", slot_plus_one),
      (val_sub, ":puppet", 1),
      (str_store_party_name, s1, ":puppet"),
    (try_end),
  ]


players_scripts = [
  # script_coop_players_reply: replies 15-20 (see above)
  ("coop_players_reply",
   [
     (store_script_param, ":kind", 1),
     (try_begin),
       (eq, ":kind", 15), #an offer of troops: kept until its menu answers
       (eq, "$coop_offer_pending", 0),
       (party_get_slot, ":n", "p_coop_buf", 4),
       (val_min, ":n", coop_net_max_stacks),
       (store_mul, ":numbers", ":n", 2),
       (val_add, ":numbers", 3),
       (try_for_range, ":k", 0, ":numbers"),
         (store_add, ":src", ":k", 2),
         (party_get_slot, ":v", "p_coop_buf", ":src"),
         (troop_set_slot, OFFER, ":k", ":v"),
       (try_end),
       (assign, "$coop_offer_pending", 1),
     (else_try),
       (eq, ":kind", 16), #how my offer went: declined troops come back
       (party_get_slot, ":accepted", "p_coop_buf", 3),
       (party_get_slot, ":n", "p_coop_buf", 4),
       (try_begin),
         (eq, ":accepted", 1),
         (display_message, "@CoopWorld: your offer was accepted.", 0x66FF66),
       (else_try),
         (try_for_range, ":k", 0, ":n"),
           (store_mul, ":at", ":k", 2),
           (val_add, ":at", 5),
           (party_get_slot, ":troop", "p_coop_buf", ":at"),
           (val_add, ":at", 1),
           (party_get_slot, ":count", "p_coop_buf", ":at"),
           (call_script, "script_coop_offer_take", ":troop", ":count"),
         (try_end),
         (display_message, "@CoopWorld: your offer was declined and came back to you.", 0xFFDD66),
       (try_end),
     (try_end),
    ]),

  # script_coop_offer_to_s2: s2 = the offered troops, one per line
  ("coop_offer_to_s2",
   [
     (str_clear, s2),
     (troop_get_slot, ":n", OFFER, 2),
     (try_for_range, ":k", 0, ":n"),
       (store_mul, ":at", ":k", 2),
       (val_add, ":at", 3),
       (troop_get_slot, ":troop", OFFER, ":at"),
       (val_add, ":at", 1),
       (troop_get_slot, reg1, OFFER, ":at"),
       (try_begin),
         (eq, ":troop", coop_trade_gold),
         (str_store_string, s2, "@{s2}^{reg1} denars"),
       (else_try),
         (ge, ":troop", coop_trade_item),
         (store_sub, ":item", ":troop", coop_trade_item),
         (is_between, ":item", all_items_begin, all_items_end),
         (str_store_item_name, s3, ":item"),
         (store_div, reg1, reg1, 100),
         (try_begin),
           (gt, reg1, 0),
           (str_store_string, s2, "@{s2}^{s3} ({reg1})"),
         (else_try),
           (str_store_string, s2, "@{s2}^{s3}"),
         (try_end),
       (else_try),
         (str_store_troop_name_by_count, s3, ":troop", reg1),
         (str_store_string, s2, "@{s2}^{reg1} {s3}"),
       (try_end),
     (try_end),
    ]),

  # script_coop_offer_take: arg1 = an offer's code, arg2 = its value (see coop_trade_gold): it comes to this
  # player (an accepted offer, or one's own declined offer coming back). An item with no room left in the
  # inventory comes as its price.
  ("coop_offer_take",
   [
     (store_script_param, ":code", 1),
     (store_script_param, ":value", 2),
     (try_begin),
       (eq, ":code", coop_trade_gold),
       (gt, ":value", 0),
       (troop_add_gold, "trp_player", ":value"),
     (else_try),
       (ge, ":code", coop_trade_item),
       (store_sub, ":item", ":code", coop_trade_item),
       (is_between, ":item", all_items_begin, all_items_end),
       (store_mod, ":imod", ":value", 100),
       (store_div, ":amount", ":value", 100),
       (store_free_inventory_capacity, ":free", "trp_player"),
       (try_begin),
         (gt, ":free", 0),
         (troop_get_inventory_capacity, ":capacity", "trp_player"),
         (assign, ":at", -1),
         (try_for_range, ":slot", num_equipment_kinds, ":capacity"), #it goes into the first free slot
           (lt, ":at", 0),
           (troop_get_inventory_slot, ":there", "trp_player", ":slot"),
           (lt, ":there", 0),
           (assign, ":at", ":slot"),
         (try_end),
         (troop_add_item, "trp_player", ":item", ":imod"),
         (try_begin),
           (gt, ":amount", 0),
           (ge, ":at", 0),
           (troop_get_inventory_slot, ":there", "trp_player", ":at"),
           (eq, ":there", ":item"),
           (troop_inventory_slot_set_item_amount, "trp_player", ":at", ":amount"),
         (try_end),
       (else_try),
         (store_item_value, reg1, ":item"),
         (troop_add_gold, "trp_player", reg1),
         (str_store_item_name, s3, ":item"),
         (display_message, "@CoopWorld: no room in your inventory for {s3}: you get its price, {reg1} denars.", 0xFFDD66),
       (try_end),
     (else_try),
       (lt, ":code", coop_trade_gold),
       (gt, ":code", 0),
       (gt, ":value", 0),
       (party_add_members, "p_main_party", ":code", ":value"),
     (try_end),
    ]),

  # script_coop_trade_back: a trade not sent: its troops and items go back to the player (its denars were never
  # taken), and none is being made
  ("coop_trade_back",
   [
     (call_script, "script_coop_gift_back"),
     (troop_get_inventory_capacity, ":capacity", BOX),
     (try_for_range, ":slot", 0, ":capacity"),
       (troop_get_inventory_slot, ":item", BOX, ":slot"),
       (ge, ":item", 0),
       (troop_get_inventory_slot_modifier, ":imod", BOX, ":slot"),
       (troop_inventory_slot_get_item_amount, ":amount", BOX, ":slot"),
       (store_mul, ":value", ":amount", 100),
       (val_add, ":value", ":imod"),
       (store_add, ":code", ":item", coop_trade_item),
       (call_script, "script_coop_offer_take", ":code", ":value"),
     (try_end),
     (troop_clear_inventory, BOX),
     (assign, "$coop_trade_gold", 0),
     (assign, "$coop_trade_open", 0),
    ]),

  # script_coop_trade_count: reg3 = the items chosen, reg4 = the denars (no more than the player carries), reg5 =
  # the denars the player carries
  ("coop_trade_count",
   [
     (assign, reg3, 0),
     (troop_get_inventory_capacity, ":capacity", BOX),
     (try_for_range, ":slot", 0, ":capacity"),
       (troop_get_inventory_slot, ":item", BOX, ":slot"),
       (ge, ":item", 0),
       (val_add, reg3, 1),
     (try_end),
     (store_troop_gold, reg5, "trp_player"),
     (val_min, "$coop_trade_gold", reg5),
     (assign, reg4, "$coop_trade_gold"),
    ]),

  # script_coop_trade_to_s12: s12 = ",code,value,..." the offer sent (denars first, then troops, then items, no
  # more than coop_net_max_stacks); what finds no room goes back. The trade is over.
  ("coop_trade_to_s12",
   [
     (str_clear, s12),
     (assign, ":n", 0),
     (try_begin),
       (gt, "$coop_trade_send_gold", 0),
       (assign, reg21, coop_trade_gold),
       (assign, reg22, "$coop_trade_send_gold"),
       (str_store_string, s12, "@{s12},{reg21},{reg22}"),
       (val_add, ":n", 1),
     (try_end),
     (assign, "$coop_trade_send_gold", 0),
     (party_get_num_companion_stacks, ":stacks", GIFT),
     (try_for_range, ":stack", 0, ":stacks"),
       (party_stack_get_troop_id, reg21, GIFT, ":stack"),
       (party_stack_get_size, reg22, GIFT, ":stack"),
       (try_begin),
         (lt, ":n", coop_net_max_stacks),
         (str_store_string, s12, "@{s12},{reg21},{reg22}"),
         (val_add, ":n", 1),
       (else_try),
         (party_add_members, "p_main_party", reg21, reg22),
       (try_end),
     (try_end),
     (party_clear, GIFT),
     (troop_get_inventory_capacity, ":capacity", BOX),
     (try_for_range, ":slot", 0, ":capacity"),
       (troop_get_inventory_slot, ":item", BOX, ":slot"),
       (ge, ":item", 0),
       (troop_get_inventory_slot_modifier, ":imod", BOX, ":slot"),
       (troop_inventory_slot_get_item_amount, ":amount", BOX, ":slot"),
       (store_mul, reg22, ":amount", 100),
       (val_add, reg22, ":imod"),
       (store_add, reg21, ":item", coop_trade_item),
       (try_begin),
         (lt, ":n", coop_net_max_stacks),
         (str_store_string, s12, "@{s12},{reg21},{reg22}"),
         (val_add, ":n", 1),
       (else_try),
         (call_script, "script_coop_offer_take", reg21, reg22),
       (try_end),
     (try_end),
     (troop_clear_inventory, BOX),
     (assign, "$coop_trade_gold", 0),
     (assign, "$coop_trade_open", 0),
    ]),

  # script_coop_gift_back: the chosen troops go back to the player's party
  ("coop_gift_back",
   [
     (party_get_num_companion_stacks, ":stacks", GIFT),
     (try_for_range, ":stack", 0, ":stacks"),
       (party_stack_get_troop_id, ":troop", GIFT, ":stack"),
       (party_stack_get_size, ":size", GIFT, ":stack"),
       (party_add_members, "p_main_party", ":troop", ":size"),
     (try_end),
     (party_clear, GIFT),
    ]),
]


def request_suffix():
  """Ops appending to s17 what the player asked for or answered since the last request."""
  return [
    (try_begin),
      (gt, "$coop_give_send", 0), #an offer for the player in this slot (+ 1): troops, items, denars
      (store_sub, reg7, "$coop_give_send", 1),
      (assign, "$coop_give_send", 0),
      # heroes (companions) are not given away: back to the party first
      (party_get_num_companion_stacks, ":stacks", GIFT),
      (try_for_range_backwards, ":stack", 0, ":stacks"),
        (party_stack_get_troop_id, ":troop", GIFT, ":stack"),
        (troop_is_hero, ":troop"),
        (party_remove_members, GIFT, ":troop", 1),
        (party_add_members, "p_main_party", ":troop", 1),
      (try_end),
      (call_script, "script_coop_trade_to_s12"),
      (str_store_string, s17, "@{s17}&give={reg7}{s12}"),
    (try_end),
    (try_begin),
      (gt, "$coop_offer_answer_id", 0),
      (assign, reg7, "$coop_offer_answer_id"),
      (assign, reg8, "$coop_offer_answer_yes"),
      (str_store_string, s17, "@{s17}&giveans={reg7},{reg8}"),
      (assign, "$coop_offer_answer_id", 0),
    (try_end),
  ]


def map_tick():
  """Ops for the map trigger (client and host): open the menu of troops offered."""
  return [
    (try_begin),
      (eq, "$coop_trade_open", 1), #a trade's window left some other way (a call to battle...): all comes back
      (map_free),
      (call_script, "script_coop_trade_back"),
    (try_end),
    (try_begin),
      (eq, "$coop_offer_pending", 1),
      (map_free),
      (jump_to_menu, "mnu_coop_troops_offered"),
    (try_end),
  ]


def trade_start(back_menu):
  """Ops: a trade with the player in $coop_give_to begins; what an earlier one left comes back first."""
  return [
    (call_script, "script_coop_trade_back"),
    (assign, "$coop_give_back", back_menu),
    (assign, "$coop_trade_open", 1),
    (jump_to_menu, "mnu_coop_give_troops"),
  ]


def plays():
  """Ops: this game is a player's (a client, or the host playing on the server)."""
  return [(this_or_next|eq, "$coop_role", coop_role_client), (eq, "$coop_srv_player", 1)]


def encounter_options():
  is_player = [(is_between, "$g_encountered_party", "p_coop_puppet_1", puppet_end())]
  return [
    ("coop_give_troops", plays() + is_player,
     "CoopWorld: trade with this player (troops, items, denars).",
     [
       (store_sub, "$coop_give_to", "$g_encountered_party", "p_coop_puppet_1"),
       (val_add, "$coop_give_to", 1),
       ] + trade_start("mnu_simple_encounter")),
  ]


def camp_options():
  return [
    ("coop_players", plays(), "CoopWorld: the other players (ride after them, trade)...",
     [(jump_to_menu, "mnu_coop_players")]),
  ]


def players_menu_options():
  """The camp's players menu: for each other player, what can be done without meeting on the map."""
  options = []
  for k in range(coop_max_players):
    puppet = f"p_coop_puppet_{k + 1}"
    name = [(party_is_active, puppet), (str_store_party_name, s1, puppet)]
    options += [
      ("coop_pl_give_%d" % k, plays() + name + [
         (store_distance_to_party_from_party, ":dist", "p_main_party", puppet),
         (le, ":dist", coop_give_distance)],
       "Trade with {s1}: troops, items, denars.",
       [
         (assign, "$coop_give_to", k + 1),
         ] + trade_start("mnu_coop_players")),
    ]
  return options + [
    ("coop_pl_write_hero", [(eq, "$coop_role", coop_role_client), (eq, "$coop_profile_state", 1)],
     "Write my hero down at the host now.",
     [
       (assign, "$coop_profile_frames", coop_profile_period_frames),
       (display_message, "@CoopWorld: your hero is written down at the host a few seconds after you are back on the map.", 0x66CCFF),
       (jump_to_menu, "mnu_coop_players"),
     ]),
    ("coop_pl_back", [], "Back.", [(jump_to_menu, "mnu_coop_camp")]),
  ]


def players_list_to_s10():
  """Ops: s10 = one line per other player: name and how far."""
  ops = [(str_clear, s10), (assign, ":any", 0)]
  for k in range(coop_max_players):
    puppet = f"p_coop_puppet_{k + 1}"
    ops += [
      (try_begin),
        (party_is_active, puppet),
        (assign, ":any", 1),
        (str_store_party_name, s1, puppet),
        (store_distance_to_party_from_party, reg1, "p_main_party", puppet),
        (str_store_string, s10, "@{s10}^{s1}: {reg1} km away."),
      (try_end),
    ]
  return ops + [
    (try_begin),
      (eq, ":any", 0),
      (str_store_string, s10, "@^Nobody else is in the world right now."),
    (try_end),
  ]


players_menus = [
  ("coop_players", 0,
   "CoopWorld: the players in this world:^{s10}^^A player close by (up to {reg2} km) may be traded with: troops, items and denars.",
   "none",
   players_list_to_s10() + [(assign, reg2, coop_give_distance)],
   players_menu_options()),

  ("coop_give_troops", 0,
   "CoopWorld: a trade with {s1}.^^Offered so far: {reg1} troops, {reg3} items, {reg4} denars (you carry {reg5}).^^Troops are chosen on the exchange screen (your party on the left, the offer on the right), items on the loot screen (the offer on the right). {s1} accepts or declines it all; what is declined comes back to you. Companions stay with you.",
   "none",
   player_name_to_s1("$coop_give_to") + [
     (assign, "$coop_trade_open", 1),
     (party_get_num_companions, reg1, GIFT),
     (call_script, "script_coop_trade_count"),
   ],
   [
     ("coop_give_choose", [], "Choose the troops.",
      [(change_screen_exchange_with_party, GIFT)]),
     ("coop_give_items", [], "Choose the items.",
      [(change_screen_loot, BOX)]),
     ] + [
     ("coop_give_gold_%d" % amount,
      [(store_troop_gold, ":gold", "trp_player"), (gt, ":gold", "$coop_trade_gold")],
      "Add %d denars." % amount,
      [
        (val_add, "$coop_trade_gold", amount),
        (store_troop_gold, ":gold", "trp_player"),
        (val_min, "$coop_trade_gold", ":gold"),
        (jump_to_menu, "mnu_coop_give_troops"),
      ]) for amount in (100, 1000, 10000)] + [
     ("coop_give_gold_none", [(gt, "$coop_trade_gold", 0)], "No denars.",
      [(assign, "$coop_trade_gold", 0), (jump_to_menu, "mnu_coop_give_troops")]),
     ("coop_give_send",
      [
        (party_get_num_companions, ":n", GIFT),
        (call_script, "script_coop_trade_count"),
        (val_add, ":n", reg3),
        (val_add, ":n", reg4),
        (gt, ":n", 0),
      ],
      "Send the offer.",
      [
        (call_script, "script_coop_trade_count"), #no more than the player carries now
        (troop_remove_gold, "trp_player", reg4),
        (assign, "$coop_trade_send_gold", reg4),
        (assign, "$coop_trade_gold", 0),
        (assign, "$coop_trade_open", 0), #what is in it goes with the next request
        (assign, "$coop_give_send", "$coop_give_to"),
        (display_message, "@CoopWorld: the offer is sent; waiting for the answer.", 0x66CCFF),
        (jump_to_menu, "$coop_give_back"),
      ]),
     ("coop_give_cancel", [], "Never mind.",
      [(call_script, "script_coop_trade_back"), (jump_to_menu, "$coop_give_back")]),
   ]),

  ("coop_troops_offered", 0,
   "CoopWorld: {s1} offers you:^{s2}",
   "none",
   [
     (troop_get_slot, ":slot", OFFER, 1),
     (val_add, ":slot", 1),
     ] + player_name_to_s1(":slot") + [
     (call_script, "script_coop_offer_to_s2"),
   ],
   [
     ("coop_offer_accept", [], "Accept.",
      [
        (troop_get_slot, ":n", OFFER, 2),
        (try_for_range, ":k", 0, ":n"),
          (store_mul, ":at", ":k", 2),
          (val_add, ":at", 3),
          (troop_get_slot, ":troop", OFFER, ":at"),
          (val_add, ":at", 1),
          (troop_get_slot, ":count", OFFER, ":at"),
          (call_script, "script_coop_offer_take", ":troop", ":count"),
        (try_end),
        (troop_get_slot, "$coop_offer_answer_id", OFFER, 0),
        (assign, "$coop_offer_answer_yes", 1),
        (assign, "$coop_offer_pending", 0),
        (change_screen_return),
      ]),
     ("coop_offer_decline", [], "Decline.",
      [
        (troop_get_slot, "$coop_offer_answer_id", OFFER, 0),
        (assign, "$coop_offer_answer_yes", 0),
        (assign, "$coop_offer_pending", 0),
        (change_screen_return),
      ]),
   ]),

]


def reply_branches():
  """else_try branches for net_reply_handler: kinds 15 and 16."""
  return [
    (else_try),
      (is_between, ":kind", 15, 17),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1),
      (call_script, "script_coop_players_reply", ":kind"),
  ]
