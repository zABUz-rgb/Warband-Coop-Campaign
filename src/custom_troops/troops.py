from header_common import *
from header_items import *
from header_troops import *
from header_skills import *
from ID_factions import *
from ID_items import *
from custom_troops.constants import *
from custom_troops import stats

# Only the worst there is, of each sort: what a soldier is first given John's gear screen replaces
FOOT = [itm_shirt, itm_wrapping_boots, itm_cudgel]
GEAR = {None: FOOT, "inf": FOOT + [itm_wooden_shield], "arc": FOOT + [itm_hunting_bow, itm_arrows],
        "cav": FOOT + [itm_wooden_shield, itm_sumpter_horse]}
WEARS = (tf_guarantee_boots | tf_guarantee_armor | tf_guarantee_helmet | tf_guarantee_gloves | tf_guarantee_horse
         | tf_guarantee_shield | tf_guarantee_ranged | tf_guarantee_polearm)  # whatever the player bought, each man has it
NAMES = {
  (1, None): ("Recruit", "Recruits"),
  (2, "inf"): ("Militia Footman", "Militia Footmen"), (3, "inf"): ("Footman", "Footmen"),
  (4, "inf"): ("Veteran Footman", "Veteran Footmen"), (5, "inf"): ("Champion Footman", "Champion Footmen"),
  (2, "arc"): ("Militia Archer", "Militia Archers"), (3, "arc"): ("Archer", "Archers"),
  (4, "arc"): ("Veteran Archer", "Veteran Archers"), (5, "arc"): ("Champion Archer", "Champion Archers"),
  (2, "cav"): ("Militia Rider", "Militia Riders"), (3, "cav"): ("Rider", "Riders"),
  (4, "cav"): ("Veteran Rider", "Veteran Riders"), (5, "cav"): ("Champion Rider", "Champion Riders"),
}


def merge(troops):
  from module_items import items
  from module_troops import swadian_face_young_1, swadian_face_old_2  # a common man's faces
  worth = stats.averages(troops, items)
  for kind, (_, tier, branch) in enumerate(KINDS):
    name, plural = NAMES[(tier, branch)]
    flags = WEARS | (tf_mounted if branch == "cav" else 0)
    for level in LEVELS:
      attributes, proficiencies, skills = stats.words(stats.scaled(worth[(tier, branch)], level))
      troops.append([troop_id(kind, level), name, plural, flags, 0, 0, fac_commoners, list(GEAR[branch]),
                     attributes, proficiencies, skills, swadian_face_young_1, swadian_face_old_2])
  troops.append(["custom_army", "Player's Army", "Player's Army", 0, 0, 0, fac_commoners, [],
                 0, 0, 0, 0, 0])
  # the same way up for all three levels; the riders' branch comes from John (the engine keeps two a troop)
  for level in LEVELS:
    upgrade2(troops, troop_id(0, level), troop_id(kind_of("inf", 2), 1), troop_id(kind_of("arc", 2), 1))
  for branch in BRANCH_NAMES:
    for tier in TIERS[:-1]:
      for level in LEVELS:
        upgrade(troops, troop_id(kind_of(branch, tier), level), troop_id(kind_of(branch, tier + 1), 1))
