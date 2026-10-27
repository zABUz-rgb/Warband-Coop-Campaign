"""CoopWorld bridge, prototype: relays the world between a server game and one client game on one PC.

Both games talk to it with Warband's send_message_to_url, which always uses port 80 and ignores
any port in the URL, so each game gets its own loopback address:

    world server game  -> http://127.0.0.1/srv?seq=S&n=K&d=sid,tmpl,x,y;...
                          reply 7777|1|has_client|client_x|client_y
    client game        -> http://127.0.0.2/cli?seq=S&x=X&y=Y
                          reply 7777|2|n|sid|tmpl|x|y|... (n entries)

Positions are map coordinates * 100. In replies to the games every coordinate is shifted by
COORD_OFFSET so that only non-negative numbers go back (how the engine parses "-5" is untested).
tmpl == REMOVED in a client entry means "this party is gone on the server".

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
NEAREST_PER_REPLY = 15
ROTATING_PER_REPLY = 8
REMOVALS_PER_REPLY = 5  # 3 header numbers + 4 per entry must stay within 128 registers


class World:
    def __init__(self):
        self.lock = threading.Lock()
        self.parties = {}       # sid -> [tmpl, x, y, last_seen]
        self.removed = []       # sids the client still has to drop
        self.client_pos = None  # (x, y)
        self.cursor = 0
        self.stats = {"srv": 0, "cli": 0, "entries_in": 0, "entries_out": 0}

    def server_report(self, entries, now):
        with self.lock:
            self.stats["srv"] += 1
            for sid, tmpl, x, y in entries:
                self.parties[sid] = [tmpl, x, y, now]
                self.stats["entries_in"] += 1
                if sid in self.removed:
                    self.removed.remove(sid)
            for sid in [s for s, p in self.parties.items() if now - p[3] > STALE_S]:
                del self.parties[sid]
                self.removed.append(sid)
            return self.client_pos

    def client_request(self, x, y):
        with self.lock:
            self.stats["cli"] += 1
            self.client_pos = (x, y)
            out = []
            while self.removed and len(out) < REMOVALS_PER_REPLY:
                out.append((self.removed.pop(0), REMOVED, 0, 0))
            by_distance = sorted(self.parties.items(),
                                 key=lambda kv: (kv[1][1] - x) ** 2 + (kv[1][2] - y) ** 2)
            chosen = {sid for sid, _ in by_distance[:NEAREST_PER_REPLY]}
            out += [(sid, p[0], p[1], p[2]) for sid, p in by_distance[:NEAREST_PER_REPLY]]
            rest = [kv for kv in sorted(self.parties.items()) if kv[0] not in chosen]
            if rest:
                start = self.cursor % len(rest)
                for sid, p in (rest[start:] + rest[:start])[:ROTATING_PER_REPLY]:
                    out.append((sid, p[0], p[1], p[2]))
                self.cursor = start + ROTATING_PER_REPLY
            self.stats["entries_out"] += len(out)
            return out


def parse_entries(d):
    entries = []
    for chunk in d.split(";"):
        parts = chunk.split(",")
        if len(parts) == 4:
            try:
                entries.append(tuple(int(v) for v in parts))
            except ValueError:
                pass
    return entries


def reply_numbers(numbers):
    return "|".join(str(int(v)) for v in numbers)


def handle_request(world, role, target, now):
    url = urlparse(target)
    q = {k: v[0] for k, v in parse_qs(url.query).items()}
    if role == "srv" and url.path == "/srv":
        client = world.server_report(parse_entries(q.get("d", "")), now)
        if client is None:
            return reply_numbers([MARKER, 1, 0, COORD_OFFSET, COORD_OFFSET])
        return reply_numbers([MARKER, 1, 1, client[0] + COORD_OFFSET, client[1] + COORD_OFFSET])
    if role == "cli" and url.path == "/cli":
        try:
            x, y = int(q.get("x", "0")), int(q.get("y", "0"))
        except ValueError:
            x = y = 0
        out = world.client_request(x, y)
        nums = [MARKER, 2, len(out)]
        for sid, tmpl, ex, ey in out:
            nums += [sid, tmpl, ex + COORD_OFFSET, ey + COORD_OFFSET]
        return reply_numbers(nums)
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
            rate = {k: (s[k] - last[k]) / 5 for k in s}
            log(f"parties known {n}, server {rate['srv']:.1f}/s ({rate['entries_in']:.0f} entries/s), "
                f"client {rate['cli']:.1f}/s ({rate['entries_out']:.0f} entries/s), client at {client}")
            last = s
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
