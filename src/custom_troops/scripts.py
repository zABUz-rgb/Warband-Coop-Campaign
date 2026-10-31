from header_common import *
from header_operations import *
from header_items import *
from header_troops import *
from module_constants import *
from coop.constants import *
from coop.mp import MP_BUF
from coop_merge import find_line, insert_before, script_block
from custom_troops.constants import *
from custom_troops import item_tiers
from custom_troops.presentations import scripts as screen_scripts

# What John Blackborn does for the player's soldiers. Three levels of a kind wear the same; a kind's gear is
# read from its first level. A soldier's kind and level give its troop: custom_first + 3 * kind + level - 1.
# In a co-op session what changes goes to the other games as a word (script_cf_custom_word_send): the host
# makes the army, the bridge remembers it, a game that joins hears all of it (tools/coop_bridge.py).

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

  # script_custom_men: arg1 = troop; reg0 = how many of it stand in the player's party
  ("custom_men",
   [
     (store_script_param, ":troop", 1),
     (party_count_companions_of_type, reg0, "p_main_party", ":troop"),
    ]),

  # script_custom_men_of_kind: arg1 = kind; reg0 = its men of all levels
  ("custom_men_of_kind",
   [
     (store_script_param, ":kind", 1),
     (assign, ":men", 0),
     ] + [op for level in LEVELS for op in [
     (call_script, "script_custom_troop", ":kind", level),
     (call_script, "script_custom_men", reg0),
     (val_add, ":men", reg0),
     ]] + [
     (assign, reg0, ":men"),
    ]),

  # script_custom_men_total: reg0 = how many of the army's soldiers stand in the player's party
  ("custom_men_total",
   [
     (assign, ":men", 0),
     (try_for_range, ":kind", 0, custom_kinds),
       (call_script, "script_custom_men_of_kind", ":kind"),
       (val_add, ":men", reg0),
     (try_end),
     (assign, reg0, ":men"),
    ]),

  # script_custom_shown: arg1 = kind; reg0 = the troop the tree shows: the highest level the player has
  ("custom_shown",
   [
     (store_script_param, ":kind", 1),
     (call_script, "script_custom_troop", ":kind", 1),
     (assign, ":shown", reg0),
     ] + [op for level in LEVELS[1:] for op in [
     (try_begin),
       (call_script, "script_custom_troop", ":kind", level),
       (assign, ":troop", reg0),
       (call_script, "script_custom_men", ":troop"),
       (gt, reg0, 0),
       (assign, ":shown", ":troop"),
     (try_end),
     ]] + [
     (assign, reg0, ":shown"),
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
     (troop_set_slot, custom_holder, ":slot", 1),
    ]),

  # script_custom_gear_spread: arg1 = kind, arg2 = item, arg3 = 1 add, 0 take away: the same for the tiers
  # above, in each branch up to the first the player chose gear for: what a man wore stays his as he rises
  ("custom_gear_spread",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":item", 2),
     (store_script_param, ":add", 3),
     (try_begin),
       (eq, ":kind", 0),
       (try_for_range, ":branch", 0, len(BRANCH_NAMES)),
         (store_mul, ":from", ":branch", len(TIERS)),
         (val_add, ":from", 1),
         (call_script, "script_custom_gear_climb", ":from", ":item", ":add"),
       (try_end),
     (else_try),
       (store_mod, ":top", ":kind", len(TIERS)),
       (neq, ":top", 0), #tier 5 is the last
       (store_add, ":from", ":kind", 1),
       (call_script, "script_custom_gear_climb", ":from", ":item", ":add"),
     (try_end),
    ]),

  # script_custom_gear_climb: arg1 = the first kind up the branch, arg2, arg3 as above
  ("custom_gear_climb",
   [
     (store_script_param, ":from", 1),
     (store_script_param, ":item", 2),
     (store_script_param, ":add", 3),
     (store_sub, ":to", ":from", 1),
     (val_div, ":to", len(TIERS)),
     (val_add, ":to", 1),
     (val_mul, ":to", len(TIERS)),
     (val_add, ":to", 1), #past the branch's tier 5
     (assign, ":go", 1),
     (try_for_range, ":kind", ":from", ":to"),
       (eq, ":go", 1),
       (store_add, ":slot", custom_slot_bought, ":kind"),
       (troop_get_slot, ":bought", custom_holder, ":slot"),
       (try_begin),
         (eq, ":bought", 1),
         (assign, ":go", 0),
       (else_try),
         (call_script, "script_custom_gear_count", ":kind"),
         (this_or_next|eq, ":add", 0),
         (lt, reg0, custom_gear_max),
         (call_script, "script_custom_item_change", ":kind", ":item", ":add"),
       (try_end),
     (try_end),
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
       (store_add, ":slot", custom_slot_bought, ":kind"),
       (troop_set_slot, custom_holder, ":slot", 1),
       (call_script, "script_custom_item_change", ":kind", ":item", 1),
       (call_script, "script_custom_gear_spread", ":kind", ":item", 1),
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
       (store_add, ":slot", custom_slot_bought, ":kind"),
       (troop_set_slot, custom_holder, ":slot", 1),
       (call_script, "script_custom_item_change", ":kind", ":item", 0),
       (call_script, "script_custom_gear_spread", ":kind", ":item", 0),
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

  # script_cf_custom_train_text: arg1 = kind, arg2 = level: an option of the training menu, or a failure for
  # a soldier the party does not have. s1 = the soldier, reg2 = the next level, reg3 = men, reg4 = dinars
  ("cf_custom_train_text",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":level", 2),
     (call_script, "script_custom_troop", ":kind", ":level"),
     (assign, ":troop", reg0),
     (call_script, "script_custom_men", ":troop"),
     (assign, reg3, reg0),
     (gt, reg3, 0),
     (str_store_troop_name, s1, ":troop"),
     (call_script, "script_custom_train_cost", ":kind", ":level"),
     (assign, reg4, reg0),
     (store_add, reg2, ":level", 1),
    ]),

  # script_custom_train: arg1 = kind, arg2 = level: all the men at that level go up one
  ("custom_train",
   [
     (store_script_param, ":kind", 1),
     (store_script_param, ":level", 2),
     (call_script, "script_custom_train_cost", ":kind", ":level"),
     (assign, ":cost", reg0),
     (store_troop_gold, ":gold", "trp_player"),
     (try_begin),
       (ge, ":gold", ":cost"),
       (call_script, "script_custom_troop", ":kind", ":level"),
       (assign, ":from", reg0),
       (store_add, ":next", ":level", 1),
       (call_script, "script_custom_troop", ":kind", ":next"),
       (assign, ":to", reg0),
       (troop_remove_gold, "trp_player", ":cost"),
       (call_script, "script_custom_swap", ":from", ":to"),
     (try_end),
    ]),

  # script_cf_custom_mount_text: arg1 = level of a recruit: an option of the training menu.
  # s1 = the recruit, reg3 = men, reg4 = dinars
  ("cf_custom_mount_text",
   [
     (store_script_param, ":level", 1),
     (call_script, "script_custom_troop", 0, ":level"),
     (assign, ":troop", reg0),
     (call_script, "script_custom_men", ":troop"),
     (assign, reg3, reg0),
     (gt, reg3, 0),
     (str_store_troop_name, s1, ":troop"),
     (store_mul, reg4, reg3, custom_mount_cost),
    ]),

  # script_custom_mount: arg1 = level of a recruit: the men get horses: they stand at the riders' first tier
  ("custom_mount",
   [
     (store_script_param, ":level", 1),
     (call_script, "script_custom_troop", 0, ":level"),
     (assign, ":from", reg0),
     (call_script, "script_custom_men", ":from"),
     (store_mul, ":cost", reg0, custom_mount_cost),
     (store_troop_gold, ":gold", "trp_player"),
     (try_begin),
       (ge, ":gold", ":cost"),
       (call_script, "script_custom_troop", kind_of("cav", TIERS[0]), 1),
       (assign, ":to", reg0),
       (troop_remove_gold, "trp_player", ":cost"),
       (call_script, "script_custom_swap", ":from", ":to"),
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
     (party_add_members, "p_main_party", custom_first, ":men"),
    ]),

  # script_custom_army_make: the army stands; the others' games hear it by its name
  ("custom_army_make",
   [
     (assign, "$custom_army_made", 1),
     (troop_set_slot, custom_holder, custom_slot_name, 1),
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

  # script_custom_session: a new session. The host's save holds the army: all of it goes to the bridge. A
  # client's copy of the save may be older: the bridge's word stands
  ("custom_session",
   [
     (assign, "$custom_word_wait", 0),
     (try_begin),
       (eq, "$coop_role", coop_role_client),
       (assign, "$custom_army_made", 0),
     (try_end),
     (try_for_range, ":kind", 0, custom_kinds),
       (store_add, ":slot", custom_slot_gear, ":kind"),
       (troop_set_slot, custom_holder, ":slot", "$custom_army_made"),
     (try_end),
     (store_add, ":names", custom_kinds, 1),
     (try_for_range, ":index", 0, ":names"),
       (store_add, ":slot", custom_slot_name, ":index"),
       (troop_set_slot, custom_holder, ":slot", "$custom_army_made"),
     (try_end),
    ]),

  # script_cf_custom_word_send: one thing of the army the other games have not heard yet, as a request of its
  # own. Fails when there is nothing to say, or the ordinary requests' turn has come
  ("cf_custom_word_send",
   own_game() + [
     (try_begin),
       (gt, "$custom_word_wait", 0),
       (val_sub, "$custom_word_wait", 1),
       (assign, ":found", -1),
     (else_try),
       (assign, ":found", -1),
       (store_add, ":names", custom_kinds, 1),
       (try_for_range, ":index", 0, ":names"),
         (eq, ":found", -1),
         (store_add, ":slot", custom_slot_name, ":index"),
         (troop_slot_eq, custom_holder, ":slot", 1),
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
       (eq, ":found", -1),
       (try_for_range, ":kind", 0, custom_kinds),
         (eq, ":found", -1),
         (store_add, ":slot", custom_slot_gear, ":kind"),
         (troop_slot_eq, custom_holder, ":slot", 1),
         (troop_set_slot, custom_holder, ":slot", 0),
         (assign, ":found", ":kind"),
         (call_script, "script_custom_gear_word", ":kind"),
       (try_end),
     (try_end),
     (ge, ":found", 0),
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
     (store_add, ":slot", custom_slot_bought, ":kind"),
     (troop_get_slot, reg8, custom_holder, ":slot"),
     (assign, reg7, ":kind"),
     (str_store_string, s17, "@&ag={reg7},{reg8}"),
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

  # script_custom_reply: arg1 = reply kind: 34 a name came (s0), 35 a kind's gear:
  # kind, bought, n, items...
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
       (party_get_slot, ":bought", BUF, ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":n", BUF, ":at"),
       (val_add, ":at", 1),
       (store_add, ":slot", custom_slot_bought, ":kind"),
       (troop_set_slot, custom_holder, ":slot", ":bought"),
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
    (is_between, ":kind", 34, 36),
    (this_or_next|eq, "$coop_role", coop_role_client),
    (eq, "$coop_srv_player", 1),
    (call_script, "script_custom_reply", ":kind"),
    (else_try),
  ])
  reply = script_block(orig_scripts, "coop_mp_reply")
  insert_before(reply, (eq, ":kind", 2), [
    (eq, ":kind", 10),
    (call_script, "script_custom_mp_gear"),
    (else_try),
  ])
