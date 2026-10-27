from header_parties import *
from ID_troops import *
from ID_factions import *
from ID_party_templates import *
from ID_map_icons import *

no_menu = 0

# Static helper parties for the co-op prototype, appended after all Native parties.
parties = [
  # the client player's party as seen on the world server
  ("coop_puppet_1", "Ally", pf_disabled|pf_always_visible|pf_show_faction, no_menu, pt_none,
   fac_player_faction, 0, ai_bhvr_hold, 0, (0, 0), [(trp_swadian_footman, 10, 0)]),
  # slot storage only: numbers of the current bridge reply (slot i = reg i), and server id -> client id + 1
  ("coop_buf", "{!}coop_buf", pf_disabled, no_menu, pt_none, fac_neutral, 0, ai_bhvr_hold, 0, (0, 0), []),
  ("coop_map", "{!}coop_map", pf_disabled, no_menu, pt_none, fac_neutral, 0, ai_bhvr_hold, 0, (0, 0), []),
  # mirrors remembered at the start of a client's encounter: slot 0 = count, then (party, sid, size)
  ("coop_enc", "{!}coop_enc", pf_disabled, no_menu, pt_none, fac_neutral, 0, ai_bhvr_hold, 0, (0, 0), []),
]


def merge(orig_parties):
  orig_parties.extend(parties)
