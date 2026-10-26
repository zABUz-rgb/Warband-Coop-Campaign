"""Append the coop_mods merge hook to the end of the Native module_*.py files (idempotent).

    python tools/add_hooks.py src
"""
import sys
from pathlib import Path

HOOKS = {
    "module_scripts.py": 'coop_mods.merge("scripts", scripts)',
    "module_game_menus.py": 'coop_mods.merge("game_menus", game_menus)',
    "module_dialogs.py": 'coop_mods.merge("dialogs", dialogs)',
    "module_simple_triggers.py": 'coop_mods.merge("simple_triggers", simple_triggers)',
    "module_triggers.py": 'coop_mods.merge("triggers", triggers)',
    "module_mission_templates.py": 'coop_mods.merge("mission_templates", mission_templates, '
                                   'common_battle_mission_start=common_battle_mission_start)',
    "module_presentations.py": 'coop_mods.merge("presentations", presentations)',
    "module_quests.py": 'coop_mods.merge("quests", quests)',
    "module_meshes.py": 'coop_mods.merge("meshes", meshes)',
    "module_parties.py": 'coop_mods.merge("parties", parties)',
    "module_party_templates.py": 'coop_mods.merge("party_templates", party_templates)',
}
MARK = "# CoopWorld merge hook"


def main():
    src = Path(sys.argv[1])
    for name, call in HOOKS.items():
        p = src / name
        text = p.read_text("latin-1")
        if MARK in text:
            continue
        nl = "\r\n" if "\r\n" in text else "\n"
        text = text.rstrip() + nl + nl + MARK + nl + "import coop_mods" + nl + call + nl
        p.write_text(text, "latin-1", newline="")
        print("hooked", name)


if __name__ == "__main__":
    main()
