from header_parties import *
from ID_troops import *
from ID_factions import *
from ID_party_templates import *
from ID_map_icons import *

no_menu = 0

# Static helper parties for the co-op prototype, appended after all Native parties.
parties = [
  # the players' parties: on the world server, and on each player's map for the other players.
  # Consecutive: coop_puppet_1 + slot. Their troops and names come from the players.
  ("coop_puppet_1", "Player 1", pf_disabled|pf_always_visible|pf_show_faction, no_menu, pt_none,
   fac_player_faction, 0, ai_bhvr_hold, 0, (0, 0), [(trp_farmer, 1, 0)]),
  ("coop_puppet_2", "Player 2", pf_disabled|pf_always_visible|pf_show_faction, no_menu, pt_none,
   fac_player_faction, 0, ai_bhvr_hold, 0, (0, 0), [(trp_farmer, 1, 0)]),
  ("coop_puppet_3", "Player 3", pf_disabled|pf_always_visible|pf_show_faction, no_menu, pt_none,
   fac_player_faction, 0, ai_bhvr_hold, 0, (0, 0), [(trp_farmer, 1, 0)]),
  ("coop_puppet_4", "Player 4", pf_disabled|pf_always_visible|pf_show_faction, no_menu, pt_none,
   fac_player_faction, 0, ai_bhvr_hold, 0, (0, 0), [(trp_farmer, 1, 0)]),
  # slot storage only: numbers of the current bridge reply (slot i = reg i), and server id -> client id + 1
  ("coop_buf", "{!}coop_buf", pf_disabled, no_menu, pt_none, fac_neutral, 0, ai_bhvr_hold, 0, (0, 0), []),
  ("coop_map", "{!}coop_map", pf_disabled, no_menu, pt_none, fac_neutral, 0, ai_bhvr_hold, 0, (0, 0), []),
  # mirrors remembered at the start of a client's encounter: slot 0 = count, then (party, sid, size)
  ("coop_enc", "{!}coop_enc", pf_disabled, no_menu, pt_none, fac_neutral, 0, ai_bhvr_hold, 0, (0, 0), []),
  # server party id -> request number until which a party the client destroyed stays gone
  ("coop_dead", "{!}coop_dead", pf_disabled, no_menu, pt_none, fac_neutral, 0, ai_bhvr_hold, 0, (0, 0), []),
]


def merge(orig_parties):
  orig_parties.extend(parties)
