"""CoopWorld bridge: links the world server game and up to MAX_PLAYERS player games.

Warband talks to it with send_message_to_url, which always uses port 80 and ignores any port in
the URL, so each game on one PC has its own loopback address:

    world server game   -> http://127.0.0.1/srv...   (on the host's PC)
    a player's game     -> http://127.0.0.2/cli...   (on every player's PC, the host's too)
    battle server game  -> http://127.0.0.3/mp...    (on the host's PC: a multiplayer server of the
                           CoopWorld module, game type Battle, where joint battles are fought)

Modes:
    host  the hub, on the host's PC: serves the world server game, the host's own player game and
          the other players, whose relays connect over TCP (a LAN, or a virtual LAN such as
          Radmin VPN or ZeroTier) with a shared key.
    join  a relay, on a friend's PC: forwards its player game's requests to the hub, and can
          fetch the host's newest save first.

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
                    [&me=t1,n1,...][&name=player name]
    fac: the kingdom the player serves (0: none);
    busy: not 0 from the start of an encounter until back on the map; hello: just joined; bye:
    stopped co-op; res: a battle result; me: its troops (empty: heroes only); name: last, may hold spaces;
    srvp=1: the host playing in the world server game itself (its party is real there, no puppet).
    A player game's triggers do not run in menus, screens and battles: it goes silent, and a player
    silent for SILENT_PAUSE_S pauses the world just like a busy one.
    reply 7777|2|n|sid|tmpl|x|y|tx|ty|att|...   positions of world parties (tmpl REMOVED: gone)
          7777|3|sid|n|t1|n1|...               troops of one party near the player
          7777|4|slot|x|y|troops|kingdom[|name]  another player's party, and whom it serves
          7777|5|paused|slot|why                    the world stands still because of player <slot>
                                                    (why: 1 in an encounter or battle, 2 in a menu);
                                                    the player's own map then stands still too

Joint battles (the player game's waiting window adds &mp=OP&bid=B[&mpe=sid][&mpp=slot][&mpc=center][&mpt=t1,n1,...]
[&hero=...]; hero, with a start or an acceptance: HERO_NUMBERS numbers, the hero's equipment, attributes,
combat skills and weapon proficiencies, in the order of coop/constants.py):
    OP 1 start a battle against the world party sid (mpt: its troops as the player sees them), the
    player in puppet slot, or storm the town or castle mpc (a siege: the players are team 1, the
    garrison team 0); with &mpd=1 defend that center against its besieger mpe (the players and the
    garrison team 0, the besieger and the army camped with it team 1);
    2 waiting; 3 accept an invitation; 4 decline, or cancel (the starter).
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

Battle server -> /mp?seq=S&st=PHASE&bid=B[&w=WINNER&r=i,fallen;...&hp=no,percent;...&wx=no,wpt,hits,damage;...]
                  &pl=no~name;...
    PHASE 0 an ordinary round, 1-3 a battle of the campaign, 4 over (w: winning team, r: the bots
    each stack lost; hp: the heroes' health at the end, 0 fallen; wx: the heroes' hits and damage by
    weapon proficiency);
    pl: the players on the server, matched to the players of the campaign by name.
    reply 7778|0                                  nothing
          7778|2|bid|offset|n|(team,player,troop,count)*n   stacks to spawn (player: who commands them, -1 the AI)
          7778|5|bid|player|hero...               a player fights as the campaign hero (after the stacks)
          7778|1|bid|stacks|mode|hint|n|(player,team)*n   start: players onto their sides, the round
                                                  restarts; mode 1 a siege (Siege game type, map by hint)
          7778|4|bid                              the outcome arrived

Coordinates are map units * 100, shifted by COORD_OFFSET in replies so the games only get
non-negative numbers. A reply holds at most 128 numbers (the engine's registers).
"""
import argparse
import base64
import hmac
import json
import socket
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MARKER = 7777
COORD_OFFSET = 100000
REMOVED = 9999
MAX_PLAYERS = 4         # puppet parties coop_puppet_1..4 in the module
CENTERS_PER_REPLY = 30  # 2 + 4 * 30 numbers
STALE_S = 15.0          # a party not reported for this long is gone
BUSY_TIMEOUT_S = 1200.0 # a player silent this long (crashed, or gone without bye) no longer pauses
SILENT_PAUSE_S = 1.0    # a player sends many requests a second on the map; this much silence = a menu
TOMBSTONE_S = 30.0
STATUS_EVERY = 50       # a player is reminded of the pause state this often, in case a reply was lost      # a party a player destroyed is not sent again for this long
NEAREST_PER_REPLY = 11
ROTATING_PER_REPLY = 3
REMOVALS_PER_REPLY = 3
RESULT_PAIRS = 53       # troop and prisoner pairs of one battle result: 5 + 3 * 4 + 4 + 1 + 2 * 53 <= 128  # 3 header numbers + 7 per entry must stay within 128 registers
MAX_STACKS = 30         # troop stacks per party in one message
CLOCK_WINDOW_S = 60.0   # game clock speed is measured over this much real time
NET_PORT = 7350
FETCHED_MARK = "coopworld_fetched.txt"  # in the save folder: which file the relay wrote the host's save to
PROTOCOL = 1
MP_MARKER = 7778
MP_ONLINE_S = 10.0      # a battle server not heard from for this long is not running
GATHER_S = 20.0         # invited players have this long to answer before the battle starts
INVITE_DIST = 1000      # map units * 100: players this close to the starter are invited
MP_MAX_BOTS = 150       # bots on the battle server; bigger armies are scaled down, losses scaled up
MP_MAX_STACKS = 60
MP_CHUNK = 30           # stacks per reply: 5 + 4 * 30 numbers
MP_LOST_S = 30.0        # a battle server back in an ordinary round this long after a start lost it
WOUNDED_PCT = 50        # of a player's fallen soldiers, this share is wounded rather than killed
XP_PER_ENEMY = 30       # battle experience for each fallen enemy, shared by the winning side's players;
                        # the losing side gets a third of it
HERO_NUMBERS = 29       # 9 equipment slots, 4 attributes, 9 combat skills, 7 proficiencies


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
        self.requests = 0
        self.cursor = 0
        self.troops_sent = {}   # sid -> troops version this player has
        self.removed = []       # sids this player still has to drop
        self.stacks = None      # its troops not yet sent to the server
        self.stacks_last = None
        self.name = None
        self.name_pending = False
        self.others_cursor = 0
        self.status_sent = None  # (paused, slot, why) this player was last told
        self.status_age = 0
        self.mp_out = []        # joint-battle replies waiting for this player
        self.on_server = False  # the host playing in the world server game: no puppet there
        self.hero = None        # the hero's equipment and stats for joint battles
        self.faction = 0        # the kingdom the player serves, 0 none
        self.centers_sent = {}  # center -> (faction, lord, besieger + 1) this player was told


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
        self.npc_stacks = []      # a defence: (team, world party, troop, count) of the garrison and the besiegers
        self.player_team = 0      # the starter's side: 0 in the field, 1 storming walls
        self.stacks = []          # [team, owner cid or None, troop, count, spawned on the server]
        self.sent = 0
        self.heroes = None        # [(player number, hero numbers)] still to send, after the stacks
        self.started = None


class World:
    def __init__(self):
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
        self.mp_names = {}      # cid -> the name its player uses on the battle server (launcher)
        self.stats = {"srv": 0, "cli": 0, "entries_in": 0, "entries_out": 0, "results": 0}

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
            self.players.pop(cid, None)
            self.mp_names.pop(cid, None)

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

    def server_report(self, entries, troops, now, hold=False, center=None):
        """Returns (pause, joins, [(slot, x, y)], payload numbers, name string or None)."""
        with self.lock:
            self.stats["srv"] += 1
            for sid in [s for s, when in self.tombstones.items() if now - when > TOMBSTONE_S]:
                del self.tombstones[sid]
            for entry in entries:
                sid, tmpl, x, y, *rest = entry
                tx, ty, att = (rest + [x, y, 0][len(rest):])[:3]  # no target: stays put; no att: open map
                if sid in self.tombstones:
                    continue  # destroyed by a player; the server has not caught up yet
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

    def player_request(self, cid, x, y, busy, result, me, now, hello=False, bye=False, name=None, mp=None,
                       on_server=False, faction=None):
        """Returns (reply numbers after the marker, trailing string or None)."""
        with self.lock:
            self.stats["cli"] += 1
            if bye:
                self.players.pop(cid, None)
                return [0], None
            p = self._player(cid)
            p.on_server = on_server
            if faction is not None:
                p.faction = faction
            p.requests += 1
            p.pos = (x, y)
            p.busy = busy
            p.last = now
            if hello:
                self.joins += 1
            if name and name != p.name:
                p.name, p.name_pending = name, True
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
            # whether another player holds the world still: at once when it changes, and now and then
            cause = self.pause_cause(now, but=p)
            status = (1, cause[0], cause[1]) if cause else (0, 0, 0)
            p.status_age += 1
            if status != p.status_sent or p.status_age >= STATUS_EVERY:
                p.status_sent, p.status_age = status, 0
                return [5, *status], None
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

    # ---- joint battles

    def _mp_online(self, now):
        return self.mp_last is not None and now - self.mp_last <= MP_ONLINE_S

    def _mp_op(self, p, mp, now):
        op, bid, b = mp["op"], mp["bid"], self.battle
        if mp.get("hero"):
            p.hero = mp["hero"]
        if op == 1:
            if b is not None:
                if p.cid not in b.sides:
                    p.mp_out.append([7, 0, 2, 0])  # another battle is on
                return
            if not self._mp_online(now):
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
                    p.mp_out.append([7, 0, 2, 0])
                    return
                b.sides[defender.cid] = 1
                b.invited.add(defender.cid)
                defender.mp_out.append([6, b.bid, 2, p.slot, -1])
            elif mp["sid"] >= 0:
                b.enemy_sid = mp["sid"]
                b.enemy_stacks = mp["troops"] or (self.troops.get(mp["sid"], (0, None))[1] or [])
            else:
                p.mp_out.append([7, 0, 2, 0])
                return
            for q in self.players.values():
                if q is p or q is defender or q.slot is None or q.pos is None or p.pos is None:
                    continue
                if (q.pos[0] - p.pos[0]) ** 2 + (q.pos[1] - p.pos[1]) ** 2 <= INVITE_DIST ** 2:
                    b.invited.add(q.cid)
                    target = b.enemy_sid if b.enemy_sid is not None else (b.center if b.center is not None else -1)
                    q.mp_out.append([6, b.bid, 1, p.slot, target])
            self.battle = b
            p.mp_out.append([7, b.bid, 0, 0])
        elif b is None or b.bid != bid:
            if op in (2, 3):
                p.mp_out.append([7, bid, 2, 0])  # that battle is gone
        elif op == 3:
            if b.state != "gathering" and p.cid not in b.sides:
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
        stacks = []
        for cid, team in sorted(b.sides.items(), key=lambda kv: (kv[1], kv[0] != b.starter)):
            q = self.players.get(cid)
            for troop, n in (q.stacks_last or []) if q is not None else []:
                stacks.append([team, cid, troop, n, 0])
        if b.defence:
            stacks += [[team, ("npc", sid), troop, n, 0] for team, sid, troop, n in b.npc_stacks]
        else:
            stacks += [[1 - b.player_team, None, troop, n, 0] for troop, n in b.enemy_stacks]
        stacks = [s for s in stacks if s[3] > 0][:MP_MAX_STACKS]
        total = sum(s[3] for s in stacks)
        scale = min(1.0, MP_MAX_BOTS / total) if total else 1.0
        for s in stacks:
            s[4] = max(1, round(s[3] * scale))
        b.stacks, b.sent, b.state = stacks, 0, "loading"

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
        for i, (team, owner, troop, count, spawned) in enumerate(b.stacks):
            fell = fallen.get(i, 0)
            lost = min(count, round(fell * count / spawned)) if spawned else 0
            fell_by_team[team] = fell_by_team.get(team, 0) + lost
            if owner is None:
                if count - lost > 0:
                    enemy_left.append((troop, count - lost))
            elif isinstance(owner, tuple):  # a defence: a world party, the garrison or a besieger
                npc_left.setdefault(owner[1], [])
                if count - lost > 0:
                    npc_left[owner[1]].append((troop, count - lost))
            else:
                wounded = lost * WOUNDED_PCT // 100
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
            q.mp_out.append([8, b.bid, won, xp, len(lost)] + [v for entry in lost for v in entry])
            no = self._mp_player_number(cid)
            used = [(wpt, hits, damage) for player, wpt, hits, damage in weapons if player == no >= 0]
            if used:
                q.mp_out.append([9, b.bid, len(used)] + [v for entry in used for v in entry])
            # last: the hero's wounds, and the capture (after which the player is in captivity)
            hp = (health or {}).get(no, -1) if no >= 0 else -1
            captor = b.enemy_sid if cid in defeated and b.enemy_sid is not None else -1  # a failed storm: no capture
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
                pairs = []
                for cid, team in b.sides.items():
                    no = self._mp_player_number(cid)
                    if no >= 0:
                        pairs += [no, team]
                b.state, b.started = "running", now
                for cid, team in b.sides.items():
                    q = self.players.get(cid)
                    if q is not None:
                        q.mp_out.append([7, b.bid, 1, team])
                mode = 1 if b.center is not None else 0
                return [1, b.bid, len(b.stacks), mode, b.center or 0, len(pairs) // 2] + pairs
            if b.state == "running" and phase == 0 and now - b.started > MP_LOST_S:
                # the battle server restarted or changed its game: the battle is lost to it
                for cid in b.sides:
                    q = self.players.get(cid)
                    if q is not None:
                        q.mp_out.append([7, b.bid, 2, 0])
                self.battle = None
            return [0]

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


def parse_center(text):
    """'center,faction,lord[,besieger+1]' -> (center, faction, lord, besieger+1) or None"""
    v = parse_ints(text) if text else None
    if v and len(v) == 3:
        v.append(0)
    return tuple(v) if v and len(v) == 4 else None


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
            players[int(no)] = name.strip()
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


def reply_text(numbers, string=None):
    text = "|".join(str(int(v)) for v in numbers)
    if string and not string.lstrip("-").isdigit():  # a number would land in a register, not s0
        text += "|" + string.replace("|", " ")
    return text


def handle_request(world, role, target, now, cid="local"):
    url = urlparse(target)
    q = {k: v[0] for k, v in parse_qs(url.query, encoding="latin-1").items()}
    if role == "srv" and url.path == "/srv":
        world.clock("srv", parse_hours(q), now)
        pause, joins, puppets, payload, name = world.server_report(
            parse_entries(q.get("d", "")), parse_troops(q.get("c", "")), now, hold=q.get("hold") == "1",
            center=parse_center(q.get("cf", "")))
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
        name = q.get("name", "").replace("|", " ").strip()[:40] or None
        mp = None
        if "mp" in q:
            troops = q.get("mpt", "").lstrip(",")
            hero = parse_ints(q.get("hero", ""))
            mp = {"op": query_int(q, "mp", 0), "bid": query_int(q, "bid", 0), "sid": query_int(q, "mpe", -1),
                  "slot": query_int(q, "mpp", -1), "center": query_int(q, "mpc", -1), "defend": q.get("mpd") == "1",
                  "troops": (parse_stacks(parse_ints(troops)) or []) if troops else [],
                  "hero": hero if hero and len(hero) == HERO_NUMBERS else None}
        nums, string = world.player_request(cid, x, y, busy, parse_result(q.get("res", "")), me, now,
                                            hello=q.get("hello") == "1", bye=q.get("bye") == "1", name=name, mp=mp,
                                            on_server=q.get("srvp") == "1",
                                            faction=query_int(q, "fac", 0) if "fac" in q else None)
        return reply_text([MARKER] + nums, string)
    if role == "mp" and url.path == "/mp":
        nums = world.mp_request(query_int(q, "st", 0), query_int(q, "bid", 0), query_int(q, "w", -1),
                                parse_fallen(q.get("r", "")), parse_mp_players(q.get("pl", "")), now,
                                parse_weapons(q.get("wx", "")), parse_fallen(q.get("hp", "")))
        return reply_text([MP_MARKER] + nums)
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
        try:
            send_http_body(conn, answer(read_http_target(conn)))
        except OSError as e:
            log(f"{name}: connection error {e}")
        finally:
            conn.close()

    def loop():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=one, args=(conn,), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return srv


# ---- the network between the hub and the relays: one JSON message per line

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


def newest_save(save_dir):
    saves = sorted(Path(save_dir).glob("sg*.sav"), key=lambda p: p.stat().st_mtime) if save_dir else []
    return saves[-1] if saves else None


def serve_relays(addr, world, key, save_dir, log):
    """The hub side of the network: each relay connection is one player."""
    host, port = addr
    srv = listen_socket(host, port)
    srv.listen(8)
    log(f"net: listening for players on {host}:{port}")
    counter = [0]

    def one(conn, peer):
        counter[0] += 1
        cid = f"net{counter[0]}@{peer[0]}"
        lock = threading.Lock()
        try:
            msgs = read_msgs(conn)
            hello = next(msgs, None)
            if (not hello or hello.get("t") != "hello" or hello.get("protocol") != PROTOCOL
                    or not hmac.compare_digest(str(hello.get("key", "")), key)):
                send_msg(conn, lock, {"t": "refused", "why": "wrong key or protocol"})
                log(f"net: refused {peer[0]}")
                return
            send_msg(conn, lock, {"t": "welcome", "cid": cid})
            world.set_mp_name(cid, hello.get("mp_name"))
            log(f"net: player {cid} connected" + (f", multiplayer name '{hello['mp_name']}'" if hello.get("mp_name") else ""))
            for msg in msgs:
                if msg.get("t") == "req":
                    body = handle_request(world, "cli", msg.get("target", "/"), time.time(), cid=cid)
                    send_msg(conn, lock, {"t": "rep", "id": msg.get("id"), "body": body})
                elif msg.get("t") == "save":
                    path = newest_save(save_dir)
                    if path is None:
                        send_msg(conn, lock, {"t": "save", "error": f"no save in {save_dir}"})
                    else:
                        data = base64.b64encode(path.read_bytes()).decode()
                        send_msg(conn, lock, {"t": "save", "name": path.name, "data": data})
                        log(f"net: sent save {path.name} to {cid}")
        except (OSError, ValueError) as e:
            log(f"net: {cid} error {e}")
        finally:
            world.drop_player(cid)  # gone: its silence no longer pauses the world
            conn.close()
            log(f"net: player {cid} left")

    def loop():
        while True:
            conn, peer = srv.accept()
            threading.Thread(target=one, args=(conn, peer), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return srv


class Relay:
    """The friend's side: forwards its player game's requests to the hub, one at a time."""

    def __init__(self, hub, key, log, timeout=3.0, mp_name=None):
        self.hub, self.key, self.log, self.timeout = hub, key, log, timeout
        self.mp_name = mp_name
        self.sock = None
        self.lock = threading.Lock()
        self.waiting = {}   # request id -> [event, reply]
        self.next_id = 0
        self.connected = threading.Event()

    def connect(self):
        sock = socket.create_connection(self.hub, timeout=10)
        sock.settimeout(None)
        send_msg(sock, self.lock, {"t": "hello", "key": self.key, "protocol": PROTOCOL, "mp_name": self.mp_name})
        msgs = read_msgs(sock)
        first = next(msgs, None)
        if not first or first.get("t") != "welcome":
            sock.close()
            raise ConnectionError((first or {}).get("why", "no answer from the host"))
        self.sock = sock
        self.connected.set()
        self.log(f"relay: connected to the host as {first.get('cid')}")
        threading.Thread(target=self._reader, args=(msgs,), daemon=True).start()

    def _reader(self, msgs):
        try:
            for msg in msgs:
                waiter = self.waiting.pop(msg.get("id"), None) if msg.get("t") == "rep" else \
                    self.waiting.pop("save", None) if msg.get("t") == "save" else None
                if waiter:
                    waiter[1] = msg
                    waiter[0].set()
        except (OSError, ValueError):
            pass
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
        return rep["body"] if rep else reply_text([0, 0])

    def fetch_save(self, save_dir, slot_name=None):
        """Copy the host's newest save into save_dir. Without slot_name: the file fetched last time
        (remembered in FETCHED_MARK), else the host's own name when free, else the lowest free sgNN:
        the game lists only the low slots, a high one such as sg90 never showed up."""
        rep = self.call({"t": "save"}, "save")
        if not rep or rep.get("error"):
            raise RuntimeError((rep or {}).get("error", "no answer"))
        folder = Path(save_dir)
        folder.mkdir(parents=True, exist_ok=True)  # a player who never saved in CoopWorld has no folder
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
        return target, rep["name"]

    def keep_connected(self):
        while True:
            if not self.connected.is_set():
                try:
                    self.connect()
                except (OSError, ConnectionError) as e:
                    self.log(f"relay: cannot reach the host: {e}; retrying")
            time.sleep(3)


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
    return documents_dir() / "Mount&Blade Warband Savegames" / "CoopWorld"


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
    world = World()
    world.set_mp_name("local", args.mp_name)
    serve_http(parse_addr(args.server, 80), lambda t: handle_request(world, "srv", t, time.time()), log, "srv")
    serve_http(parse_addr(args.client, 80), lambda t: handle_request(world, "cli", t, time.time()), log, "cli")
    serve_http(parse_addr(args.mp, 80), lambda t: handle_request(world, "mp", t, time.time()), log, "mp")
    if args.key:
        serve_relays(parse_addr(args.listen, NET_PORT), world, args.key, args.save_dir, log)
    else:
        log("net: no --key given, other players cannot join (this PC only)")
    last = dict(world.stats)
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
            paused = world.paused(time.time())
            players = ", ".join(f"{p.slot}:{p.name or p.cid}{' busy' if p.busy else ''}"
                                f"{' mp:' + world.mp_names[p.cid] if p.cid in world.mp_names else ''}"
                                for p in sorted(world.players.values(), key=lambda p: (p.slot is None, p.slot)))
            mp_text = "battle server " + ("on" if world._mp_online(time.time()) else "off")
            if world.battle is not None:
                mp_text += f", battle {world.battle.bid} {world.battle.state} sides {world.battle.sides}"
        clocks = {r: world.clock_rate(r) for r in ("srv", "cli", "cli_map")}
        clock_text = ", ".join(f"{r} {'?' if v is None else f'{v:.1f}'} h/min" for r, v in clocks.items())
        rate = {k: (s[k] - last[k]) / 5 for k in s}
        log(f"parties {n}, server {rate['srv']:.1f}/s, players {rate['cli']:.1f}/s [{players or 'none'}], "
            f"{'PAUSED' if paused else 'running'}, results {s['results']}, {clock_text}, {mp_text}")
        last = s


def run_join(args, log):
    relay = Relay(parse_addr(args.host, NET_PORT), args.key, log, mp_name=args.mp_name)
    try:
        relay.connect()
    except (OSError, ConnectionError) as e:
        log(f"relay: cannot reach the host: {e}")
    threading.Thread(target=relay.keep_connected, daemon=True).start()  # retries until the host answers
    if args.fetch_save:
        if not relay.connected.is_set():
            log("relay: waiting for the host (check its address, the key, and that both PCs are on the same network)")
        relay.connected.wait()
        path, name = relay.fetch_save(args.save_dir, args.save_slot)
        log(f"relay: the host's save {name} is now {path} - load it in the game")
    serve_http(parse_addr(args.client, 80), relay.forward, log, "cli")
    while True:
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description="CoopWorld bridge")
    sub = ap.add_subparsers(dest="mode")
    h = sub.add_parser("host", help="the hub on the host's PC (runs the world server game)")
    h.add_argument("--key", help="shared secret for other players; without it only this PC can play")
    h.add_argument("--listen", default=f"0.0.0.0:{NET_PORT}", help="where other players connect")
    h.add_argument("--server", default="127.0.0.1:80", help="address the world server game calls")
    h.add_argument("--client", default="127.0.0.2:80", help="address this PC's player game calls")
    h.add_argument("--mp", default="127.0.0.3:80", help="address the battle server game (multiplayer) calls")
    h.add_argument("--mp-name", default=None, help="the host's name on the battle server (multiplayer profile)")
    h.add_argument("--save-dir", default=str(default_save_dir()), help="the world server's saves")
    j = sub.add_parser("join", help="a relay on a friend's PC")
    j.add_argument("host", help="the host's address, e.g. 26.1.2.3 (Radmin VPN) or 192.168.1.5")
    j.add_argument("--key", required=True)
    j.add_argument("--client", default="127.0.0.2:80", help="address this PC's player game calls")
    j.add_argument("--fetch-save", action="store_true", help="copy the host's newest save here first")
    j.add_argument("--mp-name", default=None, help="this player's name on the battle server (multiplayer profile)")
    j.add_argument("--save-dir", default=str(default_save_dir()))
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
