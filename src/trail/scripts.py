from header_common import *
from header_operations import *
from coop.constants import coop_client_url, coop_role_client
from coop_merge import insert_before, script_block
from trail.marks import *

# The game's own events worth seeing in the trail
GAME_SCRIPTS = ("game_event_party_encounter", "game_event_simulate_battle", "game_event_battle_end")

scripts = [
  # script_coop_trail: arg1 = entry. Runs at the head of other people's blocks: no failing, and only
  # registers nothing else uses (s27, reg55). Off the map it goes out at once, the game may not get
  # another chance; on the map once a frame (trail/triggers.py), so a burst of triggers is one request.
  ("coop_trail",
   [
     (store_script_param, ":entry", 1),
     (try_begin),
       (this_or_next|eq, "$coop_role", coop_role_client),
       (eq, "$coop_srv_player", 1),
       (troop_get_slot, ":last", trail_holder, trail_slot_last),
       (neq, ":last", ":entry"),
       (troop_set_slot, trail_holder, trail_slot_last, ":entry"),
       (troop_get_slot, ":seq", trail_holder, trail_slot_seq),
       (store_mod, ":at", ":seq", trail_ring),
       (val_add, ":at", trail_slot_ring),
       (troop_set_slot, trail_holder, ":at", ":entry"),
       (val_add, ":seq", 1),
       (troop_set_slot, trail_holder, trail_slot_seq, ":seq"),
       (neg|map_free),
       (call_script, "script_coop_trail_flush"),
     (try_end),
    ]),

  # script_coop_trail_flush: what the bridge has not heard yet. A request of its own, on no one's turn:
  # $coop_net_pending stays out of it, and the reply stops at the head of the reply handler.
  ("coop_trail_flush",
   [
     (try_begin),
       (troop_get_slot, ":seq", trail_holder, trail_slot_seq),
       (troop_get_slot, ":sent", trail_holder, trail_slot_sent),
       (gt, ":seq", ":sent"),
       (store_sub, ":oldest", ":seq", trail_ring), #the ring ran over: the bridge sees the gap
       (val_max, ":sent", ":oldest"),
       (store_add, ":end", ":sent", trail_part),
       (val_min, ":end", ":seq"),
       (assign, reg55, ":sent"),
       (str_store_string, s27, "@" + coop_client_url + "/tr?trs={reg55}&tr="),
       (try_for_range, ":n", ":sent", ":end"),
         (store_mod, ":at", ":n", trail_ring),
         (val_add, ":at", trail_slot_ring),
         (troop_get_slot, reg55, trail_holder, ":at"),
         (str_store_string, s27, "@{s27}{reg55},"),
       (try_end),
       (troop_set_slot, trail_holder, trail_slot_sent, ":end"),
       (send_message_to_url, s27, 0),
     (try_end),
    ]),
]


def merge(orig_scripts, **extra):
  marker = Marker(SCRIPT)
  for name in GAME_SCRIPTS:
    marker(script_block(orig_scripts, name))
  orig_scripts += scripts
  handler = script_block(orig_scripts, "game_receive_url_response")
  insert_before(handler, (assign, "$coop_net_pending", 0), [
    (store_script_param, ":trail_numbers", 1),
    (this_or_next|neq, ":trail_numbers", 1),
    (neq, reg0, trail_ack),
  ])
