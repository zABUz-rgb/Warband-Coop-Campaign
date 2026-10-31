from header_common import *
from header_dialogs import *
from header_operations import *
from coop.constants import *

# The company's camp: John Blackborn has nothing to say yet but this. His lines come before Native's
# first one (which only notes who is being talked to): nothing of that is needed here.
dialogs = [
  [anyone, "start", [(store_conversation_troop, ":troop"), (eq, ":troop", coop_blackborn)],
   "Go away, traveller.", "coop_blackborn_leave", []],
  [anyone|plyr, "coop_blackborn_leave", [], "Leave.", "close_window", []],
]


def merge(orig_dialogs):
  orig_dialogs[0:0] = dialogs
