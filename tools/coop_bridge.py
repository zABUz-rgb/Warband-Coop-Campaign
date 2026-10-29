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

The battle relay: a friend's second Warband window joins the battle server at 127.0.0.1:7260 on
its own PC (Multiplayer - Favorites); the friend's bridge sends its datagrams to the host's bridge
(UDP, the relays' port), which hands them to the battle server from the host's own local address.
Warband lets players from a local network (192.168.x, 10.x) in at once but checks the others
against the internet address its authorization server saw, so a friend coming straight over a
virtual network (Radmin's 26.x) was turned away: "invalid authorization number".

    python tools/coop_bridge.py host --key SECRET [--listen 0.0.0.0:7350] [--mp-name NAME]
    python tools/coop_bridge.py join HOST_IP --key SECRET [--fetch-save] [--mp-name NAME]

--mp-name: the player's name on the battle server (multiplayer profile name). Joint battles find
the player there by it, so each player's soldiers obey that player; without it, by the hero's name
(which friends who loaded the host's save share with the host).

World server -> /srv?seq=S&h=H&n=K&d=sid,tmpl,x,y,tx,ty,att;...[&c=sid,t1,n1,...][&cf=center,faction,lord,besieger+1]
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
                    [&pf=seq,offset,total,v1,v2,...][&pfq=1][&join=slot][&joinans=slot,yes][&leave=1][&release=1]
                    [&give=slot,t1,n1,...][&giveans=id,yes]
                    [&me=t1,n1,...][&name=player name]
    fac: the kingdom the player serves (0: none); lord: the world party of the lord the player serves
    as a soldier (Freelancer), -1 or absent: none; pf: part of the player's hero (the profile, see
    coop/profile.py), kept by the hub in profiles.json under the player's name and sent back
    (kind 14) when that player joins again, or asks again with pfq (the answer got lost); join: ask the player in slot to take this one into the
    party; joinans: the answer to the player in slot asking; leave: leave the leader's party;
    release: let all followers go; give: offer troops to the player in slot; giveans: the answer
    to offer id (see coop/players.py);
    busy: not 0 from the start of an encounter until back on the map; hello: just joined; bye:
    stopped co-op; res: a battle result; me: its troops (empty: heroes only); name: last, may hold spaces;
    dbg: a client's state for the log when it goes quiet: parties, mirrors spawned, swept, Freelancer's
    state, clock (-1 ahead, 1 behind), the party its own is attached to;
    srvp=1: the host playing in the world server game itself (its party is real there, no puppet).
    A player game's triggers do not run in menus, screens and battles: it goes silent, and a player
    silent for SILENT_PAUSE_S pauses the world just like a busy one.
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
combat skills, weapon proficiencies and hit points (now, at most), in the order of coop/constants.py):
    OP 1 start a battle against the world party sid (mpt: its troops as the player sees them), the
    player in puppet slot, or storm the town or castle mpc (a siege: the players are team 1, the
    garrison team 0); with &mpd=1 defend that center against its besieger mpe (the players and the
    garrison team 0, the besieger and the army camped with it team 1);
    2 waiting; 3 accept an invitation; 4 decline, or cancel (the starter).
    With &mpa=sid[&mpat=t1,n1,...] (a start against a world party) the world party sid, the lord the
    player serves, fights on the players' side with its troops (mpat: as the player sees them). A
    start against the enemy of a battle still gathering joins that battle.
    reply 7777|6|bid|type|slot|sid   an invitation from the player in slot: type 1 may join, 2 attacked;
                                     sid: the world party fought (-1: a player), so the game can see
                                     whether it would fight its own allies
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
          7777|17|slot                         the player in slot asks to join this player's party
          7777|18|slot|accepted                the leader in slot took this player in, or not
          7777|19|slot|joined                  to a leader: the player in slot joined (1) or left (0)
          7777|20|slot                         the leader in slot let this player go
          7777|21|bid|n|(troop,count)*n        the player's share of the fallen enemies, to loot
    A follower is called into the leader's joint battles: invitation type 3, which cannot be declined.

Battle server -> /mp?seq=S&st=PHASE&bid=B[&w=WINNER&r=i,fallen;...&hp=no,percent;...&wx=no,wpt,hits,damage;...]
                  &pl=no~name;...
    PHASE 0 an ordinary round, 1-3 a battle of the campaign, 4 over (w: winning team, r: the bots
    each stack lost; hp: the heroes' health at the end, 0 fallen; wx: the heroes' hits and damage by
    weapon proficiency);
    pl: the players on the server, matched to the players of the campaign by name.
    reply 7778|0                                  nothing
          7778|2|bid|offset|n|(team,player,troop,count)*n   stacks to spawn (player: who commands them, -1 the AI)
          7778|5|bid|player|hero...               a player fights as the campaign hero (after the stacks)
          7778|6|bid|troop|hero...                a companion's gear and stats (its stack spawns it)
          7778|1|bid|stacks|mode|hint|n|(player,team)*n   start: players onto their sides, the round
                                                  restarts; mode 1 a siege (Siege game type, map by hint)
          7778|4|bid                              the outcome arrived

Coordinates are map units * 100, shifted by COORD_OFFSET in replies so the games only get
non-negative numbers. A reply holds at most 128 numbers (the engine's registers).
"""
import argparse
import base64
import hmac
import ipaddress
import json
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
CENTERS_PER_REPLY = 30  # 2 + 4 * 30 numbers
RENAME_EVERY = 40      # requests between asking a game to rename its hero
PROFILE_PER_REPLY = 120 # 5 + 120 numbers
STALE_S = 15.0          # a party not reported for this long is gone
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
ROTATING_PER_REPLY = 3
REMOVALS_PER_REPLY = 3
RESULT_PAIRS = 53       # troop and prisoner pairs of one battle result: 5 + 3 * 4 + 4 + 1 + 2 * 53 <= 128  # 3 header numbers + 7 per entry must stay within 128 registers
MAX_STACKS = 30         # troop stacks per party in one message
CLOCK_WINDOW_S = 60.0   # game clock speed is measured over this much real time
NET_PORT = 7350           # the relays' TCP link, and (UDP) the battle relay
BATTLE_PORT = 7240        # the battle server's own port (Multiplayer - Host a game)
BATTLE_LOCAL = "127.0.0.1:7260"  # on a friend's PC the second window joins the battle server here
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
INVITE_DIST = 1000      # map units * 100: players this close to the starter are invited
MP_MAX_BOTS = 150       # bots on the battle server; bigger armies are scaled down, losses scaled up
MP_MAX_STACKS = 60
MP_CHUNK = 30           # stacks per reply: 5 + 4 * 30 numbers
MP_LOST_S = 30.0        # a battle server back in an ordinary round this long after a start lost it
WOUNDED_PCT = 50        # of a player's fallen soldiers, this share is wounded rather than killed
XP_PER_ENEMY = 30       # battle experience for each fallen enemy, shared by the winning side's players;
                        # the losing side gets a third of it
MODULE_NAME = "Warband Coop Campaign"  # the module folder in Modules, and its save folder
HERO_NUMBERS = 31       # 9 equipment slots, 4 attributes, 9 combat skills, 7 proficiencies, hit points now and at most
COMPANIONS_WAIT_S = 5.0 # a battle waits this long for the starter's companions to arrive


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
        self.centers_sent = {}  # center -> (faction, lord, besieger + 1) this player was told
        self.profile_out = []   # the kept hero, in replies, after joining
        self.profile_in = None  # [seq, total, {offset: values}] the hero coming in
        self.leader = None      # cid of the player whose party this one follows
        self.join_asked = None  # cid of the player this one asked to join
        self.hours = None       # its game clock, as it last reported
        self.clock = 0          # -1 its clock is ahead of the world's, 1 behind, 0 the same time
        self.clock_since = None # when it last stopped being the same time
        self.lord = -1          # the world party of the lord it serves (Freelancer), -1 none
        self.lord_told = (-1, -1)  # (lord, enemy) it was last told


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
        self.companion_data = None  # [(troop, numbers)] still to send, after the heroes
        self.hero_troops = set()  # companions in the stacks: fallen means wounded, never killed
        self.terrain = 0
        self.created = now
        self.started = None
        self.told = set()         # invited players told on the battle server to answer in the campaign


class World:
    log = staticmethod(lambda msg: None)  # run_host sets the bridge's log: joint battles are told there
    trace = staticmethod(lambda role, cid, target, reply: None)  # run_host: trace.log of the requests that matter

    def __init__(self, profiles_path=None):
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
        self.centers = {}       # center -> (faction, lord, besieger + 1), as the world server reports them
        self.captures = []      # (center, kingdom) stormed in joint sieges, for the server
        self.saves = 0          # the host's saves sent to the players since the bridge started
        self.last_srv = None    # when the world server last reported
        self.srv_hours = None   # the world's clock (game hours), as the world server last reported it
        self.map_battles = {}   # sid -> (sid of the party it fights, real time last reported)
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
        """A player leaves the game: the leader is told, followers ride on alone, troops offered
        to this player go back to their giver."""
        p = self.players.get(cid)
        if p is None:
            return
        leader = self.players.get(p.leader) if p.leader else None
        if leader is not None and p.slot is not None:
            leader.mp_out.append([19, p.slot, 0])
        for q in self.players.values():
            if q.leader == cid and p.slot is not None:
                q.leader = None
                q.mp_out.append([20, p.slot])
        for oid, (giver, receiver, stacks) in list(self.offers.items()):
            if receiver == cid:
                del self.offers[oid]
                self._offer_answer(oid, giver, stacks, 0)

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

    def _together(self, p, together):
        """Joining parties and giving troops (coop/players.py)."""
        if together.get("join") is not None:
            leader = self._player_in_slot(together["join"], but=p)
            if leader is not None and p.slot is not None:
                if p.leader == leader.cid:  # in that party already (the answer got lost): yes again
                    p.mp_out.append([18, leader.slot, 1])
                else:
                    p.join_asked = leader.cid
                    leader.mp_out.append([17, p.slot])
        if together.get("joinans") is not None:
            slot, yes = together["joinans"]
            asker = self._player_in_slot(slot, but=p)
            if asker is not None and asker.join_asked == p.cid and p.slot is not None:
                asker.join_asked = None
                if yes:
                    asker.leader = p.cid
                    p.mp_out.append([19, asker.slot, 1])
                asker.mp_out.append([18, p.slot, 1 if yes else 0])
        if together.get("leave"):
            leader = self.players.get(p.leader) if p.leader else None
            p.leader = None
            if leader is not None and p.slot is not None:
                leader.mp_out.append([19, p.slot, 0])
        if together.get("release"):
            for q in self.players.values():
                if q.leader == p.cid and p.slot is not None:
                    q.leader = None
                    q.mp_out.append([20, p.slot])
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

    def host_saved(self):
        """The host saved the game (and the relays got the file): each player's game is told."""
        with self.lock:
            self.saves += 1

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
                self.srv_hours = hours
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
            for sid in [s for s, party in self.parties.items() if now - party[3] > STALE_S]:
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

    def _profile_part(self, p, part):
        """A part of the player's hero: keep it once all of it arrived."""
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

    def _save_profiles(self):
        if self.profiles_path is None:
            return
        try:
            tmp = self.profiles_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.profiles), "utf-8")
            tmp.replace(self.profiles_path)
        except OSError:
            pass

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
            if (hello or profile_ask) and not on_server and not p.profile_out:
                # the hero kept for this player goes back to its game, or word that there is none
                kept = self.profiles.get(self._profile_key(cid) or "", [])
                p.profile_out = [[14, off, len(kept), len(kept[off:off + PROFILE_PER_REPLY])]
                                 + kept[off:off + PROFILE_PER_REPLY]
                                 for off in range(0, len(kept), PROFILE_PER_REPLY)] or [[14, 0, 0, 0]]
            if profile is not None and not on_server:
                self._profile_part(p, profile)
            if together:
                self._together(p, together)
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
                    return [7, b.bid, 1 if b.state == "running" else 0, b.sides[cid]], wanted
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
            chosen = {sid for sid, _ in by_distance[:NEAREST_PER_REPLY]}
            out += [(sid, e[0], e[1], e[2], e[4], e[5], e[6]) for sid, e in by_distance[:NEAREST_PER_REPLY]]
            rest = [kv for kv in sorted(self.parties.items()) if kv[0] not in chosen]
            if rest:
                start = p.cursor % len(rest)
                for sid, e in (rest[start:] + rest[:start])[:ROTATING_PER_REPLY]:
                    out.append((sid, e[0], e[1], e[2], e[4], e[5], e[6]))
                p.cursor = start + ROTATING_PER_REPLY
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
                    p.mp_out.append([7, b.bid, 1 if b.state == "running" else 0, b.sides[p.cid]])
                return
            if not self._mp_online(now):
                self.log("joint battle: refused - no battle server (Multiplayer - Host a game, Battle)")
                p.mp_out.append([7, 0, 3, 0])
                return
            self.battle_seq += 1
            b = Battle(self.battle_seq, p.cid, now)
            defender = None
            if mp.get("center", -1) > 0 and mp.get("defend") and mp["sid"] > 0:
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
                if q.leader == p.cid and q is not defender and q.slot is not None:
                    # the starter's followers: called in, they fight on the starter's side
                    b.sides[q.cid] = b.player_team
                    b.invited.add(q.cid)
                    target = b.enemy_sid if b.enemy_sid is not None else (b.center if b.center is not None else -1)
                    q.mp_out.append([6, b.bid, 3, p.slot, target])
            for q in self.players.values():
                if q is p or q is defender or q.slot is None or q.pos is None or p.pos is None:
                    continue
                if q.cid in b.sides:
                    continue
                if (q.pos[0] - p.pos[0]) ** 2 + (q.pos[1] - p.pos[1]) ** 2 <= INVITE_DIST ** 2:
                    b.invited.add(q.cid)
                    target = b.enemy_sid if b.enemy_sid is not None else (b.center if b.center is not None else -1)
                    q.mp_out.append([6, b.bid, 1, p.slot, target])
            b.terrain = mp.get("terrain", 0)
            self.battle = b
            invited = ", ".join(self._who(self.players[c]) for c in sorted(b.invited) if c in self.players)
            self.log(f"joint battle {b.bid}: gathering; invited: {invited or 'nobody (no other player near)'}")
            p.mp_out.append([7, b.bid, 0, 0])
        elif b is not None and bid == 0 and op == 2 and p.cid in b.sides:
            # waiting without the battle's number (the answer to the start got lost): tell it
            p.mp_out.append([7, b.bid, 1 if b.state == "running" else 0, b.sides[p.cid]])
        elif b is None or b.bid != bid:
            if op in (2, 3):
                p.mp_out.append([7, bid, 2, 0])  # that battle is gone
        elif op == 3:
            if b.state != "gathering" and p.cid not in b.sides:
                self.log(f"joint battle {b.bid}: {self._who(p)} accepted too late - the battle began without that player")
                p.mp_out.append([7, bid, 2, 0])  # too late
                return
            b.invited.discard(p.cid)
            b.sides.setdefault(p.cid, b.player_team)  # an invited player fights on the starter's side
        elif op == 4:
            b.invited.discard(p.cid)
            if b.state == "running":
                return  # the battle goes on: that player's troops fight without the player
            if p.cid == b.starter:
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
        total = sum(s[3] for s in stacks)
        scale = min(1.0, MP_MAX_BOTS / total) if total else 1.0
        for s in stacks:
            s[4] = max(1, round(s[3] * scale))
        b.stacks, b.sent, b.state = stacks, 0, "loading"
        self.log(f"joint battle {b.bid}: going to the battle server ({len(stacks)} stacks, sides "
                 + ", ".join(f"{self._who(self.players[c])}=team {t}" for c, t in b.sides.items() if c in self.players)
                 + ")")

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

    def _finish(self, b, winner, fallen, now, weapons=(), health=None):
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
            if b.ally_sid is not None and b.ally_sid in npc_left:
                # the lord's party keeps what survived; never destroyed: the server keeps the lord, and
                # his soldiers' games must not lose the party they serve in
                self._record_result((b.ally_sid, 0, npc_left[b.ally_sid], []), None, now)
        elif captives:
            # a battle between players: the winner's side takes the prisoners
            taker = next((cid for cid, team in sorted(b.sides.items(), key=lambda kv: kv[0] != b.starter)
                          if team == winner and cid in self.players), None)
            if taker is not None:
                taken = captives[:MAX_STACKS]
                self.players[taker].mp_out.append([11, b.bid, len(taken)] + flat(taken))
        self.battle = None

    def mp_request(self, phase, bid, winner, fallen, players, now, weapons=(), health=None):
        """The battle server asks; returns the reply numbers after the marker."""
        with self.lock:
            self.mp_last = now
            self.mp_players = players
            b = self.battle
            if phase == 4:
                if b is not None and b.bid == bid and b.state == "running":
                    self._finish(b, winner, fallen, now, weapons, health)
                return [4, bid]
            self._battle_tick(now)
            b = self.battle
            if b is None:
                return [0]
            if b.state == "loading" and phase == 0:
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
                        if q is not None and q.hero and no >= 0:
                            b.heroes.append((no, q.hero))
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
                return [1, b.bid, len(b.stacks), mode, hint, len(pairs) // 2] + pairs
            if b.state == "running" and phase == 0 and now - b.started > MP_LOST_S:
                # the battle server restarted or changed its game: the battle is lost to it
                self.log(f"joint battle {b.bid}: lost - the battle server went back to an ordinary round")
                for cid in b.sides:
                    q = self.players.get(cid)
                    if q is not None:
                        q.mp_out.append([7, b.bid, 2, 0])
                self.battle = None
            return [0]

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
    """Joining parties and giving troops: {join, joinans, leave, release, give, giveans} or None."""
    out = {}
    if "join" in q:
        out["join"] = query_int(q, "join", -1)
    v = parse_ints(q.get("joinans", "")) if "joinans" in q else None
    if v and len(v) == 2:
        out["joinans"] = (v[0], v[1])
    if q.get("leave") == "1":
        out["leave"] = True
    if q.get("release") == "1":
        out["release"] = True
    v = parse_ints(q.get("give", "").replace(",,", ",")) if "give" in q else None
    if v:
        stacks = parse_stacks(v[1:]) or []
        out["give"] = (v[0], stacks)
    v = parse_ints(q.get("giveans", "")) if "giveans" in q else None
    if v and len(v) == 2:
        out["giveans"] = (v[0], v[1])
    return out or None


def parse_profile(text):
    """'seq,offset,total,v1,...' -> [seq, offset, total, v1, ...] or None"""
    v = parse_ints(text) if text else None
    return v if v and len(v) >= 3 and v[1] >= 0 and v[2] >= 0 else None


def parse_center(text):
    """'center,faction,lord[,besieger+1]' -> (center, faction, lord, besieger+1) or None"""
    v = parse_ints(text) if text else None
    if v and len(v) == 3:
        v.append(0)
    return tuple(v) if v and len(v) == 4 else None


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
    if string and not string.lstrip("-").isdigit():  # a number would land in a register, not s0
        text += "|" + game_text_out(string.replace("|", " "))
    return text


TRACE_KEYS = ("mp=", "join=", "joinans=", "leave=", "release=", "give=", "giveans=", "hello=", "bye=",
              "res=", "pfq=")
QUIET_KINDS = {0, 2, 3, 4, 5, 12}  # replies that come round all the time (positions, troops, pause...)


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


def handle_request(world, role, target, now, cid="local"):
    reply = _handle_request(world, role, target, now, cid)
    world.trace(role, cid, target, reply)
    if role == "cli":
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
                                parse_weapons(q.get("wx", "")), parse_fallen(q.get("hp", "")))
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
    return kind.isdigit() and int(kind) not in (0, 2, 4, 5)


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
        return {"t": "save", "name": path.name, "data": base64.b64encode(path.read_bytes()).decode()}

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
                try:
                    send_msg(conn, lock, {"t": "save_coming", "size": len(msg["data"])})
                    send_msg(conn, lock, dict(msg, push=True))
                    log(f"net: the host saved: {msg['name']} sent to {cid}")
                except OSError as e:
                    log(f"net: could not send the save to {cid}: {e}")

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
            for msg in msgs:
                if msg.get("t") == "log":
                    log(f"[{cid}] {str(msg.get('text', ''))[:500]}")
                elif msg.get("t") == "req":
                    body = handle_request(world, "cli", msg.get("target", "/"), time.time(), cid=cid)
                    send_msg(conn, lock, {"t": "rep", "id": msg.get("id"), "body": body})
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
        self.quiet_until = 0.0  # a save on its way: replies behind it come late, the link is fine
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
                                   "session": self.session})
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
                    self.waiting.pop("save", None) if msg.get("t") == "save" else None
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

    def forward(self, target):
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
            self.log(f"relay: the host saved the game - {path} now holds it (load it to start from there)")
        except (OSError, ValueError) as e:
            self.log(f"relay: could not keep the host's new save: {e}")

    def fetch_save(self, save_dir, slot_name=None):
        """Copy the host's newest save into save_dir (see store_save)."""
        rep = self.call({"t": "save"}, "save")
        if not rep or rep.get("error"):
            raise RuntimeError((rep or {}).get("error", "no answer"))
        return store_save(save_dir, rep, slot_name), rep["name"]

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


def _relay_back(sock, links, key_of, lock, forward, closed):
    """Datagrams coming back on one link's socket go out with forward(data) until the link has been
    silent for BATTLE_IDLE_S."""
    sock.settimeout(5)
    while True:
        try:
            data = sock.recv(65535)
        except socket.timeout:
            with lock:
                link = links.get(key_of)
                if link is None or link[0] is not sock:
                    break
                if time.time() - link[1] < BATTLE_IDLE_S:
                    continue
                links.pop(key_of, None)
            closed()
            break
        except ConnectionResetError:  # Windows: the other end's port was not open for a moment
            continue
        except OSError:
            break
        forward(data)
    sock.close()


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
    links = {}  # the friend's bridge address -> [socket to the battle server, time of its last datagram]
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
                    link = links[peer] = [sock, 0.0]
                    log(f"battle relay: a game from {peer[0]} joins the battle server through the bridge "
                        f"(the server sees it as {here}:{sock.getsockname()[1]})")

                    def forward(back, peer=peer):
                        try:
                            hub.sendto(tag + back, peer)
                        except OSError:
                            pass
                    threading.Thread(target=_relay_back, args=(sock, links, peer, lock, forward,
                                     lambda peer=peer: log(f"battle relay: the game from {peer[0]} left")),
                                     daemon=True).start()
                link[1] = time.time()
            try:
                link[0].send(data[BATTLE_TAG:])
            except OSError:
                pass

    threading.Thread(target=loop, daemon=True).start()
    log(f"battle relay: friends' second windows join the battle server (port {port}) through the bridge; "
        f"it sees them come from {source or lan_address()}, a local address")
    return hub


def serve_battle_join(local, hub_addr, key, log):
    """The friend's side: the second Warband window joins the battle server at `local`; its
    datagrams go to the host's bridge with the key's tag, the answers come back."""
    tag = battle_tag(key)
    try:
        game = udp_socket(local)
    except OSError as e:
        log(f"battle relay: cannot listen on UDP {local[0]}:{local[1]} ({e}); join the battle server directly")
        return None
    links = {}  # the game's address -> [socket to the host's bridge, time of its last datagram]
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
                    sock.connect(hub_addr)
                    link = links[src] = [sock, 0.0]

                    def forward(back, src=src):
                        if len(back) > BATTLE_TAG and hmac.compare_digest(back[:BATTLE_TAG], tag):
                            try:
                                game.sendto(back[BATTLE_TAG:], src)
                            except OSError:
                                pass
                    threading.Thread(target=_relay_back, args=(sock, links, src, lock, forward, lambda: None),
                                     daemon=True).start()
                link[1] = time.time()
            try:
                link[0].send(tag + data)
            except OSError:
                pass

    threading.Thread(target=loop, daemon=True).start()
    log(f"battle relay: in the second Warband window join the battle server at {local[0]}:{local[1]} "
        "(Multiplayer - Favorites): the bridge takes you to the host's server")
    return game


# ---- main

def parse_addr(text, default_port):
    host, _, port = text.partition(":")
    return host, int(port or default_port)


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
    log(f"logs: {Path(args.log).resolve()} and trace.log next to it (requests about battles, parties, joining)")
    world.set_mp_name("local", args.mp_name)
    serve_http(parse_addr(args.server, 80), lambda t: handle_request(world, "srv", t, time.time()), log, "srv")
    serve_http(parse_addr(args.client, 80), lambda t: handle_request(world, "cli", t, time.time()), log, "cli")
    serve_http(parse_addr(args.mp, 80), lambda t: handle_request(world, "mp", t, time.time()), log, "mp")
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
        if world._mp_online(time.time()) and seen != known:
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
        known = seen if world._mp_online(time.time()) else None
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
            players = ", ".join(f"{p.slot}:{p.name or p.cid}{' busy' if p.busy else ''}"
                                f"{f' silent {now - p.last:.0f}s' if p.last is not None and now - p.last > 2 else ''}"
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
    relay = Relay(parse_addr(args.host, NET_PORT), args.key, log, mp_name=args.mp_name)
    try:
        relay.connect()
    except (OSError, ConnectionError) as e:
        log(f"relay: cannot reach the host: {e}")
    relay.save_dir = args.save_dir if args.fetch_save else None  # each new save of the host lands here too
    threading.Thread(target=relay.keep_connected, daemon=True).start()  # retries until the host answers
    serve_battle_join(parse_addr(args.battle_listen, 7260), parse_addr(args.host, NET_PORT), args.key, relay.log)
    if args.fetch_save:
        if not relay.connected.is_set():
            log("relay: waiting for the host (check its address, the key, and that both PCs are on the same network)")
        relay.connected.wait()
        fetch_first_save(relay, args.save_dir, args.save_slot, log)
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
