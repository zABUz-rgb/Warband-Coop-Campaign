"""Build the CoopWorld packages for players: dist/CoopWorld-<date>.zip (English) and
dist/CoopWorld-ru-<date>.zip (Russian: game texts, installer and instructions).

They hold only what CoopWorld adds: the compiled module files (*.txt), the bridge and an installer.
No game files: the installer copies each player's own Modules/Native to Modules/CoopWorld and puts
the compiled files over it. The Russian one also adds CoopWorld's Russian texts
(tools/make_ru.py) to the copy of Native's languages/ru.

    python tools/make_ru.py && python tools/make_package.py
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

INSTALL_RU_PS1 = r'''# Установщик CoopWorld (русская версия). Запуск с путём к папке Mount & Blade Warband:
#   powershell -ExecutionPolicy Bypass -File install.ps1 "D:\Games\Mount and Blade - Warband"
param([Parameter(Mandatory=$true)][string]$Warband)
$ErrorActionPreference = "Stop"
$native = Join-Path $Warband "Modules\Native"
$target = Join-Path $Warband "Modules\CoopWorld"
if (-not (Test-Path (Join-Path $Warband "mb_warband.exe"))) { throw "В папке $Warband нет mb_warband.exe" }
if (-not (Test-Path $native)) { throw "В папке $Warband нет Modules\Native" }
if (Test-Path $target) {
  $backup = "$target.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")
  Rename-Item $target $backup
  Write-Host "Прежний CoopWorld сохранён как $backup"
}
Copy-Item $native $target -Recurse
Copy-Item (Join-Path $PSScriptRoot "CoopWorld\*") $target -Force
# русские тексты CoopWorld поверх русских текстов Native
$ru = Join-Path $target "languages\ru"
New-Item -ItemType Directory -Force $ru | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
foreach ($f in Get-ChildItem (Join-Path $PSScriptRoot "ru_additions") -Filter *.csv) {
  $dest = Join-Path $ru $f.Name
  $text = [IO.File]::ReadAllText($f.FullName, $utf8)
  if (Test-Path $dest) { [IO.File]::AppendAllText($dest, "`r`n" + $text, $utf8) }
  else { [IO.File]::WriteAllText($dest, [char]0xFEFF + $text, $utf8) }
}
# чтобы русский можно было выбрать в лаунчере: у некоторых изданий (GOG) нет languages\ru
$uiRu = Join-Path $Warband "languages\ru"
if (-not (Test-Path $uiRu)) {
  Copy-Item (Join-Path $Warband "languages\en") $uiRu -Recurse
  Write-Host "Добавлена папка languages\ru (интерфейс движка останется английским, тексты игры будут русскими)"
}
Write-Host "CoopWorld установлен в $target."
Write-Host "Запустите Warband, в лаунчере выберите модуль CoopWorld, а в Configure - Game - Language выберите ru."
'''

JOIN_RU_BAT = r'''@echo off
chcp 65001 >nul
rem Подключение к игре CoopWorld: join.bat АДРЕС_ХОСТА ПАРОЛЬ
rem Скачивает свежее сохранение хоста как sg90.sav (загрузите его в игре) и держит связь.
if "%~2"=="" (echo Использование: join.bat АДРЕС_ХОСТА ПАРОЛЬ & pause & exit /b 1)
python -I "%~dp0coop_bridge.py" join %1 --key %2 --fetch-save
pause
'''

HOST_RU_BAT = r'''@echo off
chcp 65001 >nul
rem Запуск игры CoopWorld у хоста: host.bat ПАРОЛЬ   (без пароля играть можно только на этом ПК)
python -I "%~dp0coop_bridge.py" host --key %1
pause
'''

README_RU = '''CoopWorld - кооперативная кампания для Mount & Blade: Warband 1.174
====================================================================

ЧТО НУЖНО
  - Warband 1.174 (Steam или GOG) и Python 3 (python.org, при установке отметьте "Add to PATH")
    на каждом компьютере.
  - Компьютеры должны видеть друг друга: одна локальная сеть или виртуальная сеть, например
    Radmin VPN или ZeroTier (обе бесплатные). Адрес хоста - тот, что показывает эта программа
    (например 26.x.x.x).
  - На компьютере хоста Windows один раз спросит, разрешить ли Python принимать подключения
    (порт TCP 7350). Разрешите для частной сети.

УСТАНОВКА (у каждого игрока)
  Распакуйте архив и выполните в PowerShell из этой папки:
    powershell -ExecutionPolicy Bypass -File install.ps1 "<папка с Warband>"
  В лаунчере Warband: модуль CoopWorld, Configure - Game - Language: ru.
  Тексты игры будут на русском. Если у вашего издания нет русского интерфейса, кнопки движка
  останутся английскими.

ХОСТ (на его компьютере живёт мир)
  1. host.bat ПАРОЛЬ - запустите мост. Пароль придумайте сами и сообщите друзьям.
  2. Запустите Warband два раза, оба с модулем CoopWorld, в оконном режиме
     (Configure - Video - Start Windowed).
     Окно 1 - сервер мира: загрузите свою кампанию,
       Лагерь - "CoopWorld: сделать эту игру СЕРВЕРОМ МИРА". Дальше это окно не трогайте.
     Окно 2 - ваша собственная игра.
  3. Для каждого подключающегося игрока: на сервере
       Лагерь - "CoopWorld: удержать мир для подключения игрока", затем сохраните игру (Esc - Сохранить).
  4. В своей игре (окно 2): загрузите это сохранение,
       Лагерь - "CoopWorld: сделать эту игру КЛИЕНТОМ". Мир на сервере пойдёт дальше сам.

ДРУГ
  1. join.bat АДРЕС_ХОСТА ПАРОЛЬ - скачает свежее сохранение хоста (sg90.sav) и будет держать связь.
     Окно моста не закрывайте, пока играете.
  2. Запустите Warband с модулем CoopWorld, загрузите это сохранение,
     Лагерь - "CoopWorld: сделать эту игру КЛИЕНТОМ". Мир хоста пойдёт дальше, как только вы подключитесь.

КАК ЭТО РАБОТАЕТ
  - Мир (лорды, бандиты, торговля, время) живёт в отдельной игре-сервере у хоста.
    Игры игроков показывают этот мир; у каждого свой отряд, остальные игроки видны на карте.
  - Пока кто-то в бою, во встрече или в меню (город, инвентарь), мир стоит у всех.
  - Итоги ваших боёв уходят на сервер: разбитые отряды исчезают у всех.
  - До 4 игроков.

ОСТАНОВКА
  В своей игре: Лагерь - "CoopWorld: остановить кооператив", затем закройте окно моста.

ЕСЛИ ЧТО-ТО НЕ ТАК
  - Мост пишет журнал в local\bridge.log рядом со своей папкой и выводит строку состояния каждые 5 секунд.
  - "cannot reach the host": проверьте адрес хоста, пароль и что Radmin VPN/ZeroTier включён у обоих.
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


BOM = "\ufeff"


def build(name, files, ru_additions=None):
    out = ROOT / "dist" / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(MODULE.glob("*.txt")):
            if f.name not in BUILD_ONLY:
                z.write(f, f"{name}/CoopWorld/{f.name}")
        z.write(ROOT / "tools" / "coop_bridge.py", f"{name}/coop_bridge.py")
        for arcname, text in files.items():
            z.writestr(f"{name}/{arcname}", text.encode("utf-8"))
        for f in sorted((ru_additions or Path("-")).glob("*.csv")) if ru_additions else []:
            z.write(f, f"{name}/ru_additions/{f.name}")
    print(f"{out} ({out.stat().st_size // 1024} KB)")


def main():
    if not (MODULE / "scripts.txt").exists():
        raise SystemExit("build the module first: python build.py")
    (ROOT / "dist").mkdir(exist_ok=True)
    day = f"{datetime.date.today():%Y%m%d}"
    build(f"CoopWorld-{day}", {"install.ps1": INSTALL_PS1, "join.bat": JOIN_BAT, "host.bat": HOST_BAT,
                               "README.txt": README})
    additions = ROOT / "dist" / "ru_additions"
    if not any(additions.glob("*.csv")):
        raise SystemExit("no Russian texts: run python tools/make_ru.py first")
    # PowerShell 5 reads a script without BOM in the ANSI code page; the batch files switch cmd to UTF-8
    build(f"CoopWorld-ru-{day}", {"install.ps1": BOM + INSTALL_RU_PS1, "join.bat": JOIN_RU_BAT,
                                  "host.bat": HOST_RU_BAT, "README.txt": BOM + README_RU}, additions)


if __name__ == "__main__":
    main()
