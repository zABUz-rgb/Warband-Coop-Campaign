# A translation keeps a menu option's text by the option's id, so options sharing an id all show one
# text: in Russian every step of Diplomacy's sneaking into a town read "Continue...". These get their
# own ids. An id means nothing else to the game: saves and the options' code do not change.
OWN_IDS = [
  ("dplmc_choose_disguise", "Choose up to {reg1} items to bring.", "dplmc_disguise_items"),
  ("dplmc_choose_disguise", "Select how much gold to carry.", "dplmc_disguise_gold"),
  ("dplmc_choose_disguise", "Attempt to sneak in...", "dplmc_disguise_sneak"),
  ("dplmc_preferences", "{reg0?En:Dis}able NPC complaints.", "dplmc_npc_complaints"),
  ("village", "Demand to meet the family of {s50}.", "dplmc_village_fugitive_family"),
  ("center_improve", "Insufficient fund in the treasury.", "dplmc_improve_no_treasury"),
  ("dplmc_notification_appoint_chamberlain", "Proceed without chamberlain.", "dplmc_appoint_no_chamberlain"),
  ("dplmc_notification_appoint_constable", "Proceed without constable.", "dplmc_appoint_no_constable"),
  ("dplmc_notification_appoint_chancellor", "Proceed without chancellor.", "dplmc_appoint_no_chancellor"),
  ("notification_lady_requests_visit", "Tell the woman to inform her mistress that you will come shortly", "lady_visit_come"),
  ("notification_lady_requests_visit", "Tell the woman to inform her mistress that you are indisposed", "lady_visit_decline"),
  ("garden", "Wait by the spring", "garden_wait_spring"),
  ("camp_recruit_prisoners", "Go back.", "recruit_prisoners_back"),
  ("start_phase_2_5", "Go find an inn...", "start_find_inn"),
  ("establish_court", "Hold off...", "establish_court_hold_off"),
]


def merge(game_menus, **unused):
  from coop_merge import MergeError, menu_options
  for menu, text, option_id in OWN_IDS:
    options = menu_options(game_menus, menu)
    found = [i for i, o in enumerate(options) if o[2] == text]
    if len(found) != 1:
      raise MergeError(f"dplmc_fix: expected one option '{text}' in {menu}, found {len(found)}")
    options[found[0]] = (option_id,) + tuple(options[found[0]][1:])
