"""Simplified Chinese translation of the CoopWorld module (languages/cns), the way make_ru.py makes the Russian.

Each text comes from the first of these that has it:
  1. the game's own Native Chinese (game/Modules/Native/languages/cns), the base for everything Native has;
  2. a Chinese translation of Diplomacy when one is put in vendor/dplmc_zh/cns (the same csv files);
  3. lang/zh.csv (kept by hand, "file|id|text", like lang/ru.csv), for the rest: Freelancer, co-op, and the
     Diplomacy texts no translation has. Quick strings and dialog lines there are kept by their English:
     "quick_strings_en|English|text", "dialogs_en|English|text".
Names of troops, items, parties, party templates and factions that Native has under another id (a copied
troop, an item kept under a new id) take Native's Chinese name by their English.

The game breaks a line only at a space, so Native's Chinese has a space after every character; lang/zh.csv
is written without them and gets them here.

    python tools/make_zh.py --missing   list texts that still need Chinese (ours first, then Diplomacy's)
    python tools/make_zh.py             write game/Modules/Warband Coop Campaign/languages/cns
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_ru as ru  # noqa: E402

ROOT = ru.ROOT
LANG = "cns"
NATIVE_ZH = ROOT / "game" / "Modules" / "Native" / "languages" / LANG
DIPLOMACY_ZH = ROOT / "vendor" / "dplmc_zh" / LANG
OURS = ROOT / "lang" / "zh.csv"
NAMED = {"troops": ("troops.txt", "trp_", True), "item_kinds": ("item_kinds1.txt", "itm_", True),
         "parties": ("parties.txt", "p_", False), "party_templates": ("party_templates.txt", "pt_", False),
         "factions": ("factions.txt", "fac_", False)}
CJK = re.compile(r"([⺀-〿㐀-䶿一-鿿豈-﫿＀-￯—…])(?! )")


def spaced(text):
    """A space after each Chinese character and full-width mark, as Native's Chinese has (line breaks)."""
    return CJK.sub(r"\1 ", text)


def lower_ids(texts):
    """The compiler writes ids in lower case (quick strings keep theirs)."""
    return {f: (items if f == "quick_strings" else {k.lower(): v for k, v in items.items()}) for f, items in texts.items()}


def compiled_names(folder, file, prefix, plural):
    """{id: English name} of a compiled module's troops, items, parties..."""
    out = {}
    path = folder / file
    if not path.exists():
        return out
    for line in path.read_text("utf-8", "replace").splitlines():
        tokens = line.split()
        at = next((i for i, t in enumerate(tokens[:6]) if t.startswith(prefix)), None)
        if at is None or at + 1 >= len(tokens):
            continue
        k = tokens[at]
        out[k] = tokens[at + 1].replace("_", " ")
        if plural and at + 2 < len(tokens):
            out[k + "_pl"] = tokens[at + 2].replace("_", " ")
    return out


def diplomacy_ids():
    """Every id compiled Diplomacy has (menus, options, strings, troops...): its texts, not CoopWorld's."""
    ids = set()
    for path in ru.DIPLOMACY_COMPILED.glob("*.txt"):
        if path.name not in ("quick_strings.txt", "conversation.txt"):
            ids.update(t.lower() for t in re.findall(r"\b(?:menu|mno|str|trp|itm|p|pt|fac|qst|ip|skl)_\w+",
                                                         path.read_text("utf-8", "replace")))
    return ids


def load_ours():
    ours, ours_en = {}, {f: {} for f in ru.BY_TEXT}
    if OURS.exists():
        for line in OURS.read_text("utf-8-sig").splitlines():
            if line.count("|") >= 2 and not line.startswith("#"):
                f, k, v = line.split("|", 2)
                v = spaced(v)
                if f.endswith("_en") and f[:-3] in ru.BY_TEXT:
                    ours_en[f[:-3]][k] = v
                else:
                    ours[(f, k.lower())] = v
    return ours, ours_en


def main():
    ours, ours_en = load_ours()
    native = {f: ru.load_csv(NATIVE_ZH / f"{f}.csv") for f in ru.FILES}
    diplomacy = {f: ru.load_csv(DIPLOMACY_ZH / f"{f}.csv") for f in ru.FILES}
    texts = lower_ids(ru.module_texts())
    english = {
        "quick_strings": (ru.compiled_quick_strings(ru.NATIVE_COMPILED), ru.compiled_quick_strings(ru.DIPLOMACY_COMPILED)),
        "dialogs": (ru.source_dialogs(ru.NATIVE_MS), ru.source_dialogs(ru.SRC)),
    }
    matched = {}
    for f in ru.BY_TEXT:
        native_en, diplomacy_en = english[f]
        bases = (ru.by_text(native_en, native[f]), ru.by_text(diplomacy_en, diplomacy[f]))
        matched[f] = {}
        for k, en in texts[f].items():
            zh = next((b[en] for b in bases if en in b), None)
            if zh is None:
                zh = ours_en[f].get(en, ours.get((f, k)))
            if zh is not None:
                matched[f][k] = zh
    # a name Native has under another id
    named = {}
    for f, (file, prefix, plural) in NAMED.items():
        by_name = ru.by_text(compiled_names(ru.NATIVE_COMPILED, file, prefix, plural), native[f])
        named[f] = {k: by_name[en] for k, en in texts[f].items()
                    if k not in native[f] and (f, k) not in ours and en in by_name}
    known = {f: {**diplomacy[f], **named.get(f, {})} for f in ru.FILES}
    gaps = ru.missing(texts, (native, known), ours, matched)
    if "--missing" in sys.argv:
        dip_en = {f: set(english[f][1].values()) for f in ru.BY_TEXT}
        dip_ids = diplomacy_ids()
        theirs = lambda f, k, en: en in dip_en[f] if f in ru.BY_TEXT else re.sub(r"_(pl|text|desc)$", "", k) in dip_ids
        mine = [g for g in gaps if not theirs(*g)]
        for f, k, en in mine + [g for g in gaps if theirs(*g)]:
            print(f"{f}|{k}|{en}")
        print(f"# {len(gaps)} texts without Chinese: {len(mine)} CoopWorld's and Freelancer's, "
              f"{len(gaps) - len(mine)} Diplomacy's", file=sys.stderr)
        return
    unused = [(f, k) for f, k in ours if k not in texts.get(f, {})]
    unused += [(f + "_en", en) for f in ru.BY_TEXT for en in ours_en[f] if en not in set(texts[f].values())]
    for f, k in unused:
        print(f"lang/zh.csv: {f}|{k} is not in the build (renamed or removed?)", file=sys.stderr)
    for f, k in ru.stale(texts, ours, {}):
        print(f"lang/zh.csv: {f}|{k}: its English has other {{reg}}/{{s}} slots now (changed? translate again)", file=sys.stderr)
    target = ru.MODULE / "languages" / LANG
    target.mkdir(parents=True, exist_ok=True)
    names = sorted({p.name for p in NATIVE_ZH.glob("*.csv")} | {p.name for p in DIPLOMACY_ZH.glob("*.csv")})
    for name in names:
        f = name[:-4]
        if f in ru.BY_TEXT:
            lines = "".join(f"\r\n{k}|{v}" for k, v in matched[f].items())
            (target / name).write_text("﻿" + lines.lstrip("\r\n") + "\r\n", "utf-8", newline="")
            continue
        path = NATIVE_ZH / name
        base_ids = ru.load_csv(path)
        add = [(k, v) for k, v in ru.load_csv(DIPLOMACY_ZH / name).items()
               if k not in base_ids and (k in texts.get(f, {}) or f not in texts)]
        have = base_ids.keys() | {k for k, _ in add}
        add += [(k, v) for (ff, k), v in sorted(ours.items()) if ff == f and k in texts.get(f, {}) and k not in have]
        have |= {k for k, _ in add}
        add += [(k, v) for k, v in sorted(named.get(f, {}).items()) if k not in have]
        base = path.read_text("utf-8-sig").rstrip("\r\n") if path.exists() else ""
        lines = "".join(f"\r\n{k}|{v}" for k, v in add)
        (target / name).write_text("﻿" + (base.replace("\r\n", "\n").replace("\n", "\r\n") + lines).lstrip("\r\n")
                                   + "\r\n", "utf-8", newline="")
    print(f"languages/{LANG} written from {NATIVE_ZH.relative_to(ROOT)}"
          + (f" and {DIPLOMACY_ZH.relative_to(ROOT)}" if DIPLOMACY_ZH.exists() else "")
          + f": CoopWorld fills what it lacks; {len(gaps)} untranslated (shown in English), {len(unused)} unused")


if __name__ == "__main__":
    main()
