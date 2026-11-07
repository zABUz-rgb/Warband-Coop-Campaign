def merge(menus):
  """The camp's men, the trade caravans, the smith and the clients' fiefs (coop/together.py, caravans.py, smith.py,
  fiefs.py)."""
  from coop.together import garrison_menus, empty_party_menus
  from coop.caravans import caravan_menus
  from coop.smith import smith_menus
  from coop.fiefs import fief_menus, fief_gift_menus
  from coop.mp_campaign import siege_actions_menus
  menus.extend(garrison_menus + caravan_menus + smith_menus + fief_menus + empty_party_menus + fief_gift_menus
               + siege_actions_menus)
