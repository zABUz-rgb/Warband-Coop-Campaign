"""Tests for coop_bridge.py: the World logic directly, then the real sockets on spare addresses.

    python -I tools/test_coop_bridge.py
"""
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coop_bridge as cb  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  ", msg)


def entries_of(nums):
    """client reply [2, n, sid, tmpl, x, y, ...] -> [(sid, tmpl, x, y), ...] without the offset"""
    assert nums[0] == 2, nums
    out = []
    for i in range(nums[1]):
        sid, tmpl, x, y = nums[2 + 4 * i:6 + 4 * i]
        out.append((sid, tmpl, x - cb.COORD_OFFSET if tmpl != cb.REMOVED else 0,
                    y - cb.COORD_OFFSET if tmpl != cb.REMOVED else 0))
    return out


def positions(w, x=0, y=0, now=0.0):
    """a client request that returns positions (troop replies come on every other request)"""
    for _ in range(4):
        nums = w.client_request(x, y, False, None, None, now)
        if nums[0] == 2:
            return entries_of(nums)
    raise AssertionError("no position reply")


def test_positions():
    w = cb.World()
    now = 1000.0
    client, pause, payload = w.server_report([(500, 3, 100, -200), (501, 4, 9000, 9000)], None, now)
    check(client is None and not pause and payload == [0], "server: no client yet, no pause, nothing to do")
    out = positions(w, now=now)
    check({e[0] for e in out} == {500, 501}, "client receives every known party")
    check(out[0] == (500, 3, 100, -200), "nearest party first, coordinates restored")
    check(w.server_report([], None, now + 1)[0] == (0, 0), "server learns the client position")
    w.server_report([(501, 4, 9000, 9000)], None, now + 20)  # 500 not reported for > STALE_S
    out = positions(w, now=now + 20)
    check(out[0] == (500, cb.REMOVED, 0, 0), "a stale party is sent as removed, first")
    w.server_report([(i, 1, i, i) for i in range(1000, 1100)], None, now + 21)
    seen = set()
    for _ in range(40):
        nums = w.client_request(0, 0, False, None, None, now + 21)
        check(len(nums) + 1 <= 128, "a reply fits 128 registers") if not seen else None
        if nums[0] == 2:
            seen |= {e[0] for e in entries_of(nums)}
    check(len(seen) == 101, "rotation reaches every party within a few replies")
    check(cb.parse_entries("1,2,3,4;bad;5,6,-7,8;9,9") == [(1, 2, 3, 4), (5, 6, -7, 8)],
          "malformed entries are skipped, negatives parsed")


def test_pause():
    w = cb.World()
    w.server_report([], None, 0.0)
    w.client_request(0, 0, True, None, None, 10.0)
    check(w.server_report([], None, 11.0)[1] is True, "a busy client pauses the world")
    check(w.server_report([], None, 10.0 + cb.BUSY_TIMEOUT_S + 1)[1] is False,
          "a client silent for too long while busy no longer pauses the world")
    w.client_request(0, 0, False, None, None, 12.0)
    check(w.server_report([], None, 13.0)[1] is False, "back on the map: the world runs")


def test_troops_and_results():
    w = cb.World()
    w.server_report([(600, 7, 0, 0)], (600, [(31, 5), (32, 2)]), 0.0)
    replies = [w.client_request(0, 0, False, None, None, 1.0) for _ in range(2)]
    troop_replies = [r for r in replies if r[0] == 3]
    check(troop_replies == [[3, 600, 2, 31, 5, 32, 2]], "client gets the troops of a nearby party once")
    replies = [w.client_request(0, 0, False, None, None, 1.0) for _ in range(4)]
    check(all(r[0] == 2 for r in replies), "unchanged troops are not sent again")
    w.server_report([(600, 7, 0, 0)], (600, [(31, 4), (32, 2)]), 2.0)
    replies = [w.client_request(0, 0, False, None, None, 2.0) for _ in range(2)]
    check([3, 600, 2, 31, 4, 32, 2] in replies, "changed troops are sent again")

    # the client fought party 600: 3 of troop 31 left, troop 32 gone
    w.client_request(0, 0, False, (600, 0, [(31, 3)]), [(40, 8)], 3.0)
    _, _, payload = w.server_report([], (600, [(31, 4), (32, 2)]), 3.0)
    check(payload == [1, 600, 0, 1, 31, 3], "server receives the battle result")
    check(w.troops[600][1] == [(31, 3)], "the server's older troops report did not undo the result")
    _, _, payload = w.server_report([], None, 3.1)
    check(payload == [2, 1, 40, 8], "then the client's own troops for the puppet")
    _, _, payload = w.server_report([], None, 3.2)
    check(payload == [0], "then nothing")
    replies = [w.client_request(0, 0, False, None, [(40, 8)], 3.3) for _ in range(4)]
    check(all(r[0] == 2 for r in replies), "the client is not sent back its own battle result")
    check(w.server_report([], None, 3.4)[2] == [0], "unchanged own troops are not resent")
    w.client_request(0, 0, False, (601, 1, []), None, 4.0)
    check(w.server_report([], None, 4.0)[2] == [1, 601, 1, 0], "a destroyed party")
    check(cb.parse_result("601,1") == (601, 1, []) and cb.parse_result("601,0,5") is None
          and cb.parse_troops("7,1,2,3,4") == (7, [(1, 2), (3, 4)]), "result and troop parsing")


def get(url):
    return urllib.request.urlopen(url, timeout=3).read().decode()


def test_sockets():
    logs = []
    w = cb.World()
    cb.listen(("127.0.0.3", 18090), w, "srv", logs.append)
    cb.listen(("127.0.0.4", 18090), w, "cli", logs.append)
    time.sleep(0.2)
    off = cb.COORD_OFFSET
    r = get("http://127.0.0.3:18090/srv?seq=1&n=2&d=700,5,123,-456;701,6,1,1;&c=700,31,9")
    check(r == f"7777|1|0|{off}|{off}|0|0", f"server reply before client: {r}")
    r = get("http://127.0.0.4:18090/cli?seq=1&x=100&y=-400&busy=1").split("|")
    check(r[:3] == ["7777", "2", "2"], "client reply header")
    check(r[3:7] == ["700", "5", str(123 + off), str(-456 + off)], "nearest entry with shifted coordinates")
    check(all(not v.startswith("-") for v in r), "no negative numbers go to the game")
    r = get("http://127.0.0.4:18090/cli?seq=2&x=100&y=-400&busy=1&res=700,0,31,4&me=40,8")
    r = get("http://127.0.0.3:18090/srv?seq=2&n=0&d=")
    check(r == f"7777|1|1|{100 + off}|{-400 + off}|1|1|700|0|1|31|4",
          f"server: client position, PAUSED, battle result: {r}")
    r = get("http://127.0.0.3:18090/srv?seq=3&n=0&d=")
    check(r.endswith("|1|2|1|40|8"), f"server: puppet troops: {r}")
    r = get("http://127.0.0.4:18090/srv?seq=3")
    check(not r.startswith("7777"), "the client address does not serve server requests")


if __name__ == "__main__":
    test_positions()
    test_pause()
    test_troops_and_results()
    test_sockets()
    print("ALL OK")
