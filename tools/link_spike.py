"""Link spike: a localhost endpoint for Warband's send_message_to_url.

Speaks plain sockets, not http.server, so that every connection is logged whatever the game
sends (any method, malformed or partial requests). Answers with "<seq>|<served>|pong"
(Warband splits the reply on '|' into reg0.. and s0..).

    python tools/link_spike.py [--port 80] [--log local/link_log.csv]

Loopback only: it is a test endpoint, never expose it.
"""
import argparse
import csv
import socket
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

lock = threading.Lock()
state = {"served": 0, "start": None, "last": None}


def handle(conn, addr, writer, log_file):
    conn.settimeout(5)
    raw = b""
    try:
        while b"\r\n\r\n" not in raw and len(raw) < 65536:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk
    except socket.timeout:
        pass
    now = time.time()
    first = raw.split(b"\r\n", 1)[0].decode("latin-1", "replace")
    parts = first.split(" ")
    method = parts[0] if parts else ""
    target = parts[1] if len(parts) > 1 else ""
    url = urlparse(target)
    q = {k: v[0] for k, v in parse_qs(url.query).items()}
    with lock:
        state["served"] += 1
        state["start"] = state["start"] or now
        gap = now - state["last"] if state["last"] else 0.0
        state["last"] = now
        served = state["served"]
        writer.writerow([f"{now:.3f}", f"{gap:.3f}", conn.getsockname()[1], q.get("form", ""), method, url.path, q.get("seq", ""), q.get("frames", ""),
                         q.get("hours", ""), q.get("free", ""), q.get("x", ""), q.get("y", ""),
                         raw[:300].decode("latin-1", "replace").replace("\r\n", " | ")])
        log_file.flush()
    body = f"{q.get('seq', '0')}|{served}|pong".encode()
    try:
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n"
                     + f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
    except OSError:
        pass
    conn.close()
    if served <= 3 or served % 20 == 0:
        elapsed = now - state["start"]
        rate = served / elapsed if elapsed > 0 else 0
        print(f"[{served}] {method} {target[:90]} gap={gap:.2f}s rate={rate:.2f}/s", flush=True)
        if served <= 3:
            print("    raw:", raw[:300], flush=True)


def accept_loop(srv, writer, log_file):
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle, args=(conn, addr, writer, log_file), daemon=True).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=80, help="the game always connects to 80")
    ap.add_argument("--extra-port", type=int, action="append", default=[],
                    help="also listen here (e.g. 80, in case the game ignores the port in the URL)")
    ap.add_argument("--log", default=str(Path(__file__).resolve().parents[1] / "local" / "link_log.csv"))
    args = ap.parse_args()
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "a", newline="", encoding="utf-8")
    writer = csv.writer(log_file)
    if log_file.tell() == 0:
        writer.writerow(["time", "gap_s", "port", "form", "method", "path", "seq", "frames", "hours", "map_free", "x", "y", "raw"])
    servers = []
    for port in [args.port] + args.extra_port:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", port))
        srv.listen(16)
        servers.append(srv)
        print(f"link spike listening on 127.0.0.1:{port} (raw), log: {log_path}", flush=True)
    for srv in servers[1:]:
        threading.Thread(target=accept_loop, args=(srv, writer, log_file), daemon=True).start()
    srv = servers[0]
    try:
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle, args=(conn, addr, writer, log_file), daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        log_file.close()
        print(f"served {state['served']} connections", flush=True)


if __name__ == "__main__":
    main()
