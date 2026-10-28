"""Tests for coop_bridge.py: the World logic, then real sockets (games' HTTP, hub and relay).

    python -I tools/test_coop_bridge.py
"""
import socket
import sys
import tempfile
import threading
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
    check(joins == 2 and sorted(puppets) == [(0, 100, 200, 0), (1, 300, 400, 0)], "two players: two puppets, two joins")
    check(payload == [3, 0] and name == "Anna", "the server learns the first player's name")
    check(w.server_report([], None, 1.2)[3:] == ([3, 1], "Boris Bek"), "then the second's")
    check(w.server_report([], None, 1.3)[3] == [0], "then nothing")
    others = [r for r in (req(w, "a", 100, 200, now=1.4) for _ in range(8)) if r[0][0] == 4]
    check(others and others[0] == ([4, 1, 300 + OFF, 400 + OFF, 0, 0], "Boris Bek"),
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
    check(w.server_report([], (600, [(31, 5)]), 2.1)[3] == [1, 600, 0, 1, 31, 3, 0], "the server gets the result")
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
    positions_at_server = sorted((int(r[6 + 4 * i]) - OFF, int(r[7 + 4 * i]) - OFF) for i in range(2))
    check(positions_at_server == [(100, -400), (5000, 5000)], "both players' positions reach the server")
    names = set()
    for _ in range(8):
        r = get("http://127.0.0.3:18090/srv?seq=3&n=0&d=")
        if "Ivan" in r or "Olga" in r:
            names.add(r.rsplit("|", 1)[1])
    check(names == {"Ivan Petrov", "Olga"}, f"both names reach the server (a raw space kept): {names}")
    cb.RECONNECT_GRACE_S = 0.6
    friend = next(p for p in w.players.values() if p.cid.startswith("net"))
    relay.sock.close()
    time.sleep(0.2)
    relay.connect()  # the link broke and came back: the same player, slot and name
    time.sleep(0.6)
    again = next((p for p in w.players.values() if p.cid.startswith("net")), None)
    check(again is friend and again.name == "Olga", "a relay that reconnects keeps its player")
    relay.sock.close()
    time.sleep(1.0)
    check(all(not p.cid.startswith("net") for p in w.players.values()), "a dropped relay frees its player")
    lost = cb.Relay(net, "secret", log)
    check(lost.forward("/cli?seq=1") == "0|0", "a relay without the host answers without a marker")
    # a hub that went quiet without closing the link (a VPN route gone): the relay drops it itself
    mute = socket.socket()
    mute.bind(("127.0.0.6", 0))
    mute.listen(1)

    def welcome_then_silence():
        conn, _ = mute.accept()
        conn.recv(4096)
        conn.sendall(b'{"t": "welcome", "cid": "x"}\n')
        time.sleep(3)
        conn.close()
    threading.Thread(target=welcome_then_silence, daemon=True).start()
    quiet = cb.Relay(mute.getsockname(), "secret", log, timeout=0.2)
    quiet.connect()
    quiet.forward("/cli?seq=1")
    check(quiet.connected.is_set(), "one late reply is not yet a dead link")
    quiet.forward("/cli?seq=2")
    check(not quiet.connected.is_set(), "two in a row: the relay drops the link to make a new one")


def mp(op, bid=0, sid=-1, slot=-1, troops=None, hero=None, center=-1):
    return {"op": op, "bid": bid, "sid": sid, "slot": slot, "troops": troops or [], "hero": hero, "center": center}


HERO = list(range(100, 100 + cb.HERO_NUMBERS))


def test_joint_battle():
    w = cb.World()
    req(w, "a", now=0.0, me=[(31, 10), (32, 4)], name="Ivan")
    req(w, "b", x=300, now=0.0, me=[(33, 6)], name="Olga")
    req(w, "c", x=50000, now=0.0, me=[(34, 2)], name="Far")
    nums, _ = req(w, "a", now=1.0, busy=True, mp=mp(1, sid=600, troops=[(40, 20)]))
    check(nums == [7, 0, 3, 0], "no battle server: the battle cannot start")
    check(w.mp_request(0, 0, -1, {}, {0: "ivan", 1: "Olga "}, 1.0) == [0], "a battle server with nothing to do")
    nums, _ = req(w, "a", now=2.0, busy=True, mp=mp(1, sid=600, troops=[(40, 20)], hero=HERO))
    bid = w.battle.bid
    check(nums == [7, bid, 0, 0], "a battle is gathering")
    check(req(w, "b", x=300, now=2.1)[0] == [6, bid, 1, w.players["a"].slot, 600],
          "a player nearby is invited, told which world party it would fight")
    check("c" not in w.battle.invited, "a player far away is not")
    check(w.mp_request(0, 0, -1, {}, {0: "ivan", 1: "Olga "}, 2.2) == [0], "nothing goes to the server while gathering")
    req(w, "b", x=300, now=3.0, busy=True, mp=mp(3, bid))
    check(w.battle.sides == {"a": 0, "b": 0}, "the invited player joins the starter's side")
    nums = w.mp_request(0, 0, -1, {}, {0: "ivan", 1: "Olga "}, 3.1)
    check(nums == [2, bid, 0, 4, 0, 0, 31, 10, 0, 0, 32, 4, 0, 1, 33, 6, 1, -1, 40, 20],
          f"stacks go to the server, each commanded by its player (matched by name): {nums}")
    nums = w.mp_request(0, 0, -1, {}, {0: "ivan", 1: "Olga "}, 3.2)
    check(nums == [5, bid, 0] + HERO, f"then the starter's hero (Olga sent none): {nums[:4]}")
    nums = w.mp_request(0, 0, -1, {}, {0: "ivan", 1: "Olga "}, 3.2)
    check(nums == [1, bid, 4, 0, 0, 2, 0, 0, 1, 0], f"then the start (a field battle), with the players' sides: {nums}")
    check(req(w, "a", now=3.3, busy=True, mp=mp(2, bid))[0] == [7, bid, 1, 0], "the players learn it is being fought")
    check(req(w, "c", x=50000, now=3.3, busy=False, mp=mp(1, sid=601))[0] == [7, 0, 2, 0], "one battle at a time")
    w.mp_players = {0: "ivan", 1: "Olga "}
    check(w.mp_request(4, bid, 0, {0: 4, 1: 2, 3: 20}, {0: "ivan", 1: "Olga "}, 9.0,
                       [(0, 0, 7, 180), (0, 3, 2, 60), (5, 1, 1, 30)], {0: 40, 1: 0}) == [4, bid],
          "the outcome is acknowledged")
    check(w.battle is None, "the battle is over")
    xp = 20 * cb.XP_PER_ENEMY // 2
    check(req(w, "a", now=9.1)[0] == [8, bid, 1, xp, 2, 31, 2, 2, 32, 1, 1],
          "the starter gets the losses (half wounded) and half the experience (two players won)")
    check(req(w, "a", now=9.1)[0] == [9, bid, 2, 0, 7, 180, 3, 2, 60],
          "and how the hero fought, by weapon proficiency (another player's blows are not the starter's)")
    check(req(w, "a", now=9.1)[0] == [10, bid, 40, -1], "and the hero's health; the winner is not captured")
    check(req(w, "b", x=300, now=9.1)[0] == [7, bid, 1, 0] and req(w, "b", x=300, now=9.1)[0] == [8, bid, 1, xp, 0],
          "a player who lost nobody still hears the outcome, after the news it was fought")
    check(req(w, "b", x=300, now=9.1)[0] == [10, bid, 0, -1], "a hero who fell comes back with 0 health")
    check(w.results[-1] == (600, 1, [], []) and 600 in w.tombstones, "the defeated world party is destroyed")


def test_factions():
    w = cb.World()
    req(w, "a", now=0.0, name="Ivan", faction=5)
    req(w, "b", x=100, now=0.0, name="Olga", faction=7)
    puppets = sorted(w.server_report([], None, 0.1)[2])
    check([f for *_, f in puppets] == [5, 7], "the server learns whom each player serves")
    seen = [req(w, "b", x=100, now=0.2 + i * 0.01)[0] for i in range(8)]
    shown = [r for r in seen if r[0] == 4]
    check(shown and shown[0][5] == 5, f"the other players see it: {shown[:1]}")
    req(w, "a", now=0.5, name="Ivan")
    check(w.players["a"].faction == 5, "a request without fac keeps the kingdom known")
    req(w, "a", now=0.6, name="Ivan", faction=0)
    check(w.players["a"].faction == 0, "and leaving a kingdom is heard")


def test_joint_siege():
    w = cb.World()
    req(w, "a", now=0.0, me=[(31, 20)], name="Ivan", faction=5)
    req(w, "h", x=100, now=0.0, me=[(33, 5)], name="Host", on_server=True)
    w.server_report([], (40, [(70, 30)]), 0.0, center=(40, 6, 333))
    w.mp_request(0, 0, -1, {}, {0: "ivan"}, 0.0)
    req(w, "a", now=1.0, busy=True, mp=mp(1, center=40, troops=[(70, 99)]))
    b = w.battle
    check(b.center == 40 and b.sides == {"a": 1}, "a siege: the starter storms the walls")
    check(req(w, "h", x=100, now=1.1, on_server=True)[0] == [6, b.bid, 1, w.players["a"].slot, 40],
          "a player nearby is called to the siege of that center")
    req(w, "h", x=100, now=1.2, on_server=True, mp=mp(3, b.bid))
    check(b.sides == {"a": 1, "h": 1}, "and joins the stormers")
    nums = w.mp_request(0, 0, -1, {}, {0: "ivan"}, 1.3)
    check(nums[4:] == [1, 0, 31, 20, 1, -1, 33, 5, 0, -1, 70, 30],
          f"the garrison as the world server reported it holds the walls: {nums}")
    nums = w.mp_request(0, 0, -1, {}, {0: "ivan"}, 1.4)
    check(nums == [1, b.bid, 3, 1, 40, 1, 0, 1], f"the start says it is a siege of center 40: {nums}")
    w.mp_request(4, b.bid, 1, {2: 30}, {}, 9.0)
    check(w.captures == [(40, 5)], "the walls are taken: the center goes to the stormer's kingdom")
    check(w.server_report([], None, 9.1)[3] == [4, 40, 5], "the world server is told")
    replies = [req(w, "a", now=9.2)[0] for _ in range(6)]
    check(not any(r[0] == 10 and r[3] >= 0 for r in replies), "nobody is captured in a siege")
    # the host storms: its own game takes the center
    req(w, "h", x=100, now=10.0, on_server=True, busy=True, mp=mp(1, center=41))
    b = w.battle
    w.mp_request(0, 0, -1, {}, {}, 10.0 + cb.GATHER_S + 1)
    w.mp_request(0, 0, -1, {}, {}, 10.0 + cb.GATHER_S + 1)
    w.mp_request(4, b.bid, 1, {}, {}, 40.0)
    replies = [req(w, "h", x=100, now=40.1, on_server=True)[0] for _ in range(8)]
    check([13, b.bid, 41] in replies, f"the host takes the center in its own game: {replies}")
    # a failed storm: the garrison keeps what survived
    w.server_report([], (42, [(70, 10)]), 50.0)
    req(w, "a", now=50.0, busy=True, mp=mp(1, center=42))
    b = w.battle
    w.mp_request(0, 0, -1, {}, {}, 50.0 + cb.GATHER_S + 1)
    w.mp_request(0, 0, -1, {}, {}, 50.0 + cb.GATHER_S + 1)
    w.mp_request(4, b.bid, 0, {1: 4}, {}, 80.0)
    check(w.results[-1][:3] == (42, 0, [(70, 6)]), "the walls held: the garrison keeps what survived")


def test_joint_defence():
    w = cb.World()
    req(w, "a", now=0.0, me=[(31, 10)], name="Ivan", faction=5)
    w.server_report([(650, 9, 0, 0), (660, 9, 0, 0, 0, 0, 651), (670, 9, 0, 0)], (40, [(80, 12)]), 0.0)
    w.server_report([], (650, [(90, 40)]), 0.0)
    w.server_report([], (660, [(91, 20)]), 0.0)
    w.mp_request(0, 0, -1, {}, {0: "ivan"}, 0.0)
    req(w, "a", now=1.0, busy=True, mp={**mp(1, sid=650, center=40), "defend": True})
    b = w.battle
    check(b.defence and b.sides == {"a": 0} and b.enemy_sid == 650, "a defence: the player holds the walls")
    nums = w.mp_request(0, 0, -1, {}, {0: "ivan"}, 1.1)
    check(nums[4:] == [0, 0, 31, 10, 0, -1, 80, 12, 1, -1, 90, 40, 1, -1, 91, 20],
          f"the player and the garrison on the walls, the besieger and its army storming them: {nums}")
    check(w.mp_request(0, 0, -1, {}, {0: "ivan"}, 1.2)[3:5] == [1, 40], "fought as a siege of center 40")
    w.mp_request(4, b.bid, 0, {1: 2, 2: 40, 3: 5}, {}, 9.0)
    check((650, 1, [], []) in w.results and (660, 0, [(91, 15)], []) in w.results,
          f"the storm is broken: the besiegers keep their survivors: {w.results}")
    check(w.results[-1] == (40, 0, [(80, 10)], []), "and the garrison its own")
    # the walls fall: the besiegers' kingdom takes the center, the defenders are captured
    w.mp_request(0, 0, -1, {}, {0: "ivan"}, 19.9)
    req(w, "a", now=20.0, busy=True, mp={**mp(1, sid=660, center=40), "defend": True})
    b = w.battle
    w.mp_request(0, 0, -1, {}, {0: "ivan"}, 20.1)
    w.mp_request(0, 0, -1, {}, {0: "ivan"}, 20.2)
    w.mp_request(4, b.bid, 1, {}, {0: "ivan"}, 30.0)
    check(w.captures == [(40, -1)], "the walls fell: the center goes to the besiegers")
    replies = [req(w, "a", now=30.1)[0] for _ in range(6)]
    check(any(r[0] == 10 and r[3] == 660 for r in replies), f"the defender is captured by the besieger: {replies}")


def test_profiles():
    path = Path(tempfile.mkdtemp()) / "profiles.json"
    w = cb.World(path)
    w.set_mp_name("a", "Ivan")
    first = req(w, "a", now=0.0, hello=True, name="Ivan")[0]
    nums = req(w, "a", now=0.0)[0]
    check(first[0] == 5 and nums == [14, 0, 0, 0], f"a new player hears the world, then: no hero kept yet: {nums}")
    hero = list(range(1, 301))
    for off in range(0, 300, 50):
        req(w, "a", now=1.0, profile=[7, off, 300] + hero[off:off + 50])
    check(w.profiles.get("ivan") == hero, "the hero arrives in parts and is kept under the player's name")
    w2 = cb.World(path)
    check(w2.profiles.get("ivan") == hero, "and survives the bridge (profiles.json)")
    w2.set_mp_name("b", "IVAN")
    req(w2, "b", now=0.0, hello=True, name="IVAN")
    replies = [req(w2, "b", now=0.1)[0] for _ in range(3)]
    check(replies[0] == [14, 0, 300, 120] + hero[:120] and replies[2] == [14, 240, 300, 60] + hero[240:],
          "joining again, the player's game gets its hero back")
    req(w2, "c", now=0.0, hello=True, name="Olga")
    req(w2, "c", now=0.1, profile=[1, 0, 100] + hero[:50])
    check("olga" not in w2.profiles, "half a hero is not kept")
    nums, _ = req(w2, "b", now=0.2, profile_ask=True)
    check(nums == [14, 0, 300, 120] + hero[:120], f"the answer got lost: asked again, the hero comes again: {nums[:4]}")
    req(w2, "h", now=0.0, hello=True, name="Host", on_server=True)
    check(not w2.players["h"].profile_out, "the host's hero lives in the world itself")


def test_names_and_saves():
    # the game's UTF-8 arrives read as cp1251 and encoded again; the bridge gets the real text back
    raw = "Игрок".encode("utf-8")
    sent = "".join(bytes([b]).decode("cp1251") if b != 0x98 else "" for b in raw).encode("utf-8")
    check(cb.game_text_in(sent.decode("latin-1")) == "Игрок", "a Russian name from the game is read right")
    check(cb.game_text_in("Ivan Petrov") == "Ivan Petrov", "a Latin name stays as it is")
    check(cb.reply_text([1], "Шамфир").split("|")[1].encode("latin-1").decode("utf-8") == "Шамфир",
          "a name goes to the game as UTF-8")
    w = cb.World()
    w.set_mp_name("a", "Шамфир")
    replies = [req(w, "a", now=0.0, hello=True, name="Игрок")]
    replies += [req(w, "a", now=0.1) for _ in range(3)]
    check(([22], "Шамфир") in replies, f"the hero gets the name its player gave join.bat: {replies}")
    replies = [req(w, "a", now=0.2, name="Шамфир")[0] for _ in range(cb.RENAME_EVERY + 5)]
    check([22] not in replies, "once the game reports that name, no more renaming")
    w.host_saved()
    replies = [req(w, "a", now=0.3)[0] for _ in range(3)]
    check(replies.count([23]) == 1, f"the host saved: the player's game is told once: {replies}")
    req(w, "h", now=0.3, hello=True, name="Host", on_server=True)
    w.host_saved()
    check([23] not in [req(w, "h", now=0.4, on_server=True)[0] for _ in range(3)], "the host is not told of its own save")

    # each save the host makes reaches the relays
    host_saves = Path(tempfile.mkdtemp())
    (host_saves / "sg00.sav").write_bytes(b"day 1")
    cb.SAVE_POLL_S = 0.1
    log = lambda m: None
    cb.serve_relays(("127.0.0.7", 18093), w, "secret", str(host_saves), log)
    friend = Path(tempfile.mkdtemp())
    relay = cb.Relay(("127.0.0.7", 18093), "secret", log)
    relay.connect()
    relay.save_dir = str(friend)
    path, _ = relay.fetch_save(str(friend))
    time.sleep(0.3)
    (host_saves / "sg00.sav").write_bytes(b"day 2, saved again")
    for _ in range(40):
        time.sleep(0.1)
        if path.read_bytes() == b"day 2, saved again":
            break
    check(path.read_bytes() == b"day 2, saved again", "a new save of the host replaces the friend's copy")


def test_lost_answers():
    w = cb.World()
    w.mp_last = 0.0
    req(w, "a", now=0.0, me=[(31, 10)], name="Ivan")
    nums, _ = req(w, "a", now=0.1, mp=mp(1, sid=700, troops=[(5, 9)]))
    bid = nums[1]
    check(nums[0] == 7 and bid > 0, f"a battle begins: {nums}")
    # that answer got lost on the way: the waiting window asks again without a number
    nums, _ = req(w, "a", now=0.2, mp=mp(1, sid=700, troops=[(5, 9)]))
    check(nums[:2] == [7, bid] and nums[2] < 2, f"a start sent again gets its own battle back, not a cancel: {nums}")
    nums, _ = req(w, "a", now=0.3, mp=mp(2, bid=0))
    check(nums[:2] == [7, bid] and nums[2] < 2, f"waiting without the number: told the battle's number: {nums}")
    check(cb.carries_news("7777|7|1|0|0") and cb.carries_news("7777|14|0|0|0"), "battle and hero replies carry news")
    check(not cb.carries_news("7777|2|0") and not cb.carries_news("0|0"), "positions and empty replies do not")


def test_notices_and_asking_again():
    w = cb.World()
    w.mp_last = 0.0
    req(w, "a", now=0.0, me=[(31, 10)], name="Ivan")
    req(w, "b", x=50, now=0.0, me=[(33, 4)], name="Olga")
    w.set_mp_name("b", "Olga")
    w.mp_request(0, 0, -1, {}, {0: "Ivan", 3: "Olga"}, 0.1)
    req(w, "a", now=0.2, mp=mp(1, sid=700, troops=[(5, 9)]))
    r = cb.handle_request(w, "mp", "/mp?seq=1&st=0&bid=0&pl=0~Ivan;3~Olga;", 0.3).split("|")
    check(r[1:3] == ["3", "3"] and "CoopWorld" in r[3].encode("latin-1").decode("utf-8"),
          f"an invited player on the battle server is told to answer in the campaign window: {r[:3]}")
    r = cb.handle_request(w, "mp", "/mp?seq=2&st=0&bid=0&pl=0~Ivan;3~Olga;", 0.4).split("|")
    check(r[1] != "3", "once")
    # asking again to join a party one rides in already: yes at once, no new question to the leader
    w2 = cb.World()
    req(w2, "a", now=0.0, name="Ivan")
    req(w2, "b", x=50, now=0.0, name="Olga")
    sa, sb = w2.players["a"].slot, w2.players["b"].slot
    req(w2, "b", now=1.0, together={"join": sa})
    req(w2, "a", now=1.1)
    req(w2, "a", now=1.2, together={"joinans": (sb, 1)})
    w2.players["b"].mp_out.clear()
    w2.players["a"].mp_out.clear()
    nums, _ = req(w2, "b", now=2.0, together={"join": sa})
    check(nums == [18, sa, 1], f"a follower asking again hears yes at once: {nums}")
    check(not any(m[0] == 17 for m in w2.players["a"].mp_out), "and the leader is not asked again")


def test_joining_and_giving():
    w = cb.World()
    req(w, "a", now=0.0, me=[(31, 10)], name="Ivan")
    req(w, "b", x=50000, now=0.0, me=[(33, 4)], name="Olga")
    slot_a, slot_b = w.players["a"].slot, w.players["b"].slot
    req(w, "b", x=50000, now=1.0, together={"join": slot_a})
    check(req(w, "a", now=1.1)[0] == [17, slot_b], "the leader hears who asks to join")
    told_leader = req(w, "a", now=1.2, together={"joinans": (slot_b, 1)})[0]
    check(w.players["b"].leader == "a", "accepted: that player follows the leader")
    check(req(w, "b", x=50000, now=1.3)[0] == [18, slot_a, 1] and told_leader == [19, slot_b, 1],
          "both are told")
    w.mp_request(0, 0, -1, {}, {}, 1.4)
    req(w, "a", now=2.0, busy=True, mp=mp(1, sid=600, troops=[(40, 5)]))
    b = w.battle
    check(b.sides.get("b") == 0 and "b" in b.invited, "the follower is called into the leader's battle, far away or not")
    check([6, b.bid, 3, slot_a, 600] in [req(w, "b", x=50000, now=2.1)[0] for _ in range(3)],
          "as an invitation that cannot be declined (type 3)")
    w.battle = None
    req(w, "b", x=50000, now=3.0, together={"leave": True})
    check(w.players["b"].leader is None, "the follower leaves the party")
    check([19, slot_b, 0] in [req(w, "a", now=3.1)[0] for _ in range(4)], "the leader is told")
    # troops: offered, declined, back
    req(w, "a", now=4.0, together={"give": (slot_b, [(31, 3)])})
    nums = req(w, "b", x=50000, now=4.1)[0]
    check(nums[0] == 15 and nums[2:] == [slot_a, 1, 31, 3], f"the receiver gets the offer: {nums}")
    req(w, "b", x=50000, now=4.2, together={"giveans": (nums[1], 0)})
    check([16, nums[1], 0, 1, 31, 3] in [req(w, "a", now=4.3)[0] for _ in range(4)], "declined troops go back")
    req(w, "a", now=5.0, together={"give": (slot_b, [(31, 2)])})
    oid = req(w, "b", x=50000, now=5.1)[0][1]
    req(w, "b", x=50000, now=5.2, together={"giveans": (oid, 1)})
    check([16, oid, 1, 1, 31, 2] in [req(w, "a", now=5.3)[0] for _ in range(4)], "accepted: the giver is told")
    # an offer to a player who leaves goes back
    req(w, "a", now=6.0, together={"give": (slot_b, [(31, 1)])})
    w.drop_player("b")
    check(any(r[0] == 16 and r[2] == 0 for r in (req(w, "a", now=6.1)[0] for _ in range(4))),
          "troops offered to a player who left come back")
    check(cb.parse_together({"give": "1,,31,2,32,1", "joinans": "2,1"}) ==
          {"give": (1, [(31, 2), (32, 1)]), "joinans": (2, 1)}, "the request's parts are read")


def test_companions_spoils_terrain():
    w = cb.World()
    req(w, "a", now=0.0, me=[(31, 10)], name="Ivan")
    w.mp_request(0, 0, -1, {}, {0: "ivan"}, 0.0)
    comp = list(range(200, 200 + cb.HERO_NUMBERS))
    req(w, "a", now=1.0, busy=True, mp={**mp(1, sid=600, troops=[(40, 8)], hero=HERO), "compn": 1, "terrain": 11})
    check(w.mp_request(0, 0, -1, {}, {0: "ivan"}, 1.1) == [0], "the battle waits for the companion")
    req(w, "a", now=1.2, busy=True, mp={**mp(2, w.battle.bid), "comp": (7, comp)})
    nums = w.mp_request(0, 0, -1, {}, {0: "ivan"}, 1.3)
    check(nums[4:] == [0, 0, 31, 10, 0, 0, 7, 1, 1, -1, 40, 8], f"the companion is a stack of one, commanded by the player: {nums}")
    bid = nums[1]
    check(w.mp_request(0, 0, -1, {}, {0: "ivan"}, 1.4)[:3] == [5, bid, 0], "then the hero")
    check(w.mp_request(0, 0, -1, {}, {0: "ivan"}, 1.5) == [6, bid, 7] + comp, "then the companion's gear and stats")
    check(w.mp_request(0, 0, -1, {}, {0: "ivan"}, 1.6)[3:5] == [0, 11], "a field battle on a forest map (terrain 11)")
    w.mp_request(4, bid, 0, {1: 1, 2: 6}, {}, 9.0)
    replies = [req(w, "a", now=9.1)[0] for _ in range(8)]
    check([8, bid, 1, 6 * cb.XP_PER_ENEMY, 1, 7, 0, 1] in replies, f"a fallen companion is wounded, never killed: {replies}")
    check([21, bid, 1, 40, 6] in replies, "the winner gets the fallen enemies as spoils")


def test_centers_reach_players():
    w = cb.World()
    req(w, "a", now=0.0, name="Ivan")
    req(w, "h", now=0.0, name="Host", on_server=True)
    w.server_report([], None, 0.0, center=cb.parse_center("40,5,300,0"))
    w.server_report([], None, 0.1, center=cb.parse_center("41,6,301,0"))
    seen = [req(w, "a", now=0.2)[0] for _ in range(6)]
    check([12, 2, 40, 5, 300, 0, 41, 6, 301, 0] in seen, f"players learn whom centers belong to: {seen}")
    w.server_report([], None, 1.0, center=cb.parse_center("40,7,302,0"))
    seen = [req(w, "a", now=1.1)[0] for _ in range(6)]
    check([12, 1, 40, 7, 302, 0] in seen, "and when one changes hands")
    w.server_report([], None, 2.0, center=cb.parse_center("40,7,302,651"))
    seen = [req(w, "a", now=2.1)[0] for _ in range(6)]
    check([12, 1, 40, 7, 302, 651] in seen, "and when one is besieged (by party 650)")
    check(not any(r[0] == 12 for r in (req(w, "h", now=1.2, on_server=True)[0] for _ in range(6))),
          "the host is not told: its game is the world")


def test_multiplayer_names():
    w = cb.World()
    req(w, "a", now=0.0, me=[(31, 2)], name="Hero")
    req(w, "b", x=100, now=0.0, me=[(33, 2)], name="Hero")  # loaded the host's save: the same hero's name
    w.set_mp_name("a", "  Ivan ")
    w.set_mp_name("b", "Olga")
    w.mp_request(0, 0, -1, {}, {0: "olga", 3: "IVAN", 5: "Hero"}, 0.0)
    check(w._mp_player_number("a") == 3 and w._mp_player_number("b") == 0,
          "players are found on the battle server by the names given to their launchers")
    check([(s, wanted, no) for s, _, wanted, no in w.mp_recognition(0.1)] ==
          [(w.players["a"].slot, "Ivan", 3), (w.players["b"].slot, "Olga", 0)], "and the bridge can tell who it found")
    w.set_mp_name("b", "")
    check(w._mp_player_number("b") == 5, "without a launcher name, by the hero's name")
    nums, name = req(w, "a", now=1.0, busy=True, mp=mp(2, 7))
    check(nums[0] == 7 and name == '"Ivan"', f"the waiting window learns the name expected: {name}")
    req(w, "c", now=1.0, name="1")
    check(req(w, "c", now=1.1, busy=True, mp=mp(2, 7))[1] == '"1"', "quoted, so a name like 1 stays a string")
    w.drop_player("a")
    check("a" not in w.mp_names, "a player who left takes the name along")


def test_joint_battle_scaled_and_lost():
    w = cb.World()
    req(w, "a", now=0.0, me=[(31, 300)], name="Ivan")
    w.mp_request(0, 0, -1, {}, {}, 0.0)
    req(w, "a", now=1.0, busy=True, mp=mp(1, sid=700, troops=[(40, 300)]))
    nums = w.mp_request(0, 0, -1, {}, {}, 1.1)
    check(nums[2:] == [0, 2, 0, -1, 31, 75, 1, -1, 40, 75], f"big armies are scaled down: {nums}")
    bid = nums[1]
    w.mp_request(0, 0, -1, {}, {}, 1.2)
    w.mp_request(4, bid, 1, {0: 75, 1: 15}, {}, 5.0)
    check(req(w, "a", now=5.1)[0][0] == 7 and req(w, "a", now=5.1)[0] == [8, bid, 0, 60 * cb.XP_PER_ENEMY // 3, 1, 31, 150, 150],
          "and their losses scaled up; the battle is lost (a third of the experience)")
    check(req(w, "a", now=5.1)[0] == [10, bid, -1, 700], "the defeated player is taken prisoner by the world party")
    check(w.results[-1] == (700, 0, [(40, 240)], [(31, 150)]),
          "the world party keeps what survived and takes the player's troops (wounded too) prisoner")
    check(w.server_report([], None, 5.2)[3] == [1, 700, 0, 1, 40, 240, 1, 31, 150], "the server gets the prisoners")


def test_joint_battle_decline_cancel_pvp():
    w = cb.World()
    req(w, "a", now=0.0, me=[(31, 5)], name="Ivan")
    req(w, "b", x=100, now=0.0, me=[(33, 6)], name="Olga")
    w.mp_request(0, 0, -1, {}, {}, 0.0)
    req(w, "a", now=1.0, busy=True, mp=mp(1, sid=600))
    bid = w.battle.bid
    req(w, "b", x=100, now=1.1)
    req(w, "b", x=100, now=1.2, mp=mp(4, bid))
    check(w.battle.sides == {"a": 0} and not w.battle.invited, "a declined invitation")
    req(w, "a", now=1.3, mp=mp(4, bid))
    check(w.battle is None, "the starter cancels the battle")
    slot_b = w.players["b"].slot
    req(w, "a", now=2.0, busy=True, mp=mp(1, slot=slot_b))
    bid = w.battle.bid
    check(req(w, "b", x=100, now=2.1)[0] == [6, bid, 2, w.players["a"].slot, -1], "the attacked player is called in")
    req(w, "b", x=100, now=2.2, mp=mp(4, bid))
    check(w.battle.sides == {"a": 0, "b": 1}, "an attacked player cannot decline")
    nums = w.mp_request(0, 0, -1, {}, {}, 2.0 + cb.GATHER_S + 1)
    check(nums[4:] == [0, -1, 31, 5, 1, -1, 33, 6], f"without an answer the battle starts anyway: {nums}")
    w.mp_request(0, 0, -1, {}, {}, 30.0)
    w.mp_request(0, 0, -1, {}, {}, 30.0 + cb.MP_LOST_S + 1)
    check(w.battle is None, "a battle server that forgot the battle frees it")
    req(w, "a", now=40.0, busy=True, mp=mp(1, slot=slot_b))
    bid = w.battle.bid
    w.mp_request(0, 0, -1, {}, {}, 40.0 + cb.GATHER_S + 1)
    w.mp_request(0, 0, -1, {}, {}, 40.0 + cb.GATHER_S + 1)
    w.mp_request(4, bid, 0, {1: 2}, {}, 70.0)
    replies = [req(w, "a", now=70.1)[0] for _ in range(8)]
    check([11, bid, 1, 33, 5] in replies, f"the winner of a battle between players takes the loser's troops: {replies}")
    replies = [req(w, "b", x=100, now=70.1)[0] for _ in range(8)]
    check(not any(r[0] == 10 and r[3] >= 0 for r in replies), "and the loser is not captured by a player")


def test_host_plays_on_server():
    w = cb.World()
    req(w, "local", x=100, y=200, now=0.0, me=[(31, 3)], name="Host", on_server=True)
    req(w, "b", x=5000, now=0.0, name="Olga")
    puppets = w.server_report([], None, 0.1)[2]
    check([s for s, *_ in puppets] == [w.players["b"].slot], "the host's own party gets no puppet on the server")
    seen = [req(w, "b", x=5000, now=0.2 + i * 0.01)[0] for i in range(8)]
    check(any(r[0] == 4 and r[1] == w.players["local"].slot for r in seen), "the other players see the host")
    check(w.pause_cause(2.0, but=w.players["b"]) == (w.players["local"].slot, 2),
          "the host's game falling silent (a menu, a battle) pauses the others")
    req(w, "b", x=5000, now=2.0)
    check(w.server_report([], None, 2.0)[0] is False, "but never the server itself: it is the host's own game")


if __name__ == "__main__":
    test_positions()
    test_players_and_puppets()
    test_pause()
    test_shared_pause()
    test_troops_results_tombstones()
    test_clock()
    test_host_plays_on_server()
    test_joint_battle()
    test_multiplayer_names()
    test_factions()
    test_joint_siege()
    test_companions_spoils_terrain()
    test_joining_and_giving()
    test_profiles()
    test_joint_defence()
    test_centers_reach_players()
    test_joint_battle_scaled_and_lost()
    test_joint_battle_decline_cancel_pvp()
    test_hub_and_relay()
    test_names_and_saves()
    test_lost_answers()
    test_notices_and_asking_again()
    print("ALL OK")
