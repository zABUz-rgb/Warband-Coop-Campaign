"""Diplomacy's own module data: its textures, and the scenes it changed from Native.

They come from the compiled Diplomacy 1.174 in vendor/ (a mod's files, never in git). build.py puts
them into the test copy's module, make_package.py into the packages (the installer lays them over
the player's copy of Native, like the compiled files).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPILED = ROOT / "vendor" / "dplmc_1174" / "Diplomacy 1.174 prejudice patch" / "Compiled" / "Diplomacy 1.174"
NATIVE = ROOT / "game" / "Modules" / "Native"


def assets():
    """[(source file, path inside the module)]; empty without the Diplomacy files in vendor/."""
    if not COMPILED.exists():
        return []
    out = [(f, f"Textures/{f.name}") for f in sorted((COMPILED / "Textures").glob("*.dds"))]
    for f in sorted((COMPILED / "SceneObj").glob("*.sco")):
        native = NATIVE / "SceneObj" / f.name
        if not native.exists() or native.read_bytes() != f.read_bytes():
            out.append((f, f"SceneObj/{f.name}"))
    return out
