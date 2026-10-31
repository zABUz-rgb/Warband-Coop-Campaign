"""Russian translation of the CoopWorld module: Diplomacy, Freelancer and co-op on top of Native.

The game reads a module's texts from Modules/<module>/languages/<lang>/*.csv, lines "id|text".
Each text comes from the first of these that has its id:
  1. the russifier's Native (vendor/l10n_ru), the base for everything Native has;
  2. the Russian translation of Diplomacy (MRCMOD's, vendor/dplmc_ru_mrcmod), for what Diplomacy adds;
  3. lang/ru.csv (kept by hand, "file|id|text"), for the rest: Freelancer, co-op, and what neither has.
     Quick strings and dialog lines there are kept by their English: "quick_strings_en|English|text",
     "dialogs_en|English|text". "game_menus_over|id|text" replaces a text the base has: for one that
     Diplomacy rewrote while the base still tells the old story.
This tool finds every id the build has and none of them translates.

Quick strings and dialog lines are matched by their English text, not by id: their ids come from
the first characters of the text (quick strings) or from the dialog states with .1, .2 for repeats
(dialogs), so a text added by Diplomacy, Freelancer or co-op in front of another moves that one to a
new id, and the translation kept under the old id would show for another text. The English each
base translation was made for comes from the game's own Native (game/Modules/Native, compiled), the
module system 1.171 (Native's dialogs) and the compiled Diplomacy 1.174.

    python tools/make_ru.py --missing   list ids that still need a translation (with the English)
    python tools/make_ru.py             write game/Modules/Warband Coop Campaign/languages/ru
                                        and dist/ru_additions/*.csv for the player package
"""
import os
import re
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MODULE = ROOT / "game" / "Modules" / "Warband Coop Campaign"
# The base Russian for Native: the russifier (vendor/l10n_ru, plain text) when it is there. The game's
# own Native ru is marked up for declension (@Pd[...], @L[...]) that this edition shows as raw codes.
RUSSIFIER = ROOT / "vendor" / "l10n_ru"
NATIVE_RU = (RUSSIFIER / "Modules" / "Native" / "languages" / "ru"
             if (RUSSIFIER / "Modules" / "Native" / "languages" / "ru").exists()
             else ROOT / "game" / "Modules" / "Native" / "languages" / "ru")
DIPLOMACY_RU = ROOT / "vendor" / "dplmc_ru_mrcmod" / "ru"
NATIVE_COMPILED = ROOT / "game" / "Modules" / "Native"
NATIVE_MS = ROOT / "vendor" / "module_system_1171" / "Module_system 1.171"
DIPLOMACY_COMPILED = ROOT / "vendor" / "dplmc_1174" / "Diplomacy 1.174 prejudice patch" / "Compiled" / "Diplomacy 1.174"
BY_TEXT = ("quick_strings", "dialogs")  # matched by English text (see above)
OURS = ROOT / "lang" / "ru.csv"
OVER = "_over"  # lang/ru.csv: this row wins over the base translations
UNREACHABLE_MENUS = ("test_scene",)
FILES = ("game_menus", "dialogs", "quests", "parties", "quick_strings", "game_strings", "troops",
         "item_kinds", "party_templates", "factions", "info_pages", "skills")
ADDITIONS = ROOT / "dist" / "ru_additions"


def load_csv(path):
    out = {}
    if path.exists():
        for line in path.read_text("utf-8-sig").splitlines():
            if "|" in line:
                k, v = line.split("|", 1)
                out[k] = v
    return out


def dialog_ids(dialogs, convert_to_identifier):
    """{dialog id: English}: the compiler's create_auto_id2."""
    auto_ids = {}
    for d in dialogs:
        text = d[3]
        auto_id = "dlga_" + convert_to_identifier(d[1]) + ":" + convert_to_identifier(d[4])
        if auto_id in auto_ids and auto_ids[auto_id] != text:
            n = 1
            while f"{auto_id}.{n}" in auto_ids:
                n += 1
            auto_id = f"{auto_id}.{n}"
        auto_ids[auto_id] = text
    return auto_ids


DIALOGS_DUMP = r"""
import json, string, sys
string.replace = lambda s, a, b, *n: s.replace(a, b, *n)
string.lower = lambda s: s.lower()
string.strip = lambda s, *c: s.strip(*c)
string.find = lambda s, a, *r: s.find(a, *r)
sys.path.insert(0, ".")
code = open("module_dialogs.py", encoding="utf-8", errors="replace").read()
code = code.split("# CoopWorld merge hook")[0]  # Diplomacy's own lines, without CoopWorld's
scope = {}
exec(compile(code, "module_dialogs.py", "exec"), scope)
from process_common import convert_to_identifier
sys.path.insert(0, sys.argv[1])
from make_ru import dialog_ids
print(json.dumps(dialog_ids(scope["dialogs"], convert_to_identifier)))
"""


def source_dialogs(folder):
    """{dialog id: English} of a module system's own dialogs (run apart: its headers are its own)."""
    import json
    import subprocess
    import warnings
    r = subprocess.run([sys.executable, "-W", "ignore", "-c", DIALOGS_DUMP, str(ROOT / "tools")], cwd=folder,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        warnings.warn(f"dialogs of {folder}: {r.stderr[-300:]}")
        return {}
    return json.loads(r.stdout)


def compiled_quick_strings(folder):
    out = {}
    path = folder / "quick_strings.txt"
    if path.exists():
        for line in path.read_text("utf-8", "replace").splitlines()[1:]:
            if " " in line:
                k, v = line.split(" ", 1)
                out[k] = v.replace("_", " ")
    return out


def by_text(english, russian):
    """{English: Russian} of a base translation, through the English its ids had."""
    out = {}
    for k, ru in russian.items():
        en = english.get(k)
        if en is not None:
            out.setdefault(en, ru)
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
    from module_strings import strings
    from module_troops import troops
    from module_items import items
    from module_party_templates import party_templates
    from module_factions import factions
    from module_info_pages import info_pages
    from module_skills import skills
    from process_common import convert_to_identifier
    texts = {f: {} for f in FILES}
    for s in strings:
        texts["game_strings"][f"str_{s[0]}"] = s[1]
    for tr in troops:
        texts["troops"][f"trp_{tr[0]}"] = tr[1]
        texts["troops"][f"trp_{tr[0]}_pl"] = tr[2]
    for it in items:
        texts["item_kinds"][f"itm_{it[0]}"] = it[1][0][1] if isinstance(it[1], list) else it[1]
        texts["item_kinds"][f"itm_{it[0]}_pl"] = (it[1][0][1] if isinstance(it[1], list) else it[1]) + "s"
    for pt in party_templates:
        texts["party_templates"][f"pt_{pt[0]}"] = pt[1]
    for fac in factions:
        texts["factions"][f"fac_{fac[0]}"] = fac[1]
    for ip in info_pages:
        texts["info_pages"][f"ip_{ip[0]}"] = ip[1]
        texts["info_pages"][f"ip_{ip[0]}_text"] = ip[2]
    for sk in skills:
        texts["skills"][f"skl_{sk[0]}"] = sk[1]
        texts["skills"][f"skl_{sk[0]}_desc"] = sk[4]
    for m in game_menus:
        texts["game_menus"][f"menu_{m[0]}"] = m[2]
        shown = {}
        for opt in m[5]:
            texts["game_menus"].setdefault(f"mno_{opt[0]}", opt[2])
            if (not opt[2].startswith("{!}") and m[0] not in UNREACHABLE_MENUS
                    and shown.setdefault(opt[0], opt[2]) != opt[2]):
                print(f"menu {m[0]}: option {opt[0]} shares its id with another, so its translation too: "
                      f"{opt[2]} (give it its own id in src/dplmc_fix/game_menus.py)", file=sys.stderr)
    texts["dialogs"] = dialog_ids(dialogs, convert_to_identifier)
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


def missing(texts, bases, ours, matched):
    """(file, id, English) of texts no base translation has and lang/ru.csv does not translate yet."""
    out = []
    for f, items in texts.items():
        for k, en in items.items():
            if f in BY_TEXT:
                known = k in matched[f]
            else:
                known = any(k in b[f] for b in bases) or (f, k) in ours
            if not en or en.startswith("{!}") or known or internal(en):
                continue
            out.append((f, k, en))
    return out


def match_by_text(texts, native, diplomacy, ours, ours_en):
    """{file: {id: Russian}} for the files matched by English text: the russifier's Native first,
    then Diplomacy's translation, then lang/ru.csv (by English; old rows by id)."""
    english = {
        "quick_strings": (compiled_quick_strings(NATIVE_COMPILED), compiled_quick_strings(DIPLOMACY_COMPILED)),
        "dialogs": (source_dialogs(NATIVE_MS), source_dialogs(SRC)),
    }
    out = {}
    for f in BY_TEXT:
        native_en, diplomacy_en = english[f]
        bases = (by_text(native_en, native[f]), by_text(diplomacy_en, diplomacy[f]))
        out[f] = {}
        for k, en in texts[f].items():
            ru = next((b[en] for b in bases if en in b), None)
            if ru is None:
                ru = ours_en[f].get(en, ours.get((f, k)))
            if ru is not None:
                out[f][k] = ru
    return out


def main():
    ours = {}
    over = {}
    ours_en = {f: {} for f in BY_TEXT}
    if OURS.exists():
        for line in OURS.read_text("utf-8-sig").splitlines():
            if line.count("|") >= 2 and not line.startswith("#"):
                f, k, v = line.split("|", 2)
                if f.endswith("_en") and f[:-3] in BY_TEXT:
                    ours_en[f[:-3]][k] = v
                elif f.endswith(OVER):
                    over[(f[:-len(OVER)], k)] = v
                else:
                    ours[(f, k)] = v
    native = {f: load_csv(NATIVE_RU / f"{f}.csv") for f in FILES}
    diplomacy = {f: load_csv(DIPLOMACY_RU / f"{f}.csv") for f in FILES}
    texts = module_texts()
    matched = match_by_text(texts, native, diplomacy, ours, ours_en)
    gaps = missing(texts, (native, diplomacy), ours, matched)
    if "--missing" in sys.argv:
        for f, k, en in gaps:
            print(f"{f}|{k}|{en}")
        print(f"# {len(gaps)} texts without Russian", file=sys.stderr)
        return
    if gaps:
        for f, k, en in gaps:
            print(f"untranslated: {f}|{k}|{en}", file=sys.stderr)
    unused = [(f, k) for f, k in (*ours, *over) if k not in texts.get(f, {})]
    unused += [(f + "_en", en) for f in BY_TEXT for en in ours_en[f] if en not in set(texts[f].values())]
    for f, k in unused:
        print(f"lang/ru.csv: {f}|{k} is not in the build (renamed or removed?)", file=sys.stderr)
    target = MODULE / "languages" / "ru"
    target.mkdir(parents=True, exist_ok=True)
    ADDITIONS.mkdir(parents=True, exist_ok=True)
    names = sorted({p.name for p in NATIVE_RU.glob("*.csv")} | {p.name for p in DIPLOMACY_RU.glob("*.csv")})
    for name in names:
        f = name[:-4]
        if f in BY_TEXT:
            lines = "".join(f"\r\n{k}|{v}" for k, v in matched[f].items())
            (target / name).write_text("\ufeff" + lines.lstrip("\r\n") + "\r\n", "utf-8", newline="")
            (ADDITIONS / name).write_text(lines.lstrip("\r\n") + "\r\n", "utf-8", newline="")
            continue
        path = NATIVE_RU / name
        base_ids = load_csv(path)
        # the russifier's Native wins, then Diplomacy's translation fills its own texts, then ours
        add = [(k, v) for k, v in load_csv(DIPLOMACY_RU / name).items()
               if k not in base_ids and (k in texts.get(f, {}) or f not in texts)]
        known = base_ids.keys() | {k for k, _ in add}
        add += [(k, v) for (ff, k), v in sorted(ours.items())
                if ff == f and k in texts.get(f, {}) and k not in known]
        replaced = {k: v for (ff, k), v in over.items() if ff == f and k in texts.get(f, {})}
        add = [(k, v) for k, v in add if k not in replaced] + sorted(replaced.items())
        base = path.read_text("utf-8-sig").rstrip("\r\n") if path.exists() else ""
        base = "\n".join(line for line in base.split("\n") if line.split("|", 1)[0] not in replaced)
        lines = "".join(f"\r\n{k}|{v}" for k, v in add)
        (target / name).write_text("﻿" + (base + lines).lstrip("\r\n") + "\r\n", "utf-8", newline="")
        if add:
            (ADDITIONS / name).write_text(lines.lstrip("\r\n") + "\r\n", "utf-8", newline="")
    print(f"languages/ru written from {NATIVE_RU.relative_to(ROOT)} and {DIPLOMACY_RU.relative_to(ROOT)}: CoopWorld fills what they lack; "
          f"{len(gaps)} untranslated, {len(unused)} unused")


if __name__ == "__main__":
    main()
