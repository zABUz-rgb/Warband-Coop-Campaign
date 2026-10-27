"""Russian translation of what CoopWorld adds to Native (Freelancer, co-op), on top of Native's own.

The game reads a module's texts from Modules/<module>/languages/<lang>/*.csv, lines "id|text".
Native ships languages/ru; this tool finds every id the CoopWorld build adds that Native's ru files
lack, and takes their Russian text from lang/ru.csv (kept by hand, "file|id|text").

    python tools/make_ru.py --missing   list ids that still need a translation (with the English)
    python tools/make_ru.py             write game/Modules/CoopWorld/languages/ru (Native's + ours)
                                        and dist/ru_additions/*.csv for the player package
"""
import os
import re
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MODULE = ROOT / "game" / "Modules" / "CoopWorld"
# The base Russian for Native: the russifier (vendor/l10n_ru, plain text) when it is there. The game's
# own Native ru is marked up for declension (@Pd[...], @L[...]) that this edition shows as raw codes.
RUSSIFIER = ROOT / "vendor" / "l10n_ru"
NATIVE_RU = (RUSSIFIER / "Modules" / "Native" / "languages" / "ru"
             if (RUSSIFIER / "Modules" / "Native" / "languages" / "ru").exists()
             else ROOT / "game" / "Modules" / "Native" / "languages" / "ru")
OURS = ROOT / "lang" / "ru.csv"
ADDITIONS = ROOT / "dist" / "ru_additions"


def load_csv(path):
    out = {}
    if path.exists():
        for line in path.read_text("utf-8-sig").splitlines():
            if "|" in line:
                k, v = line.split("|", 1)
                out[k] = v
    return out


def module_texts():
    """file -> {id: English text} for the texts the game looks up in languages/<lang>."""
    string.replace = lambda s, a, b, *n: s.replace(a, b, *n)
    string.lower = lambda s: s.lower()
    string.strip = lambda s, *c: s.strip(*c)
    string.find = lambda s, a, *r: s.find(a, *r)
    sys.path.insert(0, str(SRC))
    os.chdir(SRC)
    from module_game_menus import game_menus
    from module_dialogs import dialogs
    from module_quests import quests
    from module_parties import parties
    from process_common import convert_to_identifier
    texts = {"game_menus": {}, "dialogs": {}, "quests": {}, "parties": {}, "quick_strings": {}}
    for m in game_menus:
        texts["game_menus"][f"menu_{m[0]}"] = m[2]
        for opt in m[5]:
            texts["game_menus"].setdefault(f"mno_{opt[0]}", opt[2])
    auto_ids = {}
    for d in dialogs:  # the compiler's create_auto_id2
        text = d[3]
        auto_id = "dlga_" + convert_to_identifier(d[1]) + ":" + convert_to_identifier(d[4])
        if auto_id in auto_ids and auto_ids[auto_id] != text:
            n = 1
            while f"{auto_id}.{n}" in auto_ids:
                n += 1
            auto_id = f"{auto_id}.{n}"
        auto_ids[auto_id] = text
        texts["dialogs"][auto_id] = text
    for q in quests:
        texts["quests"][f"qst_{q[0]}"] = q[1]
        texts["quests"][f"qst_{q[0]}_text"] = q[3]
    for p in parties:
        texts["parties"][f"p_{p[0]}"] = p[1]
    for line in (MODULE / "quick_strings.txt").read_text("latin-1").splitlines()[1:]:
        if " " in line:
            k, v = line.split(" ", 1)
            texts["quick_strings"][k] = v.replace("_", " ")
    return texts


def internal(text):
    """Not for players: the co-op link's URLs and number lists ("http://...", "{s12},{reg21}", "0").
    They must stay exactly as they are, so they are never translated."""
    return "http://" in text or ("&" in text and "=" in text) or (" " not in text and not any(c.isalpha() for c in re.sub(r"\{[^}]*\}", "", text)))


def missing(texts, native, ours):
    """(file, id, English) of texts Native's ru lacks and lang/ru.csv does not translate yet."""
    out = []
    for f, items in texts.items():
        for k, en in items.items():
            if not en or en.startswith("{!}") or k in native[f] or (f, k) in ours or internal(en):
                continue
            out.append((f, k, en))
    return out


def main():
    ours = {}
    if OURS.exists():
        for line in OURS.read_text("utf-8-sig").splitlines():
            if line.count("|") >= 2 and not line.startswith("#"):
                f, k, v = line.split("|", 2)
                ours[(f, k)] = v
    native = {f: load_csv(NATIVE_RU / f"{f}.csv") for f in ("game_menus", "dialogs", "quests", "parties", "quick_strings")}
    texts = module_texts()
    gaps = missing(texts, native, ours)
    if "--missing" in sys.argv:
        for f, k, en in gaps:
            print(f"{f}|{k}|{en}")
        print(f"# {len(gaps)} texts without Russian", file=sys.stderr)
        return
    if gaps:
        for f, k, en in gaps:
            print(f"untranslated: {f}|{k}|{en}", file=sys.stderr)
    unused = [(f, k) for f, k in ours if k not in texts.get(f, {})]
    for f, k in unused:
        print(f"lang/ru.csv: {f}|{k} is not in the build (renamed or removed?)", file=sys.stderr)
    target = MODULE / "languages" / "ru"
    target.mkdir(parents=True, exist_ok=True)
    ADDITIONS.mkdir(parents=True, exist_ok=True)
    for path in sorted(NATIVE_RU.glob("*.csv")):
        f = path.stem
        base_ids = load_csv(path)
        # the base's own translation wins: ours only fills what it lacks
        add = [(k, v) for (ff, k), v in sorted(ours.items())
               if ff == f and k in texts.get(f, {}) and k not in base_ids]
        base = path.read_text("utf-8-sig").rstrip("\r\n")
        lines = "".join(f"\r\n{k}|{v}" for k, v in add)
        (target / path.name).write_text("﻿" + base + lines + "\r\n", "utf-8", newline="")
        if add:
            (ADDITIONS / path.name).write_text(lines.lstrip("\r\n") + "\r\n", "utf-8", newline="")
    print(f"languages/ru written from {NATIVE_RU.relative_to(ROOT)}: CoopWorld fills what it lacks; "
          f"{len(gaps)} untranslated, {len(unused)} unused")


if __name__ == "__main__":
    main()
