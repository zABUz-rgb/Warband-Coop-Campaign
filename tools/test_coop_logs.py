"""Tests for coop_logs.py: made-up sessions of bridge.log and trace.log, and what the report says.

    python -I tools/test_coop_logs.py
"""
import contextlib
import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coop_logs as cl  # noqa: E402

FRIEND = "net-aaaa@10.0.0.2"


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok  ", msg)


def stats(t, friend="", host="", paused=False, parties=300):
    return (f"{t} parties {parties}, server 39.0/s, players 19.6/s [0:O{friend} mp:O, 1:D{host} mp:D], "
            f"{'PAUSED' if paused else 'running'}, results 0, srv 14.0 h/min, cli 14.0 h/min, cli_map 14.0 h/min, "
            "battle server on")


BRIDGE_START = f"""\
12:00:00 logs: C:\\x\\bridge.log and trace.log next to it (requests about battles, parties, joining)
12:00:00 net: listening for players on 0.0.0.0:7350
12:00:05 net: player {FRIEND} connected, multiplayer name 'O'
12:00:10 player 0:{FRIEND} runs CoopWorld build 111 - the same as the host
12:00:10 player 1:local runs CoopWorld build 111
"""

BATTLE = """\
12:01:00 joint battle: 1:D starts a joint battle (battle 0, enemy party 473, player slot -1, center -1)
12:01:00 joint battle 1: gathering; invited: 0:O
12:01:02 joint battle: 0:O accepts the invitation (battle 1, enemy party 0, player slot 0, center 0)
12:01:02 joint battle 1: going to the battle server (2 stacks, sides 1:D=team 0, 0:O=team 0)
12:01:05 joint battle 1: started on the battle server
"""


def trace_battle(friend_state):
    """The outcome at 12:03:00; the friend gets the spoils, then the result, in friend_state."""
    return f"""\
12:00:10 cli {FRIEND} /cli?seq=1&h=1&free=1&x=0&y=0&busy=0&fac=0&hello=1&ver=111&me=&name=O
         -> 7777|22|O
12:00:10 cli local /cli?seq=1&h=1&free=1&x=0&y=0&busy=0&srvp=1&fac=0&hello=1&ver=111&me=&name=D
         -> 7777|22|D
12:03:00 mp local /mp?seq=9&st=4&bid=1&w=0&r=1,8;&pl=0~D;4~O;
         -> 7778|4|1
12:03:01 cli local /cli?seq=5&h=2&free=0&x=0&y=0&busy=1&mp=2&bid=1&me=&name=D
         -> 7777|21|1|1|113|4
12:03:01 cli local /cli?seq=6&h=2&free=0&x=0&y=0&busy=1&mp=2&bid=1&me=&name=D
         -> 7777|8|1|1|120|0
12:03:01 cli {FRIEND} /cli?{friend_state}&name=O
         -> 7777|21|1|1|113|4
12:03:02 cli {FRIEND} /cli?{friend_state}&name=O
         -> 7777|8|1|1|120|0
"""


def write(folder, bridge, trace):
    (folder / "bridge.log").write_text(bridge, encoding="utf-8")
    (folder / "trace.log").write_text(trace, encoding="utf-8")


def report(bridge, trace, *args):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        write(folder, bridge, trace)
        with contextlib.redirect_stdout(io.StringIO()):
            cl.main([str(folder), "--out", str(folder / "report.txt"), *args])
        return (folder / "report.txt").read_text(encoding="utf-8-sig")


def marked(text, mark):
    return [line for line in text.splitlines() if line.startswith(f"  {mark} ")]


def test_unwrap():
    check(cl.unwrap([23 * 3600, 23 * 3600 + 59 * 60, 60, 120]) == [-3600, -60, 60, 120],
          "a log over midnight: the lines before it are a day earlier")
    check(cl.unwrap([100, 50, 200]) == [100, 50, 200], "a line a little out of order is not a midnight")


def test_good_battle():
    in_window = "seq=7&h=2&free=0&x=0&y=0&busy=1&mp=2&bid=1&me=,49,2"
    lines = [stats(f"12:0{m}:{s:02d}") for m in range(1, 5) for s in range(0, 60, 5)]
    text = report(BRIDGE_START + BATTLE + "\n".join(lines) + "\n", trace_battle(in_window))
    check("Бой 1:" in text and "итог: победила команда 0" in text, "the battle and its outcome are in the report")
    check("O: добыча (видов войск: 1) 12:03:01 (в окне совместного боя); "
          "результат боя (победа, опыт 120, потерь стеков 0) 12:03:02" in text,
          "each player's spoils and result, and where they were then")
    check(not marked(text, "!!") and not marked(text, "? "), "a battle that went well has no problems")


def test_hang_after_battle():
    on_map = "seq=7&h=2&free=1&x=0&y=0&busy=0&fac=0"
    lines = [stats(f"12:0{m}:{s:02d}") for m in (1, 2) for s in range(0, 60, 5)]
    lines += [stats(f"12:03:{s:02d}") for s in range(0, 10, 5)]
    lines += [stats(f"12:0{3 + (10 + k * 5) // 60}:{(10 + k * 5) % 60:02d}", friend=f" silent {3 + k * 5}s")
              for k in range(30)]
    bridge = (BRIDGE_START + BATTLE + "\n".join(lines) + "\n"
              + f"12:05:40 net: lost {FRIEND}; its player waits 30 s for it to come back\n")
    text = report(bridge, trace_battle(on_map))
    problems = marked(text, "!!")
    check(len(problems) == 1 and "молчал" in problems[0] and "после результата боя" in problems[0]
          and "связь потеряна в 12:05:40" in problems[0],
          "a game that went quiet after the battle and never came back is the problem")
    check("на карте" in problems[0] and "21 (добыча)" in problems[0], "with its state and its last replies")
    check(any("добыча пришла игроку O уже на карте" in line for line in marked(text, "? ")),
          "spoils that came when the player was back on the map are noted")


def test_invitation_unanswered():
    bridge = BRIDGE_START + """\
12:01:00 joint battle: 1:D starts a joint battle (battle 0, enemy party 473, player slot -1, center -1)
12:01:00 joint battle 1: gathering; invited: 0:O
12:01:45 joint battle 1: going to the battle server (1 stacks, sides 1:D=team 0)
12:01:47 joint battle 1: started on the battle server
""" + stats("12:01:50")
    text = report(bridge, "")
    check(any("игрок O не ответил на приглашение" in line for line in marked(text, "!!")),
          "an invited player who never answered")
    check(any("итога с сервера боя нет" in line for line in marked(text, "!!")),
          "a battle without an outcome from the battle server")


def test_builds_reconnect_sessions():
    bridge = BRIDGE_START.replace("12:00:", "11:00:") + stats("11:00:30") + "\n" + BRIDGE_START + f"""\
12:00:20 player 0:{FRIEND} runs CoopWorld build 222 - NOT the host's (111): install the same package on both PCs
12:01:00 net: lost {FRIEND}; its player waits 30 s for it to come back
12:02:00 net: player net-bbbb@10.0.0.2 connected, multiplayer name 'O'
""" + stats("12:02:05") + "\n"
    text = report(bridge, "")
    check(text.count("Сессия ") == 1 and "Сессия 12:00:00" in text, "the last session only, by default")
    check(any("сборка 222 не та, что у хоста" in line for line in marked(text, "!!")), "a different build")
    check(any("фантомами" in line for line in marked(text, "? ")),
          "a player back after a lost link may keep phantom parties")
    check(report(bridge, "", "--all").count("Сессия ") == 2, "--all: every session")


def test_party_flow():
    flow = ", parties: 3 new, 2 gone, 0 back"
    bridge = BRIDGE_START + stats("12:00:15") + flow + "\n" + stats("12:00:20") + ", parties: 0 new, 0 gone, 4 back\n"
    text = report(bridge, "")
    check("Отряды у моста: новых 3, пропало 2, из пропавших вернулось 4" in text, "the bridge's party counters")
    check(any("4 раз забыл живой отряд" in line for line in marked(text, "? ")),
          "parties the bridge forgot while they were alive")


def test_short_holds():
    holds = "".join(f"12:0{m}:00 world held by player 0 ({FRIEND}): in an encounter or battle\n"
                    f"12:0{m}:05 world runs again\n" for m in range(1, 5))
    text = report(BRIDGE_START + holds + stats("12:05:00") + "\n", "")
    check(any("4 коротких пауз" in line for line in marked(text, "? ")),
          "short holds 'in an encounter or battle' without a battle are counted")


def test_captor_gone():
    text = report(BRIDGE_START + "12:01:00 party 787 is gone, the captor of 0:O\n" + stats("12:01:05") + "\n", "")
    check(any("отряд 787, взявший в плен 0:O" in line for line in marked(text, "? ")), "a captor gone from the world")


def test_parties():
    bridge = BRIDGE_START + stats("12:00:15", parties=0) + "\n" + stats("12:00:20", parties=300) + "\n" \
        + stats("12:00:25", parties=250) + "\n"
    text = report(bridge, "")
    check("Отряды мира: 300 -> 250" in text, "the parties, from the first report of the world server")
    check(any("300 -> 250" in line for line in marked(text, "? ")), "a sudden drop of the world's parties")


if __name__ == "__main__":
    test_unwrap()
    test_good_battle()
    test_hang_after_battle()
    test_invitation_unanswered()
    test_builds_reconnect_sessions()
    test_parties()
    test_party_flow()
    test_short_holds()
    test_captor_gone()
    print("ALL OK")
