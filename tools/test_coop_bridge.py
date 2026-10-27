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
    """client reply [2, n, sid, tmpl, x, y, tx, ty, att, ...] -> [(sid, tmpl, x, y, tx, ty, att)], no offset"""
    assert nums[0] == 2, nums
    out = []
    for i in range(nums[1]):
        sid, tmpl, *coords, att = nums[2 + 7 * i:9 + 7 * i]
        if tmpl != cb.REMOVED:
            coords = [c - cb.COORD_OFFSET for c in coords]
        out.append((sid, tmpl, *coords, att))
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
    client, pause, joins, payload, _ = w.server_report([(500, 3, 100, -200, 150, -250), (501, 4, 9000, 9000, 9000, 9000)],
                                             None, now)
    check(client is None and not pause and joins == 0 and payload == [0], "server: no client yet, no pause, nothing to do")
    out = positions(w, now=now)
    check({e[0] for e in out} == {500, 501}, "client receives every known party")
    check(out[0] == (500, 3, 100, -200, 150, -250, 0), "nearest party first, position and target restored")
    check(w.server_report([], None, now + 1)[0] == (0, 0), "server learns the client position")
    w.server_report([(501, 4, 9000, 9000, 9000, 9000)], None, now + 20)  # 500 not reported for > STALE_S
    out = positions(w, now=now + 20)
    check(out[0] == (500, cb.REMOVED, 0, 0, 0, 0, 0), "a stale party is sent as removed, first")
    w.server_report([(i, 1, i, i, i, i) for i in range(1000, 1100)], None, now + 21)
    seen = set()
    for _ in range(40):
        nums = w.client_request(0, 0, False, None, None, now + 21)
        check(len(nums) + 1 <= 128, "a reply fits 128 registers") if not seen else None
        if nums[0] == 2:
            seen |= {e[0] for e in entries_of(nums)}
    check(len(seen) == 101, "rotation reaches every party within a few replies")
    check(cb.parse_entries("1,2,3,4;bad;5,6,-7,8,9,10;7,1,0,0,0,0,13;9,9")
          == [(1, 2, 3, 4, 3, 4, 0), (5, 6, -7, 8, 9, 10, 0), (7, 1, 0, 0, 0, 0, 13)],
          "malformed entries skipped, negatives parsed, no target: stay put, no att: open map")
    w.server_report([(77, 1, 5, 5, 5, 5, 13)], None, now + 21)
    check([e for e in positions(w, now=now + 21) if e[0] == 77][0][6] == 13, "the town a party is in reaches the client")
    w.clock("srv", 10, 0.0)
    w.clock("srv", 12, 30.0)
    check(abs(w.clock_rate("srv") - 4.0) < 1e-9 and w.clock_rate("cli") is None,
          "game clock speed in hours per real minute")


def test_pause():
    w = cb.World()
    w.server_report([], None, 0.0)
    w.client_request(0, 0, True, None, None, 10.0)
    check(w.server_report([], None, 11.0)[1] is True, "a busy client pauses the world")
    check(w.server_report([], None, 10.0 + cb.BUSY_TIMEOUT_S + 1)[1] is False,
          "a client silent for too long while busy no longer pauses the world")
    w.client_request(0, 0, False, None, None, 12.0)
    check(w.server_report([], None, 12.2)[1] is False, "back on the map: the world runs")
    check(w.server_report([], None, 12.0 + cb.SILENT_PAUSE_S + 0.1)[1] is True,
          "a client gone silent (a menu, a screen) pauses the world")
    w.client_request(0, 0, False, None, None, 14.0, bye=True)
    check(w.server_report([], None, 20.0)[1] is False, "a client that said bye does not pause the world")


def test_troops_and_results():
    w = cb.World()
    w.server_report([(600, 7, 0, 0, 0, 0)], (600, [(31, 5), (32, 2)]), 0.0)
    replies = [w.client_request(0, 0, False, None, None, 1.0) for _ in range(2)]
    troop_replies = [r for r in replies if r[0] == 3]
    check(troop_replies == [[3, 600, 2, 31, 5, 32, 2]], "client gets the troops of a nearby party once")
    replies = [w.client_request(0, 0, False, None, None, 1.0) for _ in range(4)]
    check(all(r[0] == 2 for r in replies), "unchanged troops are not sent again")
    w.server_report([(600, 7, 0, 0, 0, 0)], (600, [(31, 4), (32, 2)]), 2.0)
    replies = [w.client_request(0, 0, False, None, None, 2.0) for _ in range(2)]
    check([3, 600, 2, 31, 4, 32, 2] in replies, "changed troops are sent again")

    # the client fought party 600: 3 of troop 31 left, troop 32 gone
    w.client_request(0, 0, False, (600, 0, [(31, 3)]), [(40, 8)], 3.0)
    _, _, _, payload, _ = w.server_report([], (600, [(31, 4), (32, 2)]), 3.0)
    check(payload == [1, 600, 0, 1, 31, 3], "server receives the battle result")
    check(w.troops[600][1] == [(31, 3)], "the server's older troops report did not undo the result")
    _, _, _, payload, _ = w.server_report([], None, 3.1)
    check(payload == [2, 1, 40, 8], "then the client's own troops for the puppet")
    _, _, _, payload, _ = w.server_report([], None, 3.2)
    check(payload == [0], "then nothing")
    replies = [w.client_request(0, 0, False, None, [(40, 8)], 3.3) for _ in range(4)]
    check(all(r[0] == 2 for r in replies), "the client is not sent back its own battle result")
    check(w.server_report([], None, 3.4)[3] == [0], "unchanged own troops are not resent")
    w.client_request(0, 0, False, None, [], 3.9)
    check(w.server_report([], None, 3.95)[3] == [2, 0], "a party of heroes only is sent as an empty list")
    w.client_request(0, 0, False, (601, 1, []), None, 4.0)
    check(w.server_report([], None, 4.0)[3] == [1, 601, 1, 0], "a destroyed party")
    check(cb.parse_result("601,1") == (601, 1, []) and cb.parse_result("601,0,5") is None
          and cb.parse_troops("7,1,2,3,4") == (7, [(1, 2), (3, 4)]), "result and troop parsing")


def test_join_and_tombstones():
    w = cb.World()
    w.server_report([(800, 5, 0, 0, 0, 0)], None, 0.0)
    w.client_request(0, 0, False, None, None, 1.0, hello=True)
    check(w.server_report([], None, 1.1)[2] == 1, "a client hello counts as a join")
    w.client_request(0, 0, False, (800, 1, []), None, 2.0)
    check(800 not in w.parties, "a party the client destroyed leaves the bridge at once")
    w.server_report([(800, 5, 0, 0, 0, 0)], None, 2.1)  # the server has not removed it yet
    check(800 not in w.parties, "and the server's late reports do not bring it back")
    replies = [w.client_request(0, 0, False, None, None, 2.2) for _ in range(4)]
    check(all(800 not in [r[2 + 7 * i] for i in range(r[1])] for r in replies if r[0] == 2),
          "so the client does not see it again")
    w.server_report([(800, 5, 0, 0, 0, 0)], None, 2.0 + cb.TOMBSTONE_S + 1)
    check(800 in w.parties, "after the tombstone time the server's report counts again (a lord who stayed)")
    w.server_report([(900, 5, 0, 0, 0, 0)], None, 3.0)
    w.server_report([], None, 3.0 + cb.STALE_S + 5, hold=True)
    check(900 in w.parties, "nothing goes stale while the server holds the world")
    w.clock("cli_map", 10, 100.0)
    w.clock("cli_map", 11, 100.5)
    w.clock("cli_map", 30, 110.0)  # more than a second later: the client rested in between
    check(w.clocks["cli_map"] == [(110.0, 30)], "the map clock only measures uninterrupted map time")


def test_name():
    w = cb.World()
    w.client_request(0, 0, False, None, None, 1.0, name="Ivan Petrov")
    check(w.server_report([], None, 1.1)[4] == "Ivan Petrov", "the client's name goes to the server once")
    check(w.server_report([], None, 1.2)[4] is None, "and only once")


def get(url):
    return urllib.request.urlopen(url, timeout=3).read().decode()


def test_sockets():
    logs = []
    w = cb.World()
    cb.listen(("127.0.0.3", 18090), w, "srv", logs.append)
    cb.listen(("127.0.0.4", 18090), w, "cli", logs.append)
    time.sleep(0.2)
    off = cb.COORD_OFFSET
    r = get("http://127.0.0.3:18090/srv?seq=1&h=50&n=2&d=700,5,123,-456,200,-456;701,6,1,1,1,1;&c=700,31,9")
    check(r == f"7777|1|0|{off}|{off}|0|0|0", f"server reply before client: {r}")
    r = get("http://127.0.0.4:18090/cli?seq=1&x=100&y=-400&busy=1").split("|")
    check(r[:3] == ["7777", "2", "2"], "client reply header")
    check(r[3:10] == ["700", "5", str(123 + off), str(-456 + off), str(200 + off), str(-456 + off), "0"],
          "nearest entry with shifted position and target")
    check(all(not v.startswith("-") for v in r), "no negative numbers go to the game")
    r = get("http://127.0.0.4:18090/cli?seq=2&x=100&y=-400&busy=2&hello=1&res=700,0,31,4&me=,40,8")
    r = get("http://127.0.0.3:18090/srv?seq=2&n=0&d=")
    check(r == f"7777|1|1|{100 + off}|{-400 + off}|1|1|1|700|0|1|31|4",
          f"server: client position, PAUSED (busy 2), one join, battle result: {r}")
    r = get("http://127.0.0.3:18090/srv?seq=3&n=0&d=")
    check(r.endswith("|1|1|2|1|40|8"), f"server: puppet troops (leading comma accepted): {r}")
    import socket
    s = socket.create_connection(("127.0.0.4", 18090))
    s.sendall(b"GET /cli?seq=4&x=1&y=1&busy=0&name=Ivan Petrov HTTP/1.1\r\nHost: x\r\n\r\n")
    s.recv(500)
    s.close()
    r = get("http://127.0.0.3:18090/srv?seq=4&n=0&d=")
    check(r.endswith("|Ivan Petrov"), f"a raw space in the request line keeps the whole name: {r}")
    r = get("http://127.0.0.4:18090/srv?seq=3")
    check(not r.startswith("7777"), "the client address does not serve server requests")


if __name__ == "__main__":
    test_positions()
    test_pause()
    test_troops_and_results()
    test_join_and_tombstones()
    test_name()
    test_sockets()
    print("ALL OK")
