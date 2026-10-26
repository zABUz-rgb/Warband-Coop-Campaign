from header_quests import *
from freelancer.constants import *

quests = [
  ("freelancer_enlisted", "Enlisted in the Party of {s13}", 0,
   "{!}You are currently enlisted in the party of {s13} of {s14}."),
  ("freelancer_vacation", "Enlisted: On Leave", 0,
   "{!}You have been granted leave from the party of {s13} of {s14}."),
  ("freelancer_captured", "Enlisted: Captured", 0,
   "{!}Your commander's party has been defeated and you have been captured. Return to the service of {s13} of {s14}."),
]


def merge(orig_quests):
  from coop_merge import insert_records_before
  insert_records_before(orig_quests, "quests_end", quests)
