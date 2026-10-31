from header_operations import eq, neq


def _build_id():
  """A number for this build of CoopWorld: the same sources give the same number. Games tell it to
  the bridge, which warns when a friend runs another build than the host (install the same package)."""
  import os, zlib
  src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  crc = 0
  for part in ("coop", "dplmc_fix", "freelancer"):  # CoopWorld's own layers over Diplomacy
    folder = os.path.join(src, part)
    for name in sorted(os.listdir(folder)):
      if name.endswith(".py"):
        with open(os.path.join(folder, name), "rb") as f:
          crc = zlib.crc32(f.read(), crc)
  return crc % 1000000000


coop_build_id = _build_id()

# Field-battle preparation: seconds during which enemy teams are neutral to everyone
coop_battle_prep_seconds = 10

# World pace: party speed in percent (100 = Native)
coop_world_speed_percent = 100

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
slot_agent_coop_x = 41           # a storming bot: where it stood at the last look (cm)
slot_agent_coop_y = 42
slot_agent_coop_still = 43       # seconds it has stood there without an enemy near
slot_agent_coop_ladder = 44      # the ladder it is sent to + 1, 0 none
slot_agent_coop_tries = 45       # ladders it was sent to so far
coop_mp_storm_still_s = 8        # a storming bot standing this long without a fight is sent to a ladder
coop_mp_storm_walk_s = 20        # one that has not reached its ladder in this time tries the next
coop_mp_ladders_s = 30           # a ladder found down (pushed off the wall) is raised again this often
slot_troop_coop_mp_hp = 300      # on the battle server: a hero's or companion's hit points from the campaign
slot_troop_coop_mp_hp_max = 301  # and its most hit points (0: not from the campaign)
coop_mp_heroes_slot = 950        # on the battle server: the player number of each borrowed hero troop
coop_mp_pairs_slot = 900         # on the battle server: the players' sides of the coming battle (player, team)*n
coop_mp_switch_wait = 3          # seconds after a new battle mission starts before the sides are set
coop_mp_resend_ms = 3000
coop_mp_confirm_wait_s = 3        # seconds a team pick waits for the server's word before it counts
coop_hold_alive = 30              # world requests a reply of the bridge keeps this game known as the host's own
coop_profile_chunk = 50           # profile numbers sent with one client request
coop_profile_ask_frames = 400     # client trigger runs before asking again for the kept hero (the answer got lost)
coop_profile_period_frames = 3000 # client trigger runs between writing the hero down (about a minute)         # the waiting window asks the bridge again after this long without a reply

coop_net_marker = 7777          # first number of every bridge reply (failed sends have none)
coop_net_offset = 100000        # coordinates come back shifted so they are never negative
coop_net_removed = 9999         # template value meaning "this party is gone on the server"
coop_net_batch_near = 6         # parties near the client's puppet per server report
coop_net_batch_far = 6          # other parties per server report, round robin (URL length)
coop_net_near_radius = 4000     # map units * 100: "near the puppet"
coop_net_max_entries = 17       # entries in one client reply: 3 + 7 * 17 numbers <= 128 registers
coop_net_resend_frames = 200    # trigger runs to wait for a lost reply
coop_net_lost_replies = 10      # client requests in a row without an answer from the host: the link is lost

# Time on the map flows only while the player moves or rests: both roles rest when idle
coop_world_time_speed = 1        # rest time speed; Native's "Wait here" uses 5, which ran the
                                 # world at about 75 game hours per real minute (bridge clock log)
coop_client_idle_frames = 30     # map frames without moving before the client rests
coop_mirror_snap = 300           # a mirror further than this (map units * 100) from the server's position
                                 # walks to that position to catch up instead of to its target
coop_mirror_jump = 1000          # further than this it jumps there at once
coop_mirror_still = 50           # a target this close to the party's position: it stays put

# Battles and pause
coop_net_max_numbers = 128       # the engine's registers: a reply never holds more numbers
coop_net_max_stacks = 30         # troop stacks per party sent in one message
coop_enc_max_parties = 20        # mirrors remembered around the player when an encounter starts
coop_enc_radius = 600            # map units * 100: mirrors this close may take part in the battle
coop_give_distance = 3          # map distance up to which troops are given from the camp menu
coop_own_troops_frames = 120     # client trigger runs between reports of the player's own troops
coop_srv_troops_radius = 1500    # map units * 100: the server reports troops of parties this close to the puppet
slot_party_coop_seen = 302       # on a client mirror: the request number of its last update from the server
slot_party_coop_gone = 303       # on a client mirror: the server dropped it while this game still needed it
coop_mirror_stale_requests = 900  # a mirror the server has not mentioned for this many requests is gone there
coop_mirror_sweep_frames = 600    # client trigger runs between looking for such mirrors
slot_party_coop_sid = 300        # on a client mirror: server party id + 1 (Native party slots end at 249)
slot_center_coop_besieger = 301  # on a client's center: the world server's party besieging it + 1, 0 none
coop_busy_timeout_frames = 60    # an encounter that never opened a menu stops counting as busy
coop_tombstone_requests = 3000   # a party the client destroyed is not mirrored again for this many requests
coop_player_stale_requests = 600 # another player's party not updated for this many requests is hidden
coop_paused_speed_percent = 1    # party speed on a player's map while another player holds the world
coop_catch_up_time_speed = 3     # rest time speed of a player whose clock is behind the world's
                                 # still (in battle or a menu): nobody moves, the map stays usable
coop_pause_reminder_frames = 600 # trigger runs between "the world is paused" reminders

# A player's hero in a joint battle: equipment, attributes, combat skills, proficiencies
# (campaign -> bridge -> battle server, in this order, then hit points and most hit points; 31 numbers)
coop_hero_skills = [36, 35, 34, 33, 27, 26, 25, 24, 23] # ironflesh, power strike/throw/draw, weapon master,
                                                        # shield, athletics, riding, horse archery
coop_hero_profs = 7              # wpt_one_handed_weapon .. wpt_firearm
coop_hero_items = 9              # ek_item_0 .. ek_horse
coop_hero_numbers = 9 + 4 + 9 + 7 + 2
slot_player_coop_hero = 100      # on the battle server: which borrowed troop is this player's hero, + 1
coop_mp_event_hero_stat = 140    # network event: (troop, stat code, value) so every game knows the hero's stats
slot_player_coop_hits = 110      # on the battle server: a hero's hits on enemies by weapon proficiency (+ wpt)
slot_player_coop_damage = 120    # and the damage they did (+ wpt)
slot_player_coop_health = 130    # a hero's health at the end of the battle in percent + 1 (0: not a hero)
slot_player_coop_fallen = 131    # 1: the player's hero fell in this battle and does not come back (as in the campaign)
slot_player_coop_kills = 132     # a joint event: the opponents this player's hero beat
# Joint events on the battle server: fought by the players' heroes alone, in practice gear, with no
# wounds, no spoils, nothing changing in the world. An event's number goes in the player's request,
# the battle server hears it as a mode (1 is a siege)
coop_event_arena = 1
coop_event_tournament = 2
coop_event_training = 3
coop_mp_mode_arena = 2
coop_mp_mode_tournament = 3
coop_mp_mode_training = 4
coop_event_duel = 4               # a player against a player, in their own gear: as EVENT_DUEL in tools/coop_bridge.py
coop_mp_mode_duel = 5
coop_duel_xp_win = 100
coop_duel_xp_lose = 50
coop_mp_tournament_rounds = 4     # as TOURNAMENT_ROUNDS in tools/coop_bridge.py
coop_mp_no_hero_s = 10            # a joint event with no hero left on the battle server ends after this long
coop_tournament_prize = 200       # Native's prize for winning a tournament, for every player of the team
coop_tournament_renown = 20
coop_tournament_xp = 250
coop_arena_grand_xp = 200         # Native's experience for the arena's grand prize
coop_arena_xp = 10                # and for the prizes under it (the lowest gives half)
# Prisoner Management: the chance in percent that a fallen enemy is taken prisoner, at skill 1, and
# what each further point adds (skill 0 takes none)
coop_prisoner_chance_first = 10
coop_prisoner_chance_step = 5
coop_hero_knocked_out_health = 5 # a hero who fell in a joint battle comes back to the map wounded, as in Native
# Weapon proficiency from a joint battle, as Native raises it in battle: for each kind of weapon used,
# (damage + coop_wpt_hit_bonus * hits) * coop_wpt_gain / (proficiency + coop_wpt_softness) points, so
# a weapon already mastered grows slowly; the engine still keeps it within the weapon master limit
coop_wpt_hit_bonus = 10
coop_wpt_gain = 3
coop_wpt_softness = 60

# What a joint battle of the map is about ($coop_mp_kind; KIND_... in tools/coop_bridge.py); 0 an ordinary one
coop_kind_lair = 1
coop_kind_caravan = 2
coop_kind_village = 3
coop_village_militia = 15         # villagers who take up arms beside the players against raiders
coop_village_relation = 3         # what a village beaten free of raiders thinks of who led the defence

# Players together (coop/together.py)
slot_party_coop_mark = 304        # on a mark on the map: its player's slot + 1
slot_party_coop_fights = 305      # on a client's mirror: the world party it fights there + 1 (mirrors fight nobody here)
coop_store_items = 120            # as SHARED_ITEMS in tools/coop_bridge.py; the loot screen holds fewer
coop_store_chunk = 25             # items of the party store sent with one request
coop_resend_requests = 20         # requests before a word nobody answered goes again
coop_follow_near = 2              # map distance at which a player riding after another is there
coop_follow_stuck_frames = 300    # map frames a party that should ride stands still: it jumps there instead
coop_follow_word_stop = 100       # $coop_follow_send: "I ride alone"; 1 to 4 the player ridden after + 1
coop_follow_end_asked = 0         # why a ride ended (the log's note)
coop_follow_end_click = 1
coop_follow_end_gone = 2
coop_follow_end_arrived = 3
coop_ping_slack = 5               # map frames that may run after an encounter began, before its menu opens
coop_signal_message = 0           # how a call to battle reached the player: a message and a sound
coop_signal_menu_opened = 1       # its menu opened over a town's or the camp's
coop_signal_map = 2               # its menu opened on the map
coop_tell_followed = 1            # kind 27 replies: as TELL_... in tools/coop_bridge.py
coop_tell_unfollowed = 2
coop_tell_mark = 3
coop_tell_gold = 4
coop_tell_store = 5
coop_tell_left = 6
coop_note_cap = 16                # notes for the bridge's log kept while no request can carry them
coop_note_prisoners = 1           # as GAME_NOTES in tools/coop_bridge.py
coop_note_troops_xp = 2
coop_note_arena = 3
coop_note_tournament = 4
coop_note_training = 5
coop_note_tree = 6
coop_note_follow_jump = 7
coop_note_signal = 8
coop_note_lair = 9
coop_note_village = 10
coop_note_caravan = 11
coop_note_duel = 12
coop_note_follow_end = 13
