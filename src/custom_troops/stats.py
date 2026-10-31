"""What soldiers of a tier and a branch are worth: counted from the six kingdoms' own soldiers when the
module is built. A kingdom's tier is how far a troop stands from its recruit; its branch comes from what it
rides and carries."""
from header_common import bignum
from header_items import itp_type_bow, itp_type_crossbow
from header_troops import level_bits, level_mask, tf_mounted

ATTRIBUTES = 4          # strength, agility, intelligence, charisma: a byte each
PROFICIENCIES = 7       # 10 bits each
SKILLS = 42             # 4 bits each
ROOTS = ("swadian_recruit", "vaegir_recruit", "khergit_tribesman", "nord_recruit", "rhodok_tribesman", "sarranid_recruit")
MAX_TIER = 5
LEVEL_PERCENT = {1: 80, 2: 100, 3: 110}


def numbers(troop):
  """[level, attributes..., proficiencies..., skills...] of a record of module_troops."""
  attributes, proficiencies, skills = troop[8], troop[9], troop[10] & ~bignum
  out = [(attributes >> level_bits) & level_mask]
  out += [(attributes >> (8 * k)) & 0xFF for k in range(ATTRIBUTES)]
  out += [(proficiencies >> (10 * k)) & 0x3FF for k in range(PROFICIENCIES)]
  out += [(skills >> (4 * k)) & 0xF for k in range(SKILLS)]
  return out


def words(values):
  """The fields of a troop's record for numbers(), rounded and kept within what they may hold."""
  level, attributes = values[0], values[1:1 + ATTRIBUTES]
  proficiencies = values[1 + ATTRIBUTES:1 + ATTRIBUTES + PROFICIENCIES]
  skills = values[1 + ATTRIBUTES + PROFICIENCIES:]
  word = (max(1, round(level)) & level_mask) << level_bits
  for k, v in enumerate(attributes):
    word |= (max(3, round(v)) & 0xFF) << (8 * k)
  wp = 0
  for k, v in enumerate(proficiencies):
    wp |= (max(0, round(v)) & 0x3FF) << (10 * k)
  known = 0
  for k, v in enumerate(skills):
    known |= min(10, max(0, round(v))) << (4 * k)
  return word, wp, known


def branch_of(troop, items):
  if troop[3] & tf_mounted:
    return "cav"
  for entry in troop[7]:
    item = entry[0] if isinstance(entry, (list, tuple)) else entry
    if 0 <= item < len(items) and items[item][3] & 0xFF in (itp_type_bow, itp_type_crossbow):
      return "arc"
  return "inf"


def groups(troops, items):
  """{(tier, branch): [troop record]}: tier 1 stands for all recruits, whatever they carry."""
  by_id = {t[0]: t for t in troops}
  out = {}

  def walk(troop_id, depth, seen):
    if troop_id in seen:
      return
    seen.add(troop_id)
    troop = by_id[troop_id]
    tier = min(MAX_TIER, depth + 1)
    out.setdefault((tier, None if tier == 1 else branch_of(troop, items)), []).append(troop)
    for n in troop[14:16]:
      if n > 0:
        walk(troops[n][0], depth + 1, seen)

  for root in ROOTS:
    walk(root, 0, set())
  return out


def averages(troops, items):
  """{(tier, branch): numbers} for tier 1 and for tiers 2 to 5 of each branch. A tier no kingdom has takes
  the one below it (or above, for the lowest), and no number falls from a tier to the next."""
  found = groups(troops, items)
  mean = {}
  for key, group in found.items():
    rows = [numbers(t) for t in group]
    mean[key] = [sum(column) / len(rows) for column in zip(*rows)]
  out = {(1, None): mean[(1, None)]}
  for branch in ("inf", "arc", "cav"):
    held = None
    for tier in range(2, MAX_TIER + 1):
      here = mean.get((tier, branch))
      if here is None:
        here = held or next(mean[(t, branch)] for t in range(tier, MAX_TIER + 1) if (t, branch) in mean)
      held = [max(a, b) for a, b in zip(held, here)] if held else here
      out[(tier, branch)] = held
  return out


def scaled(values, level):
  """A level of stats: all but the troop's own level, which sets what it takes to reach the next tier: the
  same for the three of them."""
  percent = LEVEL_PERCENT[level]
  return values[:1] + [v * percent / 100 for v in values[1:]]
