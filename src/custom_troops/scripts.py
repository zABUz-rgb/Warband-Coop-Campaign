from header_common import *
from header_operations import *
from header_items import *
from header_mission_templates import af_override_everything
from header_troops import *
from module_constants import *
from coop.constants import *
from coop.mp import MP_BUF
from coop_merge import find_line, insert_after, insert_before, script_block
from custom_troops.constants import *
from custom_troops import item_tiers
from custom_troops.presentations import scripts as screen_scripts

# What John Blackborn does for the player's soldiers. Three levels of a kind wear the same, and each kind, so each
# tier of a branch, has gear of its own; it is read from the first level.
# A soldier's kind and level give its troop: custom_first + 3 * kind + level - 1.
# In a co-op session what changes goes to the other games as a word (script_cf_custom_word_send): the host
# makes the army, the bridge keeps it in army.json, and every game that comes in hears all of it, the host's
# too: a save loaded or the bridge started anew takes nothing back (tools/coop_bridge.py).

BUF = "p_coop_buf"
BUF_FIRST = 2     # the reply's first number there: its kind is at slot 1


def item_slots():
  """Ops: each item's lowest tier, from what a soldier of each tier may be given."""
  from module_items import items
  list_tier1_items, list_tier2_items, list_tier3_items, list_tier4_items, list_tier5_items = item_tiers.tier_lists(items)
  lists = [list_tier1_items, list_tier2_items, list_tier3_items, list_tier4_items, list_tier5_items]
  return [(item_set_slot, "itm_" + item, slot_item_custom_tier, tier) for item, tier in item_tiers.first_tiers(lists).items()]


def train_cost_ops():
  """Ops: :cost, what level :level + 1 of tier :tier costs (the tier's two prices)."""
  ops = []
  for tier, (second, third) in custom_train_cost.items():
    ops += [(try_begin), (eq, ":tier", tier), (assign, ":cost", second),
            (try_begin), (eq, ":level", 2), (assign, ":cost", third), (try_end), (try_end)]
  return ops


def own_game():
  """Conditions: a game the army's words go out from: a client, or the host while its world runs."""
  return [(this_or_next|eq, "$coop_role", coop_role_client), (eq, "$coop_role", coop_role_server),
          (this_or_next|eq, "$coop_role", coop_role_client), (eq, "$coop_srv_player", 1)]


scripts = [
  # script_custom_items_init: what each item's lowest tier is, from the lists of item_tiers.py
  ("custom_items_init", item_slots()),

  # script_custom_troop: arg1 = kind, arg2 = level; reg0 = the troop
  ("custom_troop",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":level", 2),
     (store_mul, reg0, ":kind", 3),
     (val_add, reg0, ":level"),
     (val_sub, reg0, 1),
     (val_add, reg0, custom_first),
    ]),

  # script_custom_tier: arg1 = kind; reg0 = its tier
  ("custom_tier",
   [
     (store_script_param, ":kind", 1),
     (assign, reg0, 1),
     (try_begin),
       (gt, ":kind", 0),
       (store_sub, reg0, ":kind", 1),
       (val_mod, reg0, len(TIERS)),
       (val_add, reg0, 2),
     (try_end),
    ]),

  # script_custom_tier_kind: arg1 = tier; reg0 = that tier's kind in the branch $custom_branch
  ("custom_tier_kind",
   [
     (store_script_param, ":tier", 1),
     (store_mul, reg0, "$custom_branch", len(TIERS)),
     (val_add, reg0, ":tier"),
     (val_sub, reg0, 1),
    ]),

  # script_custom_level: arg1 = kind; reg0 = the level bought for it
  ("custom_level",
   [
     (store_script_param, ":kind", 1),
     (store_add, ":slot", custom_slot_level, ":kind"),
     (troop_get_slot, reg0, custom_holder, ":slot"),
     (val_max, reg0, 1),
    ]),

  # script_custom_shown: arg1 = kind; reg0 = the troop the tree shows: the kind at its level
  ("custom_shown",
   [
     (store_script_param, ":kind", 1),
     (call_script, "script_custom_level", ":kind"),
     (call_script, "script_custom_troop", ":kind", reg0),
    ]),

  # script_custom_gear_count: arg1 = kind; reg0 = how many items its soldiers carry
  ("custom_gear_count",
   [
     (store_script_param, ":kind", 1),
     (call_script, "script_custom_troop", ":kind", 1),
     (assign, ":troop", reg0),
     (assign, ":count", 0),
     (troop_get_inventory_capacity, ":capacity", ":troop"),
     (try_for_range, ":slot", 0, ":capacity"),
       (troop_get_inventory_slot, ":item", ":troop", ":slot"),
       (ge, ":item", 0),
       (val_add, ":count", 1),
     (try_end),
     (assign, reg0, ":count"),
    ]),

  # script_custom_has_item: arg1 = troop, arg2 = item; reg0 = the inventory slot it lies in, or -1
  ("custom_has_item",
   [
     (store_script_param, ":troop", 1),
     (store_script_param, ":wanted", 2),
     (assign, ":found", -1),
     (troop_get_inventory_capacity, ":capacity", ":troop"),
     (try_for_range, ":slot", 0, ":capacity"),
       (eq, ":found", -1),
       (troop_get_inventory_slot, ":item", ":troop", ":slot"),
       (eq, ":item", ":wanted"),
       (assign, ":found", ":slot"),
     (try_end),
     (assign, reg0, ":found"),
    ]),

  # script_custom_item_change: arg1 = kind, arg2 = item, arg3 = 1 add, 0 take away: on all three levels
  ("custom_item_change",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":item", 2),
     (store_script_param, ":add", 3),
     ] + [op for level in LEVELS for op in [
     (call_script, "script_custom_troop", ":kind", level),
     (assign, ":troop", reg0),
     (call_script, "script_custom_has_item", ":troop", ":item"),
     (try_begin),
       (eq, ":add", 1),
       (eq, reg0, -1),
       (troop_add_item, ":troop", ":item"),
     (else_try),
       (eq, ":add", 0),
       (ge, reg0, 0),
       (troop_set_inventory_slot, ":troop", reg0, -1),
     (try_end),
     ]] + [
     (store_add, ":slot", custom_slot_gear, ":kind"),
     (troop_set_slot, custom_holder, ":slot", custom_word_change),
    ]),

  # script_custom_portrait: arg1 = troop, arg2 = 1 for no helmet and no weapons: what a soldier carries goes on its
  # portrait as override items, the dearest of each armour and its first weapons (bought gear never shows by itself:
  # the engine drew such soldiers naked). reg0 = the dearest horse, or -1
  ("custom_portrait",
   [
     (store_script_param, ":troop", 1),
     (store_script_param, ":hide", 2),
     (cur_tableau_set_override_flags, af_override_everything),
     (troop_get_inventory_capacity, ":capacity", ":troop"),
     (try_for_range, ":type", itp_type_head_armor, itp_type_hand_armor + 1),
       (this_or_next|eq, ":hide", 0),
       (neq, ":type", itp_type_head_armor),
       (assign, ":best", -1),
       (assign, ":best_value", -1),
       (try_for_range, ":slot", 0, ":capacity"),
         (troop_get_inventory_slot, ":item", ":troop", ":slot"),
         (ge, ":item", 0),
         (item_get_type, ":item_type", ":item"),
         (eq, ":item_type", ":type"),
         (store_item_value, ":value", ":item"),
         (gt, ":value", ":best_value"),
         (assign, ":best", ":item"),
         (assign, ":best_value", ":value"),
       (try_end),
       (ge, ":best", 0),
       (cur_tableau_add_override_item, ":best"),
     (try_end),
     (assign, ":horse", -1),
     (assign, ":horse_value", -1),
     (assign, ":weapons", 0),
     (try_for_range, ":slot", 0, ":capacity"),
       (troop_get_inventory_slot, ":item", ":troop", ":slot"),
       (ge, ":item", 0),
       (item_get_type, ":item_type", ":item"),
       (try_begin),
         (eq, ":item_type", itp_type_horse),
         (store_item_value, ":value", ":item"),
         (gt, ":value", ":horse_value"),
         (assign, ":horse", ":item"),
         (assign, ":horse_value", ":value"),
       (else_try),
         (eq, ":hide", 0),
         (is_between, ":item_type", itp_type_one_handed_wpn, itp_type_goods),
         (lt, ":weapons", 4),
         (val_add, ":weapons", 1),
         (cur_tableau_add_override_item, ":item"),
       (try_end),
     (try_end),
     (assign, reg0, ":horse"),
    ]),

  # script_custom_prices: arg1 = item; reg0 = what it costs for soldiers, reg1 = what it sells for. Native's
  # penalty for an item, 100 less 5 for each point of Trade, counts from the price with no Trade at all
  ("custom_prices",
   [
     (store_script_param, ":item", 1),
     (call_script, "script_dplmc_get_trade_penalty", ":item", -1, "trp_player", -1),
     (store_add, ":penalty", reg0, 100),
     (val_max, ":penalty", 100),
     (store_item_value, ":value", ":item"),
     (store_mul, reg0, ":value", custom_gear_factor),
     (val_mul, reg0, ":penalty"),
     (val_div, reg0, 200),
     (store_mul, reg1, ":value", custom_sell_percent),
     (val_mul, reg1, 2),
     (val_div, reg1, ":penalty"),
    ]),

  # script_custom_buy: arg1 = kind, arg2 = item. The check on the tier stands here too, whatever the screen shows
  ("custom_buy",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":item", 2),
     (call_script, "script_custom_tier", ":kind"),
     (assign, ":tier", reg0),
     (item_get_slot, ":needs", ":item", slot_item_custom_tier),
     (call_script, "script_custom_troop", ":kind", 1),
     (call_script, "script_custom_has_item", reg0, ":item"),
     (assign, ":held", reg0),
     (call_script, "script_custom_gear_count", ":kind"),
     (assign, ":count", reg0),
     (call_script, "script_custom_prices", ":item"),
     (assign, ":price", reg0),
     (store_troop_gold, ":gold", "trp_player"),
     (try_begin),
       (this_or_next|eq, ":needs", 0),
       (gt, ":needs", ":tier"),
       (display_message, "@Soldiers of this tier may not have that.", 0xFF6666),
     (else_try),
       (ge, ":held", 0),
     (else_try),
       (ge, ":count", custom_gear_max),
       (assign, reg1, custom_gear_max),
       (display_message, "@A soldier carries no more than {reg1} things.", 0xFF6666),
     (else_try),
       (lt, ":gold", ":price"),
       (display_message, "@You have too few dinars.", 0xFF6666),
     (else_try),
       (troop_remove_gold, "trp_player", ":price"),
       (item_get_slot, ":paid", ":item", slot_item_custom_paid),
       (val_add, ":paid", 1),
       (item_set_slot, ":item", slot_item_custom_paid, ":paid"),
       (call_script, "script_custom_item_change", ":kind", ":item", 1),
     (try_end),
    ]),

  # script_custom_sell: arg1 = kind, arg2 = item
  ("custom_sell",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":item", 2),
     (call_script, "script_custom_troop", ":kind", 1),
     (call_script, "script_custom_has_item", reg0, ":item"),
     (try_begin),
       (ge, reg0, 0),
       (item_get_slot, ":paid", ":item", slot_item_custom_paid),
       (try_begin),
         (gt, ":paid", 0),
         (val_sub, ":paid", 1),
         (item_set_slot, ":item", slot_item_custom_paid, ":paid"),
         (call_script, "script_custom_prices", ":item"),
         (troop_add_gold, "trp_player", reg1),
       (try_end),
       (call_script, "script_custom_item_change", ":kind", ":item", 0),
     (try_end),
    ]),

  # script_custom_swap: arg1 = troop, arg2 = troop: the first's men, wounded as they were, become the second's.
  # The engine lets no script read a stack's experience: it starts anew
  ("custom_swap",
   [
     (store_script_param, ":from", 1),
     (store_script_param, ":to", 2),
     (assign, ":men", 0),
     (assign, ":wounded", 0),
     (party_get_num_companion_stacks, ":stacks", "p_main_party"),
     (try_for_range, ":stack", 0, ":stacks"),
       (party_stack_get_troop_id, ":troop", "p_main_party", ":stack"),
       (eq, ":troop", ":from"),
       (party_stack_get_size, ":men", "p_main_party", ":stack"),
       (party_stack_get_num_wounded, ":wounded", "p_main_party", ":stack"),
     (try_end),
     (try_begin),
       (gt, ":men", 0),
       (party_remove_members, "p_main_party", ":from", ":men"),
       (party_force_add_members, "p_main_party", ":to", ":men"),
       (party_wound_members, "p_main_party", ":to", ":wounded"),
     (try_end),
    ]),

  # script_custom_train_cost: arg1 = kind, arg2 = level the men stand at; reg0 = the next level's price
  ("custom_train_cost",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":level", 2),
     (call_script, "script_custom_tier", ":kind"),
     (assign, ":tier", reg0),
     (assign, ":cost", 0),
     ] + train_cost_ops() + [
     (assign, reg0, ":cost"),
    ]),

  # script_cf_custom_train_text: arg1 = kind, arg2 = level: an option of the training menu, or a failure when the
  # kind does not stand at that level. s1 = the soldier, reg2 = the next level, reg4 = dinars
  ("cf_custom_train_text",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":level", 2),
     (call_script, "script_custom_level", ":kind"),
     (eq, reg0, ":level"),
     (call_script, "script_custom_troop", ":kind", ":level"),
     (str_store_troop_name, s1, reg0),
     (call_script, "script_custom_train_cost", ":kind", ":level"),
     (assign, reg4, reg0),
     (store_add, reg2, ":level", 1),
    ]),

  # script_custom_train: arg1 = kind, arg2 = the level it stands at: it goes up one, for the men there are and those
  # to come. Their kind, and so their tier, stays
  ("custom_train",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":level", 2),
     (call_script, "script_custom_train_cost", ":kind", ":level"),
     (assign, ":cost", reg0),
     (store_troop_gold, ":gold", "trp_player"),
     (call_script, "script_custom_level", ":kind"),
     (try_begin),
       (eq, reg0, ":level"),
       (ge, ":gold", ":cost"),
       (troop_remove_gold, "trp_player", ":cost"),
       (store_add, ":next", ":level", 1),
       (store_add, ":slot", custom_slot_level, ":kind"),
       (troop_set_slot, custom_holder, ":slot", ":next"),
       (store_add, ":slot", custom_slot_level_word, ":kind"),
       (troop_set_slot, custom_holder, ":slot", custom_word_change),
       (call_script, "script_custom_levels_apply"),
     (try_end),
    ]),

  # script_custom_levels_apply: men standing below their kind's level, promoted, hired or brought from elsewhere,
  # rise to it. A promotion lands on level 1; no script reads a stack's experience, so only such men lose theirs
  ("custom_levels_apply",
   [
     (try_for_range, ":kind", 0, custom_kinds),
       (call_script, "script_custom_level", ":kind"),
       (assign, ":level", reg0),
       (gt, ":level", 1),
       (call_script, "script_custom_troop", ":kind", ":level"),
       (assign, ":to", reg0),
       (try_for_range, ":low", 1, ":level"),
         (call_script, "script_custom_troop", ":kind", ":low"),
         (call_script, "script_custom_swap", reg0, ":to"),
       (try_end),
     (try_end),
    ]),

  # script_cf_custom_can_hire: arg1 = men: fails when the dinars or the room for them are short
  ("cf_custom_can_hire",
   [
     (store_script_param, ":men", 1),
     (store_mul, ":cost", ":men", custom_recruit_cost),
     (store_troop_gold, ":gold", "trp_player"),
     (ge, ":gold", ":cost"),
     (party_get_free_companions_capacity, ":room", "p_main_party"),
     (ge, ":room", ":men"),
    ]),

  # script_custom_hire: arg1 = men: recruits, the lowest there are
  ("custom_hire",
   [
     (store_script_param, ":men", 1),
     (store_mul, ":cost", ":men", custom_recruit_cost),
     (troop_remove_gold, "trp_player", ":cost"),
     (call_script, "script_custom_level", 0),
     (call_script, "script_custom_troop", 0, reg0),
     (party_add_members, "p_main_party", reg0, ":men"),
    ]),

  # script_custom_army_make: the army stands; the others' games hear it by its name
  ("custom_army_make",
   [
     (assign, "$custom_army_made", 1),
     (troop_set_slot, custom_holder, custom_slot_name, custom_word_change),
    ]),

  # script_custom_name_set: arg1 = 0 the army, 1 + kind a soldier: its name becomes s0. Three levels of a
  # soldier bear one name
  ("custom_name_set",
   [
     (store_script_param, ":index", 1),
     (try_begin),
       (neg|str_is_empty, s0),
       (try_begin),
         (eq, ":index", 0),
         (troop_set_name, custom_holder, s0),
         (troop_set_plural_name, custom_holder, s0),
       (else_try),
         (store_sub, ":kind", ":index", 1),
         ] + [op for level in LEVELS for op in [
         (call_script, "script_custom_troop", ":kind", level),
         (troop_set_name, reg0, s0),
         (troop_set_plural_name, reg0, s0),
         ]] + [
       (try_end),
     (try_end),
    ]),

  # script_custom_open: arg1 = a screen, once John's conversation is over: his menu opens it
  ("custom_open",
   [
     (store_script_param, "$custom_screen", 1),
     (jump_to_menu, "mnu_custom_screen"),
    ]),

  # script_custom_session: a new session. The bridge's army.json is the army: it tells all the games, the host's too.
  # What the host's save holds goes to the bridge only for what it has no word of (an army older than the file).
  # A client's copy of the save may be older: the bridge's word stands
  ("custom_session",
   [
     (assign, "$custom_word_wait", 0),
     (try_begin),
       (eq, "$coop_role", coop_role_client),
       (assign, "$custom_army_made", 0),
     (try_end),
     (store_mul, ":mark", "$custom_army_made", custom_word_saved),
     (try_for_range, ":kind", 0, custom_kinds),
       (store_add, ":slot", custom_slot_gear, ":kind"),
       (troop_set_slot, custom_holder, ":slot", ":mark"),
       (call_script, "script_custom_level", ":kind"),
       (store_add, ":slot", custom_slot_level_word, ":kind"),
       (troop_set_slot, custom_holder, ":slot", 0),
       (gt, reg0, 1),
       (troop_set_slot, custom_holder, ":slot", ":mark"),
     (try_end),
     (store_add, ":names", custom_kinds, 1),
     (try_for_range, ":index", 0, ":names"),
       (store_add, ":slot", custom_slot_name, ":index"),
       (troop_set_slot, custom_holder, ":slot", ":mark"),
     (try_end),
    ]),

  # script_cf_custom_word_send: one thing of the army the other games have not heard yet, as a request of its
  # own. Fails when there is nothing to say, or the ordinary requests' turn has come
  ("cf_custom_word_send",
   own_game() + [
     (assign, ":found", -1),
     (assign, ":mark", 0),
     (try_begin),
       (gt, "$custom_word_wait", 0),
       (val_sub, "$custom_word_wait", 1),
     (else_try),
       (store_add, ":names", custom_kinds, 1),
       (try_for_range, ":index", 0, ":names"),
         (eq, ":found", -1),
         (store_add, ":slot", custom_slot_name, ":index"),
         (troop_slot_ge, custom_holder, ":slot", custom_word_change),
         (troop_get_slot, ":mark", custom_holder, ":slot"),
         (troop_set_slot, custom_holder, ":slot", 0),
         (assign, ":found", ":index"),
         (assign, reg7, ":index"),
         (try_begin),
           (eq, ":index", 0),
           (str_store_troop_name, s15, custom_holder),
         (else_try),
           (store_sub, ":kind", ":index", 1),
           (call_script, "script_custom_troop", ":kind", 1),
           (str_store_troop_name, s15, reg0),
         (try_end),
         (str_store_string, s17, "@&an={reg7},{s15}"), #name last: it may hold spaces
       (try_end),
       (try_for_range, ":kind", 0, custom_kinds),
         (eq, ":found", -1),
         (store_add, ":slot", custom_slot_gear, ":kind"),
         (troop_slot_ge, custom_holder, ":slot", custom_word_change),
         (troop_get_slot, ":mark", custom_holder, ":slot"),
         (troop_set_slot, custom_holder, ":slot", 0),
         (assign, ":found", ":kind"),
         (call_script, "script_custom_gear_word", ":kind"),
       (try_end),
       (try_for_range, ":kind", 0, custom_kinds),
         (eq, ":found", -1),
         (store_add, ":slot", custom_slot_level_word, ":kind"),
         (troop_slot_ge, custom_holder, ":slot", custom_word_change),
         (troop_get_slot, ":mark", custom_holder, ":slot"),
         (troop_set_slot, custom_holder, ":slot", 0),
         (assign, ":found", ":kind"),
         (assign, reg7, ":kind"),
         (call_script, "script_custom_level", ":kind"),
         (assign, reg6, reg0),
         (str_store_string, s17, "@&al={reg7},{reg6}"),
       (try_end),
     (try_end),
     (ge, ":found", 0),
     (try_begin),
       (eq, ":mark", custom_word_saved),
       (str_store_string, s17, "@&ao=1{s17}"),
     (try_end),
     (assign, "$custom_word_wait", custom_word_gap),
     (val_add, "$coop_net_seq", 1),
     (assign, reg1, "$coop_net_seq"),
     (set_fixed_point_multiplier, 100),
     (party_get_position, pos1, "p_main_party"),
     (position_get_x, reg2, pos1),
     (position_get_y, reg3, pos1),
     (assign, reg4, 1),
     (try_begin),
       (map_free),
       (assign, reg4, 0),
     (try_end),
     (store_current_hours, reg5),
     (assign, reg8, "$coop_srv_player"),
     (str_store_string, s10, "@" + coop_client_url + "/cli?seq={reg1}&h={reg5}&free=0&x={reg2}&y={reg3}&busy={reg4}&srvp={reg8}{s17}"),
     (assign, "$coop_net_pending", 1),
     (send_message_to_url, s10, 0),
    ]),

  # script_custom_gear_word: arg1 = kind: what its soldiers carry onto s17
  ("custom_gear_word",
   [
     (store_script_param, ":kind", 1),
     (assign, reg7, ":kind"),
     (str_store_string, s17, "@&ag={reg7}"),
     (call_script, "script_custom_troop", ":kind", 1),
     (assign, ":troop", reg0),
     (troop_get_inventory_capacity, ":capacity", ":troop"),
     (try_for_range, ":slot", 0, ":capacity"),
       (troop_get_inventory_slot, reg7, ":troop", ":slot"),
       (ge, reg7, 0),
       (str_store_string, s17, "@{s17},{reg7}"),
     (try_end),
    ]),

  # script_custom_gear_clear: arg1 = troop: nothing left on it
  ("custom_gear_clear",
   [
     (store_script_param, ":troop", 1),
     (troop_get_inventory_capacity, ":capacity", ":troop"),
     (try_for_range, ":slot", 0, ":capacity"),
       (troop_set_inventory_slot, ":troop", ":slot", -1),
     (try_end),
    ]),

  # script_custom_reply: arg1 = reply kind: 34 a name came (s0), 35 a kind's gear: kind, n, items..., 36 a kind's
  # level: kind, level
  ("custom_reply",
   [
     (store_script_param, ":reply", 1),
     (try_begin),
       (eq, ":reply", 34),
       (party_get_slot, ":index", BUF, BUF_FIRST),
       (try_begin),
         (eq, ":index", 0),
         (assign, "$custom_army_made", 1),
       (try_end),
       (call_script, "script_custom_name_set", ":index"),
     (else_try),
       (eq, ":reply", 35),
       (party_get_slot, ":kind", BUF, BUF_FIRST),
       (store_add, ":at", BUF_FIRST, 1),
       (party_get_slot, ":n", BUF, ":at"),
       (val_add, ":at", 1),
       (store_add, ":end", ":at", ":n"),
       ] + [op for level in LEVELS for op in [
       (call_script, "script_custom_troop", ":kind", level),
       (assign, ":troop", reg0),
       (call_script, "script_custom_gear_clear", ":troop"),
       (try_for_range, ":item_at", ":at", ":end"),
         (party_get_slot, ":item", BUF, ":item_at"),
         (troop_add_item, ":troop", ":item"),
       (try_end),
       ]] + [
     (else_try),
       (eq, ":reply", 36),
       (party_get_slot, ":kind", BUF, BUF_FIRST),
       (store_add, ":at", BUF_FIRST, 1),
       (party_get_slot, ":level", BUF, ":at"),
       (store_add, ":slot", custom_slot_level, ":kind"),
       (troop_set_slot, custom_holder, ":slot", ":level"),
     (try_end),
    ]),

  # script_custom_mp_gear: the battle server hears a kind's gear: MP_BUF 3 kind, 4 n, 5.. items
  ("custom_mp_gear",
   [
     (troop_get_slot, ":kind", MP_BUF, 3),
     (troop_get_slot, ":n", MP_BUF, 4),
     (store_add, ":end", 5, ":n"),
     ] + [op for level in LEVELS for op in [
     (call_script, "script_custom_troop", ":kind", level),
     (assign, ":troop", reg0),
     (call_script, "script_custom_gear_clear", ":troop"),
     (try_for_range, ":at", 5, ":end"),
       (troop_get_slot, ":item", MP_BUF, ":at"),
       (troop_add_item, ":troop", ":item"),
     (try_end),
     ]] + [
    ]),
]


def merge(orig_scripts, **extra):
  orig_scripts += scripts + screen_scripts
  # co-op: a new session, what goes out, what comes in
  script_block(orig_scripts, "coop_together_reset").append((call_script, "script_custom_session"))
  ping = script_block(orig_scripts, "coop_ping_send")
  ping[find_line(ping, (try_begin)) + 1:find_line(ping, (try_begin)) + 1] = [
    (call_script, "script_cf_custom_word_send"),
    (else_try),
  ]
  # (a name never comes without its text: the bridge sees to that)
  handler = script_block(orig_scripts, "game_receive_url_response")
  insert_before(handler, (is_between, ":kind", 27, 33), [
    (is_between, ":kind", 34, 37),
    (this_or_next|eq, "$coop_role", coop_role_client),
    (eq, "$coop_srv_player", 1),
    (call_script, "script_custom_reply", ":kind"),
    (else_try),
  ])
  # a soldier's portrait, in the party window and the troop tree
  insert_after(script_block(orig_scripts, "add_troop_to_cur_tableau_for_party"),
               (troop_get_inventory_slot, ":horse_item", ":troop_no", ek_horse), [
    (try_begin),
      (is_between, ":troop_no", custom_first, custom_holder),
      (call_script, "script_custom_portrait", ":troop_no", ":hide_weapons"),
      (assign, ":horse_item", reg0),
    (try_end),
  ])
  reply = script_block(orig_scripts, "coop_mp_reply")
  insert_before(reply, (eq, ":kind", 2), [
    (eq, ":kind", 10),
    (call_script, "script_custom_mp_gear"),
    (else_try),
  ])
