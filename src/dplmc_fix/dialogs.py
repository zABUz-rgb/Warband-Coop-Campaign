from header_common import *
from header_dialogs import *
from header_operations import *

# States of Native's and Diplomacy's talks where every line may fail (rule D4 of tools/check_flow.py): the talk
# would stop there with nothing to say. Each gets a last line that leads out and shows only when no other does.
STUCK_STATES = (
  "archer_challenge", "bandit_leader_1a", "bandit_leader_1b", "caravan_choose_disguise",
  "castle_guard_sneaked_intro_2", "companion_embassy_results", "companion_objection_response",
  "companion_was_dismissed", "convince_accept", "destroy_lair_quest_brief", "dplmc_chancellor_gift_ask_where",
  "dplmc_chancellor_message_lord_ask", "dplmc_companion_alliance_request_response",
  "dplmc_companion_defensive_request_response", "dplmc_companion_nonaggression_request_response",
  "dplmc_companion_trade_request_response", "dplmc_companion_war_request_response",
  "dplmc_constable_patrol_garrison_location", "dplmc_constable_recruit_select", "dplmc_constable_train_stop",
  "dplmc_minister_gift_type", "dplmc_minister_spy_kingdoms_select", "dplmc_talk_appoint_chamberlain_confirm",
  "dplmc_talk_appoint_chancellor_confirm", "dplmc_talk_appoint_confirm_yes",
  "dplmc_talk_appoint_constable_confirm", "dplmc_talk_staff", "dplmc_tavern_traveler_employee_3",
  "horseman_challenge", "lady_start", "lord_ask_pardon_terms", "lord_ask_to_ransom_prisoner_portion",
  "lord_hunt_down_fugitive_status", "lord_propose_mercenary", "lord_quest_intrigue_result", "lord_talk",
  "lord_talk_ask_location_2", "lord_talk_ask_marriage_1", "mayor_politics_assess_realm",
  "member_delegate_quest_ask_for_items", "merchant_demand", "merchant_quest_brief", "merchant_quest_explain_2",
  "minstrel_courtship_poem_teach_3", "minstrel_spouse_benefits", "political_quest_follow_on", "spouse_join",
  "village_elder_ask_set_fire", "village_elder_ask_set_fire_4", "village_elder_recruit_decision",
)
LEAVE_TEXT = "Let us speak of this another time."
REPEATING = 0x7000 # the bits of repeat_for_factions and the like


def leave_lines(dialogs):
  lines = []
  for state in STUCK_STATES:
    here = [d for d in dialogs if d[1] == state]
    if any(not d[0] & plyr for d in here): # last of a state, so it speaks only when no other line does
      lines.append([anyone, state, [], LEAVE_TEXT, "close_window", []])
    choices = [d for d in here if d[0] & plyr]
    if choices:
      none_holds = []
      if not any(d[0] & REPEATING for d in choices): # the others can be asked; a list that repeats keeps a way out
        none_holds = [(assign, ":any", 0)]
        for d in choices:
          none_holds += [(try_begin)] + list(d[2]) + [(assign, ":any", 1), (try_end)]
        none_holds.append((eq, ":any", 0))
      lines.append([anyone|plyr, state, none_holds, LEAVE_TEXT, "close_window", []])
  return lines


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
  dialogs += leave_lines(dialogs)
