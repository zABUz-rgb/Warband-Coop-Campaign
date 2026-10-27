"""CoopWorld bridge: links the world server game and up to MAX_PLAYERS player games.

Warband talks to it with send_message_to_url, which always uses port 80 and ignores any port in
the URL, so each game on one PC has its own loopback address:

    world server game   -> http://127.0.0.1/srv...   (on the host's PC)
    a player's game     -> http://127.0.0.2/cli...   (on every player's PC, the host's too)

Modes:
    host  the hub, on the host's PC: serves the world server game, the host's own player game and
          the other players, whose relays connect over TCP (a LAN, or a virtual LAN such as
          Radmin VPN or ZeroTier) with a shared key.
    join  a relay, on a friend's PC: forwards its player game's requests to the hub, and can
          fetch the host's newest save first.

    python tools/coop_bridge.py host --key SECRET [--listen 0.0.0.0:7350]
    python tools/coop_bridge.py join HOST_IP --key SECRET [--fetch-save]

World server -> /srv?seq=S&h=H&n=K&d=sid,tmpl,x,y,tx,ty,att;...[&c=sid,t1,n1,...]   or  /srv?seq=S&hold=1
    d: spawned parties: position, where the party is heading (tx,ty), and the party it is inside
       (a town) + 1, or 0 on the open map; c: troops of one party near a player; h: game hours.
    reply 7777|1|pause|joins|np|slot|x|y|...(np players)|kind|payload...
      pause 1: a player is in an encounter, a battle or a menu: the world stands still
      joins: how many times a player game joined (a held world runs again when it changes)
      kind 0: nothing   1: battle result sid|destroyed|n|t1|n1|...   2: player troops slot|n|t1|n1|...
      kind 3: player name slot, and the name as the reply's last (string) token

Player game -> /cli?seq=S&h=H&free=F&x=X&y=Y&busy=B[&hello=1][&bye=1][&res=sid,destroyed,t1,n1,...]
                    [&me=t1,n1,...][&name=player name]
    busy: not 0 from the start of an encounter until back on the map; hello: just joined; bye:
    stopped co-op; res: a battle result; me: its troops (empty: heroes only); name: last, may hold spaces.
    A player game's triggers do not run in menus, screens and battles: it goes silent, and a player
    silent for SILENT_PAUSE_S pauses the world just like a busy one.
    reply 7777|2|n|sid|tmpl|x|y|tx|ty|att|...   positions of world parties (tmpl REMOVED: gone)
          7777|3|sid|n|t1|n1|...               troops of one party near the player
          7777|4|slot|x|y|troops[|name]          another player's party

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
STALE_S = 15.0          # a party not reported for this long is gone
BUSY_TIMEOUT_S = 1200.0 # a player silent this long (crashed, or gone without bye) no longer pauses
SILENT_PAUSE_S = 1.0    # a player sends many requests a second on the map; this much silence = a menu
TOMBSTONE_S = 30.0      # a party a player destroyed is not sent again for this long
NEAREST_PER_REPLY = 11
ROTATING_PER_REPLY = 3
REMOVALS_PER_REPLY = 3  # 3 header numbers + 7 per entry must stay within 128 registers
MAX_STACKS = 30         # troop stacks per party in one message
CLOCK_WINDOW_S = 60.0   # game clock speed is measured over this much real time
NET_PORT = 7350
PROTOCOL = 1


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

    def paused(self, now):
        for p in self.players.values():
            if p.slot is None or p.last is None:
                continue
            silent = now - p.last
            if silent < BUSY_TIMEOUT_S and (p.busy or silent > SILENT_PAUSE_S):
                return True
        return False

    # ---- server

    def server_report(self, entries, troops, now, hold=False):
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
            if troops is not None:
                sid, stacks = troops
                # until the server applied a battle result, its report is older than the player's
                if all(r[0] != sid for r in self.results) and self.troops.get(sid, (0, None))[1] != stacks:
                    self.version += 1
                    self.troops[sid] = (self.version, stacks)
            puppets = [(p.slot, p.pos[0], p.pos[1]) for p in self.players.values()
                       if p.slot is not None and p.pos is not None]
            name = None
            pending_troops = [p for p in self.players.values() if p.slot is not None and p.stacks is not None]
            pending_names = [p for p in self.players.values() if p.slot is not None and p.name_pending]
            if self.results:
                sid, destroyed, stacks = self.results.pop(0)
                payload = [1, sid, destroyed, len(stacks)] + flat(stacks)
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
            return self.paused(now), self.joins, puppets, payload, name

    def _forget(self, sid, except_cid):
        """The party is gone: every player (but the one that removed it already) drops it."""
        self.parties.pop(sid, None)
        self.troops.pop(sid, None)
        for p in self.players.values():
            p.troops_sent.pop(sid, None)
            if p.cid != except_cid and sid not in p.removed:
                p.removed.append(sid)

    # ---- players' requests

    def player_request(self, cid, x, y, busy, result, me, now, hello=False, bye=False, name=None):
        """Returns (reply numbers after the marker, trailing string or None)."""
        with self.lock:
            self.stats["cli"] += 1
            if bye:
                self.players.pop(cid, None)
                return [0], None
            p = self._player(cid)
            p.requests += 1
            p.pos = (x, y)
            p.busy = busy
            p.last = now
            if hello:
                self.joins += 1
            if name and name != p.name:
                p.name, p.name_pending = name, True
            if result is not None:
                self.results.append(result)
                self.stats["results"] += 1
                sid, destroyed, stacks = result
                if destroyed:
                    self._forget(sid, except_cid=cid)
                    self.tombstones[sid] = now
                else:
                    # after a battle the player's view is what the party has now
                    self.version += 1
                    self.troops[sid] = (self.version, stacks)
                    p.troops_sent[sid] = self.version
            if me is not None and me != p.stacks_last:
                p.stacks = p.stacks_last = me
            by_distance = sorted(self.parties.items(),
                                 key=lambda kv: (kv[1][1] - x) ** 2 + (kv[1][2] - y) ** 2)
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
                return [4, q.slot, q.pos[0] + COORD_OFFSET, q.pos[1] + COORD_OFFSET, size], q.name
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
            parse_entries(q.get("d", "")), parse_troops(q.get("c", "")), now, hold=q.get("hold") == "1")
        nums = [MARKER, 1, int(pause), joins, len(puppets)]
        for slot, x, y in puppets:
            nums += [slot, x + COORD_OFFSET, y + COORD_OFFSET]
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
        nums, string = world.player_request(cid, x, y, busy, parse_result(q.get("res", "")), me, now,
                                            hello=q.get("hello") == "1", bye=q.get("bye") == "1", name=name)
        return reply_text([MARKER] + nums, string)
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


def serve_http(addr, answer, log, name):
    """Accept the games' HTTP requests on addr; answer(target) -> reply text."""
    host, port = addr
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
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
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
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
            log(f"net: player {cid} connected")
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

    def __init__(self, hub, key, log, timeout=3.0):
        self.hub, self.key, self.log, self.timeout = hub, key, log, timeout
        self.sock = None
        self.lock = threading.Lock()
        self.waiting = {}   # request id -> [event, reply]
        self.next_id = 0
        self.connected = threading.Event()

    def connect(self):
        sock = socket.create_connection(self.hub, timeout=10)
        sock.settimeout(None)
        send_msg(sock, self.lock, {"t": "hello", "key": self.key, "protocol": PROTOCOL})
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

    def fetch_save(self, save_dir, slot_name):
        rep = self.call({"t": "save"}, "save")
        if not rep or rep.get("error"):
            raise RuntimeError((rep or {}).get("error", "no answer"))
        target = Path(save_dir) / slot_name
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


def default_save_dir():
    return Path.home() / "Documents" / "Mount&Blade Warband Savegames" / "CoopWorld"


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
    serve_http(parse_addr(args.server, 80), lambda t: handle_request(world, "srv", t, time.time()), log, "srv")
    serve_http(parse_addr(args.client, 80), lambda t: handle_request(world, "cli", t, time.time()), log, "cli")
    if args.key:
        serve_relays(parse_addr(args.listen, NET_PORT), world, args.key, args.save_dir, log)
    else:
        log("net: no --key given, other players cannot join (this PC only)")
    last = dict(world.stats)
    while True:
        time.sleep(5)
        with world.lock:
            s, n = dict(world.stats), len(world.parties)
            paused = world.paused(time.time())
            players = ", ".join(f"{p.slot}:{p.name or p.cid}{' busy' if p.busy else ''}"
                                for p in sorted(world.players.values(), key=lambda p: (p.slot is None, p.slot)))
        clocks = {r: world.clock_rate(r) for r in ("srv", "cli", "cli_map")}
        clock_text = ", ".join(f"{r} {'?' if v is None else f'{v:.1f}'} h/min" for r, v in clocks.items())
        rate = {k: (s[k] - last[k]) / 5 for k in s}
        log(f"parties {n}, server {rate['srv']:.1f}/s, players {rate['cli']:.1f}/s [{players or 'none'}], "
            f"{'PAUSED' if paused else 'running'}, results {s['results']}, {clock_text}")
        last = s


def run_join(args, log):
    relay = Relay(parse_addr(args.host, NET_PORT), args.key, log)
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
    h.add_argument("--save-dir", default=str(default_save_dir()), help="the world server's saves")
    j = sub.add_parser("join", help="a relay on a friend's PC")
    j.add_argument("host", help="the host's address, e.g. 26.1.2.3 (Radmin VPN) or 192.168.1.5")
    j.add_argument("--key", required=True)
    j.add_argument("--client", default="127.0.0.2:80", help="address this PC's player game calls")
    j.add_argument("--fetch-save", action="store_true", help="copy the host's newest save here first")
    j.add_argument("--save-dir", default=str(default_save_dir()))
    j.add_argument("--save-slot", default="sg90.sav", help="file name for the fetched save")
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
