"""Tests for coop_bridge.py: the World logic directly, then the real sockets on spare addresses.

    python -I tools/test_coop_bridge.py
"""
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coop_bridge as cb  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  ", msg)


def test_world():
    w = cb.World()
    now = 1000.0
    check(w.server_report([(500, 3, 100, -200), (501, 4, 9000, 9000)], now) is None,
          "server gets no client position before the client calls")
    out = w.client_request(0, 0)
    check({e[0] for e in out} == {500, 501}, "client receives every known party")
    check(out[0][0] == 500, "nearest party comes first")
    check(w.server_report([], now + 1) == (0, 0), "server learns the client position")
    w.server_report([(501, 4, 9000, 9000)], now + 20)  # 500 not reported for > STALE_S
    out = w.client_request(0, 0)
    check(out[0] == (500, cb.REMOVED, 0, 0), "a stale party is sent as removed, first")
    check(500 not in w.parties, "a stale party leaves the world")
    w.server_report([(i, 1, i, i) for i in range(1000, 1100)], now + 21)
    out = w.client_request(0, 0)
    check(len(out) <= cb.REMOVALS_PER_REPLY + cb.NEAREST_PER_REPLY + cb.ROTATING_PER_REPLY,
          "a reply stays within the register budget")
    check(3 + 4 * len(out) <= 128, "numbers in a reply fit 128 registers")
    seen = set()
    for _ in range(20):
        seen |= {e[0] for e in w.client_request(0, 0)}
    check(len(seen) == 101, "rotation reaches every party within a few replies")
    check(cb.parse_entries("1,2,3,4;bad;5,6,-7,8;9,9") == [(1, 2, 3, 4), (5, 6, -7, 8)],
          "malformed entries are skipped, negatives parsed")


def get(url):
    return urllib.request.urlopen(url, timeout=3).read().decode()


def test_sockets():
    logs = []
    w = cb.World()
    cb.listen(("127.0.0.3", 18090), w, "srv", logs.append)
    cb.listen(("127.0.0.4", 18090), w, "cli", logs.append)
    time.sleep(0.2)
    r = get("http://127.0.0.3:18090/srv?seq=1&n=2&d=700,5,123,-456;701,6,1,1;")
    check(r == "7777|1|0|100000|100000", f"server reply before client: {r}")
    r = get("http://127.0.0.4:18090/cli?seq=1&x=100&y=-400").split("|")
    check(r[:3] == ["7777", "2", "2"], "client reply header")
    check(r[3:7] == ["700", "5", str(123 + cb.COORD_OFFSET), str(-456 + cb.COORD_OFFSET)],
          "nearest entry with shifted coordinates")
    check(all(not v.startswith("-") for v in r), "no negative numbers go to the game")
    r = get("http://127.0.0.3:18090/srv?seq=2&n=0&d=")
    check(r == f"7777|1|1|{100 + cb.COORD_OFFSET}|{-400 + cb.COORD_OFFSET}", f"server gets client position: {r}")
    r = get("http://127.0.0.4:18090/srv?seq=3")
    check(not r.startswith("7777"), "the client address does not serve server requests")


if __name__ == "__main__":
    test_world()
    test_sockets()
    print("ALL OK")
