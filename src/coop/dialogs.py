from header_common import *
from header_dialogs import *
from header_operations import *
from module_constants import *


def merge(orig_dialogs):
  """A town's guild master sends a trade caravan of the player's own off (coop/caravans.py); a client's king grants
  a fief (coop/fiefs.py)."""
  from coop.caravans import caravan_dialogs
  from coop.fiefs import fief_dialogs
  orig_dialogs[0:0] = caravan_dialogs + fief_dialogs
