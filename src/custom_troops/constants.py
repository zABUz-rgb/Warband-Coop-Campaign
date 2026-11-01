from coop.constants import coop_blackborn

# The kinds of soldier, each in three levels of stats: kind 0 the recruit, then each branch's tiers.
# A tier (recruit to champion) rises by experience: battles and the training field. A level (1 to 3) is stats
# bought from John, and it leaves the tier as it was.
# custom_first + 3 * kind + level - 1 is a soldier's troop; tools/test_custom_troops.py keeps it true.
BRANCH_NAMES = ("inf", "arc", "cav")
TIERS = (2, 3, 4, 5)
KINDS = [("t1_recruit", 1, None)] + [("t%d_%s" % (tier, branch), tier, branch) for branch in BRANCH_NAMES for tier in TIERS]
LEVELS = (1, 2, 3)
custom_kinds = len(KINDS)


def troop_id(kind, level):
  return "custom_%s_lvl%d" % (KINDS[kind][0], level)


def kind_of(branch, tier):
  return KINDS.index(("t%d_%s" % (tier, branch), tier, branch))


custom_first = "trp_" + troop_id(0, 1)
custom_holder = "trp_custom_army"   # its name is the army's; its slots say what the other games still have to hear
custom_npc = coop_blackborn

# the slots of custom_holder
custom_slot_name = 0                # 0 the army's name, 1 + kind a soldier's: that it has to go out
custom_slot_gear = 20               # + kind: that this kind's gear has to go out
slot_item_custom_tier = 200         # the lowest tier of soldier an item may go to, 0 none
slot_item_custom_paid = 201         # copies this game paid for: only those sell for money (what a soldier starts
                                    # with, or another player bought, brings nothing)

custom_recruit_cost = 20            # dinars a man
custom_recruits = (5, 10, 20)
custom_gear_factor = 4              # what soldiers' gear costs, times the item's value
custom_sell_percent = 50
custom_gear_max = 24                # items a kind may carry
custom_train_cost = {1: (3000, 5000), 2: (7500, 10000), 3: (12500, 15000), 4: (17500, 20000), 5: (30000, 40000)}
                                    # dinars for levels 2 and 3 by tier; level 1 comes with the man

custom_screen_shop = 1              # $custom_screen: what opens once John's conversation is over
custom_screen_names = 2
custom_screen_train = 3
custom_screen_army = 4              # the names screen with the army's common name alone
custom_screen_soldiers = 5          # and with the units' own names alone (custom_screen_names has both)

custom_word_gap = 2                 # a word to the others goes out, then this many ordinary requests' turns
custom_kind_labels = ["Recruit"] + ["%s, tier %d" % (name, tier) for name in ("Infantry", "Archers", "Riders") for tier in TIERS]
