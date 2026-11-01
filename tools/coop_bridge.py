"""Warband Coop Campaign bridge: links the world server game and up to MAX_PLAYERS player games.

Warband talks to it with send_message_to_url, which always uses port 80 and ignores any port in
the URL, so each game on one PC has its own loopback address:

    world server game   -> http://127.0.0.1/srv...   (on the host's PC)
    a player's game     -> http://127.0.0.2/cli...   (on every player's PC, the host's too)
    battle server game  -> http://127.0.0.3/mp...    (on the host's PC: a multiplayer server of the
                           Warband Coop Campaign module, game type Battle, where joint battles are fought)

Modes:
    host  the hub, on the host's PC: serves the world server game, the host's own player game and
          the other players, whose relays connect over TCP (a LAN, or a virtual LAN such as
          Radmin VPN or ZeroTier) with a shared key.
    join  a relay, on a friend's PC: forwards its player game's requests to the hub, and can
          fetch the host's newest save first.

The battle relay: a friend's second Warband window finds the battle server on its own PC, at
127.0.0.1:7240, in its server list (Local area network, with look_for_server_on_this_machine = 1 in
Warband's rgl_config.txt; the list cannot take an address typed in); the friend's bridge sends its datagrams to the host's bridge
(UDP, the relays' port), which hands them to the battle server from the host's own local address.
Warband lets players from a local network (192.168.x, 10.x) in at once but checks the others
against the internet address its authorization server saw, so a friend coming straight over a
virtual network (Radmin's 26.x) was turned away: "invalid authorization number".

    python tools/coop_bridge.py host --key SECRET [--listen 0.0.0.0:7350] [--mp-name NAME]
    python tools/coop_bridge.py join HOST_IP --key SECRET [--fetch-save] [--mp-name NAME]

--mp-name: the player's name on the battle server (multiplayer profile name). Joint battles find
the player there by it, so each player's soldiers obey that player; without it, by the hero's name
(which friends who loaded the host's save share with the host).

World server -> /srv?seq=S&h=H&n=K&d=sid,tmpl,x,y,tx,ty,att;...[&c=sid,t1,n1,...][&cf=center,faction,lord,besieger+1,bandits]
                  or  /srv?seq=S&hold=1
    d: spawned parties: position, where the party is heading (tx,ty), and the party it is inside
       (a town) + 1, or 0 on the open map; c: troops of one party (or a town's or castle's garrison)
       near a player; cf: whom one center belongs to and who besieges it, round robin; h: game hours.
    reply 7777|1|pause|joins|np|slot|x|y|kingdom|...(np players)|kind|payload...
      kingdom: the faction the player serves (0: none), which the puppet takes on the server
      pause 1: a player is in an encounter, a battle or a menu: the world stands still
      joins: how many times a player game joined (a held world runs again when it changes)
      kind 0: nothing   1: battle result sid|destroyed|n|t1|n1|...|np|t1|n1|... (np: prisoners it takes)
      2: player troops slot|n|t1|n1|...   4: a center stormed in a joint siege center|kingdom
         (kingdom -1: the defenders of a joint defence fell, the besiegers' kingdom takes it)
      kind 3: player name slot, and the name as the reply's last (string) token

Player game -> /cli?seq=S&h=H&free=F&x=X&y=Y&busy=B&fac=K[&hello=1][&bye=1][&res=sid,destroyed,t1,n1,...]
                    [&pf=seq,offset,total,v1,v2,...][&pfq=1]
                    [&give=slot,t1,n1,...][&giveans=id,yes]
                    [&lg=code,a,b,c][&fl=slot+1][&bs=x,y|-][&tg=token,amount][&st=1][&sti=token,offset,total,pairs...]
                    [&ag=kind,item,...][&an=index,name][&al=kind,level][&ao=1]
                    [&me=t1,n1,...][&name=player name]
    fac: the kingdom the player serves (0: none); lord: the world party of the lord the player serves
    as a soldier (Freelancer), -1 or absent: none; pf: part of the player's hero (the profile, see
    coop/profile.py), kept by the hub in profiles.json under the player's name and sent back
    (kind 14) when that player joins again, or asks again with pfq (the answer got lost); give: offer troops to the player in slot; giveans:
    the answer to offer id (see coop/players.py);
    lg: a note for the log (GAME_NOTES below); fl: ride after the player in slot (0: stop); bs: this
    player's camp on everybody's map (-: take it down); tg: put amount denars into the shared treasury,
    or take them (negative), repeated until kind 29 answers that token; st: open the party store;
    sti: part of the party store coming back, pairs (item, modifier + 100 * amount), repeated until kind 31;
    ag, an, al: the player's own army, a kind's gear, a name (0 the army's, 1 + kind a soldier's), a kind's
    level, kept in army.json apart from any save; ao: these come from a save, and only fill what the file lacks;
    busy: not 0 from the start of an encounter until back on the map; hello: just joined; bye:
    stopped co-op; res: a battle result; me: its troops (empty: heroes only); name: last, may hold spaces;
    dbg: a client's state for the log when it goes quiet: parties, mirrors spawned, swept, Freelancer's
    state, clock (-1 ahead, 1 behind), the party its own is attached to;
    srvp=1: the host playing in the world server game itself (its party is real there, no puppet).
    A player game's triggers do not run in menus, screens and battles: it goes silent, and a player
    silent for SILENT_PAUSE_S pauses the world just like a busy one. Such a game still sends
    /tr?trs=N&tr=e1,e2,... (a debug build only: what the game did, entries N, N+1...; see src/trail)
    /pg?seq=S&hold=H (its reply handler sends the next one: the bridge holds one with hold=1 for
    PING_HOLD_S), which keeps it silent for the world: only an invitation (kind 6) comes back, else 33.
    reply 7777|2|n|sid|tmpl|x|y|tx|ty|att|...   positions of world parties (tmpl REMOVED: gone)
          7777|3|sid|n|t1|n1|...               troops of one party near the player
          7777|4|slot|x|y|troops|kingdom[|name]  another player's party, and whom it serves
          7777|5|paused|slot|why|clock              the world stands still because of player <slot>
                                                    (why: 1 in an encounter or battle, 2 in a menu);
                                                    the player's own map then stands still too, its
                                                    clock as well; clock: -1 the player's clock is
                                                    ahead of the world's (it does not rest: standing
                                                    still, it waits; moving stays free), 1 behind (it
                                                    rests faster), 0 the same time

Joint battles (the player game's waiting window adds &mp=OP&bid=B[&mpe=sid][&mpp=slot][&mpc=center][&mpt=t1,n1,...]
[&compn=N&ter=T with a start or an acceptance: the companions coming and the terrain][&comp=troop,hero...:
one companion per request after that]
[&hero=...]; hero, with a start or an acceptance: HERO_NUMBERS numbers, the hero's equipment, attributes,
combat skills, weapon proficiencies and hit points (now, at most), in the order of coop/constants.py)
[&mpx=event,param,town,fighter,bonus with a start: a joint event instead of a battle: 1 an arena, 2 a
tournament, 3 a training, 4 a duel; param: a training's opponents for each player, a duel's opponent
(slot), town: where it is held, fighter: the troop number of the first arena fighter, bonus: what the
player's bet wins, a duel's stake]
[&mpk=K with a start: 1 a bandit lair, 2 the defence of a caravan or farmers, 3 of a village]:
    OP 1 start a battle against the world party sid (mpt: its troops as the player sees them), the
    player in puppet slot, or storm the town or castle mpc (a siege: the players are team 1, the
    garrison team 0); with &mpd=1 defend that center against its besieger mpe (the players and the
    garrison team 0, the besieger and the army camped with it team 1);
    2 waiting; 3 accept an invitation; 4 decline, or cancel (the starter).
    With &mpa=sid[&mpat=t1,n1,...] (a start against a world party) the world party sid, the lord the
    player serves, fights on the players' side with its troops (mpat: as the player sees them). A
    start against the enemy of a battle still gathering joins that battle; so does a start of the
    joint event gathering. A joint event is fought by the players' heroes alone, in practice gear, on
    one side against bots; it changes nothing in the world, and starts when its players stand on
    the battle server. A duel is the challenged player's to accept, its two heroes fight each other in
    their own gear, with no bots.
    reply 7777|6|bid|type|slot|sid   an invitation from the player in slot: type 1 may join, 2 attacked,
                                     3 + event a joint event (it may be declined);
                                     sid: the world party fought (-1: a player), so the game can see
                                     whether it would fight its own allies; a duel's: the stake
          7777|7|bid|status|team["name"]   0 gathering, 1 fought on the battle server (team 0 or 1),
                                     2 cancelled or another battle is on, 3 no battle server;
                                     "name": the name the player is expected under on the battle server
          7777|8|bid|won|xp|n|troop|killed|wounded|...   the player's losses, and battle experience
          7777|9|bid|n|(wpt,hits,damage)*n   how the player's hero fought, by weapon proficiency
          7777|10|bid|health|captor            the hero's health in percent (-1: did not fight as the hero);
                                               captor: the world party that takes the defeated player prisoner, or -1
          7777|11|bid|n|(troop,count)*n        the defeated player's troops, prisoners of the winning player
          7777|12|n|(center,faction,lord,besieger+1)*n   whom centers belong to now, who besieges them
          7777|13|bid|center                   the host stormed this center: the host's game takes it as Native does
          7777|14|offset|total|n|values...    the hero kept for this player (total 0: none, a new hero)
          7777|22|name                         the hero's name: the one its player gave the launcher
          7777|23                              the host saved the game; join.bat put the file in this player's saves
          7777|25|lord|enemy                   the lord this player serves (Freelancer) fights the world
                                               party enemy (-1: no longer): join him in a joint battle
          7777|24                              to a friend's game in the host's role (it loaded the host's save):
                                               it is a copy and becomes a client
          7777|15|id|slot|n|(troop,count)*n    the player in slot offers these troops
          7777|16|id|accepted|n|(troop,count)*n   how this player's offer went (declined: they come back)
          7777|21|bid|n|(troop,count)*n        the player's share of the fallen enemies, to loot
          7777|26|bid|event|won|value|bonus|town|n|(troop,count)*n   a joint event ended: an arena's value is
                                               the opponents beaten; a tournament's the rounds won (bonus: what
                                               the bets won); a training's the share of the opponents beaten in
                                               percent (bonus: opponents for each player, town: the players;
                                               the pairs: the opponents); a duel's won: 1 won, 0 lost, 2 a draw,
                                               its value the stake
          7777|27|code|slot|a|b                news about the player in slot (TELL_... below)
          7777|28|n|(slot,x,y,mine)*n          the players' camps on the map (mine: 1 this player's own, 2 the
                                               host's, 0 another's)
          7777|29|token|delta|balance          the shared treasury: what the transfer token did to it (token 0: news)
          7777|30|offset|total|n|(item,value)*n  the party store (offset 0: from the start)
          7777|31|state|slot                   the party store: 0 in use by the player in slot, 1 saved
          7777|32|sid|enemy|on                 a world party near this player fights the party enemy (on 0: no longer)
          7777|33                              nothing (the answer to a ping)
          7777|34|index|name                   the player's own army: a name (as for an)
          7777|35|kind|n|items*n               its kind's gear
          7777|36|kind|level                   its kind's level

Battle server -> /mp?seq=S&st=PHASE&bid=B[&w=WINNER&r=i,fallen;...&hp=no,percent;...&wx=no,wpt,hits,damage;...
                  &kl=no,count;...]&pl=no~name;...
    PHASE 0 an ordinary round, 1-3 a battle of the campaign, 4 over (w: winning team, r: the bots
    each stack lost; hp: the heroes' health at the end, 0 fallen; wx: the heroes' hits and damage by
    weapon proficiency; kl: the opponents each hero beat in a joint event);
    pl: the players on the server, matched to the players of the campaign by name.
    reply 7778|0                                  nothing
          7778|2|bid|offset|n|(team,player,troop,count)*n   stacks to spawn (player: who commands them, -1 the AI)
          7778|5|bid|player|hero...               a player fights as the campaign hero (after the stacks)
          7778|6|bid|troop|hero...                a companion's gear and stats (its stack spawns it)
          7778|1|bid|stacks|mode|hint|n|(player,team)*n   start: players onto their sides, the round
                                                  restarts; mode 1 a siege (Siege game type, map by hint),
                                                  2 an arena (hint: opponents at a time), 3 a tournament
                                                  (hint: the round), 4 a training, 5 a duel
          7778|4|bid|more                         the outcome arrived; more 1: the next round of this
                                                  tournament follows

Coordinates are map units * 100, shifted by COORD_OFFSET in replies so the games only get
non-negative numbers. A reply holds at most 128 numbers (the engine's registers).
"""
import argparse
import base64
import hmac
import ipaddress
import json
import random
import secrets
import socket
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MARKER = 7777
COORD_OFFSET = 100000
REMOVED = 9999
RECENT_KEPT = 12        # a player's last requests kept, to log when it goes quiet
RECENT_SHOWN = 6
QUIET_NOTE_S = 5.0      # a player game silent this long: its last requests go to the log
MAX_PLAYERS = 4         # puppet parties coop_puppet_1..4 in the module
CENTERS_PER_REPLY = 25  # 2 + 5 * 25 numbers
RENAME_EVERY = 40      # requests between asking a game to rename its hero
PROFILE_PER_REPLY = 120 # 5 + 120 numbers
STALE_S = 15.0          # a party not reported for this long is gone, unless a sweep of the world takes longer
STALE_SWEEPS = 2.5      # a party missed by this many sweeps of the world server's reports is gone
FAR_PER_REPORT = 6      # parties of a sweep in one report of the world server (coop_net_batch_far)
GONE_MEMORY_S = 120.0   # a party reported again this soon after it went stale was not gone (logged)
SRV_SILENT_S = 2.0      # a world server quiet this long was in a menu: its parties do not age meanwhile
BUSY_TIMEOUT_S = 1200.0 # a player silent this long (crashed, or gone without bye) no longer pauses
SILENT_PAUSE_S = 1.0    # a player sends many requests a second on the map; this much silence = a menu
TOMBSTONE_S = 30.0
STATUS_EVERY = 50       # a player is reminded of the pause state this often, in case a reply was lost
TIME_AHEAD_H = 3        # a player's clock this many game hours ahead of the world's: it stops resting
TIME_BEHIND_H = 3       # this many hours behind: the player's game rests faster to catch up
TIME_EVEN_H = 1         # within this many hours either way the clocks count as caught up again
TIME_SYNC_MAX_H = 24    # further apart than this something else is wrong (another save): left alone
MAP_BATTLE_S = 6.0      # a world party reported in a map battle counts as fighting this long
NEAREST_PER_REPLY = 11
MAX_ENTRIES = 17        # parties in one reply (coop_net_max_entries)
CLOSEST_PER_REPLY = 5   # the closest ones, in every reply: they can meet the player
VIEW_RADIUS = 4000      # map units * 100: the parties a player sees on the map (coop_net_near_radius)
ROTATING_PER_REPLY = 3
REMOVALS_PER_REPLY = 3
RESULT_PAIRS = 53       # troop and prisoner pairs of one battle result: 5 + 3 * 4 + 4 + 1 + 2 * 53 <= 128  # 3 header numbers + 7 per entry must stay within 128 registers
MAX_STACKS = 30         # troop stacks per party in one message
ARMY_KINDS = 13         # the player's own army: kinds of soldier (src/custom_troops/constants.py)
ARMY_LEVELS = 3         # and the levels of stats each
ARMY_GEAR_MAX = 24      # items a kind may carry
ARMY_NAME_MAX = 40
CLOCK_WINDOW_S = 60.0   # game clock speed is measured over this much real time
NET_PORT = 7350           # the relays' TCP link, and (UDP) the battle relay
BATTLE_PORT = 7240        # the battle server's own port (Multiplayer - Host a game)
BATTLE_LOCAL = "127.0.0.1:7240"  # on a friend's PC the second window finds the battle server here
BATTLE_PLAYING = 50       # datagrams of one game's link: a game on the server, not the server list looking
BATTLE_IDLE_S = 120.0     # a battle relay link silent this long is closed
BATTLE_TAG = 8            # bytes in front of each relayed datagram that prove the key
FETCHED_MARK = "coop_campaign_fetched.txt"  # in the save folder: which file the relay wrote the host's save to
PROTOCOL = 1
SAVE_POLL_S = 2.0         # how often the hub looks for a new save of the host
RECONNECT_GRACE_S = 30.0  # a relay that lost the hub keeps its player (slot, party, battle) this long
RELAY_MISSES = 2          # replies in a row the hub did not give in time: the link is dead, reconnect
MP_MARKER = 7778
MP_ONLINE_S = 10.0      # a battle server not heard from for this long is not running
GATHER_S = 45.0         # invited players have this long to answer before the battle starts
INVITE_DIST = 4000      # map units * 100: players this close to the starter are invited
MP_MAX_BOTS = 150       # bots on the battle server; bigger armies are scaled down, losses scaled up
MP_MAX_STACKS = 60
MP_CHUNK = 30           # stacks per reply: 5 + 4 * 30 numbers
MP_MAX_HEROES = 4        # the battle server's hero troops
MP_LOST_S = 30.0        # a battle server back in an ordinary round this long after a start lost it
WOUNDED_PCT = 50        # of a player's fallen soldiers, this share is wounded rather than killed
XP_PER_ENEMY = 30       # battle experience for each fallen enemy, shared by the winning side's players;
                        # the losing side gets a third of it
MODULE_NAME = "Warband Coop Campaign"  # the module folder in Modules, and its save folder
HERO_NUMBERS = 31       # 9 equipment slots, 4 attributes, 9 combat skills, 7 proficiencies, hit points now and at most
COMPANIONS_WAIT_S = 5.0 # a battle waits this long for the starter's companions to arrive
EVENT_ARENA, EVENT_TOURNAMENT, EVENT_TRAINING = 1, 2, 3  # joint events (coop_event_... in coop/constants.py)
ARENA_FOES = 20         # opponents of a joint arena fight, for each player
ARENA_SEQUENCE = 40     # Native's arena sends this many, the weak ones first
ARENA_AT_ONCE = 3       # opponents standing at a time, for each player
TOURNAMENT_ROUNDS = 4   # rounds of a joint tournament (coop_mp_tournament_rounds)
TOURNAMENT_TEAMS = (2, 4)  # each round this many teams, picked at random
TOURNAMENT_MEN = (2, 5)    # of this many men each (more if more players stand together), fighters fill the players' team
TOURNAMENT_SIDES = (0, 1, 3, 4)  # those teams on the battle server: 0 the players', 2 is Native's spectators
EVENT_WAIT_S = 60.0     # a joint event waits this long for its players on the battle server
EVENT_DUEL = 4          # two heroes against each other: no bots, nobody hurt in earnest, a stake
KIND_LAIR, KIND_CARAVAN, KIND_VILLAGE, KIND_BANDITS = 1, 2, 3, 4  # what a joint battle is about (coop_kind_... in coop/constants.py)
KIND_NAMES = {KIND_LAIR: "lair", KIND_CARAVAN: "caravan", KIND_VILLAGE: "village", KIND_BANDITS: "bandits"}
PLAIN_TERRAINS = (2, 3) # steppe and plain: a hideout there is fought on a map with cover
LAIR_TERRAIN = 11       # the forest's: Forest Hideout
MAP_BATTLE_DIST = 1500  # map units * 100: a map battle this close to a player is told to that player
SHARED_ITEMS = 120      # things the party store holds
STORE_CHUNK = 60        # of them in one reply: 5 + 2 * 60 numbers
STORE_LOCK_S = 600.0    # a player with the store open this long without giving it back loses it
TREASURY_TOKENS = 200   # transfers remembered, so that a repeated request changes nothing
PING_HOLD_S = 0.7       # a game off the map asks this often whether it is called to a battle
TRAIL_ACK = 7779        # the whole reply to a debug build's /tr (trail_ack in src/trail/marks.py)
ALIVE_S = 3.0           # a game that pinged this recently answers, though its map does not run
TELL_FOLLOWED, TELL_UNFOLLOWED, TELL_GOLD, TELL_STORE, TELL_LEFT, TELL_BASE, TELL_BANDITS = 1, 2, 4, 5, 6, 7, 8  # kind 27
TELL_SAVE_LOADED = 9
SYNC_KEEP = 24          # the host's last saves whose heroes and treasury are kept (sync.json)
SYNC_HERO_S = 60.0      # seconds after a host's save a hero coming in still counts as written at it
BASE_SLOT = MAX_PLAYERS  # a player's camp goes out in the slots after the players' (coop_base_slot)
# what a game tells the log with &lg=code,a,b,c (coop_note_... in coop/constants.py): the name in the
# log's "together" line, and what a, b and c are
NOTE_BANDITS = 14
GAME_NOTES = {
    1: ("prisoners", ("taken", "chance", "no_room")),
    2: ("troops_xp", ("xp", "won")),
    3: ("arena", ("kills", "prize", "won")),
    4: ("tournament", ("rounds", "gold", "stake_lost")),
    5: ("training", ("ratio", "earned")),
    6: ("tree", ("troop",)),
    7: ("follow_step", ("distance",)),
    8: ("signal", ("how", "invite")),
    9: ("lair", ("won", "quest")),
    10: ("village", ("center", "won", "relation")),
    11: ("caravan", ("won",)),
    12: ("duel", ("result", "stake", "gold")),
    13: ("follow_end", ("why",)),
    14: ("bandits", ("village", "won", "relation")),
}


def parse_ints(text):
    out = []
    for v in text.split(","):
        try:
            out.append(int(v))
        except ValueError:
            return None
    return out


def parse_stacks(values):
    """[t1, n1, t2, n2, ...] -> [(t1, n1), ...], or None when malformed."""
    if values is None or len(values) % 2:
        return None
    return [(values[i], values[i + 1]) for i in range(0, len(values), 2)][:MAX_STACKS]


def flat(stacks):
    return [v for st in stacks for v in st]


class Player:
    """One player game as the hub knows it."""

    def __init__(self, cid):
        self.cid = cid
        self.slot = None        # puppet coop_puppet_<slot+1> on the server
        self.pos = None
        self.busy = False
        self.last = None        # real time of its last request
        self.recent = []        # its last requests and their replies: what it got before going quiet
        self.quiet_told = False  # its silence is in the log already
        self.requests = 0
        self.cursor = 0
        self.troops_sent = {}   # sid -> troops version this player has
        self.removed = []       # sids this player still has to drop
        self.stacks = None      # its troops not yet sent to the server
        self.stacks_last = None
        self.name = None
        self.name_pending = False
        self.rename_wait = 0    # requests until the hero's name is asked for again
        self.saves_told = None  # the host's saves this player's game was told of
        self.hero_stale = False # the host went back to a save: this game's hero waits for the game to load it
        self.build = None       # the CoopWorld build its game runs (see coop/constants.py)
        self.others_cursor = 0
        self.status_sent = None  # (paused, slot, why) this player was last told
        self.status_age = 0
        self.mp_out = []        # joint-battle replies waiting for this player
        self.on_server = False  # the host playing in the world server game: no puppet there
        self.hero = None        # the hero's equipment and stats for joint battles
        self.companions = {}    # troop -> equipment and stats, of the companions fit for this battle
        self.companions_expected = 0
        self.faction = 0        # the kingdom the player serves, 0 none
        self.centers_sent = {}  # center -> (faction, lord, besieger + 1, bandits) this player was told
        self.sent_at = {}       # sid -> this player's request that last carried its position
        self.profile_out = []   # the kept hero, in replies, after joining
        self.profile_in = None  # [seq, total, {offset: values}] the hero coming in
        self.hours = None       # its game clock, as it last reported
        self.clock = 0          # -1 its clock is ahead of the world's, 1 behind, 0 the same time
        self.clock_since = None # when it last stopped being the same time
        self.lord = -1          # the world party of the lord it serves (Freelancer), -1 none
        self.lord_told = (-1, -1)  # (lord, enemy) it was last told
        self.follows = None     # the slot of the player it rides after
        self.together_told = False  # the marks and the treasury went to its game
        self.shared_out = []    # those replies, after the first word on the world
        self.army_out = []      # (reply, text): what this game has not heard of the army
        self.fights_told = {}   # sid -> enemy: the map battles near it that it knows of
        self.pinged = None      # real time of its last ping: its game lives, off the map
        self.signal_told = None # the battle its bridge window sounded for
        self.store_in = None    # [token, {offset: values}] the party store coming back
        self.store_done = None  # the last token that came back in full


class Battle:
    """A joint battle: gathered from the campaign, fought on the battle server."""

    def __init__(self, bid, starter, now):
        self.bid = bid
        self.starter = starter
        self.state = "gathering"  # -> "loading" (stacks go to the battle server) -> "running"
        self.sides = {starter: 0}  # cid -> team; the starter's side is 0
        self.invited = set()      # cids that have not answered yet
        self.until = now + GATHER_S
        self.enemy_sid = None
        self.enemy_stacks = []
        self.center = None        # a siege: the town or castle stormed or defended
        self.defence = False      # the players hold the walls against the world's besiegers
        self.npc_stacks = []      # (team, world party, troop, count): a defence's garrison and besiegers,
                                  # or the troops of the lord the players serve
        self.ally_sid = None      # the world party of the lord fighting on the players' side
        self.player_team = 0      # the starter's side: 0 in the field, 1 storming walls
        self.stacks = []          # [team, owner cid or None, troop, count, spawned on the server]
        self.sent = 0
        self.heroes = None        # [(player number, hero numbers)] still to send, after the stacks
        self.heroes_given = set() # cids whose hero went to the battle server (at most MP_MAX_HEROES)
        self.late = []            # replies for a hero that comes while the battle runs (kinds 5 and 9)
        self.companion_data = None  # [(troop, numbers)] still to send, after the heroes
        self.hero_troops = set()  # companions in the stacks: fallen means wounded, never killed
        self.terrain = 0
        self.created = now
        self.started = None
        self.told = set()         # invited players told on the battle server to answer in the campaign
        self.event = 0            # a joint event: EVENT_ARENA, _TOURNAMENT or _TRAINING; 0 a battle of the campaign
        self.param = 0            # a training: opponents for each player
        self.town = 0             # where the event is held
        self.fighter = 0          # the troop number of the first arena fighter
        self.teams = 0            # a tournament's round: how many teams fight in it
        self.bonus = 0            # a tournament: what the bets win, for every player
        self.round = 1            # a tournament: the round being fought
        self.kills = {}           # cid -> opponents its hero beat
        self.kind = 0             # KIND_LAIR, _CARAVAN, _VILLAGE; 0 an ordinary battle
        self.no_stacks_told = False  # a duel has none, but the battle server starts anew by them

    @property
    def fighting(self):
        """1 while the players fight on the battle server (a tournament: between its rounds too)."""
        return 1 if self.state == "running" or self.round > 1 else 0


class World:
    log = staticmethod(lambda msg: None)  # run_host sets the bridge's log: joint battles are told there
    trail = staticmethod(lambda cid, query: None)  # run_host: trail.log, a debug build's game telling what it does
    trace = staticmethod(lambda role, cid, target, reply: None)  # run_host: trace.log of the requests that matter

    def __init__(self, profiles_path=None, shared_path=None):
        self.lock = threading.Lock()
        self.parties = {}       # sid -> [tmpl, x, y, last_seen, tx, ty, att]
        self.players = {}       # cid -> Player
        self.tombstones = {}    # sid -> real time a player destroyed it
        self.troops = {}        # sid -> (version, stacks), the newest known
        self.version = 0
        self.results = []       # (sid, destroyed, stacks) for the server to apply
        self.joins = 0
        self.clocks = {"srv": [], "cli": [], "cli_map": []}
        self.battle = None
        self.battle_seq = 0
        self.mp_last = None     # real time the battle server last asked
        self.mp_players = {}    # player number on the battle server -> name
        self.centers = {}       # center -> (faction, lord, besieger + 1, bandits), as the world server reports them
        self.captures = []      # (center, kingdom) stormed in joint sieges, for the server
        self.saves = 0          # the host's saves sent to the players since the bridge started
        self.last_srv = None    # when the world server last reported
        self.srv_hours = None   # the world's clock (game hours), as the world server last reported it
        self.map_battles = {}   # sid -> (sid of the party it fights, real time last reported)
        self.report_gap = 0.1   # seconds between the world server's reports, on average
        self.profiles_path = Path(profiles_path) if profiles_path else None
        self.profiles = {}      # player key (multiplayer name, or hero name) -> the hero's numbers
        self.offers = {}        # id -> (giver cid, receiver cid, stacks): troops on their way
        self.offer_seq = 0
        self.returns = {}       # player key -> stacks declined while their giver was away
        self._offer_keys = {}   # offer id -> the giver's key, for troops coming back later
        if self.profiles_path is not None and self.profiles_path.exists():
            try:
                self.profiles = json.loads(self.profiles_path.read_text("utf-8"))
            except (OSError, ValueError):
                self.profiles = {}
        self.mp_names = {}      # cid -> the name its player uses on the battle server (launcher)
        self.stats = {"srv": 0, "cli": 0, "entries_in": 0, "entries_out": 0, "results": 0,
                      "new": 0, "gone": 0, "back": 0}  # parties learnt, gone stale, back after going stale
        self.gone_at = {}       # sid -> when it went stale: one reported again soon after was alive all along
        self.captors = {}       # sid of a world party -> the players it took prisoner in a joint battle
        self.treasury_done = {} # transfer token -> what it did to the treasury
        self.store_lock = None  # (cid, since): who has the party store open
        self.shared_path = Path(shared_path) if shared_path else (
            self.profiles_path.with_name("shared.json") if self.profiles_path else None)
        # the player's own army, kept in army.json: a save loaded, or the bridge started anew, takes nothing back
        self.army_path = self.shared_path.with_name("army.json") if self.shared_path else None
        self.army = {"names": {}, "gear": {}, "levels": {}}
        if self.army_path is not None and self.army_path.exists():
            try:
                kept = json.loads(self.army_path.read_text("utf-8"))
                self.army = {part: {int(k): v for k, v in kept.get(part, {}).items()} for part in self.army}
            except (OSError, ValueError, AttributeError):
                pass
        self.army_told = {}     # kind -> items: what the battle server's game has of its gear
        # the treasury, the party store and the players' camps, kept in shared.json
        self.shared = {"gold": 0, "items": [], "bases": [None] * MAX_PLAYERS}
        if self.shared_path is not None and self.shared_path.exists():
            try:
                self.shared.update(json.loads(self.shared_path.read_text("utf-8")))
            except (OSError, ValueError):
                pass
        old_camp = self.shared.pop("base", None)
        if old_camp:  # when there was one camp for all: the host's now
            self.shared["bases"][0] = {"who": None, "host": True, "x": old_camp[0], "y": old_camp[1]}
        # the world's clock at each of the host's saves -> the heroes and the treasury as they stood then
        self.sync_path = self.shared_path.with_name("sync.json") if self.shared_path else None
        self.sync = {}
        self.sync_open = None   # (clock, until): the save the players' heroes are still coming in for
        if self.sync_path is not None and self.sync_path.exists():
            try:
                self.sync = {int(k): v for k, v in json.loads(self.sync_path.read_text("utf-8")).items()}
            except (OSError, ValueError, AttributeError):
                self.sync = {}

    # ---- players

    def _player(self, cid):
        p = self.players.get(cid)
        if p is None:
            p = self.players[cid] = Player(cid)
        if p.slot is None:
            used = {q.slot for q in self.players.values() if q.slot is not None}
            free = [s for s in range(MAX_PLAYERS) if s not in used]
            if free:
                p.slot = free[0]
                p.name_pending = p.name is not None
        return p

    def drop_player(self, cid):
        with self.lock:
            self._part_company(cid)
            self.players.pop(cid, None)
            self.mp_names.pop(cid, None)

    def _part_company(self, cid):
        """A player leaves the game: troops offered to this player go back to their giver."""
        p = self.players.get(cid)
        if p is None:
            return
        for oid, (giver, receiver, stacks) in list(self.offers.items()):
            if receiver == cid:
                del self.offers[oid]
                self._offer_answer(oid, giver, stacks, 0)
        if self.store_lock is not None and self.store_lock[0] == cid:
            self.store_lock = None
        if p.slot is not None:
            for q in self.players.values():
                if q.follows == p.slot and q is not p:
                    q.follows = None
                    q.mp_out.append([27, TELL_LEFT, p.slot, 0, 0])

    def _player_in_slot(self, slot, but=None):
        return next((q for q in self.players.values() if q.slot == slot and q is not but), None)

    def _offer_answer(self, oid, giver_cid, stacks, accepted):
        giver = self.players.get(giver_cid)
        if giver is not None:
            giver.mp_out.append([16, oid, accepted, len(stacks)] + flat(stacks))
        elif not accepted:
            # the giver left meanwhile: the troops wait for that player's return
            key = self._offer_keys.pop(oid, None)
            if key:
                self.returns.setdefault(key, []).extend(stacks)
        self._offer_keys.pop(oid, None)

    def _act(self, p, what, **fields):
        """One line for each thing the players do together: tools/coop_logs.py builds its report on them."""
        text = " ".join(f"{k}={v}" for k, v in fields.items())
        self.log(f"together {self._who(p)}: {what}{' ' + text if text else ''}")

    def _follow(self, p, target):
        """p rides after the player in slot target - 1, or alone (target 0); its game does the riding."""
        before = self._player_in_slot(p.follows, but=p) if p.follows is not None else None
        after = self._player_in_slot(target - 1, but=p) if target > 0 else None
        p.follows = after.slot if after is not None else None
        self._act(p, "follow", target=self._who(after) if after is not None else "-")
        if before is not after and p.slot is not None:
            if before is not None:
                before.mp_out.append([27, TELL_UNFOLLOWED, p.slot, 0, 0])
            if after is not None:
                after.mp_out.append([27, TELL_FOLLOWED, p.slot, 0, 0])

    def _camp_key(self, p):
        return self._profile_key(p.cid) or p.cid

    def _marks_reply(self, p):
        """The camps, the only thing on the map all games add by themselves; none takes away what a save
        still holds."""
        out = [28, 0]
        me = self._camp_key(p)
        for index, camp in enumerate(self.shared["bases"]):
            if camp:
                own = camp["who"] == me or (camp["who"] is None and p.on_server)
                out += [BASE_SLOT + index, camp["x"] + COORD_OFFSET, camp["y"] + COORD_OFFSET,
                        1 if own else 2 if camp["host"] else 0]
                out[1] += 1
        return out

    def _marks_out(self):
        for q in self.players.values():
            q.mp_out.append(self._marks_reply(q))

    def _base(self, p, where):
        """A player's camp on everybody's map, one each, kept with the treasury; where () takes it down."""
        if p.slot is None:
            return
        bases = self.shared["bases"]
        me = self._camp_key(p)
        mine = next((i for i, camp in enumerate(bases) if camp and (
            camp["who"] == me or (camp["who"] is None and p.on_server))), None)
        free = next((i for i, camp in enumerate(bases) if not camp), None)
        if (mine is not None) == bool(where) or (where and free is None):
            return
        if where:
            bases[free] = {"who": me, "host": p.on_server, "x": where[0], "y": where[1]}
            self._act(p, "base", x=where[0], y=where[1])
        else:
            bases[mine] = None
            self._act(p, "base_off")
        self._save_shared()
        self._marks_out()
        for q in self.players.values():
            if q is not p:
                q.mp_out.append([27, TELL_BASE, p.slot, 1 if where else 0, 0])

    def _save_shared(self):
        if self.shared_path is None:
            return
        try:
            tmp = self.shared_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.shared), "utf-8")
            tmp.replace(self.shared_path)
        except OSError:
            pass

    def _treasury(self, p, token, amount):
        """amount > 0 goes in (the game took it from the hero already), < 0 comes out as far as there
        is any. The game repeats the token until it hears back: the same answer, nothing moves twice."""
        if token in self.treasury_done:
            p.mp_out.append([29, token, self.treasury_done[token], self.shared["gold"]])
            return
        delta = max(amount, -self.shared["gold"])
        self.shared["gold"] += delta
        self.treasury_done[token] = delta
        while len(self.treasury_done) > TREASURY_TOKENS:
            del self.treasury_done[next(iter(self.treasury_done))]
        self._save_shared()
        self._act(p, "gold", asked=amount, moved=delta, balance=self.shared["gold"])
        p.mp_out.append([29, token, delta, self.shared["gold"]])
        if delta:
            for q in self.players.values():
                if q is not p:
                    q.mp_out.append([29, 0, 0, self.shared["gold"]])
                    if p.slot is not None:
                        q.mp_out.append([27, TELL_GOLD, p.slot, abs(delta), 1 if delta > 0 else 0])

    def _store_open(self, p, now):
        """The party store goes to p's game, and stays with p until it comes back: one at a time, or
        what two players took at once would exist twice."""
        lock = self.store_lock
        if lock is not None and lock[0] != p.cid and lock[0] in self.players and now - lock[1] < STORE_LOCK_S:
            holder = self.players[lock[0]]
            p.mp_out.append([31, 0, holder.slot if holder.slot is not None else 0])
            self._act(p, "store_refused", used_by=self._who(holder))
            return
        self.store_lock = (p.cid, now)
        items = self.shared["items"]
        self._act(p, "store_open", items=len(items) // 2)
        count = len(items) // 2
        for at in range(0, max(1, count), STORE_CHUNK):
            part = items[at * 2:(at + STORE_CHUNK) * 2]
            p.mp_out.append([30, at, count, len(part) // 2] + part)

    def _store_put(self, p, values):
        """Part of the party store comes back: (token, offset, total, pairs...); saved once all of it is here."""
        token, offset, total, pairs = values[0], values[1], values[2], values[3:]
        if token == p.store_done:
            p.mp_out.append([31, 1, p.slot if p.slot is not None else 0])
            return
        if p.store_in is None or p.store_in[0] != token:
            p.store_in = [token, {}]
        p.store_in[1][offset] = pairs
        expected, items = 0, []
        for at, part in sorted(p.store_in[1].items()):
            if at != expected:
                return
            expected += len(part) // 2
            items += part
        if expected != total:
            return
        self.shared["items"] = items[:SHARED_ITEMS * 2]
        p.store_in, p.store_done = None, token
        if self.store_lock is not None and self.store_lock[0] == p.cid:
            self.store_lock = None
        self._save_shared()
        self._act(p, "store_saved", items=len(self.shared["items"]) // 2)
        p.mp_out.append([31, 1, p.slot if p.slot is not None else 0])
        for q in self.players.values():
            if q is not p and p.slot is not None:
                q.mp_out.append([27, TELL_STORE, p.slot, len(self.shared["items"]) // 2, 0])

    def ping(self, cid, now):
        """A game off the map asks. Only an invitation comes back; the player stays silent for the
        world, which it holds as before."""
        with self.lock:
            p = self.players.get(cid)
            if p is None:
                return [33]
            p.pinged = now
            for nums in p.mp_out:
                if nums[0] == 6:
                    p.mp_out.remove(nums)
                    self._act(p, "invite_off_map", battle=nums[1], type=nums[2])
                    return nums
            return [33]

    def signal_text(self, cid):
        """The call to a battle for the bridge's window of this player, once; None without one."""
        with self.lock:
            b, p = self.battle, self.players.get(cid)
            if b is None or p is None or b.state != "gathering" or cid not in b.invited or p.signal_told == b.bid:
                return None
            p.signal_told = b.bid
            starter = self.players.get(b.starter)
            self._act(p, "signal_bridge", battle=b.bid)
            return (f"*** {starter.name if starter is not None and starter.name else '?'} зовёт в бой "
                    f"(calls you to a battle) ***")

    def _map_battle_news(self, p):
        """A world party near this client fights: a client's mirrors fight nobody, so it hears of it
        here. One change a request; the host's own game sees the world's battles itself."""
        if p.on_server or p.pos is None:
            return None
        near = {}
        for sid, (enemy, _) in self.map_battles.items():
            party = self.parties.get(sid)
            if party is not None and (party[1] - p.pos[0]) ** 2 + (party[2] - p.pos[1]) ** 2 <= MAP_BATTLE_DIST ** 2:
                near[sid] = enemy
        for sid, enemy in sorted(p.fights_told.items()):
            if near.get(sid) != enemy:
                del p.fights_told[sid]
                return [32, sid, enemy, 0]
        for sid, enemy in sorted(near.items()):
            if sid not in p.fights_told:
                p.fights_told[sid] = enemy
                return [32, sid, enemy, 1]
        return None

    def _together(self, p, together, now):
        """What the players do together on the map (coop/players.py, coop/together.py)."""
        if together.get("give") is not None:
            slot, stacks = together["give"]
            receiver = self._player_in_slot(slot, but=p)
            if receiver is None:
                p.mp_out.append([16, 0, 0, len(stacks)] + flat(stacks))  # nobody there: back
            elif stacks:
                self.offer_seq += 1
                self.offers[self.offer_seq] = (p.cid, receiver.cid, stacks)
                self._offer_keys[self.offer_seq] = self._profile_key(p.cid)
                receiver.mp_out.append([15, self.offer_seq, p.slot, len(stacks)] + flat(stacks))
        if together.get("giveans") is not None:
            oid, yes = together["giveans"]
            offer = self.offers.get(oid)
            if offer is not None and offer[1] == p.cid:
                del self.offers[oid]
                self._offer_answer(oid, offer[0], offer[2], 1 if yes else 0)
        if together.get("note") is not None:
            code, *values = together["note"]
            name, fields = GAME_NOTES.get(code, (f"note{code}", ("a", "b", "c")))
            self._act(p, name, **dict(zip(fields, values)))
            if code == NOTE_BANDITS and values[1] == 1 and p.slot is not None:
                # a village is free: the host's game holds the world, the others hear of it
                for q in self.players.values():
                    if q is not p:
                        q.mp_out.append([27, TELL_BANDITS, p.slot, values[0], 0])
        saved = together.get("army_saved", False)
        if together.get("army_name") is not None:
            self._army_name(p, *together["army_name"], saved)
        if together.get("army_gear") is not None:
            self._army_gear(p, *together["army_gear"], saved)
        if together.get("army_level") is not None:
            self._army_level(p, *together["army_level"], saved)
        if together.get("follow") is not None:
            self._follow(p, together["follow"])
        if together.get("base") is not None:
            self._base(p, together["base"])
        if together.get("treasury") is not None:
            self._treasury(p, *together["treasury"])
        if together.get("store_open"):
            self._store_open(p, now)
        if together.get("store_put") is not None:
            self._store_put(p, together["store_put"])

    def host_saved(self, now=None):
        """The host saved the game (and the relays got the file): each player's game is told and writes its
        hero down. The heroes and the treasury are kept with that save, by the world's clock."""
        with self.lock:
            self.saves += 1
            hours = self.srv_hours
            if hours is not None:
                self.sync.pop(hours, None)  # the newest stands last
                self.sync[hours] = json.loads(json.dumps({"profiles": self.profiles, "shared": self.shared}))
                while len(self.sync) > SYNC_KEEP:
                    del self.sync[next(iter(self.sync))]
                self.sync_open = (hours, (time.time() if now is None else now) + SYNC_HERO_S)
                self._save_sync()

    def _save_sync(self):
        if self.sync_path is None:
            return
        try:
            tmp = self.sync_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.sync), "utf-8")
            tmp.replace(self.sync_path)
        except OSError:
            pass

    def _clock_reported(self, hours):
        """The world's clock from the host. Gone back, or heard for the first time since the bridge started:
        a save was loaded, and the heroes and the treasury go back to that save with it. A game still in
        the session is told to load it too; until then what it writes of its hero counts for nothing."""
        known, self.srv_hours = self.srv_hours, hours
        if known is not None and hours >= known:
            return
        kept = self.sync.get(hours)
        if kept is None:
            if known is not None:
                self.log(f"the host went back to hour {hours}: no save kept for it, the heroes stay as they are")
            return
        kept = json.loads(json.dumps(kept))
        self.profiles = kept["profiles"]
        self.shared = kept["shared"]
        self.sync_open = None
        self._save_profiles()
        self._save_shared()
        self.log(f"the host's save of hour {hours}: the heroes and the treasury are back to it")
        for q in self.players.values():
            if not q.on_server:
                q.hero_stale = True
                q.mp_out += [[27, TELL_SAVE_LOADED, 0, 0, 0], self._marks_reply(q), [29, 0, 0, self.shared["gold"]]]

    def set_mp_name(self, cid, name):
        name = " ".join((name or "").split())[:40]
        with self.lock:
            if name:
                self.mp_names[cid] = name
            else:
                self.mp_names.pop(cid, None)

    def paused(self, now):
        return self.pause_cause(now) is not None

    def pause_cause(self, now, but=None):
        """(slot, why) of a player holding the world still, other than `but`, or None.
        why: 1 in an encounter or battle, 2 silent (a menu, a screen, loading)."""
        for p in sorted(self.players.values(), key=lambda q: (q.slot is None, q.slot)):
            if p.slot is None or p.last is None or p is but:
                continue
            silent = now - p.last
            if silent < BUSY_TIMEOUT_S and (p.busy or silent > SILENT_PAUSE_S):
                return p.slot, 1 if p.busy else 2
        return None

    # ---- server

    def server_report(self, entries, troops, now, hold=False, center=None, hours=None, battles=()):
        """Returns (pause, joins, [(slot, x, y)], payload numbers, name string or None).
        battles: (sid, sid of the party it fights) of world parties in a map battle."""
        with self.lock:
            self.stats["srv"] += 1
            if hours is not None:
                self._clock_reported(hours)
            for sid, enemy in battles:
                self.map_battles[sid] = (enemy, now)
                self.map_battles[enemy] = (sid, now)
            for sid in [s for s, (_, when) in self.map_battles.items() if now - when > MAP_BATTLE_S]:
                del self.map_battles[sid]
            # the world server was silent (its game in a menu, or a joint battle on): the world stood
            # still, so its parties did not go stale meanwhile
            gap = now - self.last_srv if self.last_srv is not None else 0.0
            self.last_srv = now
            if gap > SRV_SILENT_S:
                for party in self.parties.values():
                    party[3] += gap
            elif gap > 0:
                self.report_gap += (gap - self.report_gap) * 0.05
            for sid in [s for s, when in self.tombstones.items() if now - when > TOMBSTONE_S]:
                del self.tombstones[sid]
            for entry in entries:
                sid, tmpl, x, y, *rest = entry
                tx, ty, att = (rest + [x, y, 0][len(rest):])[:3]  # no target: stays put; no att: open map
                if sid in self.tombstones:
                    continue  # destroyed by a player; the server has not caught up yet
                if sid not in self.parties:
                    self.stats["back" if now - self.gone_at.pop(sid, -GONE_MEMORY_S) < GONE_MEMORY_S else "new"] += 1
                self.parties[sid] = [tmpl, x, y, now, tx, ty, att]
                self.stats["entries_in"] += 1
                for p in self.players.values():
                    if sid in p.removed:
                        p.removed.remove(sid)
            if hold:
                # the world is held and the server sends no parties: nothing goes stale meanwhile
                for party in self.parties.values():
                    party[3] = now
            # 500 parties take the world server longer than STALE_S to report: alive ones went
            # "gone" and came back (279 times in 40 minutes), their mirrors with them
            stale = max(STALE_S, STALE_SWEEPS * self.report_gap * len(self.parties) / FAR_PER_REPORT)
            for sid in [s for s, party in self.parties.items() if now - party[3] > stale]:
                self._forget(sid, except_cid=None)
                self.stats["gone"] += 1
                self.gone_at[sid] = now
            for sid in [s for s, when in self.gone_at.items() if now - when > GONE_MEMORY_S]:
                del self.gone_at[sid]
            if center is not None:
                self.centers[center[0]] = tuple(center[1:])
            if troops is not None:
                sid, stacks = troops
                # until the server applied a battle result, its report is older than the player's
                if all(r[0] != sid for r in self.results) and self.troops.get(sid, (0, None))[1] != stacks:
                    self.version += 1
                    self.troops[sid] = (self.version, stacks)
            puppets = [(p.slot, p.pos[0], p.pos[1], p.faction) for p in self.players.values()
                       if p.slot is not None and p.pos is not None and not p.on_server]
            name = None
            pending_troops = [p for p in self.players.values() if p.slot is not None and p.stacks is not None]
            pending_names = [p for p in self.players.values() if p.slot is not None and p.name_pending]
            if self.results:
                sid, destroyed, stacks, *rest = self.results.pop(0)
                prisoners = (rest[0] if rest else [])[:max(0, RESULT_PAIRS - len(stacks))]
                payload = [1, sid, destroyed, len(stacks)] + flat(stacks) + [len(prisoners)] + flat(prisoners)
            elif self.captures:
                payload = [4, *self.captures.pop(0)]
            elif pending_troops:
                p = pending_troops[0]
                payload = [2, p.slot, len(p.stacks)] + flat(p.stacks)
                p.stacks = None
            elif pending_names:
                p = pending_names[0]
                payload, name = [3, p.slot], p.name
                p.name_pending = False
            else:
                payload = [0]
            host = next((p for p in self.players.values() if p.on_server), None)
            return self.pause_cause(now, but=host) is not None, self.joins, puppets, payload, name

    def _forget(self, sid, except_cid):
        """The party is gone: every player (but the one that removed it already) drops it."""
        if sid in self.captors:
            self.log(f"party {sid} is gone, the captor of {', '.join(sorted(self.captors.pop(sid)))}")
        self.parties.pop(sid, None)
        self.troops.pop(sid, None)
        for p in self.players.values():
            p.troops_sent.pop(sid, None)
            if p.cid != except_cid and sid not in p.removed:
                p.removed.append(sid)

    # ---- players' requests

    def _record_result(self, result, cid, now):
        """A battle changed a world party: the server applies it, the players see it at once."""
        self.results.append(result)
        self.stats["results"] += 1
        sid, destroyed, stacks = result[:3]
        if destroyed:
            self._forget(sid, except_cid=cid)
            self.tombstones[sid] = now
        else:
            # after a battle the player's view is what the party has now
            self.version += 1
            self.troops[sid] = (self.version, stacks)
            if cid in self.players:
                self.players[cid].troops_sent[sid] = self.version

    def _profile_key(self, cid):
        """Whose hero: the player's name for the battle server (given to the launcher, unique), else
        the hero's name."""
        q = self.players.get(cid)
        key = self.mp_names.get(cid) or (q.name if q is not None else None)
        return " ".join(key.lower().split()) if key else None

    def _profile_part(self, p, part, now):
        """A part of the player's hero: keep it once all of it arrived, with the host's last save if it is
        the answer to that."""
        if p.hero_stale:
            return
        seq, offset, total, values = part[0], part[1], part[2], part[3:]
        if p.profile_in is None or p.profile_in[0] != seq or p.profile_in[1] != total:
            p.profile_in = [seq, total, {}]
        p.profile_in[2][offset] = values
        got = sorted(p.profile_in[2].items())
        flat_values = [v for _, vals in got for v in vals]
        expected = 0
        for off, vals in got:
            if off != expected:
                return
            expected += len(vals)
        key = self._profile_key(p.cid)
        if expected == total and key:
            self.profiles[key] = flat_values
            p.profile_in = None
            self._save_profiles()
            if self.sync_open and now <= self.sync_open[1] and self.sync_open[0] in self.sync:
                self.sync[self.sync_open[0]]["profiles"][key] = flat_values
                self._save_sync()

    def _save_profiles(self):
        if self.profiles_path is None:
            return
        try:
            tmp = self.profiles_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.profiles), "utf-8")
            tmp.replace(self.profiles_path)
        except OSError:
            pass

    def _army_save(self):
        if self.army_path is None:
            return
        try:
            tmp = self.army_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.army), "utf-8")
            tmp.replace(self.army_path)
        except OSError:
            pass

    def _army_tell(self, p, word):
        self._army_save()
        for q in self.players.values():
            if q is not p:
                q.army_out.append(word)

    def _army_name(self, p, index, text, saved=False):
        """The host names its army (0) or a soldier (1 + kind): the other games hear it. saved: what a save
        held when its session began, which only fills a gap (so for the other two)."""
        if p.on_server and text and not (saved and index in self.army["names"]):
            self.army["names"][index] = text
            self._army_tell(p, ([34, index], text))

    def _army_gear(self, p, kind, items, saved=False):
        """What a soldier carries, whoever chose it: the other games hear it, the battle server when it asks."""
        if not (saved and kind in self.army["gear"]):
            self.army["gear"][kind] = items
            self._army_tell(p, ([35, kind, len(items)] + items, None))

    def _army_level(self, p, kind, level, saved=False):
        """The level a kind was taught, whoever paid for it. It never falls."""
        if level > self.army["levels"].get(kind, 1) and not (saved and kind in self.army["levels"]):
            self.army["levels"][kind] = level
            self._army_tell(p, ([36, kind, level], None))

    def _army_replies(self):
        """All of the army, for a game that comes in."""
        names = [([34, index], text) for index, text in sorted(self.army["names"].items())]
        return (names + [([35, kind, len(items)] + items, None) for kind, items in sorted(self.army["gear"].items())]
                + [([36, kind, level], None) for kind, level in sorted(self.army["levels"].items())])

    def player_request(self, cid, x, y, busy, result, me, now, hello=False, bye=False, name=None, mp=None,
                       on_server=False, faction=None, profile=None, together=None, profile_ask=False,
                       build=None, hours=None, lord=None):
        """Returns (reply numbers after the marker, trailing string or None)."""
        with self.lock:
            self.stats["cli"] += 1
            if bye:
                self._part_company(cid)
                self.players.pop(cid, None)
                return [0], None
            if on_server and cid.startswith("net"):
                # the host's own requests come from this PC; from a relay they come from a friend's
                # game that loaded the host's save (still in the host's role): it is a copy, a client
                return [24], None
            p = self._player(cid)
            p.on_server = on_server
            if build is not None and build != p.build:
                p.build = build
                host = next((q.build for q in self.players.values() if q.on_server and q.build), None)
                self.log(f"player {self._who(p)} runs CoopWorld build {build}"
                         + ("" if on_server or host is None else
                            " - the same as the host" if host == build else
                            f" - NOT the host's ({host}): install the same package on both PCs"))
            if faction is not None:
                p.faction = faction
            p.requests += 1
            p.pos = (x, y)
            p.busy = busy
            p.last = now
            if hours is not None:
                p.hours = hours
            if lord is not None:
                p.lord = lord
            if name and name != p.name:
                p.name, p.name_pending = name, True
            if hello:
                self.joins += 1
                p.together_told = False
                p.hero_stale = False
            if (hello or profile_ask) and not on_server and not p.profile_out:
                # the hero kept for this player goes back to its game, or word that there is none
                kept = self.profiles.get(self._profile_key(cid) or "", [])
                p.profile_out = [[14, off, len(kept), len(kept[off:off + PROFILE_PER_REPLY])]
                                 + kept[off:off + PROFILE_PER_REPLY]
                                 for off in range(0, len(kept), PROFILE_PER_REPLY)] or [[14, 0, 0, 0]]
            if profile is not None and not on_server:
                self._profile_part(p, profile, now)
            if together:
                self._together(p, together, now)
            if not p.together_told:
                p.together_told = True
                p.army_out = self._army_replies()
                if self.shared["gold"] or any(self.shared["bases"]) or on_server:  # a host's save may hold an old camp
                    p.shared_out = [self._marks_reply(p), [29, 0, 0, self.shared["gold"]]]
            back = self.returns.pop(self._profile_key(cid) or "", None)
            if back:
                p.mp_out.append([16, 0, 0, len(back)] + flat(back[:MAX_STACKS]))
            if result is not None:
                self._record_result(result, cid, now)
            if me is not None and me != p.stacks_last:
                p.stacks = p.stacks_last = me
            if mp is not None:
                self._mp_op(p, mp, now)
            self._battle_tick(now)
            wanted = self._mp_wanted_name(cid)
            wanted = f'"{wanted}"' if wanted else None  # quoted: a name like "1" stays a string
            if p.mp_out:
                nums = p.mp_out.pop(0)
                return nums, wanted if nums[0] == 7 else None
            if p.army_out:
                return p.army_out.pop(0)
            # the hero bears the name its player gave the launcher (join.bat, host.bat): asked for
            # until the game reports it
            given = self.mp_names.get(cid)
            if p.rename_wait > 0:
                p.rename_wait -= 1
            elif given and " ".join((p.name or "").split()) != given:
                p.rename_wait = RENAME_EVERY
                return [22], given
            if p.saves_told is None or p.on_server:
                p.saves_told = self.saves
            elif p.saves_told != self.saves:
                p.saves_told = self.saves
                return [23], None
            # whom centers belong to, as it changes (not for the host: its game is the world)
            if not p.on_server and p.requests % 5 == 3:
                news = [(c, *v) for c, v in sorted(self.centers.items()) if p.centers_sent.get(c) != v]
                if news:
                    news = news[:CENTERS_PER_REPLY]
                    for c, *v in news:
                        p.centers_sent[c] = tuple(v)
                    return [12, len(news)] + [v for entry in news for v in entry], None
            if mp is not None and mp["op"] in (1, 2, 3):
                # the waiting window: how the battle stands
                b = self.battle
                if b is not None and cid in b.sides:
                    return [7, b.bid, b.fighting, b.sides[cid]], wanted
                return [7, mp["bid"], 0, 0], wanted
            by_distance = sorted(self.parties.items(),
                                 key=lambda kv: (kv[1][1] - x) ** 2 + (kv[1][2] - y) ** 2)
            # the lord this player serves goes into battle: the player may join him (the host's
            # own game sees the lord's battle itself)
            if not p.on_server:
                fight = self.map_battles.get(p.lord) if p.lord >= 0 else None
                told = (p.lord, fight[0]) if fight else (-1, -1)
                if told != p.lord_told:
                    p.lord_told = told
                    if told[0] >= 0:
                        self.log(f"player {self._who(p)}: the lord it serves (party {told[0]}) fights party {told[1]}")
                    return [25, *told], None
            news = self._map_battle_news(p)
            if news is not None:
                return news, None
            # whether another player holds the world still: at once when it changes, and now and then
            cause = self.pause_cause(now, but=p)
            # the clocks: never a pause (a player held still kept its clock running whenever it tried
            # to move, and waited minutes); a player ahead only stops resting, one behind rests faster
            if not p.on_server and p.hours is not None and self.srv_hours is not None:
                self._clock_sync(p, p.hours - self.srv_hours, now)
            status = (1, cause[0], cause[1], p.clock) if cause else (0, 0, 0, p.clock)
            p.status_age += 1
            if status != p.status_sent or p.status_age >= STATUS_EVERY:
                p.status_sent, p.status_age = status, 0
                return [5, *status], None
            if p.profile_out:  # the kept hero, right after the first word on the world
                return p.profile_out.pop(0), None
            if p.shared_out:
                return p.shared_out.pop(0), None
            # every other reply: troops of the nearest party whose troops this player has not seen
            if p.requests % 2 == 0:
                for sid, _ in by_distance[:NEAREST_PER_REPLY]:
                    version, stacks = self.troops.get(sid, (0, None))
                    if stacks is not None and p.troops_sent.get(sid) != version:
                        p.troops_sent[sid] = version
                        return [3, sid, len(stacks)] + flat(stacks), None
            # every fourth: one of the other players
            others = sorted((q for q in self.players.values()
                             if q is not p and q.slot is not None and q.pos is not None), key=lambda q: q.slot)
            if others and p.requests % 4 == 1:
                q = others[p.others_cursor % len(others)]
                p.others_cursor += 1
                size = sum(n for _, n in (q.stacks_last or []))
                return [4, q.slot, q.pos[0] + COORD_OFFSET, q.pos[1] + COORD_OFFSET, size, q.faction], q.name
            out = []
            while p.removed and len(out) < REMOVALS_PER_REPLY:
                out.append((p.removed.pop(0), REMOVED, 0, 0, 0, 0, 0))
            # the lord this player serves in every reply: the player rides with him; then the
            # closest, then those on the player's screen that waited longest (only the 11 closest
            # used to be fresh: the others walked to their last target and stood there)
            near = [kv for kv in by_distance if kv[0] != p.lord]
            closest = [kv for kv in by_distance if kv[0] == p.lord] + near[:CLOSEST_PER_REPLY]
            in_view = [kv for kv in near[CLOSEST_PER_REPLY:]
                       if (kv[1][1] - x) ** 2 + (kv[1][2] - y) ** 2 <= VIEW_RADIUS ** 2]
            room = MAX_ENTRIES - len(out) - len(closest) - ROTATING_PER_REPLY
            in_view = sorted(in_view, key=lambda kv: p.sent_at.get(kv[0], 0))[:max(0, room)]
            chosen = closest + in_view
            taken = {sid for sid, _ in chosen}
            rest = [kv for kv in sorted(self.parties.items()) if kv[0] not in taken]
            if rest:
                turn = MAX_ENTRIES - len(out) - len(chosen)
                start = p.cursor % len(rest)
                chosen = chosen + (rest[start:] + rest[:start])[:turn]
                p.cursor = start + turn
            for sid, e in chosen:
                p.sent_at[sid] = p.requests
                out.append((sid, e[0], e[1], e[2], e[4], e[5], e[6]))
            self.stats["entries_out"] += len(out)
            nums = [2, len(out)]
            for sid, tmpl, ex, ey, tx, ty, att in out:
                if tmpl == REMOVED:
                    nums += [sid, tmpl, 0, 0, 0, 0, 0]
                else:
                    nums += [sid, tmpl, ex + COORD_OFFSET, ey + COORD_OFFSET, tx + COORD_OFFSET, ty + COORD_OFFSET,
                             max(att, 0)]
            return nums, None

    def _clock_sync(self, p, ahead, now):
        if abs(ahead) > TIME_SYNC_MAX_H:
            clock = 0
        elif p.clock == 0:
            clock = -1 if ahead >= TIME_AHEAD_H else 1 if ahead <= -TIME_BEHIND_H else 0
        else:
            clock = 0 if abs(ahead) <= TIME_EVEN_H else p.clock
        if clock == p.clock:
            return
        if clock == -1:
            self.log(f"player {self._who(p)}: its clock is {ahead} h ahead of the world's - it does not rest "
                     "until the world catches up (moving stays free)")
        elif clock == 1:
            self.log(f"player {self._who(p)}: its clock is {-ahead} h behind the world's - it rests faster")
        else:
            waited = f" after {now - p.clock_since:.0f} s" if p.clock_since is not None else ""
            self.log(f"player {self._who(p)}: its clock is the world's again ({ahead:+d} h){waited}")
        p.clock, p.clock_since = clock, now

    # ---- joint battles

    def _mp_online(self, now):
        return self.mp_last is not None and now - self.mp_last <= MP_ONLINE_S

    def _who(self, p):
        return f"{p.slot}:{p.name or p.cid}"

    def _mp_op(self, p, mp, now):
        op, bid, b = mp["op"], mp["bid"], self.battle
        if op in (1, 3, 4):
            what = {1: "starts a joint battle", 3: "accepts the invitation", 4: "declines / cancels"}[op]
            self.log(f"joint battle: {self._who(p)} {what} (battle {bid}, enemy party {mp['sid']}, "
                     f"player slot {mp['slot']}, center {mp['center']}{', defence' if mp.get('defend') else ''})")
        if mp.get("hero"):
            p.hero = mp["hero"]
        if mp.get("compn") is not None:  # a start or an acceptance: this battle's companions follow
            p.companions, p.companions_expected = {}, mp["compn"]
        if mp.get("comp"):
            troop, numbers = mp["comp"]
            p.companions[troop] = numbers
        if op == 1:
            event = mp.get("event")
            if (event and b is not None and b.state == "gathering" and p.cid not in b.sides
                    and b.event == event[0] and event[0] != EVENT_DUEL):
                # two friends in one town: the second one's start joins the event, and its bet counts
                self.log(f"joint battle {b.bid}: {self._who(p)} joins it (the same event)")
                b.invited.discard(p.cid)
                b.sides[p.cid] = 0
                b.bonus += event[4]
                p.mp_out.append([7, b.bid, 0, 0])
                return
            if (b is not None and b.state == "gathering" and p.cid not in b.sides and mp["sid"] >= 0
                    and b.enemy_sid == mp["sid"]):
                # the same enemy (two soldiers of one lord): this player joins the battle gathering
                self.log(f"joint battle {b.bid}: {self._who(p)} joins it (the same enemy)")
                b.invited.discard(p.cid)
                b.sides[p.cid] = b.player_team
                p.mp_out.append([7, b.bid, 0, b.player_team])
                return
            if b is not None:
                if p.cid not in b.sides:
                    self.log(f"joint battle: refused - battle {b.bid} ({b.state}) is still on")
                    p.mp_out.append([7, 0, 2, 0])  # another battle is on
                else:  # the answer to this player's start got lost: its battle, again
                    p.mp_out.append([7, b.bid, b.fighting, b.sides[p.cid]])
                return
            if not self._mp_online(now):
                self.log("joint battle: refused - no battle server (Multiplayer - Host a game, Battle)")
                p.mp_out.append([7, 0, 3, 0])
                return
            self.battle_seq += 1
            b = Battle(self.battle_seq, p.cid, now)
            b.kind = mp.get("kind", 0)
            defender = None
            if event:
                # the players' heroes alone, on one side, against bots
                b.event, b.param, b.town, b.fighter, b.bonus = event
                if b.event == EVENT_DUEL:
                    # or against each other: the challenged player answers, and is told the stake
                    defender = self._player_in_slot(b.param, but=p)
                    if defender is None:
                        self.log(f"joint battle: refused - no player in slot {b.param} to duel")
                        p.mp_out.append([7, 0, 2, 0])
                        return
                    b.sides[defender.cid] = 1
                    b.invited.add(defender.cid)
                    defender.mp_out.append([6, b.bid, 3 + EVENT_DUEL, p.slot, b.bonus])
                    self._act(p, "duel_call", rival=self._who(defender), stake=b.bonus)
            elif mp.get("center", -1) > 0 and mp.get("defend") and mp["sid"] > 0:
                # a defence: the players and the garrison hold the walls (team 0) against the
                # besieger and the parties attached to it, its army (team 1)
                b.center, b.defence, b.player_team = mp["center"], True, 0
                b.sides = {p.cid: 0}
                b.enemy_sid = mp["sid"]  # who takes the defeated defenders prisoner
                garrison = self.troops.get(b.center, (0, None))[1] or []
                b.npc_stacks = [(0, b.center, t, n) for t, n in garrison]
                army = [mp["sid"]] + sorted(s for s, e in self.parties.items() if e[6] == mp["sid"] + 1)
                for sid in army:
                    stacks = self.troops.get(sid, (0, None))[1] or (mp["troops"] if sid == mp["sid"] else [])
                    b.npc_stacks += [(1, sid, t, n) for t, n in stacks]
            elif mp.get("center", -1) > 0:  # center ids are never 0 (the player's party)
                # a siege: the players storm the walls (team 1), the garrison holds them (team 0)
                b.center = mp["center"]
                b.player_team = 1
                b.sides = {p.cid: 1}
                b.enemy_stacks = self.troops.get(b.center, (0, None))[1] or mp["troops"] or []
            elif mp["slot"] >= 0:
                defender = next((q for q in self.players.values() if q.slot == mp["slot"] and q is not p), None)
                if defender is None:
                    self.log(f"joint battle: refused - no player in slot {mp['slot']}")
                    p.mp_out.append([7, 0, 2, 0])
                    return
                b.sides[defender.cid] = 1
                b.invited.add(defender.cid)
                defender.mp_out.append([6, b.bid, 2, p.slot, -1])
            elif b.kind == KIND_BANDITS and mp["troops"]:
                # the bandits who took a village are no party of the world: its game names them, and
                # the village's men, who stand with the players
                b.enemy_stacks = mp["troops"]
                b.npc_stacks = [(b.player_team, mp.get("ally", -1), t, n) for t, n in mp.get("ally_troops") or []]
            elif mp["sid"] >= 0:
                b.enemy_sid = mp["sid"]
                b.enemy_stacks = mp["troops"] or (self.troops.get(mp["sid"], (0, None))[1] or [])
                ally = mp.get("ally", -1)
                if ally >= 0 and ally != mp["sid"]:
                    # the lord the player serves: his men fight on the players' side (the world
                    # server's view of them first, the player's otherwise)
                    b.ally_sid = ally
                    stacks = self.troops.get(ally, (0, None))[1] or mp.get("ally_troops") or []
                    b.npc_stacks = [(b.player_team, ally, t, n) for t, n in stacks]
            else:
                self.log("joint battle: refused - the enemy is not a party of the world (no server id)")
                p.mp_out.append([7, 0, 2, 0])
                return
            for q in self.players.values():
                if q is p or q is defender or q.slot is None or q.pos is None or p.pos is None:
                    continue
                if q.cid in b.sides or b.event == EVENT_DUEL:
                    continue
                if (q.pos[0] - p.pos[0]) ** 2 + (q.pos[1] - p.pos[1]) ** 2 <= INVITE_DIST ** 2:
                    b.invited.add(q.cid)
                    target = b.enemy_sid if b.enemy_sid is not None else (b.center if b.center is not None else -1)
                    q.mp_out.append([6, b.bid, 3 + b.event if b.event else 1, p.slot, target])
            b.terrain = mp.get("terrain", 0)
            if b.kind == KIND_LAIR and b.terrain in PLAIN_TERRAINS:
                b.terrain = LAIR_TERRAIN
            if b.kind in KIND_NAMES:
                self._act(p, "battle_" + KIND_NAMES[b.kind], battle=b.bid, enemy=b.enemy_sid, ally=b.ally_sid)
            self.battle = b
            invited = ", ".join(self._who(self.players[c]) for c in sorted(b.invited) if c in self.players)
            self.log(f"joint battle {b.bid}: gathering; invited: {invited or 'nobody (no other player near)'}")
            p.mp_out.append([7, b.bid, 0, 0])
        elif b is not None and bid == 0 and op == 2 and p.cid in b.sides:
            # waiting without the battle's number (the answer to the start got lost): tell it
            p.mp_out.append([7, b.bid, b.fighting, b.sides[p.cid]])
        elif b is None or b.bid != bid:
            if op in (2, 3):
                p.mp_out.append([7, bid, 2, 0])  # that battle is gone
        elif op == 3:
            if b.state != "gathering" and p.cid not in b.sides:
                if p.cid not in b.invited:
                    self.log(f"joint battle {b.bid}: {self._who(p)} accepted too late - the battle began without that player")
                    p.mp_out.append([7, bid, 2, 0])  # too late
                    return
                # the armies are on their way: the player still fights, as its hero, on the
                # starter's side; its troops and companions stay out of this battle
                b.invited.discard(p.cid)
                b.sides[p.cid] = b.player_team
                self.log(f"joint battle {b.bid}: {self._who(p)} accepted late - joins the battle as its hero; "
                         "its troops stay out of it")
                p.mp_out.append([7, b.bid, b.fighting, b.player_team])
                return
            b.invited.discard(p.cid)
            b.sides.setdefault(p.cid, b.player_team)  # an invited player fights on the starter's side
        elif op == 4:
            b.invited.discard(p.cid)
            if b.state == "running":
                return  # the battle goes on: that player's troops fight without the player
            if p.cid == b.starter or b.event == EVENT_DUEL:  # a duel takes both
                if b.event == EVENT_DUEL:
                    self._act(p, "duel_off", battle=b.bid, why="declined")
                for cid in set(b.sides) | b.invited:
                    q = self.players.get(cid)
                    if q is not None and q is not p:
                        q.mp_out.append([7, b.bid, 2, 0])
                self.battle = None
            elif b.sides.get(p.cid) == 0:
                del b.sides[p.cid]  # declined (an attacked player cannot decline)

    def _battle_tick(self, now):
        b = self.battle
        if b is None or b.state != "gathering" or (b.invited and now < b.until):
            return
        if b.event:
            self._event_tick(b, now)
            return
        # the companions come one per request: wait for them a little
        waiting = any(len(q.companions) < q.companions_expected
                      for cid, q in ((c, self.players.get(c)) for c in b.sides)
                      if q is not None and cid not in b.invited)
        if waiting and now < b.created + COMPANIONS_WAIT_S:
            return
        stacks = []
        b.companion_data = []
        for cid, team in sorted(b.sides.items(), key=lambda kv: (kv[1], kv[0] != b.starter)):
            q = self.players.get(cid)
            for troop, n in (q.stacks_last or []) if q is not None else []:
                stacks.append([team, cid, troop, n, 0])
            for troop, numbers in sorted((q.companions if q is not None else {}).items()):
                stacks.append([team, cid, troop, 1, 0])
                b.hero_troops.add(troop)
                b.companion_data.append((troop, numbers))
        if b.defence:
            stacks += [[team, ("npc", sid), troop, n, 0] for team, sid, troop, n in b.npc_stacks]
        else:
            enemy = [[1 - b.player_team, None, troop, n, 0] for troop, n in b.enemy_stacks if n > 0]
            # the lord's men: as many stacks as leave room for the enemy, the biggest first
            room = max(0, MP_MAX_STACKS - len([s for s in stacks if s[3] > 0]) - len(enemy))
            allies = sorted(([team, ("npc", sid), troop, n, 0] for team, sid, troop, n in b.npc_stacks if n > 0),
                            key=lambda s: -s[3])[:room]
            stacks += allies + enemy
        stacks = [s for s in stacks if s[3] > 0][:MP_MAX_STACKS]
        if b.center is None and not any(s[0] != b.player_team for s in stacks):
            # the enemy fell in the last battle and the lord's fight still shows: with nobody to
            # beat this battle would never end, and the players in it would wait for good
            self.log(f"joint battle {b.bid}: no enemy left - there is nothing to fight, the battle is off")
            for cid in set(b.sides) | b.invited:
                q = self.players.get(cid)
                if q is not None:
                    q.mp_out.append([7, b.bid, 2, 0])
            self.battle = None
            return
        total = sum(s[3] for s in stacks)
        scale = min(1.0, MP_MAX_BOTS / total) if total else 1.0
        for s in stacks:
            s[4] = max(1, round(s[3] * scale))
        b.stacks, b.sent, b.state = stacks, 0, "loading"
        self.log(f"joint battle {b.bid}: going to the battle server ({len(stacks)} stacks, sides "
                 + ", ".join(f"{self._who(self.players[c])}=team {t}" for c, t in b.sides.items() if c in self.players)
                 + ")")

    def _event_tick(self, b, now):
        """A joint event is fought by the heroes alone, no troops stand in for a player: it starts
        when its players stand on the battle server, or after EVENT_WAIT_S with those who came."""
        present = [cid for cid in b.sides if self._mp_player_number(cid) >= 0
                   and cid in self.players and self.players[cid].hero]
        if b.event == EVENT_DUEL and b.invited:
            self._duel_off(b, "no answer")
            return
        if len(present) < len(b.sides) and now < b.until + EVENT_WAIT_S:
            return
        if b.event == EVENT_DUEL and len(present) < len(b.sides):
            self._duel_off(b, "not on the battle server")
            return
        for cid in set(b.sides) - set(present):
            del b.sides[cid]
            q = self.players.get(cid)
            if q is not None:
                self.log(f"joint battle {b.bid}: {self._who(q)} is not on the battle server - left out of the event")
                q.mp_out.append([7, b.bid, 2, 0])
        if not b.sides:
            self.battle = None
            return
        self._load_event_round(b)

    def _duel_off(self, b, why):
        for cid in set(b.sides) | b.invited:
            q = self.players.get(cid)
            if q is not None:
                q.mp_out.append([7, b.bid, 2, 0])
        starter = self.players.get(b.starter)
        if starter is not None:
            self._act(starter, "duel_off", battle=b.bid, why=why.replace(" ", "_"))
        self.battle = None

    def _load_event_round(self, b):
        """The next fight of a joint event goes to the battle server (a tournament has several)."""
        b.stacks = self._event_stacks(b)
        b.sent, b.heroes, b.heroes_given, b.companion_data, b.late = 0, None, set(), [], []
        b.state = "loading"
        self.log(f"joint battle {b.bid}: going to the battle server ({len(b.stacks)} stacks, sides "
                 + ", ".join(f"{self._who(self.players[c])}=team {t}" for c, t in b.sides.items() if c in self.players)
                 + ")")

    def _event_stacks(self, b):
        """The bots of a joint event. On team 1: Native's line of arena fighters, or for a training each
        player's own men. A tournament's round: 2 to 4 teams of fighters, stronger ones with each round,
        the players' team filled up with them. A duel has none."""
        players = len(b.sides)
        if b.event == EVENT_DUEL:
            return []
        foes = []  # (team, troop)
        if b.event == EVENT_ARENA:
            total = ARENA_FOES * players
            for i in range(total):
                k = i * ARENA_SEQUENCE // total
                foes.append((1, b.fighter + min(9, k // 6 + k % 6)))
        elif b.event == EVENT_TOURNAMENT:
            b.teams = random.randint(*TOURNAMENT_TEAMS)
            men = max(players, random.randint(*TOURNAMENT_MEN))
            self.log(f"joint battle {b.bid}: tournament round {b.round}: {b.teams} teams of {men}")
            for team in TOURNAMENT_SIDES[:b.teams]:
                foes += [(team, b.fighter + 2 * b.round + k % 2) for k in range(men - players if team == 0 else men)]
        else:
            for cid in b.sides:
                q = self.players.get(cid)
                men = (q.stacks_last or []) if q is not None else []
                pool = [troop for troop, n in men for _ in range(min(n, b.param))]
                picked = random.sample(pool, min(b.param, len(pool)))
                foes += [(1, troop) for troop in picked + [b.fighter + 2] * (b.param - len(picked))]
        stacks = []
        for team, troop in foes:
            if stacks and stacks[-1][0] == team and stacks[-1][2] == troop:
                stacks[-1][3] += 1
                stacks[-1][4] += 1
            else:
                stacks.append([team, None, troop, 1, 1])
        return stacks

    def _hero_numbers(self, b, q):
        """A player's hero for the battle server: in a joint event at full health."""
        hero = list(q.hero)
        if b.event:
            hero[-2] = hero[-1]
        return hero

    def _mp_wanted_name(self, cid):
        """The name a campaign player is expected under on the battle server: the one given to the
        launcher, else the hero's."""
        q = self.players.get(cid)
        return self.mp_names.get(cid) or (q.name if q is not None else None)

    def _mp_player_number(self, cid):
        """The battle server's player number of a campaign player, matched by name, or -1."""
        wanted = self._mp_wanted_name(cid)
        if not wanted:
            return -1
        def norm(text):
            return " ".join(text.lower().split())
        # the game sends names in its own code page, read here as latin-1; a launcher name is real
        # text, so a Cyrillic one is compared in that form too
        wants = {norm(wanted), norm(wanted.encode("cp1251", "ignore").decode("latin-1"))}
        for no, name in sorted(self.mp_players.items()):
            if norm(name) in wants:
                return no
        return -1

    def mp_recognition(self, now):
        """[(slot, hero name, name on the battle server, its player number or None)] of the campaign's
        players; None while the battle server is off or the name is not there."""
        with self.lock:
            online = self._mp_online(now)
            out = []
            for p in sorted(self.players.values(), key=lambda q: (q.slot is None, q.slot)):
                if p.slot is None:
                    continue
                no = self._mp_player_number(p.cid) if online else -1
                out.append((p.slot, p.name or p.cid, self._mp_wanted_name(p.cid), no if no >= 0 else None))
            return out

    def _finish_event(self, b, winner, fallen, weapons, health, kills):
        """A fight of a joint event is over. Nobody is lost, wounded or taken in it; the heroes learn
        from their blows as in a battle, and each player's game gives the prize as Native would."""
        won = 1 if winner == 0 else 0
        for cid in b.sides:
            q, no = self.players.get(cid), self._mp_player_number(cid)
            if q is None:
                continue
            b.kills[cid] = b.kills.get(cid, 0) + (kills.get(no, 0) if no >= 0 else 0)
            used = [(wpt, hits, damage) for player, wpt, hits, damage in weapons if player == no >= 0]
            if used:
                q.mp_out.append([9, b.bid, len(used)] + [v for entry in used for v in entry])
        if b.event == EVENT_DUEL:
            for cid, team in b.sides.items():
                q = self.players.get(cid)
                if q is not None:
                    outcome = 2 if winner not in (0, 1) else 1 if team == winner else 0
                    q.mp_out.append([26, b.bid, EVENT_DUEL, outcome, b.bonus, 0, 0, 0])
            self.log(f"joint battle {b.bid}: the duel is over (team {winner} won)")
            self.battle = None
            return
        if (b.event == EVENT_TOURNAMENT and won and b.round < TOURNAMENT_ROUNDS
                and any(self._mp_player_number(cid) >= 0 for cid in b.sides)):
            self.log(f"joint battle {b.bid}: tournament round {b.round} won")
            b.round += 1
            self._load_event_round(b)
            return
        foes = {}
        for team, owner, troop, count, spawned in b.stacks:
            foes[troop] = foes.get(troop, 0) + count
        total = sum(foes.values())
        fell = min(total, sum(fallen.get(i, 0) for i in range(len(b.stacks))))
        for cid in b.sides:
            q, no = self.players.get(cid), self._mp_player_number(cid)
            if q is None:
                continue
            if b.event == EVENT_ARENA:
                stood = 1 if won and (health or {}).get(no, 0) > 0 else 0
                q.mp_out.append([26, b.bid, b.event, stood, b.kills.get(cid, 0), 0, b.town, 0])
            elif b.event == EVENT_TOURNAMENT:
                rounds = b.round if won else b.round - 1
                q.mp_out.append([26, b.bid, b.event, won, rounds, b.bonus if won else 0, b.town, 0])
            else:
                ratio = 100 if won else fell * 100 // max(1, total)
                pairs = sorted(foes.items())
                q.mp_out.append([26, b.bid, b.event, won, ratio, b.param, len(b.sides), len(pairs)] + flat(pairs))
        self.log(f"joint battle {b.bid}: event {b.event} over ({'the players won' if won else 'the players were beaten'})")
        self.battle = None

    def _finish(self, b, winner, fallen, now, weapons=(), health=None, kills=None):
        if b.event:
            self._finish_event(b, winner, fallen, weapons, health, kills or {})
            return
        losses = {cid: [] for cid in b.sides}
        left = {cid: [] for cid in b.sides}  # what each player has after the battle
        enemy_left = []
        npc_left = {}  # a defence: world party -> what it has after the battle
        fell_by_team = {0: 0, 1: 0}
        fallen_of_team = {0: [], 1: []}  # (troop, count) fallen on each side: the winners' spoils
        for i, (team, owner, troop, count, spawned) in enumerate(b.stacks):
            fell = fallen.get(i, 0)
            lost = min(count, round(fell * count / spawned)) if spawned else 0
            fell_by_team[team] = fell_by_team.get(team, 0) + lost
            if lost and troop not in b.hero_troops:
                fallen_of_team.setdefault(team, []).append((troop, lost))
            if owner is None:
                if count - lost > 0:
                    enemy_left.append((troop, count - lost))
            elif isinstance(owner, tuple):  # a defence: a world party, the garrison or a besieger
                npc_left.setdefault(owner[1], [])
                if count - lost > 0:
                    npc_left[owner[1]].append((troop, count - lost))
            else:
                wounded = lost if troop in b.hero_troops else lost * WOUNDED_PCT // 100
                if lost:
                    losses.setdefault(owner, []).append((troop, lost - wounded, wounded))
                if count - (lost - wounded) > 0:
                    left.setdefault(owner, []).append((troop, count - (lost - wounded)))
        # the defeated side's players: their troops are taken prisoner, by the world party or by
        # the winning player (the starter, or the attacked player)
        defeated = [cid for cid, team in b.sides.items() if winner in (0, 1) and team != winner]
        captives = [s for cid in defeated for s in left.get(cid, [])]
        world_captives = [s for cid in defeated if not getattr(self.players.get(cid), "on_server", False)
                          for s in left.get(cid, [])]  # the host's own defeat already hands them over
        # the spoils: the losers' fallen, shared among the winning players
        winners = [cid for cid, team in sorted(b.sides.items(), key=lambda kv: kv[0] != b.starter)
                   if team == winner and cid in self.players]
        shares = {}
        if winners and winner in (0, 1):
            spoils = fallen_of_team.get(1 - winner, [])
            for k, cid in enumerate(winners):
                share = [(troop, n // len(winners) + (1 if k < n % len(winners) else 0)) for troop, n in spoils]
                share = [(troop, n) for troop, n in share if n > 0][:MAX_STACKS]
                if share:
                    shares[cid] = share
        for cid, lost in losses.items():
            q = self.players.get(cid)
            if q is None:
                continue
            lost = lost[:MAX_STACKS]
            team = b.sides.get(cid)
            won = 1 if team == winner else 0
            # experience from the enemies that fell, shared by the side's players
            side_players = sum(1 for t in b.sides.values() if t == team)
            xp = fell_by_team.get(1 - team, 0) * XP_PER_ENEMY // max(1, side_players)
            if not won:
                xp //= 3
            if cid in shares:  # before the result: the spoils are there while the battle menu still is
                q.mp_out.append([21, b.bid, len(shares[cid])] + flat(shares[cid]))
            q.mp_out.append([8, b.bid, won, xp, len(lost)] + [v for entry in lost for v in entry])
            no = self._mp_player_number(cid)
            used = [(wpt, hits, damage) for player, wpt, hits, damage in weapons if player == no >= 0]
            if used:
                q.mp_out.append([9, b.bid, len(used)] + [v for entry in used for v in entry])
            # last: the hero's wounds, and the capture (after which the player is in captivity)
            hp = (health or {}).get(no, -1) if no >= 0 else -1
            captor = b.enemy_sid if cid in defeated and b.enemy_sid is not None else -1  # a failed storm: no capture
            if captor >= 0:
                self.captors.setdefault(captor, set()).add(self._who(q))
            if hp >= 0 or captor >= 0:
                q.mp_out.append([10, b.bid, hp, captor])
        if b.defence:
            # the besiegers keep what survived (a party with nobody left is gone); the garrison too,
            # unless the walls fell: then the center goes to the besiegers' kingdom
            for sid, kept in sorted(npc_left.items()):
                if sid == b.center:
                    continue
                self._record_result((sid, 0 if kept else 1, kept, []), None, now)
            if winner == b.player_team:
                self._record_result((b.center, 0, npc_left.get(b.center, []), []), None, now)
            else:
                self.captures.append((b.center, -1))
        elif b.center is not None:
            starter = self.players.get(b.starter)
            if winner == b.player_team:
                # the walls are taken: the host's own game takes the center as Native does; a
                # client's kingdom gets it on the world server
                if starter is not None and starter.on_server:
                    starter.mp_out.append([13, b.bid, b.center])
                elif starter is not None and starter.faction:
                    self.captures.append((b.center, starter.faction))
                else:
                    self._record_result((b.center, 0, [], []), None, now)  # no kingdom to give it to
            else:
                self._record_result((b.center, 0, enemy_left, []), None, now)  # what the garrison kept
        elif b.enemy_sid is not None:
            destroyed = 1 if winner == b.player_team or not enemy_left else 0
            self._record_result((b.enemy_sid, destroyed, enemy_left, [] if destroyed else world_captives), None, now)
            if b.ally_sid is not None and b.ally_sid in npc_left and b.kind != KIND_VILLAGE:
                # the lord's party keeps what survived; never destroyed: the server keeps the lord, and
                # his soldiers' games must not lose the party they serve in. A caravan or farmers with
                # nobody left are gone; a village's militia has no party of the world
                kept = npc_left[b.ally_sid]
                self._record_result((b.ally_sid, 1 if b.kind == KIND_CARAVAN and not kept else 0, kept, []),
                                    None, now)
            if b.kind in KIND_NAMES and b.starter in self.players:
                self._act(self.players[b.starter], "battle_end", kind=KIND_NAMES[b.kind], battle=b.bid,
                          won=1 if winner == b.player_team else 0)
        elif b.kind == KIND_BANDITS:
            if b.starter in self.players:
                self._act(self.players[b.starter], "battle_end", kind=KIND_NAMES[b.kind], battle=b.bid,
                          won=1 if winner == b.player_team else 0)
        elif captives:
            # a battle between players: the winner's side takes the prisoners
            taker = next((cid for cid, team in sorted(b.sides.items(), key=lambda kv: kv[0] != b.starter)
                          if team == winner and cid in self.players), None)
            if taker is not None:
                taken = captives[:MAX_STACKS]
                self.players[taker].mp_out.append([11, b.bid, len(taken)] + flat(taken))
        self.battle = None

    def mp_request(self, phase, bid, winner, fallen, players, now, weapons=(), health=None, kills=None):
        """The battle server asks; returns the reply numbers after the marker."""
        with self.lock:
            if self.mp_last is None or now - self.mp_last > MP_ONLINE_S:  # a battle server started anew
                self.army_told = {}
            self.mp_last = now
            self.mp_players = players
            b = self.battle
            if phase == 4:
                if b is not None and b.bid == bid and b.state == "running":
                    self._finish(b, winner, fallen, now, weapons, health, kills)
                # the same answer when asked again: the next round of a tournament is already loading
                more = 1 if self.battle is not None and self.battle.bid == bid else 0
                return [4, bid, more]
            self._battle_tick(now)
            b = self.battle
            if b is None:
                return [0]
            if b.state == "loading" and phase == 0:
                # the player's army goes into the battle as it is equipped: first what changed of that
                for kind, items in sorted(self.army["gear"].items()):
                    if self.army_told.get(kind) != items:
                        self.army_told[kind] = items
                        return [10, b.bid, kind, len(items)] + items
                if not b.stacks and not b.no_stacks_told:
                    b.no_stacks_told = True
                    return [2, b.bid, 0, 0]
                if b.sent < len(b.stacks):
                    chunk = b.stacks[b.sent:b.sent + MP_CHUNK]
                    nums = [2, b.bid, b.sent, len(chunk)]
                    for team, owner, troop, count, spawned in chunk:
                        group = -1 if owner is None else self._mp_player_number(owner)
                        nums += [team, group, troop, spawned]
                    b.sent += len(chunk)
                    return nums
                if b.heroes is None:
                    b.heroes = []
                    for cid in b.sides:
                        q, no = self.players.get(cid), self._mp_player_number(cid)
                        if q is not None and q.hero and no >= 0 and len(b.heroes_given) < MP_MAX_HEROES:
                            b.heroes.append((no, self._hero_numbers(b, q)))
                            b.heroes_given.add(cid)
                if b.heroes:
                    no, hero = b.heroes.pop(0)
                    return [5, b.bid, no] + hero
                if b.companion_data:
                    troop, numbers = b.companion_data.pop(0)
                    return [6, b.bid, troop] + numbers
                pairs = []
                for cid, team in b.sides.items():
                    no = self._mp_player_number(cid)
                    if no >= 0:
                        pairs += [no, team]
                b.state, b.started = "running", now
                self.log(f"joint battle {b.bid}: started on the battle server")
                for cid, team in b.sides.items():
                    q = self.players.get(cid)
                    if q is not None:
                        q.mp_out.append([7, b.bid, 1, team])
                mode = 1 if b.center is not None else 0
                hint = b.center if b.center is not None else b.terrain
                if b.event:
                    mode = b.event + 1
                    hint = b.round + 10 * b.teams if b.event == EVENT_TOURNAMENT else ARENA_AT_ONCE * len(b.sides)
                return [1, b.bid, len(b.stacks), mode, hint, len(pairs) // 2] + pairs
            if b.state == "running" and phase in (1, 2, 3):
                if not b.late:
                    self._late_heroes(b)
                if b.late:
                    return b.late.pop(0)
            if b.state == "running" and phase == 0 and now - b.started > MP_LOST_S:
                # the battle server restarted or changed its game: the battle is lost to it
                self.log(f"joint battle {b.bid}: lost - the battle server went back to an ordinary round")
                for cid in b.sides:
                    q = self.players.get(cid)
                    if q is not None:
                        q.mp_out.append([7, b.bid, 2, 0])
                self.battle = None
            return [0]

    def _late_heroes(self, b):
        """A player of the battle whose hero the battle server has not got (it came to the server
        after the start, or accepted late): the hero, then its side (kinds 5 and 9)."""
        for cid, team in sorted(b.sides.items()):
            if cid in b.heroes_given or len(b.heroes_given) >= MP_MAX_HEROES:
                continue
            q, no = self.players.get(cid), self._mp_player_number(cid)
            if q is None or not q.hero or no < 0:
                continue
            b.heroes_given.add(cid)
            b.late += [[5, b.bid, no] + self._hero_numbers(b, q), [9, b.bid, no, team]]
            self.log(f"joint battle {b.bid}: {self._who(q)} is on the battle server now - its hero joins the battle (team {team})")
            return

    def mp_notice(self):
        """(battle server player number, text) for an invited player who stands on the battle server
        while the invitation waits in that player's campaign window, or None."""
        with self.lock:
            b = self.battle
            if b is None or b.state != "gathering":
                return None
            starter = self.players.get(b.starter)
            name = starter.name if starter is not None and starter.name else "?"
            for cid in sorted(b.invited - b.told):
                no = self._mp_player_number(cid)
                if no >= 0:
                    b.told.add(cid)
                    return no, (f"CoopWorld: {name} - совместный бой, ответьте в окне кампании (Alt+Tab) / "
                                f"a joint battle, answer in the campaign window")
            return None

    # ---- clocks

    def clock(self, role, hours, now):
        """Record a game-clock sample of one game."""
        if hours is None:
            return
        with self.lock:
            samples = self.clocks[role]
            if role == "cli_map" and samples and now - samples[-1][0] > 1.0:
                samples.clear()  # the player rested or was in a menu in between: start a new run
            samples.append((now, hours))
            while samples and now - samples[0][0] > CLOCK_WINDOW_S:
                samples.pop(0)

    def clock_rate(self, role):
        """Game hours per real minute over the last CLOCK_WINDOW_S, or None without enough samples."""
        with self.lock:
            samples = list(self.clocks[role])
        if len(samples) < 2 or samples[-1][0] - samples[0][0] < 5:
            return None
        return (samples[-1][1] - samples[0][1]) * 60.0 / (samples[-1][0] - samples[0][0])


def parse_entries(d):
    """'sid,tmpl,x,y[,tx,ty[,att]];...' -> [(sid, tmpl, x, y, tx, ty, att)]; without a target the
    party stays put, without att it is on the open map"""
    entries = []
    for chunk in d.split(";"):
        parts = chunk.split(",")
        if len(parts) in (4, 6, 7):
            try:
                v = [int(x) for x in parts]
            except ValueError:
                continue
            if len(v) == 4:
                v += [v[2], v[3]]
            if len(v) == 6:
                v.append(0)
            entries.append(tuple(v))
    return entries


def parse_together(q):
    """What a player does together with the others (see World._together), or None."""
    out = {}
    v = parse_ints(q.get("give", "").replace(",,", ",")) if "give" in q else None
    if v:
        stacks = parse_stacks(v[1:]) or []
        out["give"] = (v[0], stacks)
    v = parse_ints(q.get("giveans", "")) if "giveans" in q else None
    if v and len(v) == 2:
        out["giveans"] = (v[0], v[1])
    v = parse_ints(q.get("lg", "")) if "lg" in q else None
    if v and len(v) == 4:
        out["note"] = v
    if "fl" in q:
        out["follow"] = query_int(q, "fl", 0)
    if "bs" in q:
        v = [] if q["bs"] == "-" else parse_ints(q["bs"])
        if v is not None and len(v) in (0, 2):
            out["base"] = tuple(v)
    v = parse_ints(q.get("tg", "")) if "tg" in q else None
    if v and len(v) == 2 and v[0] > 0:
        out["treasury"] = (v[0], v[1])
    if q.get("st") == "1":
        out["store_open"] = True
    v = parse_ints(q.get("sti", "")) if "sti" in q else None
    if v and len(v) >= 3 and len(v) % 2 == 1:
        out["store_put"] = v
    v = parse_ints(q.get("ag", "")) if "ag" in q else None
    if v and 0 <= v[0] < ARMY_KINDS and len(v) - 1 <= ARMY_GEAR_MAX and all(item > 0 for item in v[1:]):
        out["army_gear"] = (v[0], v[1:])
    index, _, text = q.get("an", "").partition(",")
    if index.isdigit() and int(index) <= ARMY_KINDS:
        out["army_name"] = (int(index), game_text_in(text).replace("|", " ").strip()[:ARMY_NAME_MAX])
    v = parse_ints(q.get("al", "")) if "al" in q else None
    if v and len(v) == 2 and 0 <= v[0] < ARMY_KINDS and 2 <= v[1] <= ARMY_LEVELS:
        out["army_level"] = (v[0], v[1])
    if q.get("ao") == "1" and out:
        out["army_saved"] = True
    return out or None


def parse_profile(text):
    """'seq,offset,total,v1,...' -> [seq, offset, total, v1, ...] or None"""
    v = parse_ints(text) if text else None
    return v if v and len(v) >= 3 and v[1] >= 0 and v[2] >= 0 else None


def parse_center(text):
    """'center,faction,lord[,besieger+1[,bandits]]' -> (center, faction, lord, besieger+1, bandits) or None"""
    v = parse_ints(text) if text else None
    if v and 3 <= len(v) <= 5:
        v += [0] * (5 - len(v))
        return tuple(v)
    return None


def parse_battles(text):
    """'sid,enemy;...' -> [(sid, enemy)]: world parties in a map battle"""
    out = []
    for chunk in text.split(";") if text else []:
        v = parse_ints(chunk)
        if v and len(v) == 2 and v[0] >= 0 and v[1] >= 0:
            out.append((v[0], v[1]))
    return out


def parse_hours(q):
    try:
        return int(q["h"])
    except (KeyError, ValueError):
        return None


def parse_troops(text):
    """'sid,t1,n1,...' -> (sid, stacks) or None"""
    values = parse_ints(text) if text else None
    if not values:
        return None
    stacks = parse_stacks(values[1:])
    return None if stacks is None else (values[0], stacks)


def parse_result(text):
    """'sid,destroyed,t1,n1,...' -> (sid, destroyed, stacks) or None"""
    values = parse_ints(text) if text else None
    if not values or len(values) < 2:
        return None
    stacks = parse_stacks(values[2:])
    return None if stacks is None else (values[0], 1 if values[1] else 0, stacks)


def parse_mp_players(text):
    """'no~name;...' -> {no: name}"""
    players = {}
    for chunk in text.split(";"):
        no, sep, name = chunk.partition("~")
        if sep and no.strip().isdigit() and name.strip():
            players[int(no)] = game_text_in(name).strip()
    return players


def parse_event(text):
    """mpx: [event, param, town, fighter, bonus], or None when malformed."""
    values = parse_ints(text) if text else None
    if values is None or len(values) != 5 or not EVENT_ARENA <= values[0] <= EVENT_DUEL:
        return None
    if values[0] == EVENT_TRAINING and not 1 <= values[1] <= 4:
        return None
    if values[0] == EVENT_DUEL and not 0 <= values[1] < MAX_PLAYERS:
        return None
    return values


def parse_fallen(text):
    """'i,fallen;...' -> {i: fallen}"""
    fallen = {}
    for chunk in text.split(";"):
        v = parse_ints(chunk)
        if v and len(v) == 2:
            fallen[v[0]] = v[1]
    return fallen


def parse_weapons(text):
    """'player,wpt,hits,damage;...' -> [(player, wpt, hits, damage)]"""
    out = []
    for chunk in text.split(";"):
        v = parse_ints(chunk)
        if v and len(v) == 4 and 0 <= v[1] < 7:
            out.append(tuple(v))
    return out


def query_int(q, key, default):
    try:
        return int(q.get(key, default))
    except ValueError:
        return default


def game_text_in(text):
    """A text the game sent (a name) as the real text. The game's UTF-8 reaches the bridge read as
    the Windows code page and encoded once more ('Игрок' arrives as 'Р˜РіСЂРѕРє' in UTF-8); the
    HTTP layer hands it over as Latin-1 characters, one per byte."""
    try:
        once = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    raw = bytearray()
    for ch in once:
        try:
            raw += ch.encode("cp1251")
        except UnicodeEncodeError:
            if ord(ch) > 0xFF:
                return once  # not the double encoding: the game sent plain UTF-8
            raw.append(ord(ch))  # a byte cp1251 has no letter for passes as itself
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return once


def game_text_out(text):
    """A real text for the game: its UTF-8 bytes, as Latin-1 characters for the HTTP layer."""
    return text.encode("utf-8").decode("latin-1")


def reply_text(numbers, string=None):
    text = "|".join(str(int(v)) for v in numbers)
    if string and numbers[1:2] == [34] and string.lstrip("-").isdigit():
        string = f'"{string}"'  # a name stays a string, even "1"
    if string and not string.lstrip("-").isdigit():  # a number would land in a register, not s0
        text += "|" + game_text_out(string.replace("|", " "))
    return text


TRACE_KEYS = ("mp=", "give=", "giveans=", "hello=", "bye=",
              "res=", "pfq=", "&lg=", "&fl=", "&bs=", "&tg=", "&st=", "&sti=", "&mpk=", "&ag=", "&an=", "&al=")
QUIET_KINDS = {0, 2, 3, 4, 5, 12, 33}  # replies that come round all the time (positions, troops, pause...)


def worth_tracing(role, target, reply):
    """Whether a request and its reply go to trace.log: everything about battles, parties, joining,
    results; not the endless position updates."""
    parts = reply.split("|")
    kind = int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else 0
    if role == "mp":
        return "st=0" not in target or kind != 0
    if role == "srv":
        try:
            nums = [int(v) for v in parts[:5]]
            payload_at = 5 + 4 * nums[4]
            return len(parts) > payload_at and parts[payload_at] not in ("0",)
        except (ValueError, IndexError):
            return True
    if "&mp=2&" in target and kind == 7:
        return False  # the joint battle window asking how it stands, four times a second
    return any(k in target for k in TRACE_KEYS) or kind not in QUIET_KINDS


def make_trace(path, limit=20_000_000):
    """trace.log: a request and its reply per line, for what worth_tracing keeps; kept under limit
    bytes (the older half goes to trace.old.log)."""
    path = Path(path)
    lock = threading.Lock()

    def trace(role, cid, target, reply):
        if not worth_tracing(role, target, reply):
            return
        line = (f"{time.strftime('%H:%M:%S')} {role} {cid} {game_text_in(target)[:500]}"
                f"\n         -> {game_text_in(reply)[:300]}\n")
        with lock:
            try:
                if path.exists() and path.stat().st_size > limit:
                    path.replace(path.with_name(path.stem + ".old.log"))
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line)
            except OSError:
                pass

    return trace


def make_trail(path, names_path=None, limit=20_000_000):
    """trail.log: what a debug build's game did (src/trail), an entry per line as it comes, kept under
    limit bytes as trace.log is. trail_names.json, beside this file in a debug package, says what the
    numbers stand for. A gap in the numbers is written down as such."""
    path = Path(path)
    lock = threading.Lock()
    awaited = {}
    try:
        names = json.loads(Path(names_path or Path(__file__).with_name("trail_names.json")).read_text("utf-8"))
    except (OSError, ValueError):
        names = {}

    def trail(cid, query):
        entries = parse_ints(query.get("tr", "").rstrip(","))
        if entries is None or not query.get("trs", "").isdigit():
            return
        first = int(query["trs"])
        now = time.strftime("%H:%M:%S")
        with lock:
            lines = []
            if first > awaited.get(cid, first):
                lines.append(f"{now} {cid} {awaited[cid]} lost {first - awaited[cid]}")
            lines += [f"{now} {cid} {first + k} {names.get(str(entry), entry)}" for k, entry in enumerate(entries)]
            awaited[cid] = first + len(entries)
            try:
                if path.exists() and path.stat().st_size > limit:
                    path.replace(path.with_name(path.stem + ".old.log"))
                with open(path, "a", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
            except OSError:
                pass

    return trail


def handle_request(world, role, target, now, cid="local"):
    reply = _handle_request(world, role, target, now, cid)
    world.trace(role, cid, target, reply)
    if role == "cli" and not target.startswith(("/pg", "/tr")):
        p = world.players.get(cid)
        if p is not None:
            p.recent = (p.recent + [(now, target, reply)])[-RECENT_KEPT:]
    return reply


def quiet_note(p, now):
    """A player game that just went quiet: its last request (game hour, map state) and the replies
    before, the parties among them by id, template and the party they are inside: a hang shows what
    the game was handling."""
    if not p.recent:
        return None
    when, target, _ = p.recent[-1]
    query = {k: v[0] for k, v in parse_qs(urlparse(target).query, keep_blank_values=True).items()}
    state = " ".join(f"{k}={query[k]}" for k in ("h", "free", "busy", "mp", "x", "y", "dbg") if k in query)
    replies = []
    for _, _, reply in p.recent[-RECENT_SHOWN:]:
        parts = reply.split("|")
        if len(parts) > 2 and parts[1] == "2":
            try:
                nums = [int(v) for v in parts[3:]]
            except ValueError:
                continue
            entries = [nums[i:i + 7] for i in range(0, len(nums) - 6, 7)]
            replies.append("2:" + ",".join(f"{e[0]}/{'gone' if e[1] == REMOVED else e[1]}"
                                           f"{'@' + str(e[6] - 1) if e[1] != REMOVED and e[6] else ''}"
                                           for e in entries))
        else:
            replies.append("|".join(parts[1:6]))
    return (f"player {p.slot}:{p.name or p.cid} quiet since {time.strftime('%H:%M:%S', time.localtime(when))}: "
            f"last request {state}; last replies {'; '.join(replies)}")


def _handle_request(world, role, target, now, cid="local"):
    url = urlparse(target)
    # blank values kept: "me=" is a party of heroes only, not "no report" (troops given away stayed
    # in the giver's battles until it had a soldier again)
    q = {k: v[0] for k, v in parse_qs(url.query, encoding="latin-1", keep_blank_values=True).items()}
    if role == "srv" and url.path == "/srv":
        world.clock("srv", parse_hours(q), now)
        pause, joins, puppets, payload, name = world.server_report(
            parse_entries(q.get("d", "")), parse_troops(q.get("c", "")), now, hold=q.get("hold") == "1",
            center=parse_center(q.get("cf", "")), hours=parse_hours(q), battles=parse_battles(q.get("lb", "")))
        nums = [MARKER, 1, int(pause), joins, len(puppets)]
        for slot, x, y, faction in puppets:
            nums += [slot, x + COORD_OFFSET, y + COORD_OFFSET, faction]
        return reply_text(nums + payload, name)
    if role == "cli" and url.path == "/pg":
        return reply_text([MARKER] + world.ping(cid, now))
    if role == "cli" and url.path == "/tr":  # not a sign of life: a report's silences stay what they were
        world.trail(cid, q)
        return reply_text([TRAIL_ACK])
    if role == "cli" and url.path == "/cli":
        try:
            x, y = int(q.get("x", "0")), int(q.get("y", "0"))
        except ValueError:
            x = y = 0
        busy = q.get("busy", "0") not in ("", "0")
        world.clock("cli", parse_hours(q), now)
        if q.get("free") == "1":
            world.clock("cli_map", parse_hours(q), now)
        me = None
        if "me" in q:  # present but empty: the player's party has only heroes
            me = parse_stacks(parse_ints(q["me"].lstrip(","))) if q["me"].lstrip(",") else []
        name = game_text_in(q.get("name", "")).replace("|", " ").strip()[:40] or None
        mp = None
        if "mp" in q:
            troops = q.get("mpt", "").lstrip(",")
            hero = parse_ints(q.get("hero", ""))
            comp = parse_ints(q.get("comp", "")) if "comp" in q else None
            mp = {"op": query_int(q, "mp", 0), "bid": query_int(q, "bid", 0), "sid": query_int(q, "mpe", -1),
                  "slot": query_int(q, "mpp", -1), "center": query_int(q, "mpc", -1), "defend": q.get("mpd") == "1",
                  "compn": query_int(q, "compn", 0) if "compn" in q else None,
                  "comp": (comp[0], comp[1:]) if comp and len(comp) == HERO_NUMBERS + 1 else None,
                  "terrain": query_int(q, "ter", 0),
                  "event": parse_event(q.get("mpx", "")),
                  "kind": query_int(q, "mpk", 0),
                  "troops": (parse_stacks(parse_ints(troops)) or []) if troops else [],
                  "ally": query_int(q, "mpa", -1),
                  "ally_troops": parse_stacks(parse_ints(q.get("mpat", "").lstrip(","))) or [],
                  "hero": hero if hero and len(hero) == HERO_NUMBERS else None}
        together = parse_together(q)
        nums, string = world.player_request(cid, x, y, busy, parse_result(q.get("res", "")), me, now,
                                            hello=q.get("hello") == "1", bye=q.get("bye") == "1", name=name, mp=mp,
                                            on_server=q.get("srvp") == "1",
                                            faction=query_int(q, "fac", 0) if "fac" in q else None,
                                            profile=parse_profile(q.get("pf", "")),
                                            profile_ask=q.get("pfq") == "1", together=together,
                                            build=query_int(q, "ver", 0) if "ver" in q else None,
                                            hours=parse_hours(q), lord=query_int(q, "lord", -1))
        return reply_text([MARKER] + nums, string)
    if role == "mp" and url.path == "/mp":
        nums = world.mp_request(query_int(q, "st", 0), query_int(q, "bid", 0), query_int(q, "w", -1),
                                parse_fallen(q.get("r", "")), parse_mp_players(q.get("pl", "")), now,
                                parse_weapons(q.get("wx", "")), parse_fallen(q.get("hp", "")),
                                parse_fallen(q.get("kl", "")))
        string = None
        if nums == [0]:
            notice = world.mp_notice()
            if notice is not None:
                nums, string = [3, notice[0]], notice[1]
        return reply_text([MP_MARKER] + nums, string)
    return reply_text([0, 0])  # unknown path: no marker, the game ignores it


# ---- HTTP for the games on this PC

def read_http_target(conn):
    raw = b""
    while b"\r\n\r\n" not in raw and len(raw) < 65536:
        chunk = conn.recv(8192)
        if not chunk:
            break
        raw += chunk
    # the request line may hold raw spaces (a player name): the target ends at " HTTP/"
    line = raw.split(b"\r\n", 1)[0].decode("latin-1", "replace")
    start, end = line.find(" ") + 1, line.rfind(" HTTP/")
    return line[start:end] if 0 < start <= end else (line[start:] or "/")


def send_http_body(conn, text):
    # latin-1 both ways: a name in the game's own code page comes back as the same bytes
    body = text.encode("latin-1", "replace")
    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n"
                 + f"Content-Length: {len(body)}\r\n\r\n".encode() + body)


def listen_socket(host, port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        # with SO_REUSEADDR Windows lets another program bind the same address and silently take
        # the games' requests away: claim it alone, so a clash (another bridge) fails loudly
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((host, port))
    except OSError as e:
        raise SystemExit(f"{host}:{port} is taken by another program ({e}): close it (another bridge window?) and start again")
    return srv


def serve_http(addr, answer, log, name):
    """Accept the games' HTTP requests on addr; answer(target) -> reply text."""
    host, port = addr
    srv = listen_socket(host, port)
    srv.listen(32)
    log(f"{name}: listening on {host}:{port}")

    def one(conn):
        conn.settimeout(5)
        target = None
        try:
            target = read_http_target(conn)
            send_http_body(conn, answer(target))
        except OSError as e:
            log(f"{name}: connection error {e}")
        except Exception as e:  # a request the bridge cannot read: say which, the game gets no reply
            log(f"{name}: could not handle {str(target)[:300]!r}: {e!r}")
        finally:
            conn.close()

    def loop():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=one, args=(conn,), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return srv


# ---- the network between the hub and the relays: one JSON message per line

def carries_news(body):
    """Whether a reply tells the game something it is not told again anyway: everything but the
    positions, other players' parties and the pause status, which come round all the time."""
    kind = body.split("|")[1] if body.count("|") >= 1 and body.startswith(str(MARKER)) else ""
    return kind.isdigit() and int(kind) not in (0, 2, 4, 5, 33)


def hold_ping(target):
    """A game off the map keeps one ping on its way: held here, it costs next to nothing."""
    if target.startswith("/pg") and "hold=1" in target:
        time.sleep(PING_HOLD_S)


def sound_the_call(text, log):
    """The bridge's window calls too: the game's own signal does not reach every screen."""
    log(text)
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except (ImportError, RuntimeError):
        pass


def keep_alive(sock):
    """Let the system notice a link that died without a word (a VPN dropping the route)."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, "SIO_KEEPALIVE_VALS"):
            sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 5000, 1000))
    except (OSError, ValueError):
        pass


def send_msg(sock, lock, msg):
    data = (json.dumps(msg) + "\n").encode()
    with lock:
        sock.sendall(data)


def read_msgs(sock):
    buf = b""
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            return
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if line.strip():
                yield json.loads(line)


def store_save(save_dir, rep, slot_name=None):
    """Write a save of the host into save_dir. Without slot_name: the file written last time
    (remembered in FETCHED_MARK), else the host's own name when free, else the lowest free sgNN:
    the game lists only the low slots, a high one such as sg90 never showed up. A file it replaces
    is kept as .bak."""
    folder = Path(save_dir)
    folder.mkdir(parents=True, exist_ok=True)  # a player who never saved in this module has no folder
    mark = folder / FETCHED_MARK
    if slot_name is None and mark.exists() and (folder / mark.read_text().strip()).exists():
        slot_name = mark.read_text().strip()
    if slot_name is None:
        free = [n for n in [rep["name"]] + [f"sg{i:02d}.sav" for i in range(100)] if not (folder / n).exists()]
        slot_name = free[0]
    target = folder / slot_name
    mark.write_text(slot_name)
    if target.exists():
        target.replace(target.with_suffix(".sav.bak"))
    target.write_bytes(base64.b64decode(rep["data"]))
    return target


def newest_save(save_dir):
    saves = sorted(Path(save_dir).glob("sg*.sav"), key=lambda p: p.stat().st_mtime) if save_dir else []
    return saves[-1] if saves else None


def save_stamp(path):
    """Which save of the host this is: a player that has it needs it no more."""
    st = path.stat()
    return f"{path.name}:{st.st_size}:{int(st.st_mtime)}"


def serve_relays(addr, world, key, save_dir, log):
    """The hub side of the network: each relay connection is one player."""
    host, port = addr
    srv = listen_socket(host, port)
    srv.listen(8)
    log(f"net: listening for players on {host}:{port}")
    if save_dir and newest_save(save_dir) is None:
        log(f"net: no save yet in {save_dir}: start or load the campaign and save it - "
            "every save of the host goes to the players who joined")
    counter = [0]
    owners = {}  # cid -> the connection serving it now (a reconnect takes the player over)
    links = {}   # cid -> (connection, its send lock): where a new save of the host goes

    def save_message(path):
        return {"t": "save", "name": path.name, "stamp": save_stamp(path),
                "data": base64.b64encode(path.read_bytes()).decode()}

    def push_save(cid, conn, lock, msg, why):
        try:
            send_msg(conn, lock, {"t": "save_coming", "size": len(msg["data"])})
            send_msg(conn, lock, dict(msg, push=True))
            log(f"net: {why}: {msg['name']} sent to {cid}")
        except OSError as e:
            log(f"net: could not send the save to {cid}: {e}")

    def push_saves():
        """Every save the host makes goes to all players at once: the next session starts from it."""
        def state():
            path = newest_save(save_dir)
            return (path, path.stat().st_mtime, path.stat().st_size) if path else None
        known = state()
        while True:
            time.sleep(SAVE_POLL_S)
            try:
                now_state = state()
                if now_state is None or now_state == known:
                    continue
                time.sleep(SAVE_POLL_S)  # the game may still be writing it
                if state() != now_state:
                    continue
                known = now_state
                msg = save_message(now_state[0])
            except OSError:
                continue
            world.host_saved()
            for cid, (conn, lock) in list(links.items()):
                push_save(cid, conn, lock, msg, "the host saved")

    if save_dir:
        threading.Thread(target=push_saves, daemon=True).start()

    def drop_later(cid, conn):
        time.sleep(RECONNECT_GRACE_S)
        if owners.get(cid) is conn:
            owners.pop(cid, None)
            world.drop_player(cid)  # gone: its silence no longer pauses the world
            log(f"net: player {cid} left")

    def one(conn, peer):
        counter[0] += 1
        cid = f"net{counter[0]}@{peer[0]}"
        lock = threading.Lock()
        keep_alive(conn)
        try:
            msgs = read_msgs(conn)
            hello = next(msgs, None)
            if (not hello or hello.get("t") != "hello" or hello.get("protocol") != PROTOCOL
                    or not hmac.compare_digest(str(hello.get("key", "")), key)):
                send_msg(conn, lock, {"t": "refused", "why": "wrong key or protocol"})
                log(f"net: refused {peer[0]}")
                return
            session = "".join(ch for ch in str(hello.get("session", "")) if ch.isalnum())[:16]
            if session:
                cid = f"net-{session}@{peer[0]}"
            again = cid in owners
            owners[cid] = conn
            links[cid] = (conn, lock)
            send_msg(conn, lock, {"t": "welcome", "cid": cid})
            world.set_mp_name(cid, hello.get("mp_name"))
            log(f"net: player {cid} {'connected again' if again else 'connected'}"
                + (f", multiplayer name '{hello['mp_name']}'" if hello.get("mp_name") else ""))
            if hello.get("saves") and save_dir:
                # a player that keeps the host's saves: one it missed while away comes now
                try:
                    path = newest_save(save_dir)
                    if path is not None and save_stamp(path) != hello.get("save_stamp"):
                        push_save(cid, conn, lock, save_message(path), "a save the player did not have")
                except OSError:
                    pass
            for msg in msgs:
                if msg.get("t") == "log":
                    log(f"[{cid}] {str(msg.get('text', ''))[:500]}")
                elif msg.get("t") == "req":
                    body = handle_request(world, "cli", msg.get("target", "/"), time.time(), cid=cid)
                    send_msg(conn, lock, {"t": "rep", "id": msg.get("id"), "body": body})
                elif msg.get("t") == "sig":
                    send_msg(conn, lock, {"t": "sig", "text": world.signal_text(cid)})
                elif msg.get("t") == "save":
                    path = newest_save(save_dir)
                    if path is None:
                        send_msg(conn, lock, {"t": "save", "error": f"the host has no save yet in {save_dir}"})
                    else:
                        send_msg(conn, lock, save_message(path))
                        log(f"net: sent save {path.name} to {cid}")
        except (OSError, ValueError) as e:
            log(f"net: {cid} error {e}")
        finally:
            conn.close()
            if links.get(cid, (None,))[0] is conn:
                links.pop(cid, None)
            if owners.get(cid) is conn:
                log(f"net: lost {cid}; its player waits {RECONNECT_GRACE_S:.0f} s for it to come back")
                threading.Thread(target=drop_later, args=(cid, conn), daemon=True).start()

    def loop():
        while True:
            conn, peer = srv.accept()
            threading.Thread(target=one, args=(conn, peer), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return srv


class Relay:
    """The friend's side: forwards its player game's requests to the hub, one at a time."""

    def __init__(self, hub, key, log, timeout=3.0, mp_name=None):
        self.hub, self.key, self.timeout = hub, key, timeout
        self.local_log = log
        self.unsent_log = []    # lines for the host's log written while the link was down
        self.mp_name = mp_name
        self.sock = None
        self.lock = threading.Lock()
        self.waiting = {}   # request id -> [event, reply]
        self.next_id = 0
        self.connected = threading.Event()
        self.session = secrets.token_hex(6)  # the same player for the hub over reconnects
        self.request_count = 0
        self.misses = 0
        self.save_dir = None    # where the host's saves go as the host makes them (join: --save-dir)
        self.saves = False      # the first save fetched (or tried): the hub then sends any one missed
        self.save_stamp = None  # the host's save this player has (see save_stamp)
        self.quiet_until = 0.0  # a save on its way: replies behind it come late, the link is fine
        self.trail = lambda cid, query: None  # run_join: this player's own trail.log
        self.late = []          # replies with news that came after their request gave up: next ones

    def log(self, msg):
        """This relay's log, and the host's: a line goes over the link too (kept until it is up)."""
        self.local_log(msg)
        self.unsent_log = (self.unsent_log + [f"{time.strftime('%H:%M:%S')} {msg}"])[-100:]
        self._flush_log()

    def _flush_log(self):
        if not self.connected.is_set() or self.sock is None:
            return
        try:
            while self.unsent_log:
                send_msg(self.sock, self.lock, {"t": "log", "text": self.unsent_log[0]})
                self.unsent_log.pop(0)
        except OSError:
            pass

    def connect(self):
        sock = socket.create_connection(self.hub, timeout=10)
        sock.settimeout(None)
        keep_alive(sock)
        send_msg(sock, self.lock, {"t": "hello", "key": self.key, "protocol": PROTOCOL, "mp_name": self.mp_name,
                                   "session": self.session, "saves": bool(self.saves and self.save_dir),
                                   "save_stamp": self.save_stamp})
        msgs = read_msgs(sock)
        first = next(msgs, None)
        if not first or first.get("t") != "welcome":
            sock.close()
            raise ConnectionError((first or {}).get("why", "no answer from the host"))
        self.sock = sock
        self.misses = 0
        self.connected.set()
        self._flush_log()
        self.log(f"relay: connected to the host as {first.get('cid')}")
        threading.Thread(target=self._reader, args=(msgs, sock), daemon=True).start()

    def _reader(self, msgs, sock):
        try:
            for msg in msgs:
                if msg.get("t") == "save_coming":
                    self.quiet_until = time.time() + 15 + msg.get("size", 0) / 100_000
                    continue
                if msg.get("t") == "save" and msg.get("push"):
                    self._take_pushed_save(msg)
                    continue
                waiter = self.waiting.pop(msg.get("id"), None) if msg.get("t") == "rep" else \
                    self.waiting.pop(msg["t"], None) if msg.get("t") in ("save", "sig") else None
                if waiter:
                    waiter[1] = msg
                    waiter[0].set()
                elif msg.get("t") == "rep" and carries_news(msg.get("body", "")):
                    self.late.append(msg["body"])
        except (OSError, ValueError):
            pass
        if self.sock is sock:  # not a link already replaced by a new one
            self.connected.clear()
            self.log("relay: lost the host")

    def call(self, msg, wait_key):
        waiter = [threading.Event(), None]
        self.waiting[wait_key] = waiter
        try:
            send_msg(self.sock, self.lock, msg)
        except (OSError, AttributeError):
            self.waiting.pop(wait_key, None)
            return None
        waiter[0].wait(self.timeout if wait_key != "save" else 120)
        self.waiting.pop(wait_key, None)
        return waiter[1]

    def watch_signal(self):
        while True:
            time.sleep(1.0)
            if self.connected.is_set():
                rep = self.call({"t": "sig"}, "sig")
                if rep and rep.get("text"):
                    sound_the_call(rep["text"], self.local_log)

    def pass_trail(self, target):
        """A debug build's trail goes by on its own: kept here too, told to the hub without waiting for it
        (no one waits for reply 0), so it stands in line with no request of the game."""
        self.trail("local", {k: v[0] for k, v in parse_qs(urlparse(target).query).items()})
        if self.connected.is_set():
            try:
                send_msg(self.sock, self.lock, {"t": "req", "id": 0, "target": target})
            except (OSError, AttributeError):
                pass
        return reply_text([TRAIL_ACK])

    def forward(self, target):
        if target.startswith("/tr"):
            return self.pass_trail(target)
        hold_ping(target)
        if not self.connected.is_set():
            return reply_text([0, 0])  # no marker: the game frees its request and tries again
        with self.lock:
            self.next_id += 1
            rid = self.next_id
        rep = self.call({"t": "req", "id": rid, "target": target}, rid)
        if rep:
            self.misses = 0
            if self.late:  # news that came late goes first; this reply waits its turn if it has news too
                if carries_news(rep["body"]):
                    self.late.append(rep["body"])
                return self.late.pop(0)
            return rep["body"]
        if time.time() >= self.quiet_until:
            self.misses += 1
        if self.misses == RELAY_MISSES and self.connected.is_set():
            # the hub went quiet without closing the link: drop it, keep_connected makes a new one
            self.log("relay: the host stopped answering; reconnecting")
            self.connected.clear()
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except OSError:
                pass
        return reply_text([0, 0])

    def _take_pushed_save(self, msg):
        if not self.save_dir:
            return
        try:
            path = store_save(self.save_dir, msg)
            self.save_stamp = msg.get("stamp")
            self.log(f"relay: the host saved the game - {path} now holds it (load it to start from there)")
        except (OSError, ValueError) as e:
            self.log(f"relay: could not keep the host's new save: {e}")

    def fetch_save(self, save_dir, slot_name=None):
        """Copy the host's newest save into save_dir (see store_save)."""
        rep = self.call({"t": "save"}, "save")
        if not rep or rep.get("error"):
            raise RuntimeError((rep or {}).get("error", "no answer"))
        path = store_save(save_dir, rep, slot_name)
        self.save_stamp = rep.get("stamp")
        return path, rep["name"]

    def keep_connected(self):
        while True:
            if not self.connected.is_set():
                try:
                    self.connect()
                except (OSError, ConnectionError) as e:
                    self.log(f"relay: cannot reach the host: {e}; retrying")
            time.sleep(3)


# ---- the battle relay (see the top of this file)

def battle_tag(key):
    return hmac.new(key.encode(), b"battle relay", "sha256").digest()[:BATTLE_TAG]


LAN_NETWORKS = [ipaddress.ip_network(n) for n in ("192.168.0.0/16", "172.16.0.0/12", "10.0.0.0/8")]


def lan_rank(addr):
    """The place of addr's network in LAN_NETWORKS; None if it is not a local network address."""
    a = ipaddress.ip_address(addr)
    return next((i for i, n in enumerate(LAN_NETWORKS) if a.version == 4 and a in n), None)


def lan_address():
    """This PC's address in its local network: the one the battle server sees the relayed friends
    come from. A home network's 192.168.x first (a VPN client such as AmneziaVPN holds a 10.x one
    that is gone once it disconnects), the default route's first among equals; 127.0.0.1 if none."""
    found = []
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 53))  # no datagram is sent: only picks the route
        found.append(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    try:
        found += [i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    except OSError:
        pass
    local = sorted((lan_rank(a), i, a) for i, a in enumerate(found) if lan_rank(a) is not None)
    return local[0][2] if local else "127.0.0.1"


def udp_socket(addr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(addr)
    return sock


class BattleLink:
    """One game's datagrams through the battle relay: the socket on the far side, and how many went
    each way. The server list opens a link for every look, a game on the server keeps one."""

    def __init__(self, sock):
        self.sock = sock
        self.start = self.last = time.time()
        self.out = self.back = 0

    def playing(self):
        return self.out >= BATTLE_PLAYING

    def summary(self):
        return f"after {int(self.last - self.start)} s, {self.out} datagrams there and {self.back} back"


def _relay_back(link, links, key_of, lock, forward, closed):
    """Datagrams coming back on one link's socket go out with forward(data) until the link has been
    silent for BATTLE_IDLE_S; then closed() is called."""
    while True:
        link.sock.settimeout(min(5.0, BATTLE_IDLE_S))
        try:
            data = link.sock.recv(65535)
        except socket.timeout:
            with lock:
                if links.get(key_of) is not link:
                    break
                if time.time() - link.last < BATTLE_IDLE_S:
                    continue
                links.pop(key_of, None)
            closed()
            break
        except ConnectionResetError:  # Windows: the other end's port was not open for a moment
            continue
        except OSError:
            break
        link.back += 1
        forward(data)
    link.sock.close()


def serve_battle_hub(addr, key, port, source, log):
    """The host's side: each friend's game gets its own socket from `source` (default: this PC's
    local address, looked up for each new game) to the battle server on `port` at that address, so
    the server tells the friends apart and lets them in."""
    tag = battle_tag(key)
    try:
        hub = udp_socket(addr)
    except OSError as e:
        log(f"battle relay: cannot listen on UDP {addr[0]}:{addr[1]} ({e}); friends join the battle server directly")
        return None
    links = {}  # the friend's bridge address -> BattleLink to the battle server
    lock = threading.Lock()

    def loop():
        while True:
            try:
                data, peer = hub.recvfrom(65535)
            except ConnectionResetError:
                continue
            except OSError:
                return
            if len(data) <= BATTLE_TAG or not hmac.compare_digest(data[:BATTLE_TAG], tag):
                continue
            with lock:
                link = links.get(peer)
                if link is None:
                    here = source or lan_address()
                    try:
                        sock = udp_socket((here, 0))
                        sock.connect((here, port))
                    except OSError as e:
                        log(f"battle relay: cannot reach the battle server {here}:{port}: {e}")
                        continue
                    link = links[peer] = BattleLink(sock)

                    def forward(back, peer=peer):
                        try:
                            hub.sendto(tag + back, peer)
                        except OSError:
                            pass

                    def closed(link=link, peer=peer):
                        if link.playing():
                            log(f"battle relay: the game from {peer[0]} left the battle server {link.summary()}")
                    threading.Thread(target=_relay_back, args=(link, links, peer, lock, forward, closed),
                                     daemon=True).start()
                link.last = time.time()
                link.out += 1
                if link.out == BATTLE_PLAYING:
                    log(f"battle relay: a game from {peer[0]} is on the battle server through the bridge "
                        f"(the server sees it as {link.sock.getsockname()[0]}:{link.sock.getsockname()[1]})")
            try:
                link.sock.send(data[BATTLE_TAG:])
            except OSError:
                pass

    threading.Thread(target=loop, daemon=True).start()
    log(f"battle relay: friends' second windows join the battle server (port {port}) through the bridge; "
        f"it sees them come from {source or lan_address()}, a local address")
    return hub


def rgl_setting_on(config, setting):
    """A setting of Warband's rgl_config.txt: True, False, or None when the file or the line cannot
    be read."""
    try:
        text = Path(config).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        name, _, value = line.partition("=")
        if name.strip() == setting:
            return value.strip() != "0"
    return None


def lan_search_on(config):
    return rgl_setting_on(config, "look_for_server_on_this_machine")


def tell_full_screen(config, log):
    """Two full-screen Warband windows hang when switching back after a joint battle (found 28.10):
    the setting stays the player's, the bridge's window says so."""
    if rgl_setting_on(config, "start_windowed") is False:
        log("battle relay: Warband is set to full screen - two full-screen windows can hang. Turn on Start "
            "windowed in the launcher (Configure) / Warband запускается на весь экран: два полноэкранных окна "
            "могут зависать. Включите Start windowed в лаунчере (Configure)")


def watch_lan_search(config, log, every=10, stop=None):
    """Off, the second window never sends the bridge a thing and the player only sees an empty
    list: says so in the bridge's window, at once and again whenever a closing Warband turns it off."""
    told = False
    while True:
        on = lan_search_on(config)
        if on is False and not told:
            log("battle relay: look_for_server_on_this_machine = 0 - the second window will NOT see the battle "
                "server. Close every Warband window, run join.bat again and agree to turn it on / "
                "ВЫКЛЮЧЕНО: второе окно НЕ увидит сервер боя. Закройте все окна Warband, запустите join.bat "
                "снова и согласитесь включить")
        elif on and told:
            log("battle relay: look_for_server_on_this_machine is on now; start Warband again if it was open")
        if on is not None:
            told = not on
        if stop is not None and stop.wait(every):
            return
        if stop is None:
            time.sleep(every)


def serve_battle_join(local, hub_addr, key, log):
    """The friend's side: the second Warband window finds and joins the battle server at `local`;
    its datagrams go to the host's bridge with the key's tag, the answers come back."""
    tag = battle_tag(key)
    try:
        game = udp_socket(local)
    except OSError as e:
        log(f"battle relay: cannot listen on UDP {local[0]}:{local[1]} ({e}); join the battle server directly")
        return None
    links = {}  # the game's address -> BattleLink to the host's bridge
    lock = threading.Lock()

    def loop():
        while True:
            try:
                data, src = game.recvfrom(65535)
            except ConnectionResetError:
                continue
            except OSError:
                return
            with lock:
                link = links.get(src)
                if link is None:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    try:
                        sock.connect(hub_addr)
                    except (OSError, UnicodeError) as e:
                        sock.close()
                        if not unreachable[0]:
                            unreachable[0] = True
                            log(f"battle relay: cannot reach the host's bridge at {hub_addr[0]}:{hub_addr[1]} ({e})")
                        continue
                    unreachable[0] = False
                    link = links[src] = BattleLink(sock)
                    if not looked[0]:
                        looked[0] = True
                        log("battle relay: the second window found the battle server through the bridge")

                    def forward(back, src=src):
                        if len(back) > BATTLE_TAG and hmac.compare_digest(back[:BATTLE_TAG], tag):
                            try:
                                game.sendto(back[BATTLE_TAG:], src)
                            except OSError:
                                pass

                    def closed(link=link):
                        if link.playing():
                            log(f"battle relay: the second window left the battle server {link.summary()}")
                    threading.Thread(target=_relay_back, args=(link, links, src, lock, forward, closed),
                                     daemon=True).start()
                link.last = time.time()
                link.out += 1
                if link.out == BATTLE_PLAYING:
                    log("battle relay: the second window is on the battle server through the bridge")
            try:
                link.sock.send(tag + data)
            except OSError:
                pass

    looked = [False]
    unreachable = [False]  # told once until a link opens again
    threading.Thread(target=loop, daemon=True).start()
    log(f"battle relay: the battle server waits for the second Warband window at {local[0]}:{local[1]}: "
        "Multiplayer - Join a game - Local area network (needs look_for_server_on_this_machine = 1 "
        "in Documents\\Mount&Blade Warband\\rgl_config.txt)")
    config = documents_dir() / "Mount&Blade Warband" / "rgl_config.txt"
    threading.Thread(target=watch_lan_search, args=(config, log), daemon=True).start()
    tell_full_screen(config, log)
    return game


# ---- main

def parse_addr(text, default_port):
    host, _, port = text.partition(":")
    return host, int(port or default_port)


# a dot typed with the Russian keyboard layout ('ю', 'б'), or the number pad's comma; ':' is 'Ж' there
LAYOUT_SLIPS = str.maketrans({"ю": ".", "Ю": ".", "б": ".", "Б": ".", ",": ".", "ж": ":", "Ж": ":"})


def tidy_host_address(text):
    """The host's address as a friend typed it: spaces dropped, and the keyboard slips of LAYOUT_SLIPS
    mended when that makes it an IPv4 address (with a port or not)."""
    plain = "".join(text.split())
    mended = plain.translate(LAYOUT_SLIPS)
    host, _, port = mended.partition(":")
    try:
        ipaddress.IPv4Address(host)
    except ValueError:
        return plain
    if port and not (port.isdigit() and 0 < int(port) < 65536):
        return plain
    return mended


def check_host_address(text, default_port):
    """(host, port) of the host's bridge from what the friend typed; ValueError saying what to fix
    when it is no address (join.bat asks again on the next start)."""
    addr = tidy_host_address(text)
    try:
        host, port = parse_addr(addr, default_port)
        socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    except (OSError, ValueError, UnicodeError):
        raise ValueError(
            f"'{text}' is not the host's address. Start join.bat again and type the address Radmin VPN "
            "shows for the host: four numbers with dots, e.g. 26.12.34.56 (no spaces; with the Russian "
            f"keyboard layout the dot key types 'ю'). / '{text}' - не адрес хоста. Запустите join.bat снова "
            "и введите адрес хоста из Radmin VPN: четыре числа через точку, например 26.12.34.56 (без "
            "пробелов; в русской раскладке клавиша точки печатает 'ю')") from None
    return host, port


def documents_dir():
    """The Documents folder as Windows knows it: it may be moved (OneDrive, another drive), and
    Warband keeps its saves there."""
    try:
        import ctypes
        from ctypes import wintypes
        folder_id = ctypes.c_byte * 16
        documents = folder_id.from_buffer_copy(bytes.fromhex("d09ad3fd8f23af46adb46c85480369c7"))  # FOLDERID_Documents
        path = wintypes.LPWSTR()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(documents), 0, None, ctypes.byref(path)) == 0:
            try:
                return Path(path.value)
            finally:
                ctypes.windll.ole32.CoTaskMemFree(path)
    except (AttributeError, OSError, ValueError):
        pass
    return Path.home() / "Documents"


def default_save_dir():
    return documents_dir() / "Mount&Blade Warband Savegames" / MODULE_NAME


def make_log(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(path, "a", encoding="utf-8")

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        log_file.write(line + "\n")
        log_file.flush()

    return log


def run_host(args, log):
    world = World(args.profiles or Path(args.log).with_name("profiles.json"))
    world.log = log
    world.trace = make_trace(Path(args.log).with_name("trace.log"))
    world.trail = make_trail(Path(args.log).with_name("trail.log"))
    log(f"logs: {Path(args.log).resolve()} and trace.log next to it (requests about battles, parties, joining)")
    world.set_mp_name("local", args.mp_name)
    serve_http(parse_addr(args.server, 80), lambda t: handle_request(world, "srv", t, time.time()), log, "srv")

    def answer_player(target):
        hold_ping(target)
        return handle_request(world, "cli", target, time.time())

    def watch_signal():
        while True:
            time.sleep(1.0)
            text = world.signal_text("local")
            if text:
                sound_the_call(text, log)

    serve_http(parse_addr(args.client, 80), answer_player, log, "cli")
    serve_http(parse_addr(args.mp, 80), lambda t: handle_request(world, "mp", t, time.time()), log, "mp")
    threading.Thread(target=watch_signal, daemon=True).start()
    if args.key:
        serve_relays(parse_addr(args.listen, NET_PORT), world, args.key, args.save_dir, log)
        serve_battle_hub(parse_addr(args.listen, NET_PORT), args.key, args.battle_port, args.battle_from, log)
    else:
        log("net: no --key given, other players cannot join (this PC only)")
    last = dict(world.stats)
    last_cause = None
    known = None
    while True:
        time.sleep(5)
        # who the battle server recognises: told whenever it changes
        seen = world.mp_recognition(time.time())
        on_server = sorted(world.mp_players.values())
        if world._mp_online(time.time()) and (seen, on_server) != known:
            for slot, hero, wanted, no in seen:
                if no is None:
                    log(f"battle server: player {slot} ({hero}) NOT found - nobody there is named '{wanted}'. "
                        f"Joint battles: that player's soldiers fight without the player")
                else:
                    log(f"battle server: player {slot} ({hero}) recognised as '{wanted}' (player {no} there)")
            if not seen:
                log("battle server: no campaign players yet")
            names = ", ".join(f"'{n}'" for n in world.mp_players.values()) or "nobody"
            log(f"battle server: on it now: {names}")
        known = (seen, on_server) if world._mp_online(time.time()) else None
        with world.lock:
            s, n = dict(world.stats), len(world.parties)
            now = time.time()
            cause = world.pause_cause(now)
            paused = cause is not None
            if cause != last_cause:
                if cause is None:
                    log("world runs again")
                else:
                    who = world._player_in_slot(cause[0])
                    log(f"world held by player {cause[0]} ({who.cid if who else '?'}): "
                        + ("in an encounter or battle" if cause[1] == 1 else
                           "silent - a menu, a screen, loading, or its game/link froze"))
                last_cause = cause
            for p in world.players.values():
                quiet = p.last is not None and now - p.last > QUIET_NOTE_S
                if quiet and not p.quiet_told:
                    note = quiet_note(p, now)
                    if note:
                        log(note)
                p.quiet_told = quiet
            def alive(p):  # silent for the world, but its game answers: a menu, not a hang
                return " alive" if p.pinged is not None and now - p.pinged < ALIVE_S else ""
            players = ", ".join(f"{p.slot}:{p.name or p.cid}{' busy' if p.busy else ''}"
                                f"{f' silent {now - p.last:.0f}s{alive(p)}' if p.last is not None and now - p.last > 2 else ''}"
                                f"{' mp:' + world.mp_names[p.cid] if p.cid in world.mp_names else ''}"
                                for p in sorted(world.players.values(), key=lambda p: (p.slot is None, p.slot)))
            mp_text = "battle server " + ("on" if world._mp_online(time.time()) else "off")
            if world.battle is not None:
                mp_text += f", battle {world.battle.bid} {world.battle.state} sides {world.battle.sides}"
        clocks = {r: world.clock_rate(r) for r in ("srv", "cli", "cli_map")}
        clock_text = ", ".join(f"{r} {'?' if v is None else f'{v:.1f}'} h/min" for r, v in clocks.items())
        rate = {k: (s[k] - last[k]) / 5 for k in s}
        log(f"parties {n}, server {rate['srv']:.1f}/s, players {rate['cli']:.1f}/s [{players or 'none'}], "
            f"{'PAUSED' if paused else 'running'}, results {s['results']}, {clock_text}, {mp_text}, "
            f"parties: {s['new'] - last['new']} new, {s['gone'] - last['gone']} gone, {s['back'] - last['back']} back")
        last = s


def fetch_first_save(relay, save_dir, slot_name, log):
    """join --fetch-save: the host's newest save into save_dir. A host with no save yet (a new
    campaign) or no answer does not stop the bridge: the host's next save comes here by itself."""
    try:
        path, name = relay.fetch_save(save_dir, slot_name)
    except RuntimeError as e:
        log(f"relay: no save from the host yet ({e}). Keep this window open: once the host saves the "
            f"game, the save comes into {save_dir} by itself - then load it in the game")
        return None
    log(f"relay: the host's save {name} is now {path} - load it in the game")
    return path


def run_join(args, log):
    try:
        hub = check_host_address(args.host, NET_PORT)
    except ValueError as e:
        log(f"relay: {e}")
        return
    if f"{hub[0]}:{hub[1]}" not in (args.host.strip(), f"{args.host.strip()}:{NET_PORT}"):
        log(f"relay: the host's address read as {hub[0]}:{hub[1]} (typed '{args.host}')")
    relay = Relay(hub, args.key, log, mp_name=args.mp_name)
    relay.trail = make_trail(Path(args.log).with_name("trail.log"))
    try:
        relay.connect()
    except (OSError, ConnectionError) as e:
        log(f"relay: cannot reach the host: {e}")
    relay.save_dir = args.save_dir if args.fetch_save else None  # each new save of the host lands here too
    threading.Thread(target=relay.keep_connected, daemon=True).start()  # retries until the host answers
    threading.Thread(target=relay.watch_signal, daemon=True).start()
    serve_battle_join(parse_addr(args.battle_listen, BATTLE_PORT), hub, args.key, relay.log)
    if args.fetch_save:
        if not relay.connected.is_set():
            log("relay: waiting for the host (check its address, the key, and that both PCs are on the same network)")
        relay.connected.wait()
        fetch_first_save(relay, args.save_dir, args.save_slot, log)
        relay.saves = True  # from now on a reconnect brings any save of the host missed meanwhile
    serve_http(parse_addr(args.client, 80), relay.forward, log, "cli")
    while True:
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description="Warband Coop Campaign bridge")
    sub = ap.add_subparsers(dest="mode")
    h = sub.add_parser("host", help="the hub on the host's PC (runs the world server game)")
    h.add_argument("--key", help="shared secret for other players; without it only this PC can play")
    h.add_argument("--listen", default=f"0.0.0.0:{NET_PORT}", help="where other players connect")
    h.add_argument("--server", default="127.0.0.1:80", help="address the world server game calls")
    h.add_argument("--client", default="127.0.0.2:80", help="address this PC's player game calls")
    h.add_argument("--mp", default="127.0.0.3:80", help="address the battle server game (multiplayer) calls")
    h.add_argument("--mp-name", default=None, help="the host's name on the battle server (multiplayer profile)")
    h.add_argument("--profiles", default=None, help="where the players' heroes are kept (default: profiles.json next to the log)")
    h.add_argument("--save-dir", default=str(default_save_dir()), help="the world server's saves")
    h.add_argument("--battle-port", type=int, default=BATTLE_PORT, help="the battle server's port")
    h.add_argument("--battle-from", default=None,
                   help="the address the battle server sees relayed friends come from (default: this PC's local address)")
    j = sub.add_parser("join", help="a relay on a friend's PC")
    j.add_argument("host", help="the host's address, e.g. 26.1.2.3 (Radmin VPN) or 192.168.1.5")
    j.add_argument("--key", required=True)
    j.add_argument("--client", default="127.0.0.2:80", help="address this PC's player game calls")
    j.add_argument("--fetch-save", action="store_true", help="copy the host's newest save here first")
    j.add_argument("--mp-name", default=None, help="this player's name on the battle server (multiplayer profile)")
    j.add_argument("--save-dir", default=str(default_save_dir()))
    j.add_argument("--battle-listen", default=BATTLE_LOCAL,
                   help="where the second Warband window joins the battle server through the bridge")
    j.add_argument("--save-slot", default=None,
                   help="file name for the fetched save (default: the one fetched last time, else a free low slot)")
    for p in (h, j):
        p.add_argument("--log", default=str(Path(__file__).resolve().parents[1] / "local" / "bridge.log"))
    args = ap.parse_args()
    if args.mode is None:
        args = ap.parse_args(["host"])  # the PC-only setup of the prototype
    log = make_log(args.log)
    try:
        (run_host if args.mode == "host" else run_join)(args, log)
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
