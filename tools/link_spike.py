"""Link spike: a localhost HTTP endpoint for Warband's send_message_to_url.

Answers every request with "<seq>|<served>|pong" (Warband splits the reply on '|' into
reg0.. and s0..) and logs each request so we learn whether the call works in the
single-player campaign, how often the game can call it, and what the round trip costs.

    python tools/link_spike.py [--port 7341] [--log local/link_log.csv]

Loopback only: it is a test endpoint, never expose it.
"""
import argparse
import csv
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

STATE = {"served": 0, "start": None, "last": None}


class Handler(BaseHTTPRequestHandler):
    log_writer = None

    def do_GET(self):
        now = time.time()
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        STATE["served"] += 1
        STATE["start"] = STATE["start"] or now
        gap = now - STATE["last"] if STATE["last"] else 0.0
        STATE["last"] = now
        seq = q.get("seq", "0")
        body = f"{seq}|{STATE['served']}|pong".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.log_writer.writerow([f"{now:.3f}", f"{gap:.3f}", url.path, seq, q.get("frames", ""),
                                  q.get("hours", ""), q.get("free", ""), q.get("x", ""), q.get("y", "")])
        self.log_file.flush()
        if STATE["served"] % 20 == 1:
            elapsed = now - STATE["start"]
            rate = STATE["served"] / elapsed if elapsed > 0 else 0
            print(f"[{STATE['served']}] {url.path} seq={seq} gap={gap:.2f}s rate={rate:.2f}/s "
                  f"frames={q.get('frames')} hours={q.get('hours')} free={q.get('free')} "
                  f"pos=({q.get('x')},{q.get('y')})", flush=True)

    def log_message(self, *args):
        pass  # requests go to the CSV log instead


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7341)
    ap.add_argument("--log", default=str(Path(__file__).resolve().parents[1] / "local" / "link_log.csv"))
    args = ap.parse_args()
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(log_path, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if f.tell() == 0:
        w.writerow(["time", "gap_s", "path", "seq", "frames", "hours", "map_free", "x", "y"])
    Handler.log_writer, Handler.log_file = w, f
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"link spike listening on http://127.0.0.1:{args.port}/ , log: {log_path}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        f.close()
        print(f"served {STATE['served']} requests", file=sys.stderr)


if __name__ == "__main__":
    main()
