"""CoopWorld bridge, prototype: relays the world between a server game and one client game on one PC.

Both games talk to it with Warband's send_message_to_url, which always uses port 80 and ignores
any port in the URL, so each game gets its own loopback address.

World server game -> http://127.0.0.1/srv?seq=S&h=H&n=K&d=sid,tmpl,x,y,tx,ty;...[&c=sid,t1,n1,t2,n2,...]
                     or http://127.0.0.1/srv?seq=S&hold=1 while it holds the world for a joining client
    d: spawned parties: position and where the party is heading (tx,ty), the ones near the client's
       puppet first; c: troops of one party near the puppet; h: game hours (clock speed check).
    reply 7777|1|has_client|client_x|client_y|pause|joins|kind|payload...
      pause 1: a player is in an encounter or battle, the world must stand still
      joins: how many times a client game has joined (the server holds the world until one does)
      kind 0: nothing
      kind 1: battle result  sid|destroyed|n|t1|n1|...   (troops the party has left)
      kind 2: puppet troops  n|t1|n1|...                 (the client player's party)

Client game -> http://127.0.0.2/cli?seq=S&h=H&free=F&x=X&y=Y&busy=B[&hello=1][&res=sid,destroyed,t1,n1,...][&me=t1,n1,...]
    busy: not 0 from the start of an encounter until the client is back on the map
    free: 1 when the client is on the map (its clock then runs at travel speed); hello: it just joined
    res: a battle result for one party; me: the client player's own troops
    reply 7777|2|n|sid|tmpl|x|y|tx|ty|...  (n entries; tmpl REMOVED = party gone), or
          7777|3|sid|n|t1|n1|...     (troops of one party near the client, sent when they changed)

Positions are map coordinates * 100. In replies to the games every coordinate is shifted by
COORD_OFFSET so that only non-negative numbers go back (how the engine parses "-5" is untested).
A reply holds at most 128 numbers (the engine's registers).

    python tools/coop_bridge.py [--server 127.0.0.1:80] [--client 127.0.0.2:80] [--log local/bridge.log]

Loopback only: it trusts whatever connects.
"""
import argparse
import socket
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MARKER = 7777
COORD_OFFSET = 100000
REMOVED = 9999
STALE_S = 15.0          # a party not reported for this long is gone
BUSY_TIMEOUT_S = 1200.0 # a client silent this long while busy (crashed in battle) ends the pause
NEAREST_PER_REPLY = 12
ROTATING_PER_REPLY = 4
REMOVALS_PER_REPLY = 4  # 3 header numbers + 6 per entry must stay within 128 registers
CLOCK_WINDOW_S = 60.0   # game clock speed is measured over this much real time
TOMBSTONE_S = 30.0      # a party the client destroyed is not sent again for this long
MAX_STACKS = 30         # troop stacks per party in one reply


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


class World:
    def __init__(self):
        self.lock = threading.Lock()
        self.parties = {}       # sid -> [tmpl, x, y, last_seen, tx, ty]
        self.clocks = {"srv": [], "cli": [], "cli_map": []}  # (real time, game hours) samples
        self.tombstones = {}    # sid -> real time the client destroyed it
        self.joins = 0
        self.removed = []       # sids the client still has to drop
        self.client_pos = None  # (x, y)
        self.cursor = 0
        self.busy = False
        self.last_client = None
        self.troops = {}        # sid -> (version, stacks) as last known
        self.troops_sent = {}   # sid -> version the client has
        self.version = 0
        self.results = []       # (sid, destroyed, stacks) for the server to apply
        self.puppet = None      # client player's stacks not yet sent to the server
        self.puppet_last = None
        self.stats = {"srv": 0, "cli": 0, "entries_in": 0, "entries_out": 0, "results": 0}

    def paused(self, now):
        return self.busy and self.last_client is not None and now - self.last_client < BUSY_TIMEOUT_S

    def server_report(self, entries, troops, now, hold=False):
        """Returns (client position or None, pause, payload after the pause flag)."""
        with self.lock:
            self.stats["srv"] += 1
            for sid in [s for s, when in self.tombstones.items() if now - when > TOMBSTONE_S]:
                del self.tombstones[sid]
            for sid, tmpl, x, y, tx, ty in entries:
                if sid in self.tombstones:
                    continue  # destroyed on the client; the server has not caught up yet
                self.parties[sid] = [tmpl, x, y, now, tx, ty]
                self.stats["entries_in"] += 1
                if sid in self.removed:
                    self.removed.remove(sid)
            if hold:
                # the world is held and the server sends no parties: nothing goes stale meanwhile
                for p in self.parties.values():
                    p[3] = now
            for sid in [s for s, p in self.parties.items() if now - p[3] > STALE_S]:
                del self.parties[sid]
                self.troops.pop(sid, None)
                self.removed.append(sid)
            if troops is not None:
                sid, stacks = troops
                # until the server applied a battle result, its report is older than the client's
                if all(r[0] != sid for r in self.results) and self.troops.get(sid, (0, None))[1] != stacks:
                    self.version += 1
                    self.troops[sid] = (self.version, stacks)
            if self.results:
                sid, destroyed, stacks = self.results.pop(0)
                payload = [1, sid, destroyed, len(stacks)] + flat(stacks)
            elif self.puppet is not None:
                payload = [2, len(self.puppet)] + flat(self.puppet)
                self.puppet = None
            else:
                payload = [0]
            return self.client_pos, self.paused(now), self.joins, payload

    def client_request(self, x, y, busy, result, me, now, hello=False):
        """Returns the reply numbers after the marker: [2, n, entries...] or [3, sid, n, stacks...]."""
        with self.lock:
            self.stats["cli"] += 1
            self.client_pos = (x, y)
            self.busy = busy
            self.last_client = now
            if hello:
                self.joins += 1
            if result is not None:
                self.results.append(result)
                self.stats["results"] += 1
                # after a battle the client's view is what the party has now
                sid, destroyed, stacks = result
                if destroyed:
                    self.parties.pop(sid, None)
                    self.troops.pop(sid, None)
                    self.troops_sent.pop(sid, None)
                    self.tombstones[sid] = now
                else:
                    self.version += 1
                    self.troops[sid] = (self.version, stacks)
                    self.troops_sent[sid] = self.version
            if me is not None and me != self.puppet_last:
                self.puppet = self.puppet_last = me
            by_distance = sorted(self.parties.items(),
                                 key=lambda kv: (kv[1][1] - x) ** 2 + (kv[1][2] - y) ** 2)
            # every other reply: troops of the nearest party whose troops the client has not seen
            if self.stats["cli"] % 2 == 0:
                for sid, _ in by_distance[:NEAREST_PER_REPLY]:
                    version, stacks = self.troops.get(sid, (0, None))
                    if stacks is not None and self.troops_sent.get(sid) != version:
                        self.troops_sent[sid] = version
                        return [3, sid, len(stacks)] + flat(stacks)
            out = []
            while self.removed and len(out) < REMOVALS_PER_REPLY:
                sid = self.removed.pop(0)
                self.troops_sent.pop(sid, None)
                out.append((sid, REMOVED, 0, 0, 0, 0))
            chosen = {sid for sid, _ in by_distance[:NEAREST_PER_REPLY]}
            out += [(sid, p[0], p[1], p[2], p[4], p[5]) for sid, p in by_distance[:NEAREST_PER_REPLY]]
            rest = [kv for kv in sorted(self.parties.items()) if kv[0] not in chosen]
            if rest:
                start = self.cursor % len(rest)
                for sid, p in (rest[start:] + rest[:start])[:ROTATING_PER_REPLY]:
                    out.append((sid, p[0], p[1], p[2], p[4], p[5]))
                self.cursor = start + ROTATING_PER_REPLY
            self.stats["entries_out"] += len(out)
            nums = [2, len(out)]
            for sid, tmpl, ex, ey, tx, ty in out:
                if tmpl == REMOVED:
                    nums += [sid, tmpl, 0, 0, 0, 0]
                else:
                    nums += [sid, tmpl, ex + COORD_OFFSET, ey + COORD_OFFSET, tx + COORD_OFFSET, ty + COORD_OFFSET]
            return nums

    def clock(self, role, hours, now):
        """Record a game-clock sample of one game."""
        if hours is None:
            return
        with self.lock:
            samples = self.clocks[role]
            if role == "cli_map" and samples and now - samples[-1][0] > 1.0:
                samples.clear()  # the client rested or was in a menu in between: start a new run
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
    """'sid,tmpl,x,y[,tx,ty];...' -> [(sid, tmpl, x, y, tx, ty)]; without a target the party stays put"""
    entries = []
    for chunk in d.split(";"):
        parts = chunk.split(",")
        if len(parts) in (4, 6):
            try:
                v = [int(x) for x in parts]
            except ValueError:
                continue
            entries.append(tuple(v) if len(v) == 6 else (v[0], v[1], v[2], v[3], v[2], v[3]))
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


def reply_numbers(numbers):
    return "|".join(str(int(v)) for v in numbers)


def handle_request(world, role, target, now):
    url = urlparse(target)
    q = {k: v[0] for k, v in parse_qs(url.query).items()}
    if role == "srv" and url.path == "/srv":
        world.clock("srv", parse_hours(q), now)
        client, pause, joins, payload = world.server_report(parse_entries(q.get("d", "")),
                                                            parse_troops(q.get("c", "")), now,
                                                            hold=q.get("hold") == "1")
        has, cx, cy = (0, 0, 0) if client is None else (1, client[0], client[1])
        return reply_numbers([MARKER, 1, has, cx + COORD_OFFSET, cy + COORD_OFFSET, int(pause), joins] + payload)
    if role == "cli" and url.path == "/cli":
        try:
            x, y = int(q.get("x", "0")), int(q.get("y", "0"))
        except ValueError:
            x = y = 0
        busy = q.get("busy", "0") not in ("", "0")
        world.clock("cli", parse_hours(q), now)
        if q.get("free") == "1":
            world.clock("cli_map", parse_hours(q), now)
        me = parse_stacks(parse_ints(q["me"].lstrip(","))) if q.get("me", "").lstrip(",") else None
        return reply_numbers([MARKER] + world.client_request(x, y, busy, parse_result(q.get("res", "")), me, now,
                                                             hello=q.get("hello") == "1"))
    return reply_numbers([0, 0])  # unknown path: no marker, the game ignores it


def serve_connection(conn, world, role, log):
    conn.settimeout(5)
    raw = b""
    try:
        while b"\r\n\r\n" not in raw and len(raw) < 65536:
            chunk = conn.recv(8192)
            if not chunk:
                break
            raw += chunk
        first = raw.split(b"\r\n", 1)[0].decode("latin-1", "replace").split(" ")
        target = first[1] if len(first) > 1 else "/"
        body = handle_request(world, role, target, time.time()).encode()
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n"
                     + f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
    except OSError as e:
        log(f"{role}: connection error {e}")
    finally:
        conn.close()


def listen(addr, world, role, log):
    host, port = addr
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(32)
    log(f"{role}: listening on {host}:{port}")

    def loop():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=serve_connection, args=(conn, world, role, log), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return srv


def parse_addr(text):
    host, _, port = text.partition(":")
    return host, int(port or 80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="127.0.0.1:80", help="address the world server game calls")
    ap.add_argument("--client", default="127.0.0.2:80", help="address the client game calls")
    ap.add_argument("--log", default=str(Path(__file__).resolve().parents[1] / "local" / "bridge.log"))
    args = ap.parse_args()
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "a", encoding="utf-8")

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        log_file.write(line + "\n")
        log_file.flush()

    world = World()
    listen(parse_addr(args.server), world, "srv", log)
    listen(parse_addr(args.client), world, "cli", log)
    last = dict(world.stats)
    try:
        while True:
            time.sleep(5)
            with world.lock:
                s, n, client = dict(world.stats), len(world.parties), world.client_pos
                paused = world.paused(time.time())
            clocks = {r: world.clock_rate(r) for r in ("srv", "cli", "cli_map")}
            clock_text = ", ".join(f"{r} clock {'?' if v is None else f'{v:.1f}'} h/min" for r, v in clocks.items())
            rate = {k: (s[k] - last[k]) / 5 for k in s}
            log(f"parties known {n}, server {rate['srv']:.1f}/s ({rate['entries_in']:.0f} entries/s), "
                f"client {rate['cli']:.1f}/s ({rate['entries_out']:.0f} entries/s), client at {client}, "
                f"{'PAUSED' if paused else 'running'}, battle results {s['results']}, {clock_text}")
            last = s
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
