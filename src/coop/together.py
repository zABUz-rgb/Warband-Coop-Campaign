from header_common import *
from header_operations import *
from header_game_menus import *
from header_parties import *
from module_constants import *
from coop.constants import *
from coop.players import player_name_to_s1, plays

# What players do together without meeting on the map: riding after a friend, the company's camp on
# everybody's map, the shared treasury and party store (kept by the bridge, tools/coop_bridge.py), the call to a
# battle that reaches a player in a town's menu, and the notes each game sends the bridge's log.
#   27 news about a player code|slot|a|b   28 the camp n|(slot, x, y, mine)*n
#   29 the treasury token|delta|balance    30 the store offset|total|n|(item, value)*n
#   31 the store state|slot                32 a world party near this player fights sid|enemy|on
# A store value is the item's modifier + 100 * its amount (food, ammunition).
#
# $coop_follow: the player ridden after, slot + 1. $coop_follow_party: the party ridden to (that
# player's, or a camp); $coop_follow_mark: the camp's slot_party_coop_mark on the way to a camp.
# $coop_follow_set: 1 a march order of ours stands, 2 our hold while the world stands, 0 none.
# $coop_store_state: 0 idle, 1 asked, 2 arriving, 3 here, 4 open, 5 going back.
# $coop_store_camp: the store was asked for from the camp's menu, which waits for it and comes back.
# $coop_tg_camp: money moved from the camp's menu, which stays open and is told when it is done.
# $coop_ping_on: a menu is open and the game asks the bridge for invitations (see script_coop_ping_next).
# $coop_enc_center: the party of the encounter under way, for a call to a battle to come back to.

NOTES = "trp_tutorial_student_3"   # the notes on their way to the log, 4 slots each
STORE = "trp_tutorial_student_4"   # the party store while it is here, 2 slots each
FOLLOW_CLICK = 100                 # map units * 100: a march order this far from ours is the player's own
FOLLOW_ORDER = 100                 # the friend moved this far: a new order


def first_dynamic():
  from coop.triggers import first_dynamic_party
  return first_dynamic_party()


def request_token(token):
  """Ops: a new random number for a transfer."""
  return [(store_random_in_range, token, 1, 1000000000)]


def treasury_word():
  """Ops: the transfer under way onto s17, until the bridge answers (kind 29)."""
  return [
    (try_begin),
      (neq, "$coop_tg_token", 0),
      (val_sub, "$coop_tg_wait", 1),
      (le, "$coop_tg_wait", 0),
      (assign, "$coop_tg_wait", coop_resend_requests),
      (assign, reg7, "$coop_tg_token"),
      (assign, reg8, "$coop_tg_amount"),
      (str_store_string, s17, "@{s17}&tg={reg7},{reg8}"),
    (try_end),
  ]


def tell(code, text, color):
  """A branch of script_coop_together_reply's news: a message about the player in :slot, s1 its name."""
  return [(else_try), (eq, ":code", code), (display_message, text, color)]


together_scripts = [
  # script_coop_note: arg1 = code, args 2-4 = what it says: a line for the bridge's log (GAME_NOTES in
  # tools/coop_bridge.py). Kept here until a request can carry it: a game hears no one in a menu.
  ("coop_note",
   [
     (store_script_param, ":code", 1),
     (store_script_param, ":a", 2),
     (store_script_param, ":b", 3),
     (store_script_param, ":c", 4),
     (try_begin),
       (lt, "$coop_log_n", coop_note_cap),
       (store_mul, ":at", "$coop_log_n", 4),
       (troop_set_slot, NOTES, ":at", ":code"),
       (val_add, ":at", 1),
       (troop_set_slot, NOTES, ":at", ":a"),
       (val_add, ":at", 1),
       (troop_set_slot, NOTES, ":at", ":b"),
       (val_add, ":at", 1),
       (troop_set_slot, NOTES, ":at", ":c"),
       (val_add, "$coop_log_n", 1),
     (try_end),
    ]),

  # script_coop_note_to_s17: the oldest note onto s17 (one for each request)
  ("coop_note_to_s17",
   [
     (try_begin),
       (gt, "$coop_log_n", 0),
       (troop_get_slot, reg20, NOTES, 0),
       (troop_get_slot, reg21, NOTES, 1),
       (troop_get_slot, reg22, NOTES, 2),
       (troop_get_slot, reg23, NOTES, 3),
       (str_store_string, s17, "@{s17}&lg={reg20},{reg21},{reg22},{reg23}"),
       (val_sub, "$coop_log_n", 1),
       (store_mul, ":numbers", "$coop_log_n", 4),
       (try_for_range, ":at", 0, ":numbers"),
         (store_add, ":from", ":at", 4),
         (troop_get_slot, ":v", NOTES, ":from"),
         (troop_set_slot, NOTES, ":at", ":v"),
       (try_end),
     (try_end),
    ]),

  # script_coop_together_reset: a new session: nothing under way goes on from a loaded save
  ("coop_together_reset",
   [
     (assign, "$coop_follow", 0),
     (assign, "$coop_follow_party", 0),
     (assign, "$coop_follow_mark", 0),
     (assign, "$coop_follow_set", 0),
     (assign, "$coop_follow_send", 0),
     (assign, "$coop_base_send", 0),
     (assign, "$coop_store_state", 0),
     (assign, "$coop_store_step", 0),
     (assign, "$coop_store_camp", 0),
     (assign, "$coop_tg_token", 0),
     (assign, "$coop_tg_camp", 0),
     (assign, "$coop_ping_on", 0),
     (assign, "$coop_enc_center", 0),
     (assign, "$coop_signal_bid", 0),
     (assign, "$coop_signal_menu", 0),
     (assign, "$coop_anew", 1), #the bridge sends the host's game the camps again; a client's hello says as much
     (call_script, "script_coop_marks_clear"),
    ]),

  # script_coop_follow_end: arg1 = coop_follow_end_...: the ride is over
  ("coop_follow_end",
   [
     (store_script_param, ":why", 1),
     (assign, ":base", 0),
     (try_begin),
       (ge, "$coop_follow_mark", coop_base_tag),
       (assign, ":base", "$coop_follow_party"),
     (try_end),
     (try_begin),
       (gt, "$coop_follow", 0),
       (assign, "$coop_follow_send", coop_follow_word_stop),
     (try_end),
     (assign, "$coop_follow", 0),
     (assign, "$coop_follow_party", 0),
     (assign, "$coop_follow_mark", 0),
     (assign, "$coop_follow_set", 0),
     (assign, "$coop_follow_noted", 0),
     (call_script, "script_coop_note", coop_note_follow_end, ":why", 0, 0),
     (try_begin),
       (eq, ":why", coop_follow_end_click),
       (display_message, "@CoopWorld: you took the reins: you ride on your own again.", 0xFFDD66),
     (else_try),
       (eq, ":why", coop_follow_end_gone),
       (display_message, "@CoopWorld: whom you rode after is no longer on the map.", 0xFFDD66),
     (else_try),
       (eq, ":why", coop_follow_end_arrived),
       (gt, ":base", 0),
       (party_is_active, ":base"),
       (start_encounter, ":base"), #the camp opens by itself
     (try_end),
    ]),

  # script_coop_follow_tick: the map: on towards $coop_follow_party by a march order to a point (to a
  # party, arriving would open an encounter). A click of the player's own ends the ride. While the world
  # stands no order moves a party, and one on the move would run this game's clock on: the party holds
  # and goes by steps of this script. So does a party that will not move by the order (it is the player's
  # own, the engine may refuse).
  ("coop_follow_tick",
   [
     (assign, ":target", "$coop_follow_party"),
     (assign, ":can", 0),
     (try_begin),
       (neg|party_is_active, ":target"),
       (assign, ":can", -1),
     (else_try),
       (eq, "$coop_busy", 0),
       (neq, "$freelancer_state", 1),
       (neq, "$g_player_is_captive", 1),
       (party_get_attached_to, ":attached", "p_main_party"),
       (lt, ":attached", 0),
       (assign, ":can", 1),
     (try_end),
     (try_begin),
       (eq, ":can", -1),
       (call_script, "script_coop_follow_end", coop_follow_end_gone),
     (else_try),
       (eq, ":can", 0),
       (assign, "$coop_follow_set", 0), #a new order when the way is free again
       (assign, "$coop_follow_still", 0),
     (else_try),
       (store_distance_to_party_from_party, ":dist", "p_main_party", ":target"),
       (try_begin),
         (le, ":dist", coop_follow_near),
         (assign, "$coop_follow_set", 0),
         (assign, "$coop_follow_still", 0),
         (gt, "$coop_follow_mark", 0),
         (call_script, "script_coop_follow_end", coop_follow_end_arrived),
       (else_try),
         (gt, ":dist", coop_follow_near),
         (try_begin),
           (neg|map_free),
           (rest_for_hours, 0, 0, 0), #a rest ends: the march starts next frame
         (try_end),
         (map_free),
         (set_fixed_point_multiplier, 100),
         # the player's own click since our last order?
         (try_begin),
           (gt, "$coop_follow_set", 0),
           (get_party_ai_behavior, ":behavior", "p_main_party"),
           (assign, ":own", 0),
           (try_begin),
             (this_or_next|eq, ":behavior", ai_bhvr_travel_to_party),
             (this_or_next|eq, ":behavior", ai_bhvr_attack_party),
             (eq, ":behavior", ai_bhvr_escort_party),
             (assign, ":own", 1),
           (else_try),
             (eq, ":behavior", ai_bhvr_travel_to_point),
             (party_get_ai_target_position, pos6, "p_main_party"),
             (position_get_x, ":ax", pos6),
             (position_get_y, ":ay", pos6),
             (val_sub, ":ax", "$coop_follow_x"),
             (val_sub, ":ay", "$coop_follow_y"),
             (val_abs, ":ax"),
             (val_abs, ":ay"),
             (val_add, ":ax", ":ay"),
             (gt, ":ax", FOLLOW_CLICK),
             (assign, ":own", 1),
           (try_end),
           (eq, ":own", 1),
           (call_script, "script_coop_follow_end", coop_follow_end_click),
         (try_end),
         (gt, "$coop_follow_party", 0),
         (party_get_position, pos5, ":target"),
         (position_get_x, ":tx", pos5),
         (position_get_y, ":ty", pos5),
         (party_get_position, pos6, "p_main_party"),
         (position_get_x, ":px", pos6),
         (position_get_y, ":py", pos6),
         (assign, ":stands", "$coop_world_paused"),
         (try_begin),
           (eq, "$coop_role", coop_role_server),
           (assign, ":stands", "$coop_srv_paused"),
         (try_end),
         (assign, ":step", ":stands"),
         (try_begin),
           (eq, ":stands", 1),
           (party_set_ai_behavior, "p_main_party", ai_bhvr_hold),
           (assign, "$coop_follow_set", 2),
           (assign, "$coop_follow_still", 0),
           (assign, "$coop_follow_x", ":px"), #what a click is told from while the party holds
           (assign, "$coop_follow_y", ":py"),
         (else_try),
           (store_sub, ":dx", ":tx", "$coop_follow_x"),
           (store_sub, ":dy", ":ty", "$coop_follow_y"),
           (val_abs, ":dx"),
           (val_abs, ":dy"),
           (val_add, ":dx", ":dy"),
           (try_begin),
             (this_or_next|neq, "$coop_follow_set", 1),
             (ge, ":dx", FOLLOW_ORDER),
             (party_set_ai_behavior, "p_main_party", ai_bhvr_travel_to_point),
             (party_set_ai_target_position, "p_main_party", pos5),
             (assign, "$coop_follow_x", ":tx"),
             (assign, "$coop_follow_y", ":ty"),
             (assign, "$coop_follow_set", 1),
           (try_end),
           # what the engine moved it since the last frame: a step of ours is not counted
           (try_begin),
             (this_or_next|neq, ":px", "$coop_follow_px"),
             (neq, ":py", "$coop_follow_py"),
             (assign, "$coop_follow_still", 0),
           (else_try),
             (val_add, "$coop_follow_still", 1),
           (try_end),
           (ge, "$coop_follow_still", coop_follow_stuck_frames),
           (assign, ":step", 1),
           (eq, "$coop_follow_noted", 0),
           (assign, "$coop_follow_noted", 1),
           (call_script, "script_coop_note", coop_note_follow_step, ":dist", 0, 0),
         (try_end),
         (try_begin),
           (eq, ":step", 1),
           (store_sub, ":dx", ":tx", ":px"),
           (store_sub, ":dy", ":ty", ":py"),
           (assign, ":ax", ":dx"),
           (assign, ":ay", ":dy"),
           (val_abs, ":ax"),
           (val_abs, ":ay"),
           (val_max, ":ax", ":ay"),
           (val_max, ":ax", 1),
           (val_mul, ":dx", coop_follow_step),
           (val_div, ":dx", ":ax"),
           (val_mul, ":dy", coop_follow_step),
           (val_div, ":dy", ":ax"),
           (val_add, ":px", ":dx"),
           (val_add, ":py", ":dy"),
           (position_set_x, pos6, ":px"),
           (position_set_y, pos6, ":py"),
           (party_set_position, "p_main_party", pos6),
         (try_end),
         (assign, "$coop_follow_px", ":px"),
         (assign, "$coop_follow_py", ":py"),
       (try_end),
     (try_end),
    ]),

  # script_coop_marks_clear: the marks on this map go (they are spawned anew from each word on them)
  ("coop_marks_clear",
   [
     (assign, ":last", 0),
     (try_for_parties, ":party_no"),
       (val_max, ":last", ":party_no"),
     (try_end),
     (val_add, ":last", 1),
     (try_for_range, ":party_no", first_dynamic(), ":last"), #by id, not try_for_parties: parties go meanwhile
       (party_is_active, ":party_no"),
       (party_slot_ge, ":party_no", slot_party_coop_mark, 1),
       (remove_party, ":party_no"),
     (try_end),
    ]),

  # script_coop_marks_apply: kind 28 reply. A camp is a party of this game alone, which nobody fights:
  # neutral, standing still, left out of what the host reports (coop/triggers.py)
  ("coop_marks_apply",
   [
     (call_script, "script_coop_marks_clear"),
     (party_get_slot, ":n", "p_coop_buf", 2),
     (set_fixed_point_multiplier, 100),
     (try_for_range, ":k", 0, ":n"),
       (store_mul, ":at", ":k", 4),
       (val_add, ":at", 3),
       (party_get_slot, ":slot", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":x", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":y", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":mine", "p_coop_buf", ":at"),
       (val_sub, ":x", coop_net_offset),
       (val_sub, ":y", coop_net_offset),
       (set_spawn_radius, 0),
       (spawn_around_party, "p_main_party", "pt_none"),
       (assign, ":mark", reg0),
       (party_add_members, ":mark", "trp_farmer", 1),
       (party_set_faction, ":mark", "fac_neutral"),
       (party_set_flags, ":mark", pf_always_visible, 1),
       (party_set_ai_behavior, ":mark", ai_bhvr_hold),
       (store_add, ":tag", ":slot", 1),
       (party_set_slot, ":mark", slot_party_coop_mark, ":tag"),
       (party_set_slot, ":mark", slot_party_coop_mine, ":mine"),
       (party_get_position, pos2, "p_main_party"),
       (position_set_x, pos2, ":x"),
       (position_set_y, pos2, ":y"),
       (party_set_position, ":mark", pos2),
       (party_set_icon, ":mark", "icon_camp"),
       (party_set_name, ":mark", "@The company's camp"),
       (try_begin),
         (eq, ":mine", 1),
         (party_set_name, ":mark", "@Your camp"),
       (else_try),
         (eq, ":mine", 2),
         (party_set_name, ":mark", "@The host's camp"),
       (try_end),
     (try_end),
     (try_begin), #the camp ridden to was spawned anew, or went
       (gt, "$coop_follow_mark", 0),
       (call_script, "script_coop_mark_of", "$coop_follow_mark"),
       (assign, "$coop_follow_party", reg0),
       (eq, reg0, 0),
       (call_script, "script_coop_follow_end", coop_follow_end_gone),
     (try_end),
    ]),

  # script_coop_mark_of: arg1 = a camp's tag: reg0 = its party here, or 0
  ("coop_mark_of",
   [
     (store_script_param, ":tag", 1),
     (assign, reg0, 0),
     (try_for_parties, ":party_no"),
       (party_slot_eq, ":party_no", slot_party_coop_mark, ":tag"),
       (assign, reg0, ":party_no"),
     (try_end),
    ]),

  # script_coop_camp_best: reg0 = the camp to ride to, or 0: the player's own, then the host's, then another's.
  # reg1 = 3 it is the player's own, 2 the host's, 1 another's, 0 none
  ("coop_camp_best",
   [
     (assign, reg0, 0),
     (assign, reg1, 0),
     (try_for_parties, ":party_no"),
       (party_slot_ge, ":party_no", slot_party_coop_mark, coop_base_tag),
       (party_get_slot, ":mine", ":party_no", slot_party_coop_mine),
       (assign, ":rank", 1),
       (try_begin),
         (eq, ":mine", 1),
         (assign, ":rank", 3),
       (else_try),
         (eq, ":mine", 2),
         (assign, ":rank", 2),
       (try_end),
       (gt, ":rank", reg1),
       (assign, reg1, ":rank"),
       (assign, reg0, ":party_no"),
     (try_end),
    ]),

  # script_coop_blackborn_talk: a word with him from a menu, in Native's meeting scene as with a siege's
  # commander. start_map_conversation would wait for the menu to close and open event_triggered, not start.
  ("coop_blackborn_talk",
   [
     (call_script, "script_coop_blackborn_ready"),
     (call_script, "script_get_meeting_scene"),
     (assign, ":scene", reg0),
     (modify_visitors_at_site, ":scene"),
     (reset_visitors),
     (set_visitor, 0, "trp_player"),
     (set_visitor, 17, coop_blackborn),
     (set_jump_mission, "mt_conversation_encounter"),
     (jump_to_scene, ":scene"),
     (change_screen_map_conversation, coop_blackborn),
    ]),

  # script_coop_center_news: arg1 = a center, arg2 = its besieger + 1 now, arg3 = the bandits holding it
  # (troop, 0 none), arg4 = its faction: what a player hears of it, in the host's game as in a client's
  ("coop_center_news",
   [
     (store_script_param, ":center", 1),
     (store_script_param, ":besieger", 2),
     (store_script_param, ":bandits", 3),
     (store_script_param, ":faction", 4),
     (try_begin),
       (gt, ":besieger", 0),
       (party_slot_eq, ":center", slot_center_coop_besieger, 0),
       (is_between, ":center", walled_centers_begin, walled_centers_end),
       (store_relation, ":relation", ":faction", "fac_player_supporters_faction"),
       (ge, ":relation", 0),
       (str_store_party_name, s1, ":center"),
       (display_message, "@CoopWorld: {s1} is under siege! Ride there to defend its walls together.", 0xFF6666),
     (try_end),
     (party_set_slot, ":center", slot_center_coop_besieger, ":besieger"),
     (try_begin),
       (is_between, ":center", villages_begin, villages_end),
       (try_begin),
         (gt, ":bandits", 0),
         (party_slot_eq, ":center", slot_center_coop_bandits, 0),
         (str_store_party_name, s1, ":center"),
         (display_message, "@CoopWorld: bandits have taken {s1}! Ride there to drive them out together.", 0xFF6666),
       (try_end),
       (party_set_slot, ":center", slot_center_coop_bandits, ":bandits"),
       (eq, "$coop_role", coop_role_client),
       (neg|party_slot_eq, ":center", slot_village_infested_by_bandits, "trp_peasant_woman"),
       (party_set_slot, ":center", slot_village_infested_by_bandits, ":bandits"),
     (try_end),
    ]),

  # script_coop_blackborn_ready: the man of the company's camp, as he is to be met
  ("coop_blackborn_ready",
   [
     (troop_set_name, coop_blackborn, "@John Blackborn"),
     (troop_clear_inventory, coop_blackborn),
     ] + [(troop_add_item, coop_blackborn, item) for item in
          ("itm_black_hood", "itm_leather_jerkin", "itm_leather_gloves", "itm_leather_boots", "itm_sword_medieval_b")] + [
     (troop_equip_items, coop_blackborn),
    ]),

  # script_coop_treasury_move: arg1 = denars into the treasury, or out of it (negative). What goes in
  # leaves the hero at once; the word goes with the next requests until the bridge answers (kind 29),
  # whichever way the answer got lost, nothing moves twice.
  ("coop_treasury_move",
   [
     (store_script_param, ":amount", 1),
     (try_begin),
       (eq, "$coop_tg_token", 0),
       (neq, ":amount", 0),
       ] + request_token("$coop_tg_token") + [
       (assign, "$coop_tg_amount", ":amount"),
       (assign, "$coop_tg_wait", 0),
       (try_begin),
         (gt, ":amount", 0),
         (troop_remove_gold, "trp_player", ":amount"),
       (try_end),
       (display_message, "@CoopWorld: to the shared treasury...", 0x66CCFF),
     (try_end),
    ]),

  # script_coop_store_cache: kind 30 reply, part of the party store
  ("coop_store_cache",
   [
     (party_get_slot, ":offset", "p_coop_buf", 2),
     (party_get_slot, ":total", "p_coop_buf", 3),
     (party_get_slot, ":n", "p_coop_buf", 4),
     (try_begin),
       (is_between, "$coop_store_state", 1, 3),
       (try_for_range, ":k", 0, ":n"),
         (store_add, ":at", ":k", ":offset"),
         (val_mul, ":at", 2),
         (store_mul, ":from", ":k", 2),
         (val_add, ":from", 5),
         (party_get_slot, ":v", "p_coop_buf", ":from"),
         (troop_set_slot, STORE, ":at", ":v"),
         (val_add, ":at", 1),
         (val_add, ":from", 1),
         (party_get_slot, ":v", "p_coop_buf", ":from"),
         (troop_set_slot, STORE, ":at", ":v"),
       (try_end),
       (assign, "$coop_store_state", 2),
       (store_add, ":end", ":offset", ":n"),
       (ge, ":end", ":total"),
       (assign, "$coop_store_n", ":total"),
       (assign, "$coop_store_state", 3),
       (eq, "$coop_store_camp", 1),
       (assign, "$coop_store_step", 1),
       (jump_to_menu, "mnu_coop_store"),
     (try_end),
    ]),

  # script_coop_store_show: the party store on the loot screen: what stays on its side when it closes
  # is the store from then on
  ("coop_store_show",
   [
     (troop_clear_inventory, "trp_temp_troop"),
     (try_for_range, ":k", 0, "$coop_store_n"),
       (store_mul, ":at", ":k", 2),
       (troop_get_slot, ":item", STORE, ":at"),
       (val_add, ":at", 1),
       (troop_get_slot, ":value", STORE, ":at"),
       (store_mod, ":imod", ":value", 100),
       (store_div, ":amount", ":value", 100),
       (is_between, ":item", 0, all_items_end),
       (troop_add_item, "trp_temp_troop", ":item", ":imod"),
       (gt, ":amount", 0),
       (store_add, ":slot", ":k", 10), #a cleared inventory fills from its first free slot
       (troop_get_inventory_slot, ":there", "trp_temp_troop", ":slot"),
       (eq, ":there", ":item"),
       (troop_inventory_slot_set_item_amount, "trp_temp_troop", ":slot", ":amount"),
     (try_end),
     (change_screen_loot, "trp_temp_troop"),
    ]),

  # script_coop_store_read: the loot screen closed: its side goes back to the bridge, part by part
  ("coop_store_read",
   [
     (troop_get_inventory_capacity, ":capacity", "trp_temp_troop"),
     (assign, ":n", 0),
     (try_for_range, ":slot", 0, ":capacity"),
       (lt, ":n", coop_store_items),
       (troop_get_inventory_slot, ":item", "trp_temp_troop", ":slot"),
       (ge, ":item", 0),
       (troop_get_inventory_slot_modifier, ":imod", "trp_temp_troop", ":slot"),
       (troop_inventory_slot_get_item_amount, ":amount", "trp_temp_troop", ":slot"),
       (store_mul, ":value", ":amount", 100),
       (val_add, ":value", ":imod"),
       (store_mul, ":at", ":n", 2),
       (troop_set_slot, STORE, ":at", ":item"),
       (val_add, ":at", 1),
       (troop_set_slot, STORE, ":at", ":value"),
       (val_add, ":n", 1),
     (try_end),
     (troop_clear_inventory, "trp_temp_troop"),
     (assign, "$coop_store_n", ":n"),
     (assign, "$coop_store_at", 0),
     (assign, "$coop_store_wait", 0),
     ] + request_token("$coop_store_token") + [
     (assign, "$coop_store_state", 5),
    ]),

  # script_coop_store_send: the store's or the treasury's next word from a menu, where no request of the
  # map's runs: the chain of script_coop_ping_next carries it. A bridge that does not answer ends the wait.
  ("coop_store_send",
   [
     (str_clear, s17),
     (try_begin),
       (is_between, "$coop_store_state", 1, 3),
       (val_add, "$coop_store_asks", 1),
       (gt, "$coop_store_asks", coop_store_asks_max),
       (assign, "$coop_store_state", 0),
       (assign, "$coop_store_camp", 0),
       (display_message, "@CoopWorld: the party store does not answer.", 0xFF6666),
       (jump_to_menu, "mnu_coop_shared"),
     (else_try),
       (eq, "$coop_store_state", 1),
       (val_sub, "$coop_store_wait", 1),
       (le, "$coop_store_wait", 0),
       (assign, "$coop_store_wait", coop_resend_requests),
       (str_store_string, s17, "@&st=1"),
     (try_end),
     (call_script, "script_coop_store_part_to_s17"),
     ] + treasury_word() + [
     (val_add, "$coop_net_seq", 1),
     (assign, reg1, "$coop_net_seq"),
     (set_fixed_point_multiplier, 100),
     (party_get_position, pos1, "p_main_party"),
     (position_get_x, reg2, pos1),
     (position_get_y, reg3, pos1),
     (store_current_hours, reg5),
     (assign, reg8, "$coop_srv_player"),
     (str_store_string, s10, "@" + coop_client_url + "/cli?seq={reg1}&h={reg5}&free=0&x={reg2}&y={reg3}&busy=1&srvp={reg8}{s17}"),
     (assign, "$coop_net_pending", 1),
     (send_message_to_url, s10, 0),
    ]),

  # script_coop_store_part_to_s17: the next part of the party store onto s17; when all went, again
  # after a while, until the bridge answers (kind 31)
  ("coop_store_part_to_s17",
   [
     (try_begin),
       (eq, "$coop_store_state", 5),
       (try_begin),
         (gt, "$coop_store_wait", 0),
         (val_sub, "$coop_store_wait", 1),
       (else_try),
         (assign, reg20, "$coop_store_token"),
         (assign, reg21, "$coop_store_at"),
         (assign, reg22, "$coop_store_n"),
         (str_store_string, s17, "@{s17}&sti={reg20},{reg21},{reg22}"),
         (store_add, ":end", "$coop_store_at", coop_store_chunk),
         (val_min, ":end", "$coop_store_n"),
         (try_for_range, ":k", "$coop_store_at", ":end"),
           (store_mul, ":at", ":k", 2),
           (troop_get_slot, reg20, STORE, ":at"),
           (val_add, ":at", 1),
           (troop_get_slot, reg21, STORE, ":at"),
           (str_store_string, s17, "@{s17},{reg20},{reg21}"),
         (try_end),
         (assign, "$coop_store_at", ":end"),
         (ge, "$coop_store_at", "$coop_store_n"),
         (assign, "$coop_store_at", 0),
         (assign, "$coop_store_wait", coop_resend_requests),
       (try_end),
     (try_end),
    ]),

  # script_cf_coop_protected: arg1 = a party: a caravan or farmers, whom the players may defend
  ("cf_coop_protected",
   [
     (store_script_param, ":party_no", 1),
     (party_get_template_id, ":template", ":party_no"),
     (this_or_next|eq, ":template", "pt_kingdom_caravan_party"),
     (this_or_next|eq, ":template", "pt_merchant_caravan"),
     (eq, ":template", "pt_village_farmers"),
    ]),

  # script_cf_coop_fight_here: arg1 = a mirror met on a client's map. Passes when it is in a map battle
  # (kind 32; mirrors fight nobody here) with a side the players may defend:
  # $coop_fight_ally, $coop_fight_enemy = the two sides
  ("cf_coop_fight_here",
   [
     (store_script_param, ":party_no", 1),
     (party_get_slot, ":enemy_sid", ":party_no", slot_party_coop_fights),
     (gt, ":enemy_sid", 0),
     (val_sub, ":enemy_sid", 1),
     (party_get_slot, ":enemy", "p_coop_map", ":enemy_sid"),
     (val_sub, ":enemy", 1),
     (gt, ":enemy", 0),
     (party_is_active, ":enemy"),
     (assign, ":ally", -1),
     (try_begin),
       (call_script, "script_cf_coop_protected", ":party_no"),
       (assign, ":ally", ":party_no"),
     (else_try),
       (call_script, "script_cf_coop_protected", ":enemy"),
       (assign, ":ally", ":enemy"),
       (assign, ":enemy", ":party_no"),
     (try_end),
     (gt, ":ally", 0),
     (assign, "$coop_fight_ally", ":ally"),
     (assign, "$coop_fight_enemy", ":enemy"),
    ]),

  # script_coop_together_reply: arg1 = kind: replies 27 to 32
  ("coop_together_reply",
   [
     (store_script_param, ":kind", 1),
     (try_begin),
       (eq, ":kind", 27), #news about a player
       (party_get_slot, ":code", "p_coop_buf", 2),
       (party_get_slot, ":slot", "p_coop_buf", 3),
       (party_get_slot, reg1, "p_coop_buf", 4),
       (party_get_slot, reg2, "p_coop_buf", 5),
       (store_add, ":tag", ":slot", 1),
       ] + player_name_to_s1(":tag") + [
       (try_begin),
         (eq, ":code", coop_tell_followed),
         (display_message, "@CoopWorld: {s1} rides after you.", 0x66CCFF),
       ] + tell(coop_tell_unfollowed, "@CoopWorld: {s1} rides on alone.", 0xFFDD66) + [
       (else_try),
         (eq, ":code", coop_tell_bandits),
         (is_between, reg1, villages_begin, villages_end),
         (party_set_slot, reg1, slot_village_infested_by_bandits, 0),
         (party_set_slot, reg1, slot_center_coop_bandits, 0),
         (str_store_party_name, s2, reg1),
         (display_message, "@CoopWorld: {s1} drove the bandits out of {s2}.", 0x66FF66),
       (else_try),
         (eq, ":code", coop_tell_base),
         (try_begin),
           (eq, reg1, 1),
           (display_message, "@CoopWorld: {s1} set up the company's camp: the treasury and the party store are there.", 0x66CCFF),
         (else_try),
           (display_message, "@CoopWorld: {s1} took the company's camp down.", 0xFFDD66),
         (try_end),
       (else_try),
         (eq, ":code", coop_tell_gold),
         (assign, reg3, reg1),
         (try_begin),
           (eq, reg2, 1),
           (display_message, "@CoopWorld: {s1} put {reg3} denars into the shared treasury.", 0x66CCFF),
         (else_try),
           (display_message, "@CoopWorld: {s1} took {reg3} denars from the shared treasury.", 0x66CCFF),
         (try_end),
       ] + tell(coop_tell_store, "@CoopWorld: {s1} closed the party store: {reg1} things in it.", 0x66CCFF) + [
       (else_try),
         (eq, ":code", coop_tell_left),
         (eq, "$coop_follow", ":tag"),
         (call_script, "script_coop_follow_end", coop_follow_end_gone),
       (else_try),
         (eq, ":code", coop_tell_save_loaded),
         (display_message, "@CoopWorld: the host went back to an earlier save. Load the host's save again: your hero and the treasury went back with it.", 0xFFDD66),
       (else_try),
         (eq, ":code", coop_tell_save_again),
         (display_message, "@CoopWorld: save the game now: your friends get that save and load it.", 0xFFDD66),
       (else_try),
         (eq, ":code", coop_tell_base_up), #paid only now: a word nobody answered costs nothing
         (troop_remove_gold, "trp_player", coop_base_cost),
         (display_message, "@CoopWorld: the tents go up. Ride into the camp for the treasury and the party store.", 0x66CCFF),
       (try_end),
     (else_try),
       (eq, ":kind", 28),
       (call_script, "script_coop_marks_apply"),
     (else_try),
       (eq, ":kind", 29), #the shared treasury
       (party_get_slot, ":token", "p_coop_buf", 2),
       (party_get_slot, ":delta", "p_coop_buf", 3),
       (party_get_slot, "$coop_shared_gold", "p_coop_buf", 4),
       (gt, ":token", 0),
       (eq, ":token", "$coop_tg_token"),
       (assign, "$coop_tg_token", 0),
       (assign, reg1, "$coop_shared_gold"),
       (try_begin),
         (lt, ":delta", 0),
         (store_sub, reg2, 0, ":delta"),
         (troop_add_gold, "trp_player", reg2),
         (display_message, "@CoopWorld: you took {reg2} denars. {reg1} left in the shared treasury.", 0x66FF66),
       (else_try),
         (gt, ":delta", 0),
         (assign, reg2, ":delta"),
         (display_message, "@CoopWorld: {reg2} denars went in. {reg1} in the shared treasury.", 0x66FF66),
       (else_try),
         (display_message, "@CoopWorld: the shared treasury is empty.", 0xFFDD66),
       (try_end),
       (eq, "$coop_tg_camp", 1), #the camp's menu shows what came of it
       (assign, "$coop_tg_camp", 0),
       (jump_to_menu, "mnu_coop_shared"),
     (else_try),
       (eq, ":kind", 30),
       (call_script, "script_coop_store_cache"),
     (else_try),
       (eq, ":kind", 31), #the party store: 0 another player has it open, 1 saved
       (party_get_slot, ":state", "p_coop_buf", 2),
       (party_get_slot, ":slot", "p_coop_buf", 3),
       (try_begin),
         (eq, ":state", 1),
         (eq, "$coop_store_state", 5),
         (assign, "$coop_store_state", 0),
         (assign, reg1, "$coop_store_n"),
         (display_message, "@CoopWorld: the party store is saved at the host: {reg1} things.", 0x66FF66),
       (else_try),
         (eq, ":state", 0),
         (eq, "$coop_store_state", 1),
         (assign, "$coop_store_state", 0),
         (store_add, ":tag", ":slot", 1),
         ] + player_name_to_s1(":tag") + [
         (display_message, "@CoopWorld: {s1} has the party store open: wait for it to close.", 0xFFDD66),
         (eq, "$coop_store_camp", 1),
         (assign, "$coop_store_camp", 0),
         (jump_to_menu, "mnu_coop_shared"),
       (try_end),
     (else_try),
       (eq, ":kind", 32), #a world party near this player fights
       (eq, "$coop_role", coop_role_client),
       (party_get_slot, ":sid", "p_coop_buf", 2),
       (party_get_slot, ":enemy", "p_coop_buf", 3),
       (party_get_slot, ":on", "p_coop_buf", 4),
       (party_get_slot, ":party_no", "p_coop_map", ":sid"),
       (val_sub, ":party_no", 1),
       (gt, ":party_no", 0),
       (party_is_active, ":party_no"),
       (val_add, ":enemy", 1),
       (val_mul, ":enemy", ":on"),
       (party_set_slot, ":party_no", slot_party_coop_fights, ":enemy"),
       (eq, ":on", 1),
       (call_script, "script_cf_coop_protected", ":party_no"),
       (str_store_party_name, s1, ":party_no"),
       (display_message, "@CoopWorld: {s1} is under attack nearby! Ride up to defend it together.", 0xFF6666),
     (try_end),
    ]),

  # script_coop_after_battle: arg1 = won: what a joint battle was about, after its outcome
  ("coop_after_battle",
   [
     (store_script_param, ":won", 1),
     (try_begin),
       (eq, "$coop_mp_kind", coop_kind_lair),
       (assign, ":quest", 0),
       (try_begin),
         (eq, ":won", 1),
         (check_quest_active, "qst_destroy_bandit_lair"),
         (quest_slot_eq, "qst_destroy_bandit_lair", slot_quest_target_party, "$coop_mp_enemy_party"),
         (call_script, "script_succeed_quest", "qst_destroy_bandit_lair"),
         (assign, ":quest", 1),
       (try_end),
       (call_script, "script_coop_note", coop_note_lair, ":won", ":quest", 0),
     (else_try),
       (eq, "$coop_mp_kind", coop_kind_caravan),
       (call_script, "script_coop_note", coop_note_caravan, ":won", 0, 0),
     (else_try),
       (eq, "$coop_mp_kind", coop_kind_bandits),
       (assign, ":relation", 0),
       (try_begin),
         (eq, ":won", 1),
         (assign, ":relation", coop_village_relation),
         (party_set_slot, "$coop_mp_village", slot_village_infested_by_bandits, 0),
         (party_set_slot, "$coop_mp_village", slot_center_coop_bandits, 0),
         (call_script, "script_change_player_relation_with_center", "$coop_mp_village", ":relation"),
         (str_store_party_name, s1, "$coop_mp_village"),
         (display_message, "@CoopWorld: the bandits are driven out of {s1}.", 0x66FF66),
       (try_end),
       (call_script, "script_coop_note", coop_note_bandits, "$coop_mp_village", ":won", ":relation"),
     (else_try),
       (eq, "$coop_mp_kind", coop_kind_village),
       (assign, ":relation", 0),
       (try_begin),
         (eq, ":won", 1),
         (assign, ":relation", coop_village_relation),
         (call_script, "script_change_player_relation_with_center", "$coop_mp_village", ":relation"),
       (try_end),
       (call_script, "script_coop_note", coop_note_village, "$coop_mp_village", ":won", ":relation"),
     (try_end),
     (assign, "$coop_mp_kind", 0),
    ]),

  # script_coop_client_duel_result: arg1 = 1 won, 0 lost, 2 a draw, arg2 = the stake. The stake leaves
  # the loser only here, so a duel cancelled on its way costs nothing.
  ("coop_client_duel_result",
   [
     (store_script_param, ":result", 1),
     (store_script_param, ":stake", 2),
     (assign, ":gold", 0),
     (assign, reg1, ":stake"),
     (try_begin),
       (eq, ":result", 1),
       (assign, ":gold", ":stake"),
       (try_begin),
         (gt, ":stake", 0),
         (troop_add_gold, "trp_player", ":stake"),
       (try_end),
       (add_xp_to_troop, coop_duel_xp_win, "trp_player"),
       (display_message, "@CoopWorld: you won the duel! The stake: {reg1} denars.", 0x66FF66),
     (else_try),
       (eq, ":result", 0),
       (store_troop_gold, ":have", "trp_player"),
       (val_min, ":have", ":stake"),
       (try_begin),
         (gt, ":have", 0),
         (troop_remove_gold, "trp_player", ":have"),
       (try_end),
       (store_sub, ":gold", 0, ":have"),
       (add_xp_to_troop, coop_duel_xp_lose, "trp_player"),
       (display_message, "@CoopWorld: you lost the duel. The stake: {reg1} denars.", 0xFF6666),
     (else_try),
       (display_message, "@CoopWorld: the duel ended in a draw: the stake stays with each of you.", 0xFFDD66),
     (try_end),
     (call_script, "script_coop_note", coop_note_duel, ":result", ":stake", ":gold"),
     (assign, "$coop_mp_bet", 0),
     (assign, "$coop_mp_bet_win", 0),
    ]),

  # script_coop_signal_battle: an invitation waits: it shows at once. On the map the map's own trigger
  # opens it. Where triggers do not run, in a town's or a village's menu or in the camp (the menus that
  # ask the bridge, $coop_ping_on), its menu opens from here, and "Decline" comes back. In a walk
  # through a town or a battle it says so and tries again with the next ping.
  ("coop_signal_battle",
   [
     (try_begin),
       (eq, "$coop_mp_invite_pending", 1),
       (try_begin),
         (neq, "$coop_signal_bid", "$coop_mp_bid"),
         (assign, "$coop_signal_bid", "$coop_mp_bid"),
         (store_add, ":tag", "$coop_mp_inv_slot", 1),
         ] + player_name_to_s1(":tag") + [
         (play_sound, "snd_quest_concluded"),
         (display_message, "@CoopWorld: {s1} calls you to battle!", 0xFF4444),
         (call_script, "script_coop_note", coop_note_signal, coop_signal_message, "$coop_mp_inv_type", 0),
       (try_end),
       (eq, "$coop_ping_on", 1),
       (neg|map_free),
       (get_player_agent_no, ":agent"),
       (lt, ":agent", 0), #walking in a town, in a battle: a menu must wait
       (neg|is_presentation_active, "prsnt_coop_mp_wait"),
       (neg|is_presentation_active, "prsnt_coop_troop_tree"),
       (le, "$g_player_besiege_town", 0),
       (neq, "$g_player_is_captive", 1),
       (neq, "$freelancer_state", 1),
       (assign, ":menu", -1),
       (try_begin),
         (le, "$coop_enc_center", 0),
         (assign, ":menu", 0), #the camp: back to the map
       (else_try),
         (party_slot_eq, "$coop_enc_center", slot_party_type, spt_village),
         (assign, ":menu", "mnu_village"),
       (else_try),
         (is_between, "$coop_enc_center", walled_centers_begin, walled_centers_end),
         (assign, ":menu", "mnu_castle_outside"),
       (try_end),
       (ge, ":menu", 0), #an encounter on the field keeps its own menu
       (assign, "$coop_signal_menu", ":menu"),
       (assign, "$coop_mp_invite_pending", 0),
       (call_script, "script_coop_note", coop_note_signal, coop_signal_menu_opened, "$coop_mp_inv_type", 0),
       (jump_to_menu, "mnu_coop_mp_invite"),
     (try_end),
    ]),

  # script_coop_ping_send: one question to the bridge: is this player called to a battle?
  ("coop_ping_send",
   [
     (try_begin),
       (this_or_next|is_between, "$coop_store_state", 1, 3),
       (this_or_next|eq, "$coop_store_state", 5),
       (neq, "$coop_tg_token", 0),
       (call_script, "script_coop_store_send"),
     (else_try),
       (val_add, "$coop_net_seq", 1),
       (assign, reg20, "$coop_net_seq"),
       (str_store_string, s10, "@" + coop_client_url + "/pg?seq={reg20}&hold=1"),
       (assign, "$coop_net_pending", 1),
       (send_message_to_url, s10, 0),
     (try_end),
    ]),

  # script_coop_ping_kick: a menu of the camp, a town or a village opens, the map's triggers stop: from
  # here on the game goes on asking, each answer sending the next question (so a bridge that stopped
  # answering stops it too). The first run of the map's trigger ends it.
  ("coop_ping_kick",
   [
     (try_begin),
       (this_or_next|eq, "$coop_role", coop_role_client),
       (eq, "$coop_srv_player", 1),
       (assign, "$coop_ping_on", 1),
       (assign, "$coop_ping_tick", "$coop_tick"),
       (eq, "$coop_net_pending", 0),
       (call_script, "script_coop_ping_send"),
     (try_end),
    ]),

  # script_coop_ping_next: a reply came
  ("coop_ping_next",
   [
     (try_begin),
       (eq, "$coop_ping_on", 1),
       (try_begin),
         (store_sub, ":frames", "$coop_tick", "$coop_ping_tick"),
         (gt, ":frames", coop_ping_slack), #the map runs again
         (assign, "$coop_ping_on", 0),
       (else_try),
         (call_script, "script_coop_signal_battle"),
         (eq, "$coop_net_pending", 0),
         (neg|is_presentation_active, "prsnt_coop_mp_wait"), #it asks by itself
         (call_script, "script_coop_ping_send"),
       (try_end),
     (try_end),
    ]),

  # script_coop_decline_now: a call to battle declined in a menu, where no map request carries the word
  ("coop_decline_now",
   [
     (assign, "$coop_mp_state", 0),
     (val_add, "$coop_net_seq", 1),
     (assign, reg1, "$coop_net_seq"),
     (set_fixed_point_multiplier, 100),
     (party_get_position, pos1, "p_main_party"),
     (position_get_x, reg2, pos1),
     (position_get_y, reg3, pos1),
     (store_current_hours, reg5),
     (assign, reg7, "$coop_mp_bid"),
     (assign, reg8, "$coop_srv_player"),
     (str_store_string, s10, "@" + coop_client_url + "/cli?seq={reg1}&h={reg5}&free=0&x={reg2}&y={reg3}&busy=1&srvp={reg8}&mp=4&bid={reg7}"),
     (assign, "$coop_net_pending", 1),
     (send_message_to_url, s10, 0),
    ]),

  # script_coop_client_mp_begin_bandits: arg1 = a village bandits took: a joint battle against them,
  # beside its men. They are no party of the world: this game names them to the bridge.
  ("coop_client_mp_begin_bandits",
   [
     (store_script_param, ":village", 1),
     (assign, "$coop_mp_next_kind", coop_kind_bandits),
     (assign, "$coop_mp_village", ":village"),
     (call_script, "script_coop_client_mp_begin", -1),
    ]),

  # script_coop_client_mp_begin_village: arg1 = a raided village: a joint battle against its raiders,
  # beside its villagers (the battle's kind tells the bridge)
  ("coop_client_mp_begin_village",
   [
     (store_script_param, ":village", 1),
     (assign, ":raider", -1),
     (try_begin),
       (eq, "$coop_srv_player", 1),
       (party_get_slot, ":raider", ":village", slot_village_raided_by),
     (else_try),
       (party_get_slot, ":sid", ":village", slot_center_coop_besieger),
       (val_sub, ":sid", 1),
       (ge, ":sid", 0),
       (party_get_slot, ":raider", "p_coop_map", ":sid"),
       (val_sub, ":raider", 1),
     (try_end),
     (try_begin),
       (gt, ":raider", 0),
       (party_is_active, ":raider"),
       (assign, "$coop_mp_next_kind", coop_kind_village),
       (assign, "$coop_mp_village", ":village"),
       (call_script, "script_coop_client_mp_begin", ":raider"),
     (else_try),
       (display_message, "@CoopWorld: the raiders are not here any more.", 0xFFDD66),
     (try_end),
    ]),

  # script_coop_server_raids_over: arg1 = a world party the players beat: a raid of its ends at once,
  # also when it was a lord's party that lives on without its men
  ("coop_server_raids_over",
   [
     (store_script_param, ":party_no", 1),
     (try_for_range, ":village", villages_begin, villages_end),
       (party_slot_eq, ":village", slot_village_raided_by, ":party_no"),
       (party_set_slot, ":village", slot_village_raid_progress, 0),
       (call_script, "script_village_set_state", ":village", svs_normal),
       (str_store_party_name, s1, ":village"),
       (display_message, "@CoopWorld: the raid on {s1} is beaten off.", 0x66FF66),
     (try_end),
    ]),
]


def request_suffix():
  """Ops appending to s17 what the player did since the last request (client and host alike)."""
  return [
    (try_begin),
      (gt, "$coop_follow_send", 0),
      (store_mod, reg7, "$coop_follow_send", coop_follow_word_stop), #the stop word: fl=0
      (str_store_string, s17, "@{s17}&fl={reg7}"),
      (assign, "$coop_follow_send", 0),
    (try_end),
    (try_begin),
      (eq, "$coop_base_send", 1),
      (assign, "$coop_base_send", 0),
      (assign, reg7, "$coop_base_x"),
      (assign, reg8, "$coop_base_y"),
      (str_store_string, s17, "@{s17}&bs={reg7},{reg8}"),
    (else_try),
      (eq, "$coop_base_send", 2),
      (assign, "$coop_base_send", 0),
      (str_store_string, s17, "@{s17}&bs=-"),
    (try_end),
  ] + treasury_word() + [
    (try_begin),
      (eq, "$coop_store_state", 1),
      (val_sub, "$coop_store_wait", 1),
      (le, "$coop_store_wait", 0),
      (assign, "$coop_store_wait", coop_resend_requests),
      (str_store_string, s17, "@{s17}&st=1"),
    (try_end),
    (call_script, "script_coop_store_part_to_s17"),
    (call_script, "script_coop_note_to_s17"),
  ]


def map_tick():
  """Ops for the map trigger (client and host)."""
  return [
    (val_add, "$coop_tick", 1),
    # an encounter ended, or its town was left: nothing to come back to
    (try_begin),
      (gt, "$coop_enc_center", 0),
      (map_free),
      (val_add, "$coop_enc_age", 1),
      (ge, "$coop_enc_age", 3), #the map is still free the frame an encounter starts
      (assign, "$coop_enc_center", 0),
    (try_end),
    (try_begin),
      (gt, "$coop_follow_party", 0),
      (call_script, "script_coop_follow_tick"),
    (try_end),
    (try_begin),
      (eq, "$coop_store_state", 3),
      (map_free),
      (assign, "$coop_store_step", 1),
      (jump_to_menu, "mnu_coop_store"),
    (else_try),
      (eq, "$coop_store_state", 4), #its menu closed some other way: the bridge's copy stands
      (map_free),
      (assign, "$coop_store_state", 0),
    (try_end),
  ]


def encounter_end():
  """Ops at the end of script_game_event_party_encounter: the company's camp, or a battle a
  client's mirrors cannot show, take the place of the menu Native chose; the party met is noted for a
  call to a battle."""
  return [
    (try_begin),
      (ge, "$g_encountered_party", first_dynamic()),
      (party_slot_ge, "$g_encountered_party", slot_party_coop_mark, coop_base_tag),
      (jump_to_menu, "mnu_coop_shared"),
    (else_try),
      (eq, "$coop_role", coop_role_client),
      (ge, "$g_encountered_party", first_dynamic()),
      (call_script, "script_cf_coop_fight_here", "$g_encountered_party"),
      (jump_to_menu, "mnu_coop_map_fight"),
    (try_end),
    (assign, "$coop_enc_center", "$g_encountered_party"),
    (assign, "$coop_enc_age", 0),
    (call_script, "script_coop_ping_kick"),
  ]


def reply_branches():
  """else_try branches for net_reply_handler: kinds 27 to 32 (33 says nothing)."""
  return [
    (else_try),
      (is_between, ":kind", 27, 33),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1),
      (call_script, "script_coop_together_reply", ":kind"),
  ]


def camp_options():
  return [
    ("coop_base_build", plays() + [(call_script, "script_coop_camp_best"), (neq, reg1, 3),
                                   (eq, "$coop_base_send", 0),
                                   (try_begin),
                                     (store_troop_gold, ":gold", "trp_player"),
                                     (lt, ":gold", coop_base_cost),
                                     (disable_menu_option),
                                   (try_end)],
     "CoopWorld: set up the company's camp here (%d denars)." % coop_base_cost,
     [
       (set_fixed_point_multiplier, 100),
       (party_get_position, pos1, "p_main_party"),
       (position_get_x, "$coop_base_x", pos1),
       (position_get_y, "$coop_base_y", pos1),
       (assign, "$coop_base_send", 1),
       (change_screen_return),
     ]),
    ("coop_base_ride", plays() + [(call_script, "script_coop_camp_best"), (gt, reg0, 0), (str_store_party_name, s1, reg0)],
     "CoopWorld: ride to {s1} (the treasury and the party store are there).",
     [
       (call_script, "script_coop_camp_best"),
       (assign, "$coop_follow_party", reg0),
       (party_get_slot, "$coop_follow_mark", reg0, slot_party_coop_mark),
       (assign, "$coop_follow", 0),
       (assign, "$coop_follow_set", 0),
       (change_screen_return),
     ]),
    ("coop_tree", [], "CoopWorld: the troop tree.",
     [(start_presentation, "prsnt_coop_troop_tree")]),
  ]


def players_menu_options(k, name):
  """What the camp's players menu offers for the player in slot k, whose puppet ops are name."""
  tag = k + 1
  return [
    ("coop_pl_follow_%d" % k, plays() + name + [(neq, "$coop_follow", tag)],
     "Ride after {s1} (a click of your own on the map stops it).",
     [
       (assign, "$coop_follow", tag),
       (assign, "$coop_follow_send", tag),
       (store_add, "$coop_follow_party", "p_coop_puppet_1", k),
       (assign, "$coop_follow_mark", 0),
       (assign, "$coop_follow_set", 0),
       (display_message, "@CoopWorld: you ride after {s1}.", 0x66CCFF),
       (change_screen_return),
     ]),
    ("coop_pl_duel_%d" % k, plays() + name + [(eq, "$coop_mp_state", 0), (neg|troop_is_wounded, "trp_player"),
                                              (neq, "$g_player_is_captive", 1)],
     "Challenge {s1} to a duel.",
     [(assign, "$coop_duel_with", tag), (jump_to_menu, "mnu_coop_duel_stake")]),
  ]


def players_stop_option():
  return ("coop_pl_stop_follow", plays() + [(gt, "$coop_follow", 0)] + player_name_to_s1("$coop_follow"),
          "Stop riding after {s1}.",
          [(call_script, "script_coop_follow_end", coop_follow_end_asked), (jump_to_menu, "mnu_coop_players")])


# the bandit lair's menu: storm it together, on the battle server (the party is a client's mirror, or
# the host's own). Looters' first hideout belongs to Native's opening quest.
def lair_option(ready):
  return (
    "coop_mp_lair",
    ready + [
      (party_slot_eq, "$g_encountered_party", slot_party_ai_substate, 0),
      (party_get_template_id, ":template", "$g_encountered_party"),
      (neq, ":template", "pt_looter_lair"),
      (this_or_next|party_slot_ge, "$g_encountered_party", slot_party_coop_sid, 1),
      (eq, "$coop_role", coop_role_server),
    ],
    "CoopWorld: storm the hideout together (joint battle on the multiplayer server).",
    [
      (assign, "$coop_mp_next_kind", coop_kind_lair),
      (call_script, "script_coop_client_mp_begin", "$g_encountered_party"),
    ])


# the host riding up to a battle of the world: Native's own menu for it. A client's mirrors fight
# nobody: script_cf_coop_fight_here brings it to coop_map_fight instead.
def pre_join_option(ready):
  return (
    "coop_mp_help",
    ready + [
      (eq, "$coop_srv_player", 1),
      (gt, "$g_encountered_party_2", 0),
      (call_script, "script_cf_coop_protected", "$g_encountered_party"),
      (str_store_party_name, s1, "$g_encountered_party"),
    ],
    "CoopWorld: defend {s1} together (joint battle on the multiplayer server).",
    [
      (store_add, "$coop_mp_next_ally", "$g_encountered_party", 1),
      (assign, "$coop_mp_next_kind", coop_kind_caravan),
      (call_script, "script_coop_client_mp_begin", "$g_encountered_party_2"),
    ])


# a village's menu with bandits in it: the fight of Native's next option, together. The village's own
# trouble of Diplomacy (a peasant woman in that slot) is no fight.
def bandits_option(ready):
  return (
    "coop_mp_bandits",
    ready + [
      (party_get_slot, ":bandits", "$current_town", slot_village_infested_by_bandits),
      (gt, ":bandits", 0),
      (neq, ":bandits", "trp_peasant_woman"),
    ],
    "CoopWorld: attack the bandits together (joint battle on the multiplayer server).",
    [(call_script, "script_coop_client_mp_begin_bandits", "$current_town")])


# a raided village's menu, for a client (as the server reports it, + 1) and for the host
def village_option(ready):
  return (
    "coop_mp_village",
    ready + [
      (store_encountered_party, ":village"),
      (try_begin),
        (eq, "$coop_srv_player", 1),
        (party_get_slot, ":raider", ":village", slot_village_raided_by),
      (else_try),
        (party_get_slot, ":raider", ":village", slot_center_coop_besieger),
        (val_sub, ":raider", 1),
      (try_end),
      (gt, ":raider", 0),
    ],
    "CoopWorld: drive the raiders off together (joint battle on the multiplayer server).",
    [
      (store_encountered_party, ":village"),
      (call_script, "script_coop_client_mp_begin_village", ":village"),
    ])


def treasury_options():
  """The camp's menu stays open: the word goes by the chain of requests a menu runs, and the answer reloads it."""
  stay = [(assign, "$coop_tg_camp", 1), (call_script, "script_coop_ping_kick"), (jump_to_menu, "mnu_coop_shared")]
  options = []
  for amount in (100, 1000):
    options.append(("coop_tg_in_%d" % amount,
                    plays() + [(eq, "$coop_tg_token", 0), (store_troop_gold, ":gold", "trp_player"), (ge, ":gold", amount)],
                    "Put in %d denars." % amount,
                    [(call_script, "script_coop_treasury_move", amount)] + stay))
  options.append(("coop_tg_in_all",
                  plays() + [(eq, "$coop_tg_token", 0), (store_troop_gold, ":gold", "trp_player"), (gt, ":gold", 0)],
                  "Put in everything you carry.",
                  [(store_troop_gold, ":gold", "trp_player"), (call_script, "script_coop_treasury_move", ":gold")] + stay))
  for amount in (100, 1000):
    options.append(("coop_tg_out_%d" % amount, plays() + [(eq, "$coop_tg_token", 0), (ge, "$coop_shared_gold", amount)],
                    "Take %d denars." % amount,
                    [(call_script, "script_coop_treasury_move", -amount)] + stay))
  options.append(("coop_tg_out_all", plays() + [(eq, "$coop_tg_token", 0), (gt, "$coop_shared_gold", 0)],
                  "Take everything in it.",
                  [(store_sub, ":amount", 0, "$coop_shared_gold"), (call_script, "script_coop_treasury_move", ":amount")] + stay))
  options.append(("coop_tg_wait", plays() + [(neq, "$coop_tg_token", 0)], "The coins are being counted. Look again.",
                  [(jump_to_menu, "mnu_coop_shared")]))
  options.append(("coop_shared_off", [(eq, "$coop_role", coop_role_single), (disable_menu_option)],
                  "Co-op is off: the treasury and the store wait for the next session.", []))
  return options


together_menus = [
  # the company's camp, met on the map: the treasury, the store and its people
  ("coop_shared", 0,
   "CoopWorld: the company's camp.^^The treasury holds {reg1} denars; you carry {reg2}. Here every player can put money in and take it out; so with the store's things. They are kept at the host, in shared.json, and stay there from session to session.",
   "none",
   [(set_background_mesh, "mesh_pic_camp"), (assign, reg1, "$coop_shared_gold"), (store_troop_gold, reg2, "trp_player")],
   treasury_options() + [
     ("coop_store_open", plays() + [(eq, "$coop_store_state", 0)],
      "Open the party store (one player at a time).",
      [
        (assign, "$coop_tg_camp", 0),
        (assign, "$coop_store_state", 1),
        (assign, "$coop_store_wait", 0),
        (assign, "$coop_store_asks", 0),
        (assign, "$coop_store_camp", 1),
        (call_script, "script_coop_ping_kick"),
        (jump_to_menu, "mnu_coop_store_wait"),
      ]),
     ("coop_blackborn", [], "Talk to John Blackborn.",
      [(assign, "$coop_tg_camp", 0), (call_script, "script_coop_blackborn_talk")]),
     ("coop_base_down", plays() + [(party_slot_eq, "$g_encountered_party", slot_party_coop_mine, 1)],
      "Take the camp down (the treasury and the store stay with the company, the denars do not come back).",
      [
        (assign, "$coop_tg_camp", 0),
        (assign, "$coop_base_send", 2),
        (display_message, "@CoopWorld: the tents come down.", 0xFFDD66),
        (leave_encounter),
        (change_screen_return),
      ]),
     ("coop_shared_back", [], "Back to the map.", [(assign, "$coop_tg_camp", 0), (leave_encounter), (change_screen_return)]),
   ]),

  # the store is asked for from here: a menu stops the map's requests, so the answers come to this one
  ("coop_store_wait", 0,
   "CoopWorld: the party store is on its way...",
   "none",
   [(set_background_mesh, "mesh_pic_camp")],
   [
     ("coop_store_wait_back", [], "Back to the camp.",
      [
        (assign, "$coop_store_state", 0),
        (assign, "$coop_store_camp", 0),
        (jump_to_menu, "mnu_coop_shared"),
      ]),
   ]),

  # the store as Native's victory menu shows the loot (see coop_loot): the screen from the menu's own
  # code, and when it closes the code runs again, reads what is left and goes back to the map
  ("coop_store", 0,
   "CoopWorld: the party store.",
   "none",
   [
     (try_begin),
       (eq, "$coop_store_step", 1),
       (assign, "$coop_store_step", 2),
       (assign, "$coop_store_state", 4),
       (call_script, "script_coop_store_show"),
     (else_try),
       (eq, "$coop_store_step", 2),
       (assign, "$coop_store_step", 0),
       (call_script, "script_coop_store_read"),
       (try_begin),
         (eq, "$coop_store_camp", 1),
         (assign, "$coop_store_camp", 0),
         (call_script, "script_coop_ping_kick"), #it goes back from the camp's menu too
         (jump_to_menu, "mnu_coop_shared"),
       (else_try),
         (change_screen_return),
       (try_end),
     (try_end),
   ],
   [
     ("coop_store_leave", [], "Back to the map.",
      [
        (try_begin),
          (eq, "$coop_store_step", 2),
          (assign, "$coop_store_step", 0),
          (call_script, "script_coop_store_read"),
        (try_end),
        (assign, "$coop_store_camp", 0),
        (change_screen_map),
      ]),
   ]),

  ("coop_map_fight", 0,
   "CoopWorld: {s2} are attacking {s1} here.",
   "none",
   [(str_store_party_name, s1, "$coop_fight_ally"), (str_store_party_name, s2, "$coop_fight_enemy")],
   [
     ("coop_fight_join",
      [(this_or_next|eq, "$coop_role", coop_role_client), (eq, "$coop_srv_player", 1),
       (eq, "$coop_mp_state", 0), (neg|troop_is_wounded, "trp_player"), (neq, "$g_player_is_captive", 1),
       (party_is_active, "$coop_fight_ally"), (party_is_active, "$coop_fight_enemy")],
      "Defend {s1} together with your friends (joint battle on the multiplayer server).",
      [
        (party_get_slot, "$coop_mp_next_ally", "$coop_fight_ally", slot_party_coop_sid),
        (assign, "$coop_mp_next_kind", coop_kind_caravan),
        (call_script, "script_coop_client_mp_begin", "$coop_fight_enemy"),
      ]),
     ("coop_fight_leave", [], "Leave them to it.", [(leave_encounter), (change_screen_return)]),
   ]),

  ("coop_duel_stake", 0,
   "CoopWorld: a duel with {s1}.^^You fight each other on the multiplayer server, in your own gear, without troops. Nobody is hurt in earnest, nobody is taken, your troops lose nothing. {s1} sees the stake and may decline it; the winner takes the stake from the loser, and both learn from the blows.",
   "none",
   player_name_to_s1("$coop_duel_with"),
   [
     ("coop_duel_%d" % amount,
      [(store_troop_gold, ":gold", "trp_player"), (ge, ":gold", amount)],
      "%d denars." % amount,
      [
        (store_sub, ":slot", "$coop_duel_with", 1),
        (call_script, "script_coop_client_mp_begin_event", coop_event_duel, ":slot", 0, amount),
      ])
     for amount in (100, 500, 1000)
   ] + [
     ("coop_duel_free", [], "No stake.",
      [
        (store_sub, ":slot", "$coop_duel_with", 1),
        (call_script, "script_coop_client_mp_begin_event", coop_event_duel, ":slot", 0, 0),
      ]),
     ("coop_duel_back", [], "Go back.", [(jump_to_menu, "mnu_coop_players")]),
   ]),
]
