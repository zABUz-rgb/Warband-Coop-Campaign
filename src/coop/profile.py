from header_common import *
from header_operations import *
from module_constants import *
from coop.constants import *

# A client's own hero between sessions. A client starts every session from the host's save, whose
# player is the host's hero; so the client's game sends the bridge its own hero now and then (the
# profile), and when it joins again the bridge sends it back and the game puts it in place: gold,
# experience, renown, honor, right to rule, the kingdom served, where the party stands, attributes,
# skills, weapon proficiencies, the whole inventory, the party's troops (wounded too) and prisoners.
# (Experience only grows: the level can be raised to the profile's, never lowered.)
#
# Layout (numbers): version, gold, xp, renown, honor, right to rule, kingdom, x, y,
#   4 attributes, NUM_SKILLS skills, 7 proficiencies,
#   inventory capacity, (item, modifier, amount) * capacity,
#   members n, (troop, count, wounded) * n, prisoners n, (troop, count) * n
# trp_tutorial_student_3 keeps the profile coming in, trp_tutorial_student_4 the one going out.

PROFILE_VERSION = 1
NUM_SKILLS = 42
PROFILE_IN = "trp_tutorial_student_3"
PROFILE_OUT = "trp_tutorial_student_4"


def put(value):
  return [(troop_set_slot, PROFILE_OUT, ":at", value), (val_add, ":at", 1)]


def take(dest):
  return [(troop_get_slot, dest, PROFILE_IN, ":at"), (val_add, ":at", 1)]


profile_scripts = [
  # script_coop_profile_build: the player's hero into PROFILE_OUT; $coop_profile_len numbers
  ("coop_profile_build",
   [
     (assign, ":at", 0),
     ] + put(PROFILE_VERSION) + [
     (store_troop_gold, ":v", "trp_player"),
     ] + put(":v") + [
     (troop_get_xp, ":v", "trp_player"),
     ] + put(":v") + [
     (troop_get_slot, ":v", "trp_player", slot_troop_renown),
     ] + put(":v") + put("$player_honor") + put("$player_right_to_rule") + put("$players_kingdom") + [
     (set_fixed_point_multiplier, 100),
     (party_get_position, pos1, "p_main_party"),
     (position_get_x, ":v", pos1),
     ] + put(":v") + [
     (position_get_y, ":v", pos1),
     ] + put(":v") + [
     (try_for_range, ":attribute", 0, 4),
       (store_attribute_level, ":v", "trp_player", ":attribute"),
       ] + put(":v") + [
     (try_end),
     (try_for_range, ":skill", 0, NUM_SKILLS),
       (store_skill_level, ":v", ":skill", "trp_player"),
       ] + put(":v") + [
     (try_end),
     (try_for_range, ":wpt", 0, coop_hero_profs),
       (store_proficiency_level, ":v", "trp_player", ":wpt"),
       ] + put(":v") + [
     (try_end),
     (troop_get_inventory_capacity, ":capacity", "trp_player"),
     ] + put(":capacity") + [
     (try_for_range, ":i", 0, ":capacity"),
       (troop_get_inventory_slot, ":item", "trp_player", ":i"),
       (troop_get_inventory_slot_modifier, ":modifier", "trp_player", ":i"),
       (assign, ":amount", 0),
       (try_begin),
         (ge, ":item", 0),
         (troop_inventory_slot_get_item_amount, ":amount", "trp_player", ":i"),
       (try_end),
       ] + put(":item") + put(":modifier") + put(":amount") + [
     (try_end),
     # members: the count first, filled in after
     (assign, ":count_at", ":at"),
     ] + put(0) + [
     (assign, ":n", 0),
     (party_get_num_companion_stacks, ":stacks", "p_main_party"),
     (try_for_range, ":stack", 0, ":stacks"),
       (party_stack_get_troop_id, ":troop", "p_main_party", ":stack"),
       (neq, ":troop", "trp_player"),
       (party_stack_get_size, ":size", "p_main_party", ":stack"),
       (party_stack_get_num_wounded, ":wounded", "p_main_party", ":stack"),
       ] + put(":troop") + put(":size") + put(":wounded") + [
       (val_add, ":n", 1),
     (try_end),
     (troop_set_slot, PROFILE_OUT, ":count_at", ":n"),
     (assign, ":count_at", ":at"),
     ] + put(0) + [
     (assign, ":n", 0),
     (party_get_num_prisoner_stacks, ":stacks", "p_main_party"),
     (try_for_range, ":stack", 0, ":stacks"),
       (party_prisoner_stack_get_troop_id, ":troop", "p_main_party", ":stack"),
       (party_prisoner_stack_get_size, ":size", "p_main_party", ":stack"),
       ] + put(":troop") + put(":size") + [
       (val_add, ":n", 1),
     (try_end),
     (troop_set_slot, PROFILE_OUT, ":count_at", ":n"),
     (assign, "$coop_profile_len", ":at"),
     (assign, "$coop_profile_sent", 0),
     (val_add, "$coop_profile_seq", 1),
    ]),

  # script_coop_profile_chunk: s19 = "&pf=seq,offset,total,v,..." the profile's next part, or empty
  ("coop_profile_chunk",
   [
     (str_clear, s19),
     (try_begin),
       (lt, "$coop_profile_sent", "$coop_profile_len"),
       (store_sub, ":n", "$coop_profile_len", "$coop_profile_sent"),
       (val_min, ":n", coop_profile_chunk),
       (assign, reg20, "$coop_profile_seq"),
       (assign, reg21, "$coop_profile_sent"),
       (assign, reg22, "$coop_profile_len"),
       (str_store_string, s19, "@&pf={reg20},{reg21},{reg22}"),
       (store_add, ":end", "$coop_profile_sent", ":n"),
       (try_for_range, ":i", "$coop_profile_sent", ":end"),
         (troop_get_slot, reg20, PROFILE_OUT, ":i"),
         (str_store_string, s19, "@{s19},{reg20}"),
       (try_end),
       (assign, "$coop_profile_sent", ":end"),
     (try_end),
    ]),

  # script_coop_profile_receive: kind 14 reply, part of the profile kept for this player:
  # offset|total|n|values (total 0: none kept, this is a new player)
  ("coop_profile_receive",
   [
     (try_begin), #an early way out, not a failure of the caller
       (party_get_slot, ":offset", "p_coop_buf", 2),
       (party_get_slot, ":total", "p_coop_buf", 3),
       (party_get_slot, ":n", "p_coop_buf", 4),
       (eq, "$coop_profile_state", 0), #settled already: a late copy must not take the hero back
       (try_begin),
         (eq, ":offset", 0),
         (assign, "$coop_profile_got", 0),
       (try_end),
       (val_add, "$coop_profile_got", ":n"),
       (try_for_range, ":k", 0, ":n"),
         (store_add, ":src", ":k", 5),
         (store_add, ":dst", ":k", ":offset"),
         (party_get_slot, ":v", "p_coop_buf", ":src"),
         (troop_set_slot, PROFILE_IN, ":dst", ":v"),
       (try_end),
       (try_begin),
         (eq, ":total", 0),
         (assign, "$coop_profile_state", 1), #nothing to put back: this hero is the player's from now on
         (display_message, "@CoopWorld: a new hero - from now on it is kept between sessions.", 0x66CCFF),
       (else_try),
         (store_add, ":end", ":offset", ":n"),
         (ge, ":end", ":total"),
         (ge, "$coop_profile_got", ":total"), #a part went missing: asked for again (client_tick)
         (assign, "$coop_profile_ready", 1),
       (try_end),
     (try_end),
    ]),

  # script_coop_profile_apply: the profile kept for this player replaces the host's hero this
  # session began with
  ("coop_profile_apply",
   [
     (assign, ":at", 0),
     ] + take(":version") + [
     (try_begin),
       (eq, ":version", PROFILE_VERSION),
       ] + take(":v") + [
       (store_troop_gold, ":gold", "trp_player"),
       (troop_remove_gold, "trp_player", ":gold"),
       (troop_add_gold, "trp_player", ":v"),
       ] + take(":v") + [
       (troop_get_xp, ":xp", "trp_player"),
       (try_begin),
         (gt, ":v", ":xp"),
         (store_sub, ":more", ":v", ":xp"),
         (add_xp_to_troop, ":more", "trp_player"),
       (try_end),
       ] + take(":v") + [
       (troop_set_slot, "trp_player", slot_troop_renown, ":v"),
       ] + take("$player_honor") + take("$player_right_to_rule") + take(":kingdom") + [
       (try_begin),
         (neq, ":kingdom", "$players_kingdom"),
         (try_begin),
           (is_between, "$players_kingdom", npc_kingdoms_begin, npc_kingdoms_end),
           (call_script, "script_player_leave_faction", 0),
         (try_end),
         (is_between, ":kingdom", npc_kingdoms_begin, npc_kingdoms_end),
         (call_script, "script_player_join_faction", ":kingdom"),
       (try_end),
       ] + take(":x") + take(":y") + [
       (set_fixed_point_multiplier, 100),
       (init_position, pos1),
       (position_set_x, pos1, ":x"),
       (position_set_y, pos1, ":y"),
       (party_set_position, "p_main_party", pos1),
       (try_for_range, ":attribute", 0, 4),
         ] + take(":v") + [
         (call_script, "script_coop_mp_hero_stat", "trp_player", ":attribute", ":v"),
       (try_end),
       (try_for_range, ":skill", 0, NUM_SKILLS),
         ] + take(":v") + [
         (store_add, ":code", ":skill", 10),
         (call_script, "script_coop_mp_hero_stat", "trp_player", ":code", ":v"),
       (try_end),
       (try_for_range, ":wpt", 0, coop_hero_profs),
         ] + take(":v") + [
         (store_add, ":code", ":wpt", 100),
         (call_script, "script_coop_mp_hero_stat", "trp_player", ":code", ":v"),
       (try_end),
       ] + take(":saved_capacity") + [
       (troop_get_inventory_capacity, ":capacity", "trp_player"),
       (try_for_range, ":i", 0, ":saved_capacity"),
         ] + take(":item") + take(":modifier") + take(":amount") + [
         (lt, ":i", ":capacity"),
         (troop_set_inventory_slot, "trp_player", ":i", ":item"),
         (ge, ":item", 0),
         (troop_set_inventory_slot_modifier, "trp_player", ":i", ":modifier"),
         (gt, ":amount", 0),
         (troop_inventory_slot_set_item_amount, "trp_player", ":i", ":amount"),
       (try_end),
       (try_for_range, ":i", ":saved_capacity", ":capacity"),
         (troop_set_inventory_slot, "trp_player", ":i", -1),
       (try_end),
       # the party: the host's men out, the player's own in
       (party_get_num_companion_stacks, ":stacks", "p_main_party"),
       (try_for_range_backwards, ":stack", 0, ":stacks"),
         (party_stack_get_troop_id, ":troop", "p_main_party", ":stack"),
         (neq, ":troop", "trp_player"),
         (party_stack_get_size, ":size", "p_main_party", ":stack"),
         (party_remove_members, "p_main_party", ":troop", ":size"),
       (try_end),
       ] + take(":n") + [
       (try_for_range, ":unused", 0, ":n"),
         ] + take(":troop") + take(":size") + take(":wounded") + [
         (party_add_members, "p_main_party", ":troop", ":size"),
         (gt, ":wounded", 0),
         (party_wound_members, "p_main_party", ":troop", ":wounded"),
       (try_end),
       (party_get_num_prisoner_stacks, ":stacks", "p_main_party"),
       (try_for_range_backwards, ":stack", 0, ":stacks"),
         (party_prisoner_stack_get_troop_id, ":troop", "p_main_party", ":stack"),
         (party_prisoner_stack_get_size, ":size", "p_main_party", ":stack"),
         (party_remove_prisoners, "p_main_party", ":troop", ":size"),
       (try_end),
       ] + take(":n") + [
       (try_for_range, ":unused", 0, ":n"),
         ] + take(":troop") + take(":size") + [
         (party_add_prisoners, "p_main_party", ":troop", ":size"),
       (try_end),
       (display_message, "@CoopWorld: your own hero is back - gold, skills, gear, troops and prisoners as you left them.", 0x66FF66),
     (else_try),
       (display_message, "@CoopWorld: the hero kept for you is from another version of CoopWorld and was not put back.", 0xFF6666),
     (try_end),
     (assign, "$coop_profile_state", 1),
    ]),
]


def client_tick():
  """Ops for the client's map trigger, before its request is built: a received profile is put in
  place on the free map; now and then the hero is written down; s19 = the part sent with this
  request (only once the profile question of this session is settled, never the host's hero)."""
  return [
    (try_begin),
      (eq, "$coop_profile_ready", 1),
      (map_free),
      (assign, "$coop_profile_ready", 0),
      (call_script, "script_coop_profile_apply"),
    (try_end),
    (str_clear, s19),
    # the bridge's answer about the kept hero got lost (a broken link): ask again, else this
    # session's hero would never be written down
    (try_begin),
      (eq, "$coop_profile_state", 0),
      (eq, "$coop_profile_ready", 0),
      (val_add, "$coop_profile_ask_frames", 1),
      (ge, "$coop_profile_ask_frames", coop_profile_ask_frames),
      (assign, "$coop_profile_ask_frames", 0),
      (str_store_string, s19, "@&pfq=1"),
    (try_end),
    (try_begin),
      (eq, "$coop_profile_state", 1),
      (val_add, "$coop_profile_frames", 1),
      (try_begin),
        (ge, "$coop_profile_frames", coop_profile_period_frames),
        (ge, "$coop_profile_sent", "$coop_profile_len"),
        (assign, "$coop_profile_frames", 0),
        (call_script, "script_coop_profile_build"),
      (try_end),
      (call_script, "script_coop_profile_chunk"),
    (try_end),
  ]
