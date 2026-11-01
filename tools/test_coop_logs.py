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

cl.windows_faults = lambda: []  # a test run has nothing to say about this PC

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


def report(bridge, trace, *args, trail=""):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        write(folder, bridge, trace)
        if trail:
            (folder / "trail.log").write_text(trail, encoding="utf-8")
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


def test_late_heroes():
    bridge = BRIDGE_START + """\
12:01:00 joint battle: 1:D starts a joint battle (battle 0, enemy party 473, player slot -1, center -1)
12:01:00 joint battle 1: gathering; invited: 0:O
12:01:45 joint battle 1: going to the battle server (1 stacks, sides 1:D=team 0)
12:01:47 joint battle 1: started on the battle server
12:02:10 joint battle: 0:O accepts the invitation (battle 1, enemy party 0, player slot 0, center 0)
12:02:10 joint battle 1: 0:O accepted late - joins the battle as its hero; its troops stay out of it
12:02:30 joint battle 1: 0:O is on the battle server now - its hero joins the battle (team 0)
""" + stats("12:02:50")
    text = report(bridge, "")
    check("O: согласие после сбора - в бою героем, без своих отрядов" in text, "a late acceptance is in the report")
    check("O: герой отправлен на сервер боя уже во время боя" in text, "and the hero sent while the battle ran")
    check(not any("не ответил на приглашение" in line for line in marked(text, "!!")),
          "a player who accepted late answered")


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


def test_quiet_at_the_end():
    lines = [stats("12:01:00"), "12:01:07 player 0:O quiet since 12:01:01: last request h=48 free=1 busy=0 x=1 y=2; "
             "last replies 2:500/3@120", stats("12:01:05", friend=" silent 4s"), stats("12:01:10", friend=" silent 9s"),
             stats("12:01:15", friend=" silent 14s")]
    text = report(BRIDGE_START + "\n".join(lines) + "\n", "")
    quiet = [line for line in marked(text, "? ") if "молчал 14 с" in line]
    check(quiet and "игровой день 3, 00:00" in quiet[0] and "2:500/3@120" in quiet[0],
          "a short silence at the end of the log, with the game hour and the last replies")


def test_clocks_and_lords():
    text = report(BRIDGE_START + """12:01:00 player 1:O: its clock is 3 h ahead of the world's - it does not rest until the world catches up (moving stays free)
12:01:08 player 1:O: its clock is the world's again (+1 h) after 8 s
12:02:00 player 1:O: its clock is 4 h behind the world's - it rests faster
12:06:00 player 1:O: its clock is the world's again (-1 h) after 240 s
12:07:00 player 1:O: the lord it serves (party 700) fights party 800
""" + stats("12:07:05") + "\n", "")
    check(any("время на 3 ч впереди мира" in line for line in marked(text, "  ")), "a clock ahead of the world's")
    check(any("через 8 с" in line for line in marked(text, "  ")), "caught up soon: just noted")
    check(any("через 4 мин 0 с" in line for line in marked(text, "? ")), "a long way to catch up: worth a look")
    check(any("отряд 700), бьётся с отрядом 800" in line for line in marked(text, "  ")), "the lord's battle")


def test_together():
    lines = [
        "together 1:D: prisoners taken=3 chance=20 no_room=1",
        "together 1:D: troops_xp xp=120 won=1",
        "together 1:D: arena kills=4 prize=30 won=0",
        "together 1:D: tournament rounds=4 gold=250 stake_lost=0",
        "together 0:O: tournament rounds=1 gold=0 stake_lost=50",
        "together 1:D: training ratio=75 earned=900",
        "together 1:D: tree troop=120",
        "together 0:O: follow target=1:D the Great",
        "together 0:O: follow_step distance=12",
        "together 0:O: follow_end why=1",
        "together 1:D: gold asked=100 moved=100 balance=600",
        "together 0:O: gold asked=-700 moved=-600 balance=0",
        "together 0:O: store_open items=3",
        "together 1:D: store_refused used_by=0:O",
        "together 0:O: store_saved items=2",
        "together 0:O: invite_off_map battle=2 type=1",
        "together 0:O: signal how=1 invite=1",
        "together 0:O: signal_bridge battle=2",
        "together 1:D: battle_lair battle=3 enemy=800 ally=None",
        "together 1:D: battle_end kind=lair battle=3 won=1",
        "together 1:D: lair won=1 quest=1",
        "together 1:D: village center=120 won=1 relation=3",
        "together 1:D: caravan won=0",
        "together 1:D: duel_call rival=0:O stake=500",
        "together 1:D: duel_off battle=4 why=no_answer",
        "together 0:O: duel result=1 stake=500 gold=500",
        "together 1:D: something_new a=1",
    ]
    text = report(BRIDGE_START + "".join(f"12:01:{k:02d} {line}\n" for k, line in enumerate(lines))
                  + stats("12:02:00") + "\n", "")
    for said in ("пленные после боя: взято 3, шанс 20%, без места осталось 1", "опыт отряду за бой: 120 (победа)",
                 "арена: побеждено 4, награда 30", "турнир выигран: раундов 4, получено 250",
                 "турнир проигран: раундов выиграно 1, ставка потеряна 50",
                 "тренировка: побеждено 75%", "древо войск: открыт юнит 120", "едет за игроком 1:D the Great",
                 "поход окончен: щёлкнул по карте сам",
                 "казна: положил 100, остаток 600", "казна: взял 600, остаток 0", "открыл склад: вещей 3",
                 "склад занят: его держит 0:O", "склад сохранён: вещей 2",
                 "приглашение (бой 2, бой рядом) дошло вне карты", "сигнал к бою: окно открылось поверх меню (бой рядом)",
                 "сигнал к бою 2 показан в окне моста", "начал бой: логово, бой 3, враг 800",
                 "бой 3 (логово) окончен: победа", "логово: победа, задание выполнено",
                 "деревня 120: победа, отношение +3", "защита каравана: поражение",
                 "вызвал на дуэль игрока 0:O, ставка 500", "дуэль 4 отменена: соперник не ответил",
                 "дуэль: победа, ставка 500, деньги +500", "something_new a=1"):
        check(said in text, f"the report says: {said}")
    check(any("не послушался приказа" in line for line in marked(text, "? ")), "a ride that had to jump is worth a look")


def test_menu_or_hang():
    menu = [stats(f"12:01:{s:02d}", friend=f" silent {s + 3}s alive") for s in range(0, 40, 5)]
    menu.append(stats("12:01:40"))
    text = report(BRIDGE_START + "\n".join(menu) + "\n", "")
    quiet = [line for line in text.splitlines() if "молчал" in line]
    check(quiet and "это меню, а не зависание" in quiet[0] and "!!" not in quiet[0],
          "a game silent for the world that goes on answering is in a menu")
    hang = [stats(f"12:01:{s:02d}", friend=f" silent {s + 3}s alive") for s in range(0, 20, 5)]
    hang += [stats(f"12:01:{s:02d}", friend=f" silent {s + 3}s") for s in range(20, 55, 5)]
    text = report(BRIDGE_START + "\n".join(hang) + "\n", "")
    check(any("потом перестала: зависание или закрытие" in line for line in marked(text, "!!")),
          "a game that stopped answering in the middle of a silence is a problem")


def test_trail():
    hang = [stats(f"12:01:{s:02d}", friend=f" silent {s + 3}s alive") for s in range(0, 20, 5)]
    hang += [stats(f"12:01:{s:02d}", friend=f" silent {s + 3}s") for s in range(20, 55, 5)]
    bridge = BRIDGE_START + "\n".join(hang) + "\n"
    trail = "".join(f"12:00:{s:02d} {FRIEND} {s} menu m{s}\n" for s in range(30, 56, 5))
    trail += f"12:00:56 {FRIEND} 56 lost 3\n12:00:56 {FRIEND} 59 option town: town_leave\n"
    trail += f"12:00:40 local 7 menu camp\n"
    text = report(bridge, "", trail=trail)
    quiet = next(line for line in text.splitlines() if "молчал" in line)
    check("Последние действия:" in quiet and "12:00:56 option town: town_leave" in quiet,
          f"a silence shows what the game did just before it: {quiet}")
    check("потеряно записей: 3" in quiet, "and says when some of it never arrived")
    check("menu m30" not in quiet, "only the last few")
    check("След действий (последнее внизу):" in text and "menu camp" in text, "each player's trail has a section")
    check("След действий" not in report(bridge, ""), "a plain build's session has none")
    check(cl.read_trail([Path("no such file")]) == [], "no trail.log, no trail")
    check(cl.KINDS[34] and cl.KINDS[35], "the army's replies have names")


def test_faults():
    crash = "2026-10-30 22:03:11|1000|mb_warband.exe|1.174.0.0|5a1|mb_warband.exe|1.174.0.0|5a1|c0000005|0003b094|1a|1dc"
    hang = "2026-10-30 22:05:00|1002|mb_warband.exe|1.174.0.0|15a4|1dc|0"
    other = "2026-10-30 22:06:00|1000|notepad.exe|1.0|5a1|ntdll.dll|1.0|5a1|c0000005|0003b094|1a|1dc"
    said = cl.parse_faults("\n".join([crash, hang, other, "garbage", ""]))
    check(len(said) == 2, f"the game's own, nothing else: {said}")
    check("код c0000005, смещение 0003b094" in said[0] and "2026-10-30 22:03:11" in said[0], "a crash: its code and offset")
    check("зависание" in said[1], "a window closed while it did not answer")
    check(cl.parse_faults("") == [], "nothing found, nothing said")


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
    test_late_heroes()
    test_builds_reconnect_sessions()
    test_parties()
    test_party_flow()
    test_short_holds()
    test_captor_gone()
    test_quiet_at_the_end()
    test_clocks_and_lords()
    test_together()
    test_menu_or_hang()
    test_trail()
    test_faults()
    print("ALL OK")
