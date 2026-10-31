def merge(dialogs, **unused):
  from coop_merge import MergeError
  # "Of course, take care with these." leads to a state Diplomacy never wrote: the companion takes
  # the delegated quest without the goods, as with the next answer, through the state where they
  # speak (member_delegate_quest_confirm holds only the player's lines, nobody would answer)
  fixed = 0
  for i, d in enumerate(dialogs):
    if d[1] == "member_delegate_quest_ask_for_items" and d[4] == "member_delegate_quest_assess_for_items":
      d = list(d)
      d[4] = "member_delegate_quest_soldiers"
      dialogs[i] = d
      fixed += 1
  if fixed != 1:
    raise MergeError(f"dplmc_fix: expected one dialog line to member_delegate_quest_assess_for_items, found {fixed}")
