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

# Co-op network (prototype). Roles: who this game is in a co-op session.
coop_role_single = 0
coop_role_server = 1   # world server: owns the world, rests continuously, mirrors nothing
coop_role_client = 2   # player client: world simulation off, shows the server's parties

# send_message_to_url ignores ports: each game uses its own loopback address on port 80
coop_server_url = "http://127.0.0.1"
coop_client_url = "http://127.0.0.2"

coop_net_marker = 7777          # first number of every bridge reply (failed sends have none)
coop_net_offset = 100000        # coordinates come back shifted so they are never negative
coop_net_removed = 9999         # template value meaning "this party is gone on the server"
coop_net_batch = 8              # parties per server report (URL length)
coop_net_max_entries = 28       # entries in one client reply: 3 + 4 * 28 numbers <= 128 registers
coop_net_resend_frames = 200    # trigger runs to wait for a lost reply

# Time on the map flows only while the player moves or rests: both roles rest when idle
coop_world_time_speed = 5        # rest time speed, as Native's "Wait here"
coop_client_idle_frames = 30     # map frames without moving before the client rests
coop_mirror_snap = 500           # a mirror further than this (map units * 100) jumps instead of walking

# Battles and pause
coop_net_max_numbers = 128       # the engine's registers: a reply never holds more numbers
coop_net_max_stacks = 30         # troop stacks per party sent in one message
coop_enc_max_parties = 20        # mirrors remembered around the player when an encounter starts
coop_enc_radius = 600            # map units * 100: mirrors this close may take part in the battle
coop_own_troops_frames = 120     # client trigger runs between reports of the player's own troops
coop_srv_troops_radius = 1500    # map units * 100: the server reports troops of parties this close to the puppet
slot_party_coop_sid = 300        # on a client mirror: server party id + 1 (Native party slots end at 249)
