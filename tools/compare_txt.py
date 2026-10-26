"""Compare compiled module .txt files with a reference module (e.g. the shipped Native).

    python tools/compare_txt.py <built_module_dir> <reference_module_dir>

Whitespace runs are normalised; numbers that differ only in float formatting count as equal.
"""
import re
import sys
from pathlib import Path

TOKEN = re.compile(r"\S+")


def same_token(a, b):
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) < 1e-5
    except ValueError:
        return False


def compare(built, ref):
    ta, tb = TOKEN.findall(built), TOKEN.findall(ref)
    if len(ta) != len(tb):
        return f"token count {len(ta)} vs {len(tb)}"
    for i, (a, b) in enumerate(zip(ta, tb)):
        if not same_token(a, b):
            ctx = " ".join(ta[max(0, i - 4):i + 4])
            return f"token {i}: {a!r} vs {b!r} near: {ctx}"
    return None


def main():
    built_dir, ref_dir = Path(sys.argv[1]), Path(sys.argv[2])
    skip = {"variables.txt", "variable_uses.txt", "tag_uses.txt"}
    ok = bad = 0
    for ref in sorted(ref_dir.glob("*.txt")):
        if ref.name in skip:
            continue
        built = built_dir / ref.name
        if not built.exists():
            continue
        diff = compare(built.read_text("latin-1"), ref.read_text("latin-1"))
        if diff:
            bad += 1
            print(f"DIFF {ref.name}: {diff}")
        else:
            ok += 1
    print(f"same: {ok}, different: {bad}")


if __name__ == "__main__":
    main()
