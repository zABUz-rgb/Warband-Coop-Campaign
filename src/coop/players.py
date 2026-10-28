from header_common import *
from header_operations import *
from header_game_menus import *
from module_constants import *
from coop.constants import *

# Players together on the map: one player joins another's party (asks, the other accepts or
# declines; then follows the leader and is called into the leader's joint battles), and players
# give each other troops (chosen on the exchange screen, the receiver accepts or declines; declined
# troops go back). Requests go out with the next map request (s17), answers come back as replies:
#   15 an offer of troops id|from slot|n|(troop, count)*n    16 how the offer went id|accepted|n|...
#   17 a player asks to join this one: from slot              18 the answer: leader slot|accepted
#   19 to the leader: slot|joined (1) or left (0)             20 the leader let this player go: leader slot
# Player slots are kept + 1, so that 0 (a new game's globals) means none.
# trp_tutorial_student_2 keeps a troop offer while its menu is open; p_temp_party_2 the troops
# chosen for one.

OFFER = "trp_tutorial_student_2"
GIFT = "p_temp_party_2"


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
         (display_message, "@CoopWorld: your troops were accepted.", 0x66FF66),
       (else_try),
         (try_for_range, ":k", 0, ":n"),
           (store_mul, ":at", ":k", 2),
           (val_add, ":at", 5),
           (party_get_slot, ":troop", "p_coop_buf", ":at"),
           (val_add, ":at", 1),
           (party_get_slot, ":count", "p_coop_buf", ":at"),
           (party_add_members, "p_main_party", ":troop", ":count"),
         (try_end),
         (display_message, "@CoopWorld: your troops were declined and came back to you.", 0xFFDD66),
       (try_end),
     (else_try),
       (eq, ":kind", 17), #a player asks to join my party
       (party_get_slot, ":slot", "p_coop_buf", 2),
       (store_add, "$coop_join_from", ":slot", 1),
       (assign, "$coop_join_request_pending", 1),
     (else_try),
       (eq, ":kind", 18), #the answer to my request
       (party_get_slot, ":slot", "p_coop_buf", 2),
       (party_get_slot, ":accepted", "p_coop_buf", 3),
       (store_add, ":leader", ":slot", 1),
       ] + player_name_to_s1(":leader") + [
       (try_begin),
         (eq, ":accepted", 1),
         (assign, "$coop_leader", ":leader"),
         (display_message, "@CoopWorld: {s1} takes you into the party. You follow {s1} and fight in {s1}'s battles. Camp - leave the party, to ride on your own again.", 0x66FF66),
       (else_try),
         (display_message, "@CoopWorld: {s1} does not take you into the party.", 0xFFDD66),
       (try_end),
     (else_try),
       (eq, ":kind", 19), #to the leader: a player joined or left
       (party_get_slot, ":slot", "p_coop_buf", 2),
       (party_get_slot, ":joined", "p_coop_buf", 3),
       (store_add, ":follower", ":slot", 1),
       ] + player_name_to_s1(":follower") + [
       (try_begin),
         (eq, ":joined", 1),
         (val_add, "$coop_followers", 1),
         (display_message, "@CoopWorld: {s1} follows you now.", 0x66FF66),
       (else_try),
         (val_sub, "$coop_followers", 1),
         (val_max, "$coop_followers", 0),
         (display_message, "@CoopWorld: {s1} left your party.", 0xFFDD66),
       (try_end),
     (else_try),
       (eq, ":kind", 20), #the leader let me go
       ] + player_name_to_s1("$coop_leader") + [
       (assign, "$coop_leader", 0),
       (display_message, "@CoopWorld: {s1} released you from the party. You ride on your own again.", 0xFFDD66),
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
       (str_store_troop_name_by_count, s3, ":troop", reg1),
       (str_store_string, s2, "@{s2}^{reg1} {s3}"),
     (try_end),
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
      (gt, "$coop_join_ask", 0), #I ask the player in this slot (+ 1) to take me in
      (store_sub, reg7, "$coop_join_ask", 1),
      (str_store_string, s17, "@{s17}&join={reg7}"),
      (assign, "$coop_join_ask", 0),
    (try_end),
    (try_begin),
      (gt, "$coop_join_answer_slot", 0), #my answer to a player asking to join me
      (store_sub, reg7, "$coop_join_answer_slot", 1),
      (assign, reg8, "$coop_join_answer_yes"),
      (str_store_string, s17, "@{s17}&joinans={reg7},{reg8}"),
      (assign, "$coop_join_answer_slot", 0),
    (try_end),
    (try_begin),
      (eq, "$coop_leave_party", 1),
      (assign, "$coop_leave_party", 0),
      (str_store_string, s17, "@{s17}&leave=1"),
    (try_end),
    (try_begin),
      (eq, "$coop_release_followers", 1),
      (assign, "$coop_release_followers", 0),
      (str_store_string, s17, "@{s17}&release=1"),
    (try_end),
    (try_begin),
      (gt, "$coop_give_send", 0), #troops for the player in this slot (+ 1)
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
      (call_script, "script_coop_troops_to_s12", GIFT, 1),
      (party_clear, GIFT),
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
  """Ops for the map trigger (client and host): follow the leader; open the menus of requests."""
  return [
    (try_begin),
      (gt, "$coop_leader", 0),
      (eq, "$coop_busy", 0),
      (store_add, ":leader_party", "p_coop_puppet_1", "$coop_leader"),
      (val_sub, ":leader_party", 1),
      (party_is_active, ":leader_party"),
      (party_get_position, pos5, ":leader_party"),
      (party_set_position, "p_main_party", pos5),
    (try_end),
    (try_begin),
      (eq, "$coop_join_request_pending", 1),
      (map_free),
      (assign, "$coop_join_request_pending", 0),
      (jump_to_menu, "mnu_coop_join_request"),
    (else_try),
      (eq, "$coop_offer_pending", 1),
      (map_free),
      (jump_to_menu, "mnu_coop_troops_offered"),
    (try_end),
  ]


def plays():
  """Ops: this game is a player's (a client, or the host playing on the server)."""
  return [(this_or_next|eq, "$coop_role", coop_role_client), (eq, "$coop_srv_player", 1)]


def encounter_options():
  is_player = [(is_between, "$g_encountered_party", "p_coop_puppet_1", puppet_end())]
  return [
    ("coop_join_ask", plays() + is_player + [(eq, "$coop_leader", 0)],
     "CoopWorld: ask to join this player's party (follow and fight together).",
     [
       (store_sub, "$coop_join_ask", "$g_encountered_party", "p_coop_puppet_1"),
       (val_add, "$coop_join_ask", 1),
       (str_store_party_name, s1, "$g_encountered_party"),
       (display_message, "@CoopWorld: you ask {s1} to take you into the party...", 0x66CCFF),
       (leave_encounter),
       (change_screen_return),
     ]),
    ("coop_give_troops", plays() + is_player,
     "CoopWorld: give troops to this player.",
     [
       (store_sub, "$coop_give_to", "$g_encountered_party", "p_coop_puppet_1"),
       (val_add, "$coop_give_to", 1),
       (party_clear, GIFT),
       (jump_to_menu, "mnu_coop_give_troops"),
     ]),
  ]


def camp_options():
  return [
    ("coop_players", plays(), "CoopWorld: the other players (join a party, give troops)...",
     [(jump_to_menu, "mnu_coop_players")]),
    ("coop_leave_party", plays() + [(gt, "$coop_leader", 0)] + player_name_to_s1("$coop_leader"),
     "CoopWorld: leave {s1}'s party and ride on your own.",
     [(assign, "$coop_leave_party", 1), (assign, "$coop_leader", 0), (change_screen_return)]),
    ("coop_release_followers", plays() + [(gt, "$coop_followers", 0)],
     "CoopWorld: release the players following you.",
     [(assign, "$coop_release_followers", 1), (assign, "$coop_followers", 0), (change_screen_return)]),
  ]


def players_menu_options():
  """The camp's players menu: for each other player, what can be done without meeting on the map."""
  options = []
  for k in range(coop_max_players):
    puppet = f"p_coop_puppet_{k + 1}"
    name = [(party_is_active, puppet), (str_store_party_name, s1, puppet)]
    options += [
      ("coop_pl_join_%d" % k, plays() + name + [(eq, "$coop_leader", 0)],
       "Ask {s1} to take you into the party.",
       [
         (assign, "$coop_join_ask", k + 1),
         (display_message, "@CoopWorld: you ask {s1} to take you into the party...", 0x66CCFF),
         (change_screen_return),
       ]),
      ("coop_pl_give_%d" % k, plays() + name + [
         (store_distance_to_party_from_party, ":dist", "p_main_party", puppet),
         (le, ":dist", coop_give_distance)],
       "Give troops to {s1}.",
       [
         (assign, "$coop_give_to", k + 1),
         (party_clear, GIFT),
         (jump_to_menu, "mnu_coop_give_troops"),
       ]),
    ]
  return options + [
    ("coop_pl_write_hero", [(eq, "$coop_role", coop_role_client), (eq, "$coop_profile_state", 1)],
     "Write my hero down at the host now.",
     [
       (assign, "$coop_profile_frames", coop_profile_period_frames),
       (display_message, "@CoopWorld: writing your hero down at the host in a few seconds.", 0x66CCFF),
       (change_screen_return),
     ]),
    ("coop_pl_back", [], "Back.", [(jump_to_menu, "mnu_camp")]),
  ]


def players_list_to_s10():
  """Ops: s10 = one line per other player: name, how far, in whose party."""
  ops = [(str_clear, s10), (assign, ":any", 0)]
  for k in range(coop_max_players):
    puppet = f"p_coop_puppet_{k + 1}"
    ops += [
      (try_begin),
        (party_is_active, puppet),
        (assign, ":any", 1),
        (str_store_party_name, s1, puppet),
        (store_distance_to_party_from_party, reg1, "p_main_party", puppet),
        (str_store_string, s10, "@{s10}^{s1}: {reg1} km away"),
        (try_begin),
          (eq, "$coop_leader", k + 1),
          (str_store_string, s10, "@{s10} - you ride in this party"),
        (try_end),
        (str_store_string, s10, "@{s10}."),
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
   "CoopWorld: the players in this world:^{s10}^^Troops are given to a player who is close by (up to {reg2} km); a party can be joined from anywhere: you then ride to its leader.",
   "none",
   players_list_to_s10() + [(assign, reg2, coop_give_distance)],
   players_menu_options()),

  ("coop_give_troops", 0,
   "CoopWorld: troops for {s1}.^^Chosen so far: {reg1}. Choose them on the exchange screen (your party on the left, the gift on the right); {s1} accepts or declines them, and declined troops come back to you. Companions stay with you.",
   "none",
   player_name_to_s1("$coop_give_to") + [
     (party_get_num_companions, reg1, GIFT),
   ],
   [
     ("coop_give_choose", [], "Choose the troops.",
      [(change_screen_exchange_with_party, GIFT)]),
     ("coop_give_send", [(party_get_num_companions, ":n", GIFT), (gt, ":n", 0)], "Send them.",
      [
        (assign, "$coop_give_send", "$coop_give_to"),
        (display_message, "@CoopWorld: troops sent; waiting for the answer.", 0x66CCFF),
        (leave_encounter),
        (change_screen_return),
      ]),
     ("coop_give_cancel", [], "Never mind.",
      [(call_script, "script_coop_gift_back"), (leave_encounter), (change_screen_return)]),
   ]),

  ("coop_troops_offered", 0,
   "CoopWorld: {s1} offers you troops:^{s2}",
   "none",
   [
     (troop_get_slot, ":slot", OFFER, 1),
     (val_add, ":slot", 1),
     ] + player_name_to_s1(":slot") + [
     (call_script, "script_coop_offer_to_s2"),
   ],
   [
     ("coop_offer_accept", [], "Accept them.",
      [
        (troop_get_slot, ":n", OFFER, 2),
        (try_for_range, ":k", 0, ":n"),
          (store_mul, ":at", ":k", 2),
          (val_add, ":at", 3),
          (troop_get_slot, ":troop", OFFER, ":at"),
          (val_add, ":at", 1),
          (troop_get_slot, ":count", OFFER, ":at"),
          (party_add_members, "p_main_party", ":troop", ":count"),
        (try_end),
        (troop_get_slot, "$coop_offer_answer_id", OFFER, 0),
        (assign, "$coop_offer_answer_yes", 1),
        (assign, "$coop_offer_pending", 0),
        (change_screen_return),
      ]),
     ("coop_offer_decline", [], "Decline them.",
      [
        (troop_get_slot, "$coop_offer_answer_id", OFFER, 0),
        (assign, "$coop_offer_answer_yes", 0),
        (assign, "$coop_offer_pending", 0),
        (change_screen_return),
      ]),
   ]),

  ("coop_join_request", 0,
   "CoopWorld: {s1} asks to join your party.^^{s1} will follow you on the map and fight in your joint battles, until leaving the party or until you release your followers (camp menu).",
   "none",
   player_name_to_s1("$coop_join_from"),
   [
     ("coop_join_accept", [], "Take {s1} in.",
      [(assign, "$coop_join_answer_slot", "$coop_join_from"), (assign, "$coop_join_answer_yes", 1),
       (change_screen_return)]),
     ("coop_join_decline", [], "Decline.",
      [(assign, "$coop_join_answer_slot", "$coop_join_from"), (assign, "$coop_join_answer_yes", 0),
       (change_screen_return)]),
   ]),
]


def reply_branches():
  """else_try branches for net_reply_handler: kinds 15 to 20."""
  return [
    (else_try),
      (is_between, ":kind", 15, 21),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1),
      (call_script, "script_coop_players_reply", ":kind"),
  ]
