"""One-off port of the Freelancer 1.51 modmerger source into src/freelancer/ (Python 3).

Keeps each file's data part (everything before the ModMerger glue), expands tabs and
points constants at freelancer.constants. The merge functions are written by hand.

    python tools/port_freelancer.py <vendor freelancer dir> <src/freelancer>
"""
import re
import sys
from pathlib import Path

FILES = ["scripts", "game_menus", "dialogs", "simple_triggers", "triggers",
         "mission_templates", "presentations", "quests", "meshes"]
CUT = re.compile(r"^(from util_\w+ import|# Used by modmerger|def modmerge)", re.M)


def port(text):
    text = text.replace("\r\n", "\n")
    m = CUT.search(text)
    if m:
        text = text[:m.start()]
    text = re.sub(r"^[ \t]+", lambda m: m.group(0).expandtabs(8), text, flags=re.M)
    text = text.replace("from module_constants import *\nfrom module_constants import *\n",
                        "from module_constants import *\n")
    text = text.replace("from module_constants import *\n",
                        "from module_constants import *\nfrom freelancer.constants import *\n", 1)
    # needed by the menu blocks
    text = text.replace("# -*- coding: cp1254 -*-\n", "")
    return text.rstrip() + "\n"


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    for name in FILES:
        text = (src / f"freelancer_{name}.py").read_text("latin-1")
        out = port(text)
        if "freelancer.constants" not in out:
            out = out.replace("\n\n", "\nfrom freelancer.constants import *\n\n", 1)
        (dst / f"{name}.py").write_text(out, "utf-8")
        print("ported", name)


if __name__ == "__main__":
    main()
