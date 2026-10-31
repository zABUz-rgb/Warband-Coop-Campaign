"""Build CoopWorld: runs the module system's process_*.py steps in order (Python 3).

    python build.py
    python build.py --trail      a debug build: the game tells the bridge all it does (src/trail)
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
RUNNER = ROOT / "tools" / "run_step.py"

STEPS = [
    "process_init", "process_global_variables", "process_strings", "process_skills",
    "process_music", "process_animations", "process_meshes", "process_sounds",
    "process_skins", "process_map_icons", "process_factions", "process_items",
    "process_scenes", "process_troops", "process_particle_sys", "process_scene_props",
    "process_tableau_materials", "process_presentations", "process_party_tmps",
    "process_parties", "process_quests", "process_info_pages", "process_scripts",
    "process_mission_tmps", "process_game_menus", "process_simple_triggers",
    "process_dialogs", "process_global_variables_unused", "process_postfx",
]


def main():
    trail = "--trail" in sys.argv
    plain = {k: v for k, v in os.environ.items() if k != "COOP_TRAIL"}
    plain["PYTHONDONTWRITEBYTECODE"] = "1"
    env = dict(plain, COOP_TRAIL="1") if trail else plain
    for step in STEPS:
        r = subprocess.run([sys.executable, "-W", "ignore", str(RUNNER), step], cwd=SRC, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout + r.stderr).strip()
        if out:
            print(out)
        # the compiler only prints errors (unknown ids, unassigned locals) and keeps going
        if r.returncode != 0 or "Traceback" in out or "error" in out.lower():
            print(f"BUILD FAILED at {step}")
            sys.exit(1)
    # Diplomacy's textures and changed scenes go with the compiled files
    sys.path.insert(0, str(ROOT / "tools"))
    from dplmc_assets import assets
    sys.path.insert(0, str(SRC))
    from module_info import export_dir
    for source, rel in assets():
        dest = Path(export_dir) / rel
        if not dest.exists() or dest.read_bytes() != source.read_bytes():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(source.read_bytes())
    # mistakes the compiler lets pass (empty "@" strings, unbalanced try blocks, scripts that end
    # their caller, globals never set): see tools/check_module.py; talks and menus with no way out,
    # scripts called wrong, the bridge and the game disagreeing: see tools/check_flow.py
    # (check_flow judges what the mods did to the base game, so the trail's marks stay out of it)
    for check, its_env in (("check_module", env), ("check_flow", plain)):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / f"{check}.py")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=its_env)
        problems = [l for l in r.stdout.splitlines() if not l.startswith("note:")]
        print("\n".join(problems))
        if r.returncode != 0:
            print(f"BUILD FAILED at {check}")
            sys.exit(1)
    names = Path(export_dir) / "trail_names.json"
    if trail:
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "trail_names.py"), str(names)], env=env)
        if r.returncode != 0:
            print("BUILD FAILED at trail_names")
            sys.exit(1)
    elif names.exists():
        names.unlink()
    print("BUILD OK")


if __name__ == "__main__":
    main()
