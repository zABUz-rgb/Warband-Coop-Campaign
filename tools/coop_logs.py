"""CoopWorld session report: what happened in a session, read from the bridge's logs.

After playing, on the host's PC (the logs are in Documents\\CoopWorld):

    python tools/coop_logs.py [FOLDER] [--all] [--silence 30] [--out FILE]

bridge.log has the bridge's events and, every 5 s, a line on the parties and players (who is busy,
who has been silent how long); trace.log has the requests and replies about battles, joining and
results. The report goes through the last session (--all: every session in bridge.log):

  - players, their builds (a different build than the host's), connections lost and made again;
  - every joint battle: who started it, who was invited and answered, the sides, the outcome from
    the battle server, and when each player got the result and the spoils, in which state;
  - silences: a player's game that stopped asking (a menu, a screen, a hang), with the state it was
    last seen in and the replies it got last, and whether it came back;
  - the world's parties (sudden drops), how long the world stood still, the bridge's own errors.

Lines marked !! are problems, ?  worth a look, the rest is what happened. The report is printed
and written to report.txt next to the logs (FOLDER defaults to Documents\\CoopWorld).
"""
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DAY = 86400
STATS_EVERY_S = 5
AFTER_BATTLE_S = 120    # a silence that begins this soon after a player got the result is the battle's
LONG_SILENCE_S = 120    # a menu this long: worth a look
PARTY_DROP = 0.05       # this share of the world's parties gone between two stats lines (and 15 at least)

KINDS = {1: "итог для мира", 2: "позиции", 3: "войска", 4: "игрок", 5: "пауза", 6: "приглашение",
         7: "состояние боя", 8: "результат боя", 9: "владение оружием", 10: "здоровье/плен",
         11: "пленные", 12: "владельцы центров", 13: "штурм", 14: "герой", 15: "предложены войска",
         16: "ответ на войска", 17: "просьба вступить", 18: "ответ на просьбу", 19: "вступил/ушёл",
         20: "отпущен", 21: "добыча", 22: "имя", 23: "сохранение хоста", 24: "стать клиентом"}

LINE = re.compile(r"^(\d\d):(\d\d):(\d\d) (.*)$")
TRACE = re.compile(r"^(\d\d):(\d\d):(\d\d) (\S+) (\S+) (.*)$")
STATS = re.compile(r"^parties (\d+), server [\d.]+/s, players [\d.]+/s \[(.*?)\], (running|PAUSED)")
FLOW = re.compile(r"parties: (\d+) new, (\d+) gone, (\d+) back$")  # the stats lines of newer bridges
SLOT = re.compile(r"(\d+):(.*?)( busy)?(?: silent (\d+)s)?(?: mp:[^,]*)?(?:, (?=\d+:)|$)")
START = re.compile(r"^joint battle: (\d+):(.*?) starts a joint battle \(battle -?\d+, enemy party (-?\d+), "
                   r"player slot (-?\d+), center (-?\d+)")
GATHER = re.compile(r"^joint battle (\d+): gathering; invited: (.*)$")
ANSWER = re.compile(r"^joint battle: (\d+):(.*?) (accepts the invitation|declines / cancels) \(battle (-?\d+)")
GOING = re.compile(r"^joint battle (\d+): going to the battle server \((\d+) stacks, sides (.*)\)$")
SIDE = re.compile(r"(\d+):(.*?)=team (\d)")
STARTED = re.compile(r"^joint battle (\d+): started on the battle server")
BATTLE_LOST = re.compile(r"^joint battle (\d+): lost")
TOO_LATE = re.compile(r"^joint battle (\d+): (\d+):(.*?) accepted too late")
REFUSED = re.compile(r"^joint battle: refused - (.*)$")
RUNS = re.compile(r"^player (\d+):(\S+) runs CoopWorld build (\d+)(.*)$")
HELD = re.compile(r"^world held by player (\d+) \(([^)]+)\): (.*)$")
CONNECTED = re.compile(r"^net: player (\S+) (connected again|connected), multiplayer name '(.*)'")
LEFT = re.compile(r"^net: player (\S+) left")
NET_LOST = re.compile(r"^net: lost (\S+);")
NET_ERROR = re.compile(r"^net: (\S+) error (.*)$")
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
    def __init__(self, events, trace):
        self.events = events
        self.start, self.end = events[0][0], events[-1][0]
        self.trace = [e for e in trace if self.start - 1 <= e[0] <= self.end + STATS_EVERY_S]
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


def analyze(events, trace, silence=30):
    """One session's report lines."""
    s = Session(events, trace)
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
        m = REFUSED.match(text)
        if m:
            s.note(t, "? ", f"совместный бой не начат: {m.group(1)}")
            continue
        if "Traceback" in text or "Exception" in text:
            s.note(t, "!!", "ошибка в мосте: " + text.splitlines()[-1][:200])

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
                                               int(sm.group(4)) if sm.group(4) else 0)
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

    episodes = []  # [slot, name, start, last t, longest, how it ended]
    open_ = {}
    for i, (t, _, _, slots) in enumerate(stats):
        for slot, (name, _, quiet) in slots.items():
            ep = open_.get(slot)
            if quiet:
                if ep is not None and ep[1] == name and quiet > ep[4]:
                    ep[3], ep[4] = t, quiet
                else:
                    if ep is not None:
                        ep[5] = "back"
                    open_[slot] = ep = [slot, name, t - quiet, t, quiet, None, slots[slot][1]]
                    episodes.append(ep)
            elif ep is not None:
                ep[5] = "back"
                del open_[slot]
        for slot in [k for k in open_ if k not in slots]:
            open_.pop(slot)[5] = "gone"
    for ep in open_.values():
        ep[5] = "end"

    for slot, name, begin, last, longest, ended, busy in episodes:
        if longest < silence:
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
        lost = next((t for t, text in events if begin <= t <= last + STATS_EVERY_S * 2
                     and NET_LOST.match(text) and cid and NET_LOST.match(text).group(1) == cid), None)
        after = [r for r in results.get(cid, []) if 0 <= begin - r <= AFTER_BATTLE_S]
        how = {"back": "вернулся", "gone": "ушёл из игры", "end": "так и не вернулся до конца лога"}[ended]
        if lost is not None:
            how = f"связь потеряна в {stamp(lost)}"
        text = f"игрок {name or s.who(cid)} молчал {span(longest)} ({how}){seen}"
        near = [f"{stamp(t)} {text_}" for t, text_ in events
                if abs(t - begin) <= STATS_EVERY_S and not STATS.match(text_) and not text_.startswith("world ")]
        if near:
            text += ". Рядом по времени: " + "; ".join(near)
        # a game that never came back after a battle is what this report is for; one that went
        # quiet at the end of the session may just have been closed
        came_back = ended == "back" and lost is None
        if after:
            text += f". Это через {span(begin - after[-1])} после результата боя"
        if after and not came_back:
            mark = "!!"
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
                                lost=None, late=[], missing=[])
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
                   and kind_of(e[4]) in (8, 9, 10, 11, 13, 21) and number(e[4], 2) == bid]
            line = []
            for e in got:
                line.append(f"{KINDS[kind_of(e[4])]}{detail(e[4])} {stamp(e[0])} ({state(e[3])})")
            out.append(f"    {name}: " + ("; ".join(line) if line else "ничего не получил"))
            result = next((e for e in got if kind_of(e[4]) == 8), None)
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
        return Path(buf.value) / "CoopWorld"
    except (AttributeError, OSError):
        return Path.home() / "Documents" / "CoopWorld"


def main(argv=None):
    ap = argparse.ArgumentParser(description="CoopWorld: a session's report from bridge.log and trace.log")
    ap.add_argument("folder", nargs="?", help="where the logs are (default: Documents\\CoopWorld)")
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
            return 0
        print(f"нет {bridge}")
        return 1
    events = read_bridge(bridge)
    if not events:
        print(f"{bridge} пуст")
        return 1
    trace = read_trace([folder / "trace.old.log", folder / "trace.log"], events[-1][0])
    chosen = sessions(events) if args.all else sessions(events)[-1:]
    lines = [f"CoopWorld: отчёт по {bridge} и trace.log"]
    for part in chosen:
        lines.append("")
        lines += analyze(part, trace, args.silence)
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
