from header_parties import *
from ID_factions import *
from ID_party_templates import *

no_menu = 0

parties = [
  ("freelancer_party_backup","{!}",  pf_disabled, no_menu, pt_none, fac_neutral,0,ai_bhvr_hold,0,(1,1),[]),
]


def merge(orig_parties):
  from coop_merge import insert_records_before
  insert_records_before(orig_parties, "zendar", parties)
