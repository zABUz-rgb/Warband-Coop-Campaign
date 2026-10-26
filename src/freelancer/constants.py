from module_constants import *
from header_operations import neq, eq

#+FREELANCER start
freelancer_version = 13
#Floris or no Diplomacy:
freelancer_can_use_item  = "script_troop_can_use_item"

#Party Slots
slot_party_orig_morale = slot_party_ai_rationale
slot_freelancer_equip_start = 100 #only used for freelancer_party_backup
slot_freelancer_version     = slot_freelancer_equip_start - 2 #only used for freelancer_party_backup

#Faction Slot
slot_faction_freelancer_troop = 101 #should be unused

#Troop Slots
slot_troop_freelancer_start_xp   =  slot_troop_signup   #110 -only used for player
slot_troop_freelancer_start_date =  slot_troop_signup_2 #111 -only used for player

plyr_mission_vacation = 1
#+Freelancer end

not_in_party = [(neq, "$freelancer_state", 1),]
not_enlisted = [(eq,  "$freelancer_state", 0),]
