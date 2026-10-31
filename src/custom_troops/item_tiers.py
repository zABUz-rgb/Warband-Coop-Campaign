"""Which items a soldier of each tier may be given. Items are ranked by their kind and value when the module
is built: list_tier1_items to list_tier5_items, each with the tier below in it."""
from header_items import *

# the dearest item of a kind that tiers 1, 2 and 3 may have: no mail, no two-handed sword and no warhorse at
# tier 1, mail shirts and riding horses from tier 2, plate and the best weapons from tier 3
LIMITS = {
  itp_type_horse: (240, 810, 1400),
  itp_type_one_handed_wpn: (110, 280, 400),
  itp_type_two_handed_wpn: (100, 300, 524),
  itp_type_polearm: (125, 250, 400),
  itp_type_arrows: (72, 124, 350),
  itp_type_bolts: (64, 64, 210),
  itp_type_shield: (100, 200, 332),
  itp_type_bow: (58, 164, 437),
  itp_type_crossbow: (67, 182, 349),
  itp_type_thrown: (155, 300, 525),
  itp_type_head_armor: (100, 340, 810),
  itp_type_body_armor: (320, 1200, 3000),
  itp_type_foot_armor: (75, 200, 853),
  itp_type_hand_armor: (90, 350, 710),
}
TIER_4_SHARE = 90                 # percent of what the game sells, the cheapest
NOT_FOR_SOLDIERS = ("dress", "gown", "wimple", "female", "veil", "lady", "bride", "court_", "barbette", "head_cloth",
                    "headcloth", "turret_hat", "arena", "tourney", "practice", "tutorial", "heraldic")


def for_soldiers(item):
  """Sold in the game's shops (lords' and kings' own things are not), not of one kingdom alone, and fit for a
  soldier to wear."""
  flags = item[3]
  if not flags & itp_merchandise or flags & itp_unique or flags & 0xFF not in LIMITS:
    return False
  if len(item) > 9 and item[9]:
    return False
  return not any(word in item[0] for word in NOT_FOR_SOLDIERS)


def tier_lists(items):
  """[list_tier1_items, ..., list_tier5_items]: item ids, the cheapest first."""
  pool = sorted((item for item in items if for_soldiers(item)), key=lambda item: item[5])
  lists = []
  for k in range(3):
    lists.append([item[0] for item in pool if item[5] <= LIMITS[item[3] & 0xFF][k]])
  lists.append([item[0] for item in pool[:len(pool) * TIER_4_SHARE // 100]])
  lists[3] = sorted(set(lists[3]) | set(lists[2]), key=[item[0] for item in pool].index)
  lists.append([item[0] for item in pool])
  return lists


def first_tiers(lists):
  """{item id: the lowest tier that may have it}."""
  out = {}
  for tier, items in enumerate(lists, 1):
    for item_id in items:
      out.setdefault(item_id, tier)
  return out
