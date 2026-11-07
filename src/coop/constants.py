from header_operations import eq, neq


def _build_id():
  """A number for this build of CoopWorld: the same sources give the same number. Games tell it to
  the bridge, which warns when a friend runs another build than the host (install the same package)."""
  import os, zlib
  from coop_mods import MODS
  src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  crc = 0
  for part in MODS:  # CoopWorld's own layers over Diplomacy; with the trail it is another build
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
coop_mp_round_seconds = 7200     # a campaign battle's round has no practical time limit (1500 men come in waves)
slot_agent_coop_stack = 40       # on a bot of the multiplayer server: its stack + 1 (Native agent slots end at 28)
slot_agent_coop_x = 41           # a bot of a siege: where it stood at the last look (cm)
slot_agent_coop_y = 42
slot_agent_coop_still = 43       # seconds: it stood idle, or walked to the point it was sent to, or stood in a fight
slot_agent_coop_ladder = 44      # a storming bot: the way up the walls it went to + 1 (a ladder, a siege tower), 0 none
slot_agent_coop_calm = 45        # seconds left in which only an enemy within coop_mp_reach makes it fight (it stood at
                                 # one it could not reach: behind the bars of a gate)
slot_agent_coop_stage = 46       # a storming bot: 0 under the walls, 1 to the foot of its way up, 2 up it, 3 on the
                                 # walls (its own AI leads it), 4 to the flag
slot_agent_coop_sent = 47        # 1 while it walks to the point it was sent to (scripted), or stands at its post
coop_mp_storm_still_s = 8        # a bot of a siege standing this long with no fight goes on (up the walls, to the flag)
coop_mp_storm_walk_s = 60        # one that has not reached the foot of its way up (or the flag) by then goes another way
coop_mp_storm_climb_s = 30       # nor the top of the wall from there
coop_mp_storm_shoot_s = 40       # a storming archer shoots from where it stands this long before it climbs too
coop_mp_fight_near = 600         # cm: a storming bot with an enemy this close on its level fights it (its own AI leads)
coop_mp_hold_near = 1500         # cm: a defender fights an enemy this close on its level, else it goes back to its post
coop_mp_hold_level = 350         # cm: "on its level": this much higher or lower at most
coop_mp_reach = 300              # cm: an enemy this close is fought whatever else
coop_mp_calm_s = 30              # seconds a bot that stood at an enemy out of its reach goes its way
coop_mp_way_crowd = 1000         # cm: a way up the walls counts this much farther for every bot already going there
coop_mp_ladders_s = 30           # a ladder found down (pushed off the wall) is raised again this often
coop_mp_field_bots = 150         # bots of the campaign's armies on the field at once; the others come as reinforcements
coop_mp_field_least = 30         # a side's place on the field: never less than this (or all it has)
coop_mp_wave_pct = 25            # a side's reinforcements come once it has lost this share of its place on the field
coop_mp_wave_tell_s = 30         # a side's reinforcements are told on the server at most this often
coop_mp_ways_slot = 1000         # on the battle server (trp_temp_array_a): a siege's ways up the walls, 8 slots each:
                                 # kind (0 ladder, 1 siege tower), scene prop, foot x y z, top x y z (cm)
coop_mp_max_ways = 12
coop_mp_entries_slot = 1100      # the garrison's spawn points on this map (mp.py DEFENDER_ENTRIES)
coop_mp_crowd_slot = 1200        # the storming bots going to each way up (script_coop_mp_storm)
slot_troop_coop_mp_hp = 300      # on the battle server: a hero's or companion's hit points from the campaign
slot_troop_coop_mp_hp_max = 301  # and its most hit points (0: not from the campaign)
coop_mp_heroes_slot = 950        # on the battle server: the player number of each borrowed hero troop
coop_mp_pairs_slot = 900         # on the battle server: the players' sides of the coming battle (player, team)*n
coop_mp_spawn_wait_s = 3         # seconds a bot may keep the next ones waiting
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
coop_mirror_snap = 60            # a mirror further than this (map units * 100) from the server's position
                                 # walks to that position to catch up instead of to its target
coop_mirror_jump = 150           # further than this it jumps there at once
coop_mirror_still = 50           # a target this close to the party's position: it stays put
coop_puppet_jump = 1000          # another player's marker jumps only further than this: it knows no target

# Battles and pause
coop_net_max_numbers = 128       # the engine's registers: a reply never holds more numbers
coop_net_max_stacks = 30         # troop stacks per party sent in one message
coop_enc_max_parties = 20        # mirrors remembered around the player when an encounter starts
coop_enc_radius = 600            # map units * 100: mirrors this close may take part in the battle
coop_give_distance = 3          # map distance up to which troops are given from the camp menu
coop_trade_gold = 99999         # a trade's entry (code, value): denars, value the amount (11-07, the user's ask)
coop_trade_item = 100000        # code - this: an item, value amount * 100 + its modifier (amount 0: whole);
                                # any other code is a troop, value its count
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
coop_mp_event_hero_stat = 125    # network event: (troop, stat code, value) so every game knows the hero's stats.
                                 # Below 128 (11-07): 140 never reached the clients, as no event above 127 does (the
                                 # counter and the Retreat were the server's own player's only); Native's go up to 124
slot_player_coop_hits = 110      # on the battle server: a hero's hits on enemies by weapon proficiency (+ wpt)
slot_player_coop_damage = 120    # and the damage they did (+ wpt)
slot_player_coop_health = 130    # a hero's health at the end of the battle in percent + 1 (0: not a hero)
slot_player_coop_fallen = 131    # 1: the player's hero fell in this battle and does not come back (as in the campaign)
slot_player_coop_kills = 132     # a joint event: the opponents this player's hero beat
slot_player_coop_orders = 133    # a siege: 1 while the player leads its men by orders (the storm and the hold leave
                                 # them be); a charge gives them back
coop_mp_event_retreat = 126      # network event, a player to the battle server: its side sounds the retreat (< 128)
coop_mp_stat_campaign = 1001     # the code in coop_mp_event_hero_stat: 1 while a campaign battle runs (field or siege), 0 after
coop_mp_stat_foes = 1002        # the code in coop_mp_event_hero_stat: the opponents still standing in a joint event (-1: the counter goes)
coop_mp_stat_kills = 1003       # the same: the opponents this player beat in it
coop_mp_stat_own_side = 1004    # the same, in a battle of the campaign: troop field = this player's side standing, value = its reserve
coop_mp_stat_enemy_side = 1005  # and the other side's
slot_agent_coop_stuck = 48       # a storming bot sent to a point: seconds it stood still on the way
coop_mp_storm_nudge_s = 6        # one that stood still this long is sent there again (a new path)
coop_mp_tower_foot = 800         # cm: at a siege tower a bot this close to its foot goes up (the crowd at it waits there)
coop_mp_tower_climb_s = 60       # and has this long to get up (a crowd goes up the tower's stairs one by one)
coop_mp_tower_cap = 24           # bots going to one siege tower before it counts as crowded (a ladder: coop_mp_ladder_cap)
coop_mp_ladder_cap = 8
coop_mp_way_full = 5000          # cm: a way up counts this much farther for every bot past its cap
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
coop_mp_stat_team_event = 1000    # the code in coop_mp_event_hero_stat telling every game of $coop_mp_team_event
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
coop_truce_hours = 24 # a party that took a player prisoner leaves it alone this long after the escape
coop_truce_battle_hours = 6 # and the party a player fought in a joint battle, this long after it
coop_beaten_hours = 24            # the host: a party beaten in a joint battle is no lord's foe for so long (its removal comes later)
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
coop_kind_bandits = 4             # bandits who took a village: no party of the world, its game names them
coop_village_militia = 15         # villagers who take up arms beside the players against raiders
coop_village_relation = 3         # what a village beaten free of raiders thinks of who led the defence

# Players together (coop/together.py)
slot_center_coop_bandits = 306    # what this game last heard of a village's bandits: said once
slot_party_coop_mark = 304        # on a camp on the map: the slot it came in + 1
slot_party_coop_mine = 307        # and whose: 1 this player's own, 2 the host's, 0 another player's
coop_base_slot = coop_max_players # a player's camp goes to the games in the slots after the players'
                                  # (BASE_SLOT in tools/coop_bridge.py): each camp keeps its own
coop_base_tag = coop_base_slot + 1 # and the lowest slot_party_coop_mark
coop_base_cost = 1000             # denars it takes to set the camp up
coop_blackborn = "trp_tutorial_trainer" # John Blackborn: a new troop would change what a save holds, so he
                                  # is the spare hero of Native's old tutorial, named by script_coop_blackborn_ready
slot_party_coop_fights = 305      # on a client's mirror: the world party it fights there + 1 (mirrors fight nobody here)
coop_store_items = 120            # as SHARED_ITEMS in tools/coop_bridge.py; the loot screen holds fewer
coop_store_chunk = 25             # items of the party store sent with one request
coop_store_asks_max = 300         # requests the party store may take to arrive in a menu
coop_resend_requests = 20         # requests before a word nobody answered goes again
coop_follow_near = 2              # map distance at which a player riding after another is there
coop_follow_stuck_frames = 30     # map frames a party that should ride stands still: it goes by steps instead
coop_follow_step = 8              # map units * 100 such a step takes a frame, a loaded party's pace (the map's
                                  # triggers run some 35 times a second)
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
coop_tell_gold = 4
coop_tell_store = 5
coop_tell_left = 6
coop_tell_base = 7
coop_tell_bandits = 8
coop_tell_save_loaded = 9
coop_tell_base_up = 10
coop_tell_save_again = 11
coop_tell_week = 12               # a, b: the mines' income and the camps' wages of a week
coop_tell_deserted = 13           # a: men who left the camps unpaid
coop_mine_cost = 2000             # denars a mine at the player's own camp costs, paid once the bridge says yes
coop_mine_pay = 10                # as MINE_PAY in tools/coop_bridge.py: denars a prisoner in it brings a week
coop_camp_men = 80                # as CAMP_MEN: men that may stay at one camp
coop_camp_info = 100              # slots of the notes' troop: what the bridge said of camp k, 4 from here + 4 * k:
                                  # a mine (1), prisoners in it, men left there, their wages a week
coop_mine_pairs = 120             # and from here the prisoners on their way to a mine, 2 slots each
coop_mine_stacks = 30             # prisoner stacks sent at once
coop_gar_slots = 200              # and from here the men left at a camp on their way back, 3 slots each
coop_gar_stacks = 90              # of them at most
coop_gar_chunk = 20               # of them sent with one request
coop_hold_tag = 1000              # slot_party_coop_mark of the party holding a camp's men while they are shown:
                                  # no camp (camps are coop_base_tag up to it), no party of the world

# Trade caravans of the players (coop/caravans.py)
coop_tell_caravan_off = 14        # kind 27: as TELL_CARAVAN_... in tools/coop_bridge.py
coop_tell_caravan_home = 15
coop_tell_caravan_lost = 16
coop_tell_caravan_disbanded = 17
coop_cv_fee_near = 0              # denars a caravan for the towns nearby costs (free since 11-05, the user's wish)
coop_cv_fee_round = 0             # and one round the world (free too)
coop_cv_towns_near = 5            # towns each rides to
coop_cv_towns_round = 18
coop_cv_near_towns = 6            # the one nearby trades among the towns nearest its first
coop_cv_cargo_near = 30           # units of a good each buys at once
coop_cv_cargo_round = 60
coop_cv_spread = 10               # per cent a caravan pays over a town's price, and gets under it
coop_cv_pairs = 480               # slots of the notes' troop: the guards of a caravan sent off, 2 each
coop_cv_stacks = 30               # of them at most
coop_cv_ends = 540                # and (the host's game) from here the caravans home, waiting to be counted:
coop_cv_end_size = 124            # token, denars, n, (troop, count, level, wage) * n each
coop_cv_ends_max = 4
slot_party_coop_cv_token = 320    # on a caravan of the players (the host's game): its bridge token
slot_party_coop_cv_owner = 321    # its player's slot + 1
slot_party_coop_cv_type = 322     # 1 the towns nearby, 2 round the world
slot_party_coop_cv_towns = 323    # towns still to ride to
slot_party_coop_cv_good = 324     # the good it carries
slot_party_coop_cv_qty = 325      # and how much
slot_party_coop_cv_target = 326   # the town it rides to
slot_party_coop_cv_enemies = 327  # the kingdoms at war with its owner, one bit each
slot_party_coop_cv_gold = 328     # denars it carries
slot_party_coop_cv_home = 329     # the first town it rode to
# a friend in a talk, a menu or a trade no longer pauses the world (11-07): the host's game holds only the party met
coop_mp_joiners_max = 8           # parties nearby that may join a joint battle (Native's rules, 11-07)
coop_mp_join_lord_reach = 5       # map distance: a lord this close joins (Native: 4..7 by day)
coop_mp_jt_max = 8                # parties whose men a battle's start tells the bridge (&mpjt, URL length)
coop_mp_jt_stacks = 10            # stacks of each
coop_mp_join_bandit_reach = 3     # bandits (Native: 3 by day)
coop_storm_wait_hours = 6         # an assault of the world's besiegers waits this long for the players at its walls
coop_storm_near = 3               # map distance: a player this close to a town or castle is at its walls
slot_center_coop_storm_since = 345  # on a town or castle (the host's game): the hour + 1 its assault began to wait
slot_center_coop_storm_told = 346   # on a town or castle: 1 once the players heard of the assault (any game)
slot_agent_coop_rider = 49       # a siege's horseman: 1 the garrison's (out at the horse spawns, free of the hold),
                                 # 2 the attackers' (gets off its horse at the walls)
coop_mp_acav_slot = 1320          # MP_ARR: the storming horsemen's spawns of the siege map
coop_mp_dismount_near = 700       # cm: a storming horseman this close to a way up (or the flag) gets off its horse
slot_agent_coop_kite = 50        # a horse archer riding away from an enemy too close, 1 while it does (scripted)
coop_mp_steppe_hint = 1000        # a siege's map hint past this: a Khergit town (the steppe storm, 11-07)
coop_mp_cav_slot = 1300           # MP_ARR: the horse spawns of the siege map (coop_mp_siege_entries)
coop_mp_ha_near = 2200            # cm: a horse archer with arrows rides away from an enemy this close
coop_mp_ha_away = 3500            # cm: and this far from it
coop_mp_lord_wait_s = 60          # a lord's infantry holds its ground this long, unless the enemy comes near
coop_mp_lord_near = 4000          # cm: an enemy this close to a lord's held infantry: it charges
slot_party_coop_held = 340        # on a player's puppet (the host's game): the world party it meets + 1, held still
slot_party_coop_hold_bhvr = 341   # on that party: its AI behaviour before the hold, given back after
slot_party_coop_hold_object = 342 # its AI object
slot_party_coop_hold_x = 343      # its AI target position
slot_party_coop_hold_y = 344
coop_load_mark_troop = "trp_tutorial_student_4"  # a regular troop's inventory is in no save: an item given to it
coop_load_mark_item = "itm_smoked_fish"          # in this process is gone after a load, whatever came before
coop_note_cap = 16                # notes for the bridge's log kept while no request can carry them
coop_note_prisoners = 1           # as GAME_NOTES in tools/coop_bridge.py
coop_note_troops_xp = 2
coop_note_arena = 3
coop_note_tournament = 4
coop_note_training = 5
coop_note_tree = 6
coop_note_follow_step = 7
coop_note_signal = 8
coop_note_lair = 9
coop_note_village = 10
coop_note_caravan = 11
coop_note_duel = 12
coop_note_follow_end = 13
coop_note_bandits = 14

# A client's fiefs (coop/fiefs.py): a vassal of a kingdom holds centers in the host's world through a stand-in lord
coop_fief_proxy = "trp_tutorial_fighter_1"  # the stand-ins of the vassals 0 to 2 (Native's tutorial only uses them),
coop_fief_vassals = 3                     # and fighter 4 (a client's game): the host as lord of its own fiefs
coop_fief_host = "trp_tutorial_fighter_4"
coop_fief_list = 1100             # slots of the notes' troop: a fief's garrison as the bridge listed it, 2 each
coop_fief_stacks = 30             # of them at most (MAX_STACKS in tools/coop_bridge.py)
coop_fief_delta = 1220            # and what the player changed in it, 2 each, up to twice as many
coop_fief_cands = 1340            # the lordless centers a king may grant, up to coop_fief_cands_max
coop_fief_cands_max = 10
coop_fief_gifts = 1350            # the fiefs this player may give to another, up to coop_fief_gifts_max
coop_fief_gifts_max = 20
coop_fief_gift_asks = 30          # a gift nobody answers after this many words is given up
coop_fief_totals = 1400           # (the host's game) the stand-ins' rents and wages since the campaign began, 2 each
coop_fief_grants = 1410           # (the host's game) grants answered, to tell the bridge: token, done, up to 4
coop_fief_grants_max = 4
coop_fief_ring = 1500             # (the host's game) garrison changes applied: token, n, (troop, short) * n
coop_fief_ring_size = 42
coop_fief_ring_max = 4
coop_fief_short_max = 20
coop_fief_week_h = 24 * 7
coop_fief_worth = 200             # a king grants a fief to renown + relation * 20 at least this,
coop_fief_worth_more = 250        # and this much more for each fief the vassal holds already
