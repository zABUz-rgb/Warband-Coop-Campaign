def merge(presentations, **unused):
  # the waiting window of a joint battle (coop/mp_campaign.py)
  from coop.mp_campaign import mp_campaign_presentations
  presentations.extend(mp_campaign_presentations)
