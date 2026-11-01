from header_common import *
from header_dialogs import *
from header_operations import *
from coop.constants import coop_role_client
from custom_troops.constants import *

# John Blackborn, at the company's camp and in the player's towns and castles. His lines come before Native's
# first one (which only notes who is being talked to): nothing of that is needed here.
# A client has no way of making the army: the host's stands for all the players.

JOHN = [(store_conversation_troop, ":troop"), (eq, ":troop", custom_npc)]
NOT_CLIENT = [(neq, "$coop_role", coop_role_client)]


def hire_lines():
  return [[anyone|plyr, "custom_buy_many", [(call_script, "script_cf_custom_can_hire", men)], "%d." % men, "custom_bought",
           [(call_script, "script_custom_hire", men)]] for men in custom_recruits]


def branch_lines():
  """Whom the player means: the recruit is one soldier, a branch asks for its tier next."""
  lines = [[anyone|plyr, "custom_pick", [], "Recruits.", "close_window",
            [(assign, "$custom_kind", 0), (call_script, "script_custom_open", "$custom_for")]]]
  for branch, name in enumerate(("Infantry.", "Archers.", "Riders.")):
    lines.append([anyone|plyr, "custom_pick", [], name, "custom_tiers", [(assign, "$custom_branch", branch)]])
  return lines


def tier_lines():
  return [[anyone|plyr, "custom_pick_tier",
           [
             (call_script, "script_custom_tier_kind", tier),
             (call_script, "script_custom_troop", reg0, 1),
             (str_store_troop_name, s1, reg0),
             (assign, reg1, tier),
           ],
           "{s1}, tier {reg1}.", "close_window",
           [
             (call_script, "script_custom_tier_kind", tier),
             (assign, "$custom_kind", reg0),
             (call_script, "script_custom_open", "$custom_for"),
           ]] for tier in TIERS]


dialogs = [
  [anyone, "start", JOHN + [(eq, "$custom_army_made", 0), (eq, "$coop_role", coop_role_client)],
   "Sorry, there is nothing I can do for you.", "close_window", []],
  [anyone, "start", JOHN + [(eq, "$custom_army_made", 0)],
   "Good day. What brings you to me?", "custom_new", []],
  [anyone, "start", JOHN, "Good to see you, my lord.", "custom_hello", []],

  # the army is not there yet
  [anyone|plyr, "custom_new", [], "I want to raise an army of my own.", "custom_name_ask", []],
  [anyone|plyr, "custom_new", [], "Nothing. Farewell.", "close_window", []],
  [anyone, "custom_name_ask", [], "What would you like to call it? And how shall the men of each tier be known?", "custom_name_how", []],
  [anyone|plyr, "custom_name_how", [], "I will write the names myself.", "close_window",
   [(call_script, "script_custom_open", custom_screen_names)]],
  [anyone|plyr, "custom_name_how", [], "Leave the usual names.", "custom_made", [(call_script, "script_custom_army_make")]],
  [anyone, "custom_made", [(str_store_troop_name, s1, custom_holder)], "It is done: {s1} stands ready, my lord. What now?", "custom_main", []],

  # the army stands
  [anyone|plyr, "custom_hello", [], "I need to see to my own troops.", "custom_what", []],
  [anyone|plyr, "custom_hello", [], "Nothing. Farewell.", "close_window", []],
  [anyone, "custom_what", [], "Of course, my lord. What exactly do you wish to do?", "custom_main", []],
  [anyone|plyr, "custom_main", [], "Change my men's gear. Show me the equipment.", "custom_who",
   [(assign, "$custom_for", custom_screen_shop)]],
  [anyone|plyr, "custom_main", [], "Teach them new skills. Improve their stats.", "custom_who",
   [(assign, "$custom_for", custom_screen_train)]],
  [anyone|plyr, "custom_main", [], "I want to buy soldiers for the company.", "custom_buy", []],
  [anyone|plyr, "custom_main", NOT_CLIENT, "I want to rename something.", "custom_rename", []],
  [anyone|plyr, "custom_main", [], "Nothing, let us go on.", "close_window", []],

  # whose gear, or whose training
  [anyone, "custom_who", [], "Which of them, my lord?", "custom_pick", []],
  ] + branch_lines() + [
  [anyone|plyr, "custom_pick", [], "Nothing, let us go on.", "custom_what", []],
  [anyone, "custom_tiers", [], "Which tier?", "custom_pick_tier", []],
  ] + tier_lines() + [
  [anyone|plyr, "custom_pick_tier", [], "Someone else.", "custom_who", []],

  # names
  [anyone, "custom_rename", [], "What is to have a new name?", "custom_rename_what", []],
  [anyone|plyr, "custom_rename_what", [], "The army: its common name.", "close_window",
   [(call_script, "script_custom_open", custom_screen_army)]],
  [anyone|plyr, "custom_rename_what", [], "The units: their own names, such as archers.", "close_window",
   [(call_script, "script_custom_open", custom_screen_soldiers)]],
  [anyone|plyr, "custom_rename_what", [], "Nothing, let us go on.", "custom_what", []],

  # recruits
  [anyone, "custom_buy", [(assign, reg1, custom_recruit_cost)], "How many men do you want? Each one costs {reg1} dinars.", "custom_buy_many", []],
  ] + hire_lines() + [
  [anyone|plyr, "custom_buy_many", [], "Nothing, forget it.", "custom_what", []],
  [anyone, "custom_bought", [], "They are yours, my lord. Anything else?", "custom_main", []],
]


def merge(orig_dialogs):
  orig_dialogs[0:0] = dialogs
