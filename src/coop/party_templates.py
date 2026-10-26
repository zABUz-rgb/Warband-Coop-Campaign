from header_parties import pf_quest_party
from coop.constants import coop_bandit_size_percent


def scaled(n):
  return max(1, (n * coop_bandit_size_percent + 50) // 100)


def merge(party_templates):
  """Bandit parties and lairs (bandit personality, not quest parties) get smaller stacks."""
  from module_party_templates import bandit_personality
  count = 0
  for i, pt in enumerate(party_templates):
    flags, personality, stacks = pt[2], pt[5], pt[6]
    if personality != bandit_personality or flags & pf_quest_party or not stacks:
      continue
    new_stacks = []
    for st in stacks:
      st = list(st)
      st[1], st[2] = scaled(st[1]), scaled(st[2])
      new_stacks.append(tuple(st))
    party_templates[i] = pt[:6] + (new_stacks,) + pt[7:]
    count += 1
  if count == 0:
    from coop_merge import MergeError
    raise MergeError("no bandit party templates found")
