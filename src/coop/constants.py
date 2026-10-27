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
coop_max_players = 4   # player parties coop_puppet_1..4 (tools/coop_bridge.py MAX_PLAYERS)
coop_host_cli_every = 3         # a world server the host plays in: every 3rd request is the host's own
                                 # player request (/cli), so the others see and wait for the host
coop_role_held = 3     # world server holding the world still until a client joins; it sends no
                       # world data, so a client game that loads its save (and with it this role)
                       # does not act as a second server before it switches to client

# send_message_to_url ignores ports: each game uses its own loopback address on port 80
coop_server_url = "http://127.0.0.1"
coop_client_url = "http://127.0.0.2"
coop_mp_url = "http://127.0.0.3"      # the joint-battle multiplayer server game (host's PC)
coop_mp_marker = 7778

# Joint battles on the multiplayer server (coop/mp.py, coop/mp_campaign.py)
coop_mp_max_stacks = 60          # troop stacks of one battle, both sides
coop_mp_stride = 8               # slots per stack on the multiplayer server
coop_mp_round_seconds = 3600     # a campaign battle's round has no practical time limit
slot_agent_coop_stack = 40       # on a bot of the multiplayer server: its stack + 1 (Native agent slots end at 28)
coop_mp_resend_ms = 3000         # the waiting window asks the bridge again after this long without a reply

coop_net_marker = 7777          # first number of every bridge reply (failed sends have none)
coop_net_offset = 100000        # coordinates come back shifted so they are never negative
coop_net_removed = 9999         # template value meaning "this party is gone on the server"
coop_net_batch_near = 6         # parties near the client's puppet per server report
coop_net_batch_far = 6          # other parties per server report, round robin (URL length)
coop_net_near_radius = 3000     # map units * 100: "near the puppet"
coop_net_max_entries = 17       # entries in one client reply: 3 + 7 * 17 numbers <= 128 registers
coop_net_resend_frames = 200    # trigger runs to wait for a lost reply

# Time on the map flows only while the player moves or rests: both roles rest when idle
coop_world_time_speed = 1        # rest time speed; Native's "Wait here" uses 5, which ran the
                                 # world at about 75 game hours per real minute (bridge clock log)
coop_client_idle_frames = 30     # map frames without moving before the client rests
coop_mirror_snap = 300           # a mirror further than this (map units * 100) from the server's position
                                 # walks to that position to catch up instead of to its target
coop_mirror_jump = 2000          # further than this it jumps there at once
coop_mirror_still = 50           # a target this close to the party's position: it stays put

# Battles and pause
coop_net_max_numbers = 128       # the engine's registers: a reply never holds more numbers
coop_net_max_stacks = 30         # troop stacks per party sent in one message
coop_enc_max_parties = 20        # mirrors remembered around the player when an encounter starts
coop_enc_radius = 600            # map units * 100: mirrors this close may take part in the battle
coop_own_troops_frames = 120     # client trigger runs between reports of the player's own troops
coop_srv_troops_radius = 1500    # map units * 100: the server reports troops of parties this close to the puppet
slot_party_coop_sid = 300        # on a client mirror: server party id + 1 (Native party slots end at 249)
coop_busy_timeout_frames = 60    # an encounter that never opened a menu stops counting as busy
coop_tombstone_requests = 3000   # a party the client destroyed is not mirrored again for this many requests
coop_player_stale_requests = 600 # another player's party not updated for this many requests is hidden
coop_paused_speed_percent = 1    # party speed on a player's map while another player holds the world
                                 # still (in battle or a menu): nobody moves, the map stays usable
coop_pause_reminder_frames = 600 # trigger runs between "the world is paused" reminders

# A player's hero in a joint battle: equipment, attributes, combat skills, proficiencies
# (campaign -> bridge -> battle server, in this order; 29 numbers)
coop_hero_skills = [36, 35, 34, 33, 27, 26, 25, 24, 23] # ironflesh, power strike/throw/draw, weapon master,
                                                        # shield, athletics, riding, horse archery
coop_hero_profs = 7              # wpt_one_handed_weapon .. wpt_firearm
coop_hero_items = 9              # ek_item_0 .. ek_horse
coop_hero_numbers = 9 + 4 + 9 + 7
slot_player_coop_hero = 100      # on the battle server: which borrowed troop is this player's hero, + 1
coop_mp_event_hero_stat = 140    # network event: (troop, stat code, value) so every game knows the hero's stats
slot_player_coop_hits = 110      # on the battle server: a hero's hits on enemies by weapon proficiency (+ wpt)
slot_player_coop_damage = 120    # and the damage they did (+ wpt)
# Weapon proficiency from a joint battle, as Native raises it in battle: for each kind of weapon used,
# (damage + coop_wpt_hit_bonus * hits) * coop_wpt_gain / (proficiency + coop_wpt_softness) points, so
# a weapon already mastered grows slowly; the engine still keeps it within the weapon master limit
coop_wpt_hit_bonus = 10
coop_wpt_gain = 3
coop_wpt_softness = 60
