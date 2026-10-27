from header_operations import eq, neq

# Field-battle preparation: seconds during which enemy teams are neutral to everyone
coop_battle_prep_seconds = 10

# World pace: party speed in percent (100 = Native)
coop_world_speed_percent = 80

# Bandit party templates: troop stack sizes in percent (100 = Native)
coop_bandit_size_percent = 50

# Hour at which a player turned out of a town may come back
coop_dawn_hour = 6

# Mission templates that get the preparation phase
coop_prep_mission_templates = ("lead_charge", "village_attack_bandits", "village_raid")

# Link spike: how many trigger runs to wait for a lost reply.
# The bridge must listen on port 80: send_message_to_url ignores the port in the URL.
coop_link_resend_frames = 200
