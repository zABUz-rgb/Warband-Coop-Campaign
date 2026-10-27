"""Tests for coop_bridge.py: the World logic, then real sockets (games' HTTP, hub and relay).

    python -I tools/test_coop_bridge.py
"""
import socket
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coop_bridge as cb  # noqa: E402

OFF = cb.COORD_OFFSET


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  ", msg)


def entries_of(nums):
    """[2, n, sid, tmpl, x, y, tx, ty, att, ...] -> [(sid, tmpl, x, y, tx, ty, att)] without the offset"""
    assert nums[0] == 2, nums
    out = []
    for i in range(nums[1]):
        sid, tmpl, *coords, att = nums[2 + 7 * i:9 + 7 * i]
        if tmpl != cb.REMOVED:
            coords = [c - OFF for c in coords]
        out.append((sid, tmpl, *coords, att))
    return out


def req(w, cid="a", x=0, y=0, now=0.0, **kw):
    busy, result, me = kw.pop("busy", False), kw.pop("result", None), kw.pop("me", None)
    return w.player_request(cid, x, y, busy, result, me, now, **kw)


def positions(w, cid="a", now=0.0):
    for _ in range(8):
        nums, _ = req(w, cid, now=now)
        if nums[0] == 2:
            return entries_of(nums)
    raise AssertionError("no position reply")


def test_positions():
    w = cb.World()
    w.server_report([(500, 3, 100, -200, 150, -250, 0), (501, 4, 9000, 9000, 9000, 9000, 0)], None, 0.0)
    out = positions(w)
    check({e[0] for e in out} == {500, 501}, "a player receives every known party")
    check(out[0] == (500, 3, 100, -200, 150, -250, 0), "nearest first: position, target, town")
    w.server_report([(501, 4, 9000, 9000)], None, 20.0)  # 500 not reported for > STALE_S
    check(positions(w, now=20.0)[0] == (500, cb.REMOVED, 0, 0, 0, 0, 0), "a stale party is sent as removed, first")
    w.server_report([(i, 1, i, i) for i in range(1000, 1100)], None, 21.0)
    seen, fits = set(), True
    for _ in range(80):
        nums, _ = req(w, now=21.0)
        fits = fits and len(nums) + 1 <= 128
        if nums[0] == 2:
            seen |= {e[0] for e in entries_of(nums)}
    check(fits, "every reply fits 128 registers")
    check(len(seen) == 101, "rotation reaches every party within a few replies")
    check(cb.parse_entries("1,2,3,4;bad;5,6,-7,8,9,10;7,1,0,0,0,0,13;9,9")
          == [(1, 2, 3, 4, 3, 4, 0), (5, 6, -7, 8, 9, 10, 0), (7, 1, 0, 0, 0, 0, 13)],
          "malformed entries skipped, negatives parsed, no target: stay put, no att: open map")


def test_players_and_puppets():
    w = cb.World()
    req(w, "a", 100, 200, now=1.0, hello=True, name="Anna")
    req(w, "b", 300, 400, now=1.0, hello=True, name="Boris Bek")
    pause, joins, puppets, payload, name = w.server_report([], None, 1.1)
    check(joins == 2 and sorted(puppets) == [(0, 100, 200), (1, 300, 400)], "two players: two puppets, two joins")
    check(payload == [3, 0] and name == "Anna", "the server learns the first player's name")
    check(w.server_report([], None, 1.2)[3:] == ([3, 1], "Boris Bek"), "then the second's")
    check(w.server_report([], None, 1.3)[3] == [0], "then nothing")
    others = [r for r in (req(w, "a", 100, 200, now=1.4) for _ in range(8)) if r[0][0] == 4]
    check(others and others[0] == ([4, 1, 300 + OFF, 400 + OFF, 0], "Boris Bek"),
          "a player sees the other player's party and name")
    check(all(r[0][1] != 0 for r in others), "and never its own")
    for cid in "cde":
        req(w, cid, now=1.5)
    check(w.players["e"].slot is None and len([p for p in w.players.values() if p.slot is not None]) == 4,
          f"at most {cb.MAX_PLAYERS} players get a party")
    req(w, "b", now=1.6, bye=True)
    req(w, "e", now=1.7)
    check(w.players["e"].slot == 1, "a player who left frees the party for the next one")
    req(w, "a", now=1.8, me=[(40, 8)])
    check(w.server_report([], None, 1.9)[3][:3] == [2, 0, 1], "a player's troops go to its puppet")
    req(w, "a", now=2.0, me=[])
    check(w.server_report([], None, 2.1)[3] == [2, 0, 0], "a party of heroes only is sent as an empty list")


def statuses(w, cid, now, n=4, **kw):
    return [r[0] for r in (req(w, cid, now=now, **kw) for _ in range(n)) if r[0][0] == 5]


def test_shared_pause():
    w = cb.World()
    req(w, "a", now=1.0)
    req(w, "b", now=1.0)
    check(statuses(w, "b", 1.1) == [], "nothing new: no status reply")
    req(w, "a", now=2.0, busy=True)
    check(statuses(w, "b", 2.1) == [[5, 1, 0, 1]], "player b is told at once: the world stands, player 0 is in battle")
    check(statuses(w, "a", 2.1, busy=True) in ([], [[5, 0, 0, 0]]),
          "the player in battle is not paused by itself")
    req(w, "a", now=3.0)
    check(statuses(w, "b", 3.1) == [[5, 0, 0, 0]], "the battle is over: the world runs again for b")
    check(statuses(w, "b", 3.0 + cb.SILENT_PAUSE_S + 0.2)[:1] == [[5, 1, 0, 2]],
          "player a silent in a menu: b stands still too (why 2)")
    w2 = cb.World()
    req(w2, "a", now=0.0)
    got = [r[0] for r in (req(w2, "a", now=0.0) for _ in range(cb.STATUS_EVERY + 2)) if r[0][0] == 5]
    check(len(got) == 1, "an unchanged state is repeated now and then, in case a reply was lost")


def test_pause():
    w = cb.World()
    req(w, "a", now=10.0, busy=True)
    check(w.server_report([], None, 10.1)[0] is True, "a busy player pauses the world")
    req(w, "a", now=10.2)
    req(w, "b", now=10.2)
    check(w.server_report([], None, 10.3)[0] is False, "everyone on the map: the world runs")
    req(w, "a", now=10.9)
    check(w.server_report([], None, 10.2 + cb.SILENT_PAUSE_S + 0.1)[0] is True,
          "one player gone silent (a menu) pauses the world for all")
    req(w, "b", now=12.0, bye=True)
    req(w, "a", now=12.0)
    check(w.server_report([], None, 12.1)[0] is False, "a player that said bye pauses nothing")
    w.drop_player("a")
    check(w.server_report([], None, 30.0)[0] is False, "a player whose connection dropped pauses nothing")


def test_troops_results_tombstones():
    w = cb.World()
    w.server_report([(600, 7, 0, 0)], (600, [(31, 5), (32, 2)]), 0.0)
    replies = [req(w, "a", now=1.0)[0] for _ in range(2)]
    check([3, 600, 2, 31, 5, 32, 2] in replies, "a player gets the troops of a nearby party")
    check(all(r[0] == 2 for r in (req(w, "a", now=1.0)[0] for _ in range(4))), "unchanged troops are not resent")
    req(w, "a", now=2.0, result=(600, 0, [(31, 3)]))
    check(w.server_report([], (600, [(31, 5)]), 2.1)[3] == [1, 600, 0, 1, 31, 3], "the server gets the result")
    check(w.troops[600][1] == [(31, 3)], "the server's older report did not undo the result")
    check([3, 600, 1, 31, 3] in [req(w, "b", now=2.2)[0] for _ in range(4)],
          "another player gets the new troops of that party")
    w.server_report([(601, 7, 0, 0)], None, 3.0)
    positions(w, "b", now=3.0)
    req(w, "a", now=3.1, result=(601, 1, []))
    check(601 not in w.parties, "a party a player destroyed leaves the hub at once")
    w.server_report([(601, 7, 0, 0)], None, 3.2)
    check(601 not in w.parties, "the server's late reports do not bring it back")
    check(601 in w.players["b"].removed and 601 not in w.players["a"].removed,
          "the other player is told to drop it, the one who destroyed it is not")
    w.server_report([(601, 7, 0, 0)], None, 3.0 + cb.TOMBSTONE_S + 1)
    check(601 in w.parties, "after the tombstone time the server's report counts again (a lord who stayed)")
    w.server_report([(602, 1, 0, 0)], None, 40.0)
    w.server_report([], None, 40.0, hold=True)
    w.server_report([], None, 40.0 + cb.STALE_S + 5, hold=True)
    check(602 in w.parties, "nothing goes stale while the server holds the world")


def test_clock():
    w = cb.World()
    w.clock("srv", 10, 0.0)
    w.clock("srv", 12, 30.0)
    check(abs(w.clock_rate("srv") - 4.0) < 1e-9, "game clock speed in hours per real minute")


def get(url):
    return urllib.request.urlopen(url, timeout=3).read().decode("latin-1")


def raw_get(host, port, target):
    s = socket.create_connection((host, port))
    s.sendall(f"GET {target} HTTP/1.1\r\nHost: x\r\n\r\n".encode("latin-1"))
    data = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
    s.close()
    return data.split(b"\r\n\r\n", 1)[1].decode("latin-1")


def test_hub_and_relay():
    logs = []
    log = logs.append
    w = cb.World()
    srv, cli, net = ("127.0.0.3", 18090), ("127.0.0.4", 18090), ("127.0.0.5", 18091)
    save_dir = Path(tempfile.mkdtemp())
    (save_dir / "sg00.sav").write_bytes(b"old")
    time.sleep(0.05)
    (save_dir / "sg03.sav").write_bytes(b"\x00world\xffsave")
    cb.serve_http(srv, lambda t: cb.handle_request(w, "srv", t, time.time()), log, "srv")
    cb.serve_http(cli, lambda t: cb.handle_request(w, "cli", t, time.time()), log, "cli")
    cb.serve_relays(net, w, "secret", str(save_dir), log)
    time.sleep(0.2)

    r = get("http://127.0.0.3:18090/srv?seq=1&h=50&n=1&d=700,5,123,-456,200,-456,0;&c=700,31,9")
    check(r == "7777|1|0|0|0|0", f"server reply before any player: {r}")
    r = raw_get(*cli, "/cli?seq=1&x=100&y=-400&busy=0&hello=1&me=,40,8&name=Ivan Petrov").split("|")
    check(r == ["7777", "5", "0", "0", "0"], f"a new player first hears that the world runs: {r}")
    for seq in (2, 3, 4):  # the reply kinds take turns: wait for the positions
        r = raw_get(*cli, f"/cli?seq={seq}&x=100&y=-400&busy=0").split("|")
        if r[1] == "2":
            break
    check(r[:3] == ["7777", "2", "1"] and r[3:10] == ["700", "5", str(123 + OFF), str(-456 + OFF),
                                                     str(200 + OFF), str(-456 + OFF), "0"],
          "the host's own player: positions with shifted coordinates")
    check(all(not v.startswith("-") for v in r), "no negative numbers go to the game")

    try:
        cb.Relay(net, "wrong", log).connect()
        refused = False
    except ConnectionError:
        refused = True
    check(refused, "a relay with a wrong key is refused")

    relay = cb.Relay(net, "secret", log)
    relay.connect()
    remote_dir = Path(tempfile.mkdtemp())
    (remote_dir / "sg90.sav").write_bytes(b"friend's own")
    path, name = relay.fetch_save(remote_dir, "sg90.sav")
    check(name == "sg03.sav" and path.read_bytes() == b"\x00world\xffsave",
          "a relay fetches the host's newest save, byte for byte")
    check((remote_dir / "sg90.sav.bak").read_bytes() == b"friend's own", "a save it replaces is kept as .bak")
    fresh = remote_dir / "never saved in CoopWorld" / "CoopWorld"
    path, _ = relay.fetch_save(fresh)
    check(path.read_bytes() == b"\x00world\xffsave", "a player with no CoopWorld save folder yet gets it created")
    check(path.name == "sg03.sav", "the save keeps the host's name when it is free (a low slot the game lists)")
    path, _ = relay.fetch_save(fresh)
    check(path.name == "sg03.sav" and (fresh / "sg03.sav.bak").exists(),
          "the next join overwrites the save it fetched before, keeping a .bak")
    own = remote_dir / "own"
    own.mkdir()
    (own / "sg03.sav").write_bytes(b"the friend's own sg03")
    (own / "sg00.sav").write_bytes(b"the friend's own sg00")
    path, _ = relay.fetch_save(own)
    check(path.name == "sg01.sav" and (own / "sg03.sav").read_bytes() == b"the friend's own sg03",
          "the friend's own saves are never touched: the lowest free slot is used")
    cb.serve_http(("127.0.0.6", 18090), relay.forward, log, "relay")
    time.sleep(0.1)
    r = raw_get("127.0.0.6", 18090, "/cli?seq=1&x=5000&y=5000&busy=0&hello=1&me=41,3&name=Olga").split("|")
    check(r[0] == "7777", f"a friend's game is answered through the relay: {r[:3]}")
    r = get("http://127.0.0.3:18090/srv?seq=2&n=0&d=").split("|")
    check(r[2:5] == ["0", "2", "2"], f"server: running, two joins, two players' parties: {r[:5]}")
    positions_at_server = sorted((int(r[6 + 3 * i]) - OFF, int(r[7 + 3 * i]) - OFF) for i in range(2))
    check(positions_at_server == [(100, -400), (5000, 5000)], "both players' positions reach the server")
    names = set()
    for _ in range(8):
        r = get("http://127.0.0.3:18090/srv?seq=3&n=0&d=")
        if "Ivan" in r or "Olga" in r:
            names.add(r.rsplit("|", 1)[1])
    check(names == {"Ivan Petrov", "Olga"}, f"both names reach the server (a raw space kept): {names}")
    relay.sock.close()
    time.sleep(0.3)
    check(all(not p.cid.startswith("net") for p in w.players.values()), "a dropped relay frees its player")
    lost = cb.Relay(net, "secret", log)
    check(lost.forward("/cli?seq=1") == "0|0", "a relay without the host answers without a marker")


if __name__ == "__main__":
    test_positions()
    test_players_and_puppets()
    test_pause()
    test_shared_pause()
    test_troops_results_tombstones()
    test_clock()
    test_hub_and_relay()
    print("ALL OK")
