"""Expand leading tabs (Python 2 semantics: tab stop 8) so Python 3 accepts the module system.

    python tools/fix_tabs.py src [more dirs or files]
"""
import re
import sys
from pathlib import Path

LEAD = re.compile(r"^[ \t]+", re.M)


def fix(path):
    raw = path.read_bytes()
    text = raw.decode("latin-1")
    out = LEAD.sub(lambda m: m.group(0).expandtabs(8), text.replace("\r\n", "\n"))
    if "\r\n" in text:
        out = out.replace("\n", "\r\n")
    if out != text:
        path.write_bytes(out.encode("latin-1"))
        return True
    return False


def main():
    changed = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        for f in ([p] if p.is_file() else sorted(p.rglob("*.py"))):
            changed += fix(f)
    print(f"fixed {changed} files")


if __name__ == "__main__":
    main()
