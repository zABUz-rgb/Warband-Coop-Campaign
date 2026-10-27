"""Build the CoopWorld package for players: dist/CoopWorld-<date>.zip

It holds only what CoopWorld adds: the compiled module files (*.txt), the bridge and an installer.
No game files: the installer copies each player's own Modules/Native to Modules/CoopWorld and puts
the compiled files over it.

    python tools/make_package.py
"""
import datetime
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "game" / "Modules" / "CoopWorld"
BUILD_ONLY = {"variables.txt", "variable_uses.txt", "tag_uses.txt"}  # compiler state; quick_strings.txt is read by the game

INSTALL_PS1 = r'''# CoopWorld installer: run it with the path of your Mount & Blade Warband folder.
#   powershell -ExecutionPolicy Bypass -File install.ps1 "D:\Games\Mount and Blade - Warband"
param([Parameter(Mandatory=$true)][string]$Warband)
$ErrorActionPreference = "Stop"
$native = Join-Path $Warband "Modules\Native"
$target = Join-Path $Warband "Modules\CoopWorld"
if (-not (Test-Path (Join-Path $Warband "mb_warband.exe"))) { throw "mb_warband.exe not found in $Warband" }
if (-not (Test-Path $native)) { throw "Modules\Native not found in $Warband" }
if (Test-Path $target) {
  $backup = "$target.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")
  Rename-Item $target $backup
  Write-Host "Old CoopWorld kept as $backup"
}
Copy-Item $native $target -Recurse
Copy-Item (Join-Path $PSScriptRoot "CoopWorld\*") $target -Force
Write-Host "CoopWorld installed in $target. Start Warband and choose the CoopWorld module."
'''

JOIN_BAT = r'''@echo off
rem Join a CoopWorld game. Usage: join.bat HOST_ADDRESS KEY
rem Fetches the host's save as sg90.sav (load it in the game), then keeps the link open.
if "%~2"=="" (echo Usage: join.bat HOST_ADDRESS KEY & pause & exit /b 1)
python -I "%~dp0coop_bridge.py" join %1 --key %2 --fetch-save
pause
'''

HOST_BAT = r'''@echo off
rem Host a CoopWorld game. Usage: host.bat KEY   (without a key only this PC can play)
python -I "%~dp0coop_bridge.py" host --key %1
pause
'''

README = '''CoopWorld - co-op campaign for Mount & Blade: Warband 1.174
=============================================================

Needs: Warband 1.174 (Steam or GOG) and Python 3 (python.org) on every PC.
Install: powershell -ExecutionPolicy Bypass -File install.ps1 "<your Warband folder>"

The PCs must reach each other: the same LAN, or a virtual LAN such as Radmin VPN or ZeroTier
(both free). The host's address is then the one that program shows (e.g. 26.x.x.x).
The host's PC must let Python accept connections on TCP port 7350 (Windows asks once).

HOST (runs the world):
  1. host.bat SECRET          - start the bridge, choose any SECRET and tell it your friends
  2. Start Warband twice, both with the CoopWorld module, in windowed mode.
     Window 1 = the world server: load your campaign, Camp - "run this game as the WORLD SERVER".
     Window 2 = your own game.
  3. For each joining player: on the server, Camp - "hold the world for a joining client",
     then save the game (Esc - Save).
  4. Your own game (window 2): load that save, Camp - "run this game as a CLIENT".

FRIEND:
  1. join.bat HOST_ADDRESS SECRET  - fetches the host's newest save as sg90.sav, keeps the link
  2. Start Warband with CoopWorld, load that save, Camp - "run this game as a CLIENT".
     The host's world runs on as soon as you joined.

Stopping: Camp - "CoopWorld: stop co-op" in your game, then close the bridge window.
'''


def main():
    if not (MODULE / "scripts.txt").exists():
        raise SystemExit("build the module first: python build.py")
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    name = f"CoopWorld-{datetime.date.today():%Y%m%d}"
    out = out_dir / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(MODULE.glob("*.txt")):
            if f.name not in BUILD_ONLY:
                z.write(f, f"{name}/CoopWorld/{f.name}")
        z.write(ROOT / "tools" / "coop_bridge.py", f"{name}/coop_bridge.py")
        z.writestr(f"{name}/install.ps1", INSTALL_PS1)
        z.writestr(f"{name}/join.bat", JOIN_BAT)
        z.writestr(f"{name}/host.bat", HOST_BAT)
        z.writestr(f"{name}/README.txt", README)
    print(f"{out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
