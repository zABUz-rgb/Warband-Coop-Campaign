"""Warband Coop Campaign session report: what happened in a session, read from the bridge's logs.

After playing, on the host's PC (the logs are in Documents\\Warband Coop Campaign):

    python tools/coop_logs.py [FOLDER] [--all] [--silence 30] [--out FILE]

bridge.log has the bridge's events and, every 5 s, a line on the parties and players (who is busy,
who has been silent how long); trace.log has the requests and replies about battles, joining and
results. The report goes through the last session (--all: every session in bridge.log):

  - players, their builds (a different build than the host's), connections lost and made again;
  - every joint battle: who started it, who was invited and answered, the sides, the outcome from
    the battle server, and when each player got the result and the spoils, in which state;
  - what the players did together, item by item: prisoners, troops' experience, arena, tournament,
    training, the troop tree, the ride after a friend, the camp, the treasury, the store, the call to
    battle, lairs, caravans, villages, duels;
  - silences: a player's game that stopped asking (a menu, a screen, a hang), with the state it was
    last seen in and the replies it got last, and whether it came back. A game in a menu goes on
    answering (the word alive in the stats line), one that hung does not;
  - the world's parties (sudden drops), how long the world stood still, the bridge's own errors;
  - from a debug build (python build.py --trail) trail.log: each player's last actions, the last ones
    before a silence, and the game's crashes and hangs in Windows' own log, with the code and the offset.

Lines marked !! are problems, ?  worth a look, the rest is what happened. The report is printed
and written to report.txt next to the logs (FOLDER defaults to Documents\\Warband Coop Campaign).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DAY = 86400
STATS_EVERY_S = 5
TRAIL_SHOWN = 15        # a player's last actions in the report
TRAIL_BEFORE = 6        # the last ones before a silence
FAULT_DAYS = 7          # how far back to read Windows' log
AFTER_BATTLE_S = 120    # a silence that begins this soon after a player got the result is the battle's
LONG_SILENCE_S = 120    # a menu this long: worth a look
PARTY_DROP = 0.05       # this share of the world's parties gone between two stats lines (and 15 at least)

KINDS = {1: "итог для мира", 2: "позиции", 3: "войска", 4: "игрок", 5: "пауза", 6: "приглашение",
         7: "состояние боя", 8: "результат боя", 9: "владение оружием", 10: "здоровье/плен",
         11: "пленные", 12: "владельцы центров", 13: "штурм", 14: "герой", 15: "предложены войска",
         16: "ответ на войска", 17: "просьба вступить", 18: "ответ на просьбу", 19: "вступил/ушёл",
         20: "отпущен", 21: "добыча", 22: "имя", 23: "сохранение хоста", 24: "стать клиентом",
         25: "бой лорда", 26: "итог события", 27: "вести об игроке", 28: "лагерь", 29: "казна", 30: "склад",
         31: "состояние склада", 32: "бой рядом", 33: "проверка связи", 34: "название войска",
         35: "снаряжение войска"}

SIGNAL_HOW = {0: "сообщение и звук", 1: "окно открылось поверх меню", 2: "окно открылось на карте"}
FOLLOW_END = {0: "по своей команде", 1: "щёлкнул по карте сам", 2: "цель пропала с карты", 3: "доехал до метки"}
DUEL_OFF = {"declined": "соперник отказался", "no_answer": "соперник не ответил",
            "not_on_the_battle_server": "кто-то не вышел на сервер боя"}
BATTLE_KINDS = {"lair": "логово", "caravan": "караван или крестьяне", "village": "деревня"}
INVITE_TYPES = {1: "бой рядом", 2: "нападение", 3: "бой лидера", 4: "арена", 5: "турнир", 6: "тренировка", 7: "дуэль"}


def together_text(what, f):
    """What a line of the bridge's "together" log says, or None for one this report does not know."""
    n = lambda key: int(f.get(key, "0") or 0)  # noqa: E731
    won = lambda: "победа" if f.get("won") == "1" else "поражение"  # noqa: E731
    if what == "prisoners":
        room = f", без места осталось {n('no_room')}" if n("no_room") else ""
        return (f"пленные после боя: взято {n('taken')}, шанс {n('chance')}%{room}" if n("chance")
                else "пленные после боя: нет навыка Содержание пленных, никого не взято")
    if what == "troops_xp":
        return f"опыт отряду за бой: {n('xp')} ({won()})"
    if what == "arena":
        return f"арена: побеждено {n('kills')}, награда {n('prize')} динаров" + (", устоял до конца" if n("won") else "")
    if what == "tournament":
        return (f"турнир выигран: раундов {n('rounds')}, получено {n('gold')} динаров" if n("gold")
                else f"турнир проигран: раундов выиграно {n('rounds')}, ставка потеряна {n('stake_lost')}")
    if what == "training":
        return f"тренировка: побеждено {n('ratio')}% противников, отряд получил {n('earned')} опыта"
    if what == "tree":
        return f"древо войск: открыт юнит {n('troop')}"
    if what == "follow":
        target = f.get("target", "-")
        return "едет один" if target == "-" else f"едет за игроком {target}"
    if what == "follow_jump":
        return f"поход: приказ двигаться не сработал, отряд перенесён к цели (было {n('distance')} км)"
    if what == "follow_end":
        return "поход окончен: " + FOLLOW_END.get(n("why"), "?")
    if what == "base":
        return f"поставил лагерь отряда ({n('x') // 100}, {n('y') // 100})"
    if what == "base_off":
        return "убрал лагерь отряда"
    if what == "gold":
        moved = n("moved")
        word = f"положил {moved}" if moved > 0 else f"взял {-moved}" if moved < 0 else "казна пуста, ничего не взято"
        return f"казна: {word}, остаток {n('balance')}"
    if what == "store_open":
        return f"открыл склад: вещей {n('items')}"
    if what == "store_saved":
        return f"склад сохранён: вещей {n('items')}"
    if what == "store_refused":
        return f"склад занят: его держит {f.get('used_by', '?')}"
    if what == "invite_off_map":
        return f"приглашение (бой {n('battle')}, {INVITE_TYPES.get(n('type'), '?')}) дошло вне карты"
    if what == "signal":
        return f"сигнал к бою: {SIGNAL_HOW.get(n('how'), '?')} ({INVITE_TYPES.get(n('invite'), '?')})"
    if what == "signal_bridge":
        return f"сигнал к бою {n('battle')} показан в окне моста"
    if what == "duel_call":
        return f"вызвал на дуэль игрока {f.get('rival', '?')}, ставка {n('stake')}"
    if what == "duel_off":
        return f"дуэль {n('battle')} отменена: {DUEL_OFF.get(f.get('why'), f.get('why', '?'))}"
    if what == "duel":
        word = {0: "проигрыш", 1: "победа", 2: "ничья"}.get(n("result"), "?")
        return f"дуэль: {word}, ставка {n('stake')}, деньги {n('gold'):+d}"
    if what in ("battle_lair", "battle_caravan", "battle_village"):
        return f"начал бой: {BATTLE_KINDS[what[7:]]}, бой {n('battle')}, враг {n('enemy')}"
    if what == "battle_end":
        return f"бой {n('battle')} ({BATTLE_KINDS.get(f.get('kind'), '?')}) окончен: {won()}"
    if what == "lair":
        return f"логово: {won()}" + (", задание выполнено" if n("quest") else "")
    if what == "village":
        return f"деревня {n('center')}: {won()}, отношение {n('relation'):+d}"
    if what == "caravan":
        return f"защита каравана: {won()}"
    return None

LINE = re.compile(r"^(\d\d):(\d\d):(\d\d) (.*)$")
TRACE = re.compile(r"^(\d\d):(\d\d):(\d\d) (\S+) (\S+) (.*)$")
TRAIL = re.compile(r"^(\d\d):(\d\d):(\d\d) (\S+) (\d+) (.*)$")
TRAIL_LOST = re.compile(r"^lost (\d+)$")
STATS = re.compile(r"^parties (\d+), server [\d.]+/s, players [\d.]+/s \[(.*?)\], (running|PAUSED)")
FLOW = re.compile(r"parties: (\d+) new, (\d+) gone, (\d+) back$")  # the stats lines of newer bridges
SLOT = re.compile(r"(\d+):(.*?)( busy)?(?: silent (\d+)s)?( alive)?(?: mp:[^,]*)?(?:, (?=\d+:)|$)")
TOGETHER = re.compile(r"^together (\d+):(.*?): (\w+)(?: (.*))?$")
TOGETHER_FIELD = re.compile(r"(\w+)=(.*?)(?= \w+=|$)")
START = re.compile(r"^joint battle: (\d+):(.*?) starts a joint battle \(battle -?\d+, enemy party (-?\d+), "
                   r"player slot (-?\d+), center (-?\d+)")
GATHER = re.compile(r"^joint battle (\d+): gathering; invited: (.*)$")
ANSWER = re.compile(r"^joint battle: (\d+):(.*?) (accepts the invitation|declines / cancels) \(battle (-?\d+)")
GOING = re.compile(r"^joint battle (\d+): going to the battle server \((\d+) stacks, sides (.*)\)$")
SIDE = re.compile(r"(\d+):(.*?)=team (\d)")
STARTED = re.compile(r"^joint battle (\d+): started on the battle server")
BATTLE_LOST = re.compile(r"^joint battle (\d+): lost")
TOO_LATE = re.compile(r"^joint battle (\d+): (\d+):(.*?) accepted too late")
JOINED_LATE = re.compile(r"^joint battle (\d+): (\d+):(.*?) accepted late - ")
HERO_LATE = re.compile(r"^joint battle (\d+): (\d+):(.*?) is on the battle server now - ")
REFUSED = re.compile(r"^joint battle: refused - (.*)$")
LOG_FOLDER = "Warband Coop Campaign"  # in Documents: the bridge's logs and the players' heroes
RUNS = re.compile(r"^player (\d+):(\S+) runs CoopWorld build (\d+)(.*)$")
HELD = re.compile(r"^world held by player (\d+) \(([^)]+)\): (.*)$")
CONNECTED = re.compile(r"^net: player (\S+) (connected again|connected), multiplayer name '(.*)'")
LEFT = re.compile(r"^net: player (\S+) left")
NET_LOST = re.compile(r"^net: lost (\S+);")
NET_ERROR = re.compile(r"^net: (\S+) error (.*)$")
QUIET = re.compile(r"^player (\d+):(.*?) quiet since (\d\d:\d\d:\d\d): last request (.*?); last replies (.*)$")
CAPTOR_GONE = re.compile(r"^party (\d+) is gone, the captor of (.*)$")
CLOCK_OFF = re.compile(r"^player (\d+):(.*?): its clock is (\d+) h (ahead of|behind) the world's")
CLOCK_EVEN = re.compile(r"^player (\d+):(.*?): its clock is the world's again \(([+-]?\d+) h\)(?: after (\d+) s)?")
LORD_FIGHTS = re.compile(r"^player (\d+):(.*?): the lord it serves \(party (\d+)\) fights party (\d+)")
MP_FOUND = re.compile(r"^battle server: player (\d+) \((.*?)\) (NOT found|recognised as)")


def clock(h, m, s):
    return int(h) * 3600 + int(m) * 60 + int(s)


def stamp(t):
    t = int(t) % DAY
    return f"{t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d}"


def span(seconds):
    seconds = int(seconds)
    return f"{seconds // 60} мин {seconds % 60} с" if seconds >= 60 else f"{seconds} с"


def unwrap(times):
    """Clock times of a log's lines in file order -> seconds from the last line's midnight: the
    logs have no dates, so a jump back of more than half a day is a midnight between two lines."""
    out, day, later = [0] * len(times), 0, None
    for i in range(len(times) - 1, -1, -1):
        if later is not None and times[i] > later + DAY // 2:
            day -= 1
        out[i] = times[i] + day * DAY
        later = times[i]
    return out


def read_bridge(path):
    """bridge.log -> [(t, text)]; a line without a time (a traceback) goes with the line before."""
    lines = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LINE.match(raw)
        if m:
            lines.append([clock(*m.groups()[:3]), m.group(4)])
        elif lines and raw.strip():
            lines[-1][1] += "\n" + raw
    times = unwrap([t for t, _ in lines])
    return [(t, text) for t, (_, text) in zip(times, lines)]


def read_trace(paths, last_bridge_t=None):
    """trace.old.log and trace.log -> [(t, role, cid, query dict, reply numbers)]."""
    raw = []
    for path in paths:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            m = TRACE.match(line)
            if not m:
                continue
            reply = ""
            if i + 1 < len(lines) and lines[i + 1].lstrip().startswith("->"):
                reply = lines[i + 1].strip()[2:].strip()
            h, mi, s, role, cid, target = m.groups()
            query = {k: v[0] for k, v in parse_qs(urlparse(target).query, keep_blank_values=True).items()}
            raw.append((clock(h, mi, s), role, cid, query, reply.split("|")))
    times = unwrap([e[0] for e in raw])
    if times and last_bridge_t is not None:
        while times[-1] > last_bridge_t + DAY // 2:  # the two logs end on the same day
            times = [t - DAY for t in times]
    return [(t, *e[1:]) for t, e in zip(times, raw)]


def read_trail(paths, last_bridge_t=None):
    """trail.old.log and trail.log -> [(t, cid, text)]."""
    raw = []
    for path in paths:
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                m = TRAIL.match(line)
                if m:
                    raw.append((clock(*m.groups()[:3]), m.group(4), m.group(6)))
    times = unwrap([e[0] for e in raw])
    if times and last_bridge_t is not None:
        while times[-1] > last_bridge_t + DAY // 2:
            times = [t - DAY for t in times]
    return [(t, *e[1:]) for t, e in zip(times, raw)]


def action(text):
    """A line of the trail for the report."""
    m = TRAIL_LOST.match(text)
    return f"(потеряно записей: {m.group(1)})" if m else text


FAULTS = ("Get-WinEvent -FilterHashtable @{LogName='Application';ProviderName='Application Error','Application Hang';"
          "StartTime=(Get-Date).AddDays(-%d)} -ErrorAction SilentlyContinue | ForEach-Object {"
          " $_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss') + '|' + $_.Id + '|' + ($_.Properties.Value -join '|') }")


def parse_faults(text):
    """Lines of FAULTS -> report lines about the game: event 1000 is a crash (name, versions, the faulting
    module, the code, the offset), 1002 a window that stopped answering and was closed."""
    out = []
    for line in text.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 3 or "mb_warband" not in parts[2].lower():
            continue
        if parts[1] == "1000" and len(parts) > 9:
            out.append(f"  {parts[0]} вылет: код {parts[8]}, смещение {parts[9]}, модуль {parts[5]}")
        elif parts[1] == "1002":
            out.append(f"  {parts[0]} зависание: окно перестало отвечать, его закрыли")
    return out


def windows_faults():
    """The game's crashes and hangs in Windows' log; none where it cannot be read."""
    try:
        done = subprocess.run(["powershell", "-NoProfile", "-Command", FAULTS % FAULT_DAYS], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    return parse_faults(done.stdout or "")


def number(parts, i, default=None):
    try:
        return int(parts[i])
    except (IndexError, ValueError):
        return default


def state(query):
    """What a player's game was doing, from its request."""
    op = query.get("mp")
    if op is not None:
        return {"1": "начинает совместный бой", "2": "в окне совместного боя", "3": "принимает приглашение",
                "4": "отказывается от боя"}.get(op, "в окне совместного боя")
    if query.get("free") == "1":
        return "на карте"
    if query.get("busy", "0") != "0":
        return "во встрече или меню"
    return "не на карте (меню, экран)"


class Session:
    def __init__(self, events, trace, trail=()):
        self.events = events
        self.start, self.end = events[0][0], events[-1][0]
        self.trace = [e for e in trace if self.start - 1 <= e[0] <= self.end + STATS_EVERY_S]
        self.trail = [e for e in trail if self.start - 1 <= e[0] <= self.end + STATS_EVERY_S]
        self.findings = []  # (t, mark, text)
        self.names = {}     # cid -> hero name, from the requests
        self.slot_cid = []  # (t, slot, cid)
        for t, role, cid, q, _ in self.trace:
            if role == "cli" and q.get("name"):
                self.names[cid] = q["name"]

    def note(self, t, mark, text):
        self.findings.append((t, mark, text))

    def cid_of(self, slot, name, t):
        """The game behind a slot and a name at time t."""
        known = [c for when, s, c in self.slot_cid if s == slot and when <= t + STATS_EVERY_S]
        if known:
            return known[-1]
        same = [c for c, n in self.names.items() if n == name]
        return same[0] if len(same) == 1 else None

    def who(self, cid):
        name = self.names.get(cid)
        place = "хост" if cid == "local" else cid
        return f"{name} ({place})" if name else place

    def last_request(self, cid, before):
        found = None
        for e in self.trace:
            if e[0] > before:
                break
            if e[1] == "cli" and e[2] == cid:
                found = e
        return found

    def actions(self, cid, before, count):
        """The player's last entries of the trail up to a moment."""
        return [e for e in self.trail if e[1] == cid and e[0] <= before][-count:]

    def replies(self, cid, after, before):
        return [e for e in self.trace if e[1] == "cli" and e[2] == cid and after <= e[0] <= before]


def detail(parts):
    """What a battle reply says, in a few words."""
    kind = kind_of(parts)
    if kind == 8:
        won, xp, n = number(parts, 3), number(parts, 4), number(parts, 5)
        return f" ({'победа' if won else 'поражение'}, опыт {xp}, потерь стеков {n})"
    if kind == 10:
        health, captor = number(parts, 3, -1), number(parts, 4, -1)
        words = ([f"здоровье {health}%"] if health >= 0 else []) + ([f"плен у отряда {captor}"] if captor >= 0 else [])
        return f" ({', '.join(words)})" if words else ""
    if kind in (11, 21):
        return f" (видов войск: {number(parts, 3, 0)})"
    return ""


def kind_of(parts):
    return number(parts, 1) if parts and parts[0] == "7777" else None


def analyze(events, trace, silence=30, trail=()):
    """One session's report lines."""
    s = Session(events, trace, trail)
    out = [f"Сессия {stamp(s.start)} - {stamp(s.end)} ({span(s.end - s.start)})"]

    # ---- players, builds, connections
    builds, lost_ips = {}, {}
    for t, text in events:
        m = RUNS.match(text)
        if m:
            slot, who, build, rest = int(m.group(1)), m.group(2), m.group(3), m.group(4)
            # the bridge names the player by its hero's name once it knows it, else by the game
            cid = who if who == "local" or who.startswith("net-") else                 next((c for c, n in s.names.items() if n == who), who)
            s.slot_cid.append((t, slot, cid))
            builds[cid] = build
            if "NOT the host" in rest:
                s.note(t, "!!", f"{s.who(cid)}: сборка {build} не та, что у хоста{rest.split('NOT the host')[1]}")
            continue
        m = HELD.match(text)
        if m:
            s.slot_cid.append((t, int(m.group(1)), m.group(2)))
            continue
        m = CONNECTED.match(text)
        if m:
            cid, again = m.group(1), m.group(2) == "connected again"
            ip = cid.split("@")[-1]
            if again:
                s.note(t, "  ", f"игрок {cid} подключился снова (в пределах 30 с: всё сохранено)")
            elif ip in lost_ips:
                s.note(t, "? ", f"игрок с {ip} подключился заново (связь терялась в {stamp(lost_ips.pop(ip))}): "
                                "отряды, пропавшие у хоста за это время, могут держаться у этого игрока "
                                "фантомами ~1,5 мин")
            else:
                s.note(t, "  ", f"игрок {cid} подключился, имя на сервере боя '{m.group(3)}'")
            continue
        m = NET_LOST.match(text)
        if m:
            lost_ips[m.group(1).split("@")[-1]] = t
            s.note(t, "? ", f"потеряна связь с {s.who(m.group(1))}")
            continue
        m = LEFT.match(text)
        if m:
            s.note(t, "  ", f"игрок {s.who(m.group(1))} вышел из co-op")
            continue
        m = NET_ERROR.match(text)
        if m:
            reason = m.group(2)
            if "10054" in reason:
                reason = "соединение закрыто с той стороны (игра или мост друга закрыты либо упали)"
            s.note(t, "  ", f"{s.who(m.group(1))}: {reason}")
            continue
        m = CAPTOR_GONE.match(text)
        if m:
            s.note(t, "? ", f"у мира пропал отряд {m.group(1)}, взявший в плен {m.group(2)}: "
                            "клиент держит его копию, пока игрок в плену")
            continue
        m = REFUSED.match(text)
        if m:
            s.note(t, "? ", f"совместный бой не начат: {m.group(1)}")
            continue
        m = CLOCK_OFF.match(text)
        if m:
            where = "впереди мира: стоя на месте, ждёт его" if m.group(4) == "ahead of" else                 "позади мира: стоя на месте, догоняет быстрее"
            s.note(t, "  ", f"игрок {m.group(2)}: время на {m.group(3)} ч {where}")
            continue
        m = CLOCK_EVEN.match(text)
        if m:
            took = int(m.group(4)) if m.group(4) else 0
            s.note(t, "? " if took > 120 else "  ",
                   f"игрок {m.group(2)}: время снова как у мира ({m.group(3)} ч)"
                   + (f" через {span(took)}" if m.group(4) else "")
                   + (" - долго: игрок, видимо, всё время шёл или мир стоял" if took > 120 else ""))
            continue
        m = LORD_FIGHTS.match(text)
        if m:
            s.note(t, "  ", f"игрок {m.group(2)}: лорд, которому он служит (отряд {m.group(3)}), "
                            f"бьётся с отрядом {m.group(4)}")
            continue
        if "Traceback" in text or "Exception" in text:
            s.note(t, "!!", "ошибка в мосте: " + text.splitlines()[-1][:200])

    # a hold "in an encounter or battle" over within seconds: a client resting on the spot used to
    # count as one until a game hour passed
    short, held = {}, None
    for t, text in events:
        m = HELD.match(text)
        if m:
            held = (t, m.group(2)) if m.group(3).startswith("in an encounter") else None
        elif text == "world runs again" and held is not None:
            if t - held[0] <= 10:
                short.setdefault(held[1], []).append(held[0])
            held = None
    for cid, times in short.items():
        if len(times) >= 3:
            s.note(times[0], "? ", f"игрок {s.who(cid)}: {len(times)} коротких пауз мира «во встрече или бою» "
                                   f"(до 10 с, без боя) - так выглядела остановка героя на месте")

    names_now = sorted(set(c for _, _, c in s.slot_cid) | set(s.names))
    out.append("Игроки:")
    for cid in names_now:
        if cid in s.names or cid in builds:
            out.append(f"  {s.who(cid)}" + (f", сборка {builds[cid]}" if cid in builds else ""))

    # ---- the stats lines: parties, pauses, silences
    stats, flow = [], []
    for t, text in events:
        m = STATS.match(text)
        if m:
            slots = {}
            if m.group(2) != "none":
                for sm in SLOT.finditer(m.group(2)):
                    slots[int(sm.group(1))] = (sm.group(2), bool(sm.group(3)),
                                               int(sm.group(4)) if sm.group(4) else 0, bool(sm.group(5)))
            stats.append((t, int(m.group(1)), m.group(3) == "PAUSED", slots))
            f = FLOW.search(text)
            if f:
                flow.append((t, *map(int, f.groups())))
    if stats:
        counts = [n for _, n, _, _ in stats if n] or [0]  # 0 until the world server reports
        out.append(f"Отряды мира: {counts[0]} -> {counts[-1]} (от {min(counts)} до {max(counts)})")
        paused = sum(1 for e in stats if e[2])
        out.append(f"Мир стоял на паузе {paused * 100 // len(stats)}% времени")
        for (t0, n0, _, _), (t1, n1, _, _) in zip(stats, stats[1:]):
            if n0 - n1 >= max(15, n0 * PARTY_DROP):
                s.note(t1, "? ", f"отрядов в мире разом стало меньше: {n0} -> {n1}")
    if flow:
        new, gone, back = (sum(f[i] for f in flow) for i in (1, 2, 3))
        out.append(f"Отряды у моста: новых {new}, пропало {gone}, из пропавших вернулось {back}")
        if back:
            worst = max(flow, key=lambda f: f[3])
            s.note(worst[0], "? ", f"мост {back} раз забыл живой отряд и узнал его снова (больше всего - "
                                   f"{worst[3]} за 5 с): у игроков такой отряд пропадает с карты и появляется вновь")

    results = {}  # cid -> [t of kind 8 replies]
    for t, role, cid, q, parts in s.trace:
        if role == "cli" and kind_of(parts) == 8:
            results.setdefault(cid, []).append(t)

    episodes = []  # [slot, name, start, last t, longest, how it ended, busy, answered at all, answering last]
    open_ = {}
    for i, (t, _, _, slots) in enumerate(stats):
        for slot, (name, _, quiet, alive) in slots.items():
            ep = open_.get(slot)
            if quiet:
                if ep is not None and ep[1] == name and quiet > ep[4]:
                    ep[3], ep[4] = t, quiet
                    ep[7], ep[8] = ep[7] or alive, alive
                else:
                    if ep is not None:
                        ep[5] = "back"
                    open_[slot] = ep = [slot, name, t - quiet, t, quiet, None, slots[slot][1], alive, alive]
                    episodes.append(ep)
            elif ep is not None:
                ep[5] = "back"
                del open_[slot]
        for slot in [k for k in open_ if k not in slots]:
            open_.pop(slot)[5] = "gone"
    for ep in open_.values():
        ep[5] = "end"

    for slot, name, begin, last, longest, ended, busy, answered, answering in episodes:
        # a game that never came back is reported however short: the session may have been closed on it
        if longest < (min(silence, 10) if ended != "back" else silence):
            continue
        cid = s.cid_of(slot, name, begin)
        req = s.last_request(cid, begin + 2) if cid else None
        if req and begin - req[0] <= 30:
            seen = f"; перед этим ({stamp(req[0])}): {state(req[3])}"
        else:  # trace.log keeps only some requests: the state line knows whether it was in an encounter
            seen = "; по строке состояния: " + ("во встрече или бою" if busy else "не во встрече (меню, экран, карта)")
        got = s.replies(cid, begin - 30, begin + 2) if cid else []
        kinds = [kind_of(e[4]) for e in got if kind_of(e[4]) not in (None, 0, 7)]
        if kinds:
            seen += ", последние ответы: " + ", ".join(f"{k} ({KINDS.get(k, '?')})" for k in kinds[-4:])
        did = s.actions(cid, begin + 2, TRAIL_BEFORE) if cid else []
        if did:
            seen += ". Последние действия: " + "; ".join(f"{stamp(e[0])} {action(e[2])}" for e in did)
        lost = next((t for t, text in events if begin <= t <= last + STATS_EVERY_S * 2
                     and NET_LOST.match(text) and cid and NET_LOST.match(text).group(1) == cid), None)
        after = [r for r in results.get(cid, []) if 0 <= begin - r <= AFTER_BATTLE_S]
        how = {"back": "вернулся", "gone": "ушёл из игры", "end": "так и не вернулся до конца лога"}[ended]
        if lost is not None:
            how = f"связь потеряна в {stamp(lost)}"
        text = f"игрок {name or s.who(cid)} молчал {span(longest)} ({how}){seen}"
        told = next((m for t, m in ((t, QUIET.match(x)) for t, x in events) if m and int(m.group(1)) == slot
                     and begin - 5 <= t <= begin + 15), None)
        if told:
            hour = re.search(r"h=(\d+)", told.group(4))
            when = ""
            if hour:
                h = int(hour.group(1))
                when = f" (игровой день {h // 24 + 1}, {h % 24:02d}:00)"
            text += f". Последний запрос: {told.group(4)}{when}; последние ответы: {told.group(5)}"
        near = [f"{stamp(t)} {text_}" for t, text_ in events
                if abs(t - begin) <= STATS_EVERY_S and not STATS.match(text_) and not text_.startswith("world ")
                and not QUIET.match(text_)]
        if near:
            text += ". Рядом по времени: " + "; ".join(near)
        # a game that never came back after a battle is what this report is for; one that went
        # quiet at the end of the session may just have been closed
        came_back = ended == "back" and lost is None
        if after:
            text += f". Это через {span(begin - after[-1])} после результата боя"
        hung = answered and not answering
        if answering:
            text += ". Игра отвечала на проверку связи: это меню, а не зависание"
        elif hung:
            text += ". Игра отвечала на проверку связи, потом перестала: зависание или закрытие"
        if hung:
            mark = "!!"
        elif after and not came_back:
            mark = "!!"
        elif answering:
            mark = "  "
        elif not came_back:
            mark, text = "? ", text + " - игру закрыли, или она зависла"
        elif longest >= LONG_SILENCE_S or (after and longest >= 60):
            mark, text = "? ", text + " - долго в меню или на экране"
        else:
            mark = "  "
        s.note(begin, mark, text)

    # ---- joint battles
    battles, pending, found = {}, None, {}
    for t, text in events:
        m = MP_FOUND.match(text)
        if m:
            found[int(m.group(1))] = (m.group(2), m.group(3) == "recognised as")
            continue
        m = START.match(text)
        if m:
            pending = dict(t=t, slot=int(m.group(1)), name=m.group(2), enemy=int(m.group(3)),
                           center=int(m.group(5)))
            continue
        m = GATHER.match(text)
        if m:
            bid = int(m.group(1))
            battles[bid] = dict(pending or dict(t=t, slot=None, name="?", enemy=None, center=-1),
                                bid=bid, invited=m.group(2), answers=[], sides=None, started=None,
                                lost=None, late=[], missing=[], joined_late=[], heroes_late=[])
            pending = None
            continue
        m = ANSWER.match(text)
        if m and int(m.group(4)) in battles:
            battles[int(m.group(4))]["answers"].append((t, int(m.group(1)), m.group(2), m.group(3)))
            continue
        m = GOING.match(text)
        if m and int(m.group(1)) in battles:
            b = battles[int(m.group(1))]
            b["sides"] = [(int(a), n, int(team)) for a, n, team in SIDE.findall(m.group(3))]
            b["missing"] = [n for a, n, _ in b["sides"] if int(a) in found and not found[int(a)][1]]
            continue
        m = STARTED.match(text)
        if m and int(m.group(1)) in battles:
            battles[int(m.group(1))]["started"] = t
            continue
        m = BATTLE_LOST.match(text)
        if m and int(m.group(1)) in battles:
            battles[int(m.group(1))]["lost"] = t
            continue
        m = TOO_LATE.match(text)
        if m and int(m.group(1)) in battles:
            battles[int(m.group(1))]["late"].append((t, m.group(3)))
            continue
        m = JOINED_LATE.match(text)
        if m and int(m.group(1)) in battles:
            battles[int(m.group(1))]["joined_late"].append((t, m.group(3)))
            continue
        m = HERO_LATE.match(text)
        if m and int(m.group(1)) in battles:
            battles[int(m.group(1))]["heroes_late"].append((t, m.group(3)))

    outcomes = {}
    for t, role, cid, q, parts in s.trace:
        if role == "mp" and q.get("st") == "4":
            bid = int(q.get("bid", "0") or 0)
            outcomes.setdefault(bid, (t, int(q.get("w", "-1") or -1)))

    if battles:
        out.append("Совместные бои:")
    for bid, b in sorted(battles.items()):
        where = f"штурм/оборона центра {b['center']}" if b["center"] not in (None, -1) else f"враг {b['enemy']}"
        out.append(f"  Бой {bid}: {stamp(b['t'])}, начал {b['name']}, {where}; приглашены: {b['invited']}")
        for t, slot, name, what in b["answers"]:
            out.append(f"    {stamp(t)} {name}: {'согласие' if what.startswith('accepts') else 'отказ / отмена'}")
        for t, name in b["late"]:
            s.note(t, "? ", f"бой {bid}: согласие игрока {name} пришло слишком поздно, бой начался без этого игрока")
        answered = {slot for _, slot, _, _ in b["answers"]}
        if b["sides"] is None:
            if not any(what.startswith("declines") for *_, what in b["answers"]):
                s.note(b["t"], "? ", f"бой {bid} не дошёл до сервера боя")
            continue
        out.append("    стороны: " + ", ".join(f"{n} (команда {team})" for _, n, team in b["sides"]))
        invited = re.findall(r"(\d+):([^,]+)", b["invited"])
        for slot, name in invited:
            if int(slot) not in answered and all(int(slot) != a for a, _, _ in b["sides"]):
                s.note(b["t"], "!!", f"бой {bid}: игрок {name.strip()} не ответил на приглашение, "
                                     "бой прошёл без этого игрока")
        for name in b["missing"]:
            s.note(b["t"], "? ", f"бой {bid}: игрока {name} нет на сервере боя - его бойцы дрались без героя")
        if b["started"] is None:
            s.note(b["t"], "!!", f"бой {bid}: стороны собраны, но бой не начался на сервере боя")
            continue
        out.append(f"    {stamp(b['started'])} начался на сервере боя")
        for t, name in b["joined_late"]:
            out.append(f"    {stamp(t)} {name}: согласие после сбора - в бою героем, без своих отрядов")
        for t, name in b["heroes_late"]:
            out.append(f"    {stamp(t)} {name}: герой отправлен на сервер боя уже во время боя (игрок зашёл на сервер позже)")
        if b["lost"] is not None:
            s.note(b["lost"], "!!", f"бой {bid} потерян: сервер боя вернулся к обычному раунду")
            continue
        outcome = outcomes.get(bid)
        if outcome is None:
            s.note(b["started"], "!!", f"бой {bid}: итога с сервера боя нет (бой не закончен, или мост остановлен)")
            continue
        t_end, winner = outcome
        out.append(f"    {stamp(t_end)} итог: " + (f"победила команда {winner}" if winner in (0, 1) else "ничья"))
        for slot, name, team in b["sides"]:
            cid = s.cid_of(slot, name, b["t"])
            got = [e for e in s.trace if e[1] == "cli" and e[2] == cid and e[0] >= t_end - 1
                   and kind_of(e[4]) in (8, 9, 10, 11, 13, 21, 26) and number(e[4], 2) == bid]
            line = []
            for e in got:
                line.append(f"{KINDS[kind_of(e[4])]}{detail(e[4])} {stamp(e[0])} ({state(e[3])})")
            out.append(f"    {name}: " + ("; ".join(line) if line else "ничего не получил"))
            result = next((e for e in got if kind_of(e[4]) in (8, 26)), None)  # 26: a joint event's end
            if result is None:
                s.note(t_end, "!!", f"бой {bid}: результат не дошёл до игрока {name}")
                continue
            if result[0] - t_end > 15:
                s.note(result[0], "? ", f"бой {bid}: результат дошёл до игрока {name} через {span(result[0] - t_end)}")
            loot = next((e for e in got if kind_of(e[4]) == 21), None)
            if loot is not None and state(loot[3]) == "на карте":
                s.note(loot[0], "? ", f"бой {bid}: добыча пришла игроку {name} уже на карте, не в меню боя "
                                      "(ждёт в Лагерь - CoopWorld: кооператив)")
            if team == winner and loot is None and winner in (0, 1):
                out.append(f"    ({name}: добычи нет - павших врагов не было, или их добыча ушла другим)")

    # ---- what the players did together
    together, known = [], set()
    for t, text in events:
        m = TOGETHER.match(text)
        if not m:
            continue
        what, fields = m.group(3), dict(TOGETHER_FIELD.findall(m.group(4) or ""))
        said = together_text(what, fields)
        name = m.group(2)
        together.append(f"  {stamp(t)} {name}: {said if said is not None else what + ' ' + (m.group(4) or '')}")
        known.add(what)
        if what == "follow_jump":
            s.note(t, "? ", f"игрок {name}: отряд не послушался приказа идти за другом и был перенесён к цели")
        elif what == "store_refused":
            s.note(t, "  ", f"игрок {name}: склад занят другим игроком")
        elif what == "duel_off" and fields.get("why") != "declined":
            s.note(t, "? ", f"игрок {name}: {together_text(what, fields)}")
    if together:
        out.append("Совместные дела:")
        out += together

    # ---- a debug build's trail
    if s.trail:
        out.append("След действий (последнее внизу):")
        for cid in sorted({e[1] for e in s.trail}):
            out.append(f"  {s.who(cid)}:")
            out += [f"    {stamp(e[0])} {action(e[2])}" for e in s.actions(cid, s.end + STATS_EVERY_S, TRAIL_SHOWN)]

    # ---- the report
    s.findings.sort(key=lambda f: f[0])
    problems = sum(1 for f in s.findings if f[1] == "!!")
    look = sum(1 for f in s.findings if f[1] == "? ")
    out.append("По времени (!! - проблема, ?  - стоит посмотреть):")
    for t, mark, text in s.findings:
        out.append(f"  {mark} {stamp(t)} {text}")
    out.append(f"Итог: проблем {problems}, стоит посмотреть {look}.")
    return out


def sessions(events):
    """bridge.log -> one list of events per bridge start."""
    starts = [i for i, (_, text) in enumerate(events) if text.startswith("logs: ")] or [0]
    if starts[0] != 0:
        starts.insert(0, 0)
    bounds = starts + [len(events)]
    return [events[a:b] for a, b in zip(bounds, bounds[1:]) if b > a]


def default_folder():
    try:
        import ctypes.wintypes
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)  # CSIDL_PERSONAL: Documents
        return Path(buf.value) / LOG_FOLDER
    except (AttributeError, OSError):
        return Path.home() / "Documents" / LOG_FOLDER


def fault_lines():
    faults = windows_faults()
    return ["", f"Журнал Windows за {FAULT_DAYS} дн.:"] + faults if faults else []


def main(argv=None):
    ap = argparse.ArgumentParser(description="Warband Coop Campaign: a session's report from bridge.log and trace.log")
    ap.add_argument("folder", nargs="?", help="where the logs are (default: Documents\\Warband Coop Campaign)")
    ap.add_argument("--all", action="store_true", help="every session in bridge.log, not only the last")
    ap.add_argument("--silence", type=int, default=30, help="report silences this long and longer (s)")
    ap.add_argument("--out", help="the report file (default: report.txt next to the logs)")
    args = ap.parse_args(argv)
    folder = Path(args.folder) if args.folder else default_folder()
    bridge = folder / "bridge.log"
    if not bridge.exists():
        join = folder / "join.log"
        if join.exists():
            print(f"{bridge} нет: это компьютер друга. Отчёт строится на компьютере хоста; join.log:")
            print(join.read_text(encoding="utf-8", errors="replace")[-3000:])
            mine = read_trail([folder / "trail.old.log", folder / "trail.log"])
            if mine:
                print("След действий (последнее внизу):")
                print("\n".join(f"  {stamp(e[0])} {action(e[2])}" for e in mine[-TRAIL_SHOWN:]))
            print("\n".join(fault_lines()))
            return 0
        print(f"нет {bridge}")
        return 1
    events = read_bridge(bridge)
    if not events:
        print(f"{bridge} пуст")
        return 1
    trace = read_trace([folder / "trace.old.log", folder / "trace.log"], events[-1][0])
    trail = read_trail([folder / "trail.old.log", folder / "trail.log"], events[-1][0])
    chosen = sessions(events) if args.all else sessions(events)[-1:]
    lines = [f"CoopWorld: отчёт по {bridge} и trace.log"]
    for part in chosen:
        lines.append("")
        lines += analyze(part, trace, args.silence, trail)
    lines += fault_lines()
    text = "\n".join(lines) + "\n"
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8"))
    out = Path(args.out) if args.out else folder / "report.txt"
    out.write_text("﻿" + text, encoding="utf-8")
    print(f"\nОтчёт сохранён: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
