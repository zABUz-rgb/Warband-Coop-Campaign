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
RUSSIFIER_UI = ROOT / "vendor" / "l10n_ru" / "languages" / "ru"  # the russifier's engine interface
BUILD_ONLY = {"variables.txt", "variable_uses.txt", "tag_uses.txt"}  # compiler state; quick_strings.txt is read by the game

# One installer, two languages: install.ps1 (and install.bat, which starts it and keeps the window
# open) for a double click. It finds Warband by itself (GOG and Steam registry, the folder the package
# is in) or lets the player pick it, shows every error, waits for Enter, and logs to install.log.
INSTALL_TEMPLATE = r"""# {title}
#   install.bat                    - double click: finds Warband or asks for the folder
#   powershell -ExecutionPolicy Bypass -File install.ps1 "D:\Games\Mount and Blade - Warband"
param([string]$Warband)
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
try {{ Start-Transcript -Path (Join-Path $here "install.log") -Force | Out-Null }} catch {{}}

function Done($code) {{
  try {{ Stop-Transcript | Out-Null }} catch {{}}
  Write-Host ""
  try {{ Read-Host "{press_enter}" | Out-Null }} catch {{}}  # no console (started by a tool): just end
  exit $code
}}

function Is-Warband($dir) {{
  return $dir -and (Test-Path (Join-Path $dir "mb_warband.exe")) -and (Test-Path (Join-Path $dir "Modules\Native"))
}}

function Find-Warband {{
  $found = @()
  foreach ($key in "HKLM:\SOFTWARE\WOW6432Node\GOG.com\Games\1207666913", "HKLM:\SOFTWARE\GOG.com\Games\1207666913") {{
    try {{ $found += (Get-ItemProperty $key -ErrorAction Stop).path }} catch {{}}
  }}
  try {{
    $steam = (Get-ItemProperty "HKCU:\Software\Valve\Steam" -ErrorAction Stop).SteamPath
    $libraries = @($steam)
    $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
    if (Test-Path $vdf) {{
      $libraries += Select-String -Path $vdf -Pattern '"path"\s+"([^"]+)"' | ForEach-Object {{ $_.Matches[0].Groups[1].Value -replace '\\\\', '\' }}
    }}
    foreach ($lib in $libraries) {{ $found += Join-Path $lib "steamapps\common\MountBlade Warband" }}
  }} catch {{}}
  $dir = $here
  while ($dir) {{ $found += $dir; $dir = Split-Path $dir -Parent }}
  return $found | Where-Object {{ Is-Warband $_ }} | Select-Object -Unique
}}

try {{
  if (-not (Test-Path (Join-Path $here "CoopWorld\scripts.txt"))) {{
    throw "{not_unpacked}"
  }}
  if (-not $Warband) {{
    foreach ($candidate in @(Find-Warband)) {{
      $answer = Read-Host "{found_ask}"
      if ($answer -eq "" -or $answer -match '^[yYдД]') {{ $Warband = $candidate; break }}
    }}
  }}
  if (-not $Warband) {{
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "{pick_folder}"
    if ($dialog.ShowDialog() -eq "OK") {{ $Warband = $dialog.SelectedPath }}
  }}
  if (-not $Warband) {{ throw "{no_folder}" }}
  $Warband = $Warband.Trim('"')
  if (-not (Test-Path (Join-Path $Warband "mb_warband.exe"))) {{ throw "{no_exe}" }}
  $native = Join-Path $Warband "Modules\Native"
  $target = Join-Path $Warband "Modules\CoopWorld"
  if (-not (Test-Path $native)) {{ throw "{no_native}" }}
  if (Get-Process mb_warband -ErrorAction SilentlyContinue) {{ throw "{game_running}" }}
  Write-Host "{installing}"
  if (Test-Path $target) {{
    $backup = "$target.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")
    Rename-Item $target $backup
    Write-Host "{kept_old}"
  }}
  Copy-Item $native $target -Recurse
  # file by file: Copy-Item of a folder onto an existing one (languages) would nest it instead
  $source = Join-Path $here "CoopWorld"
  foreach ($file in Get-ChildItem $source -Recurse -File) {{
    $dest = Join-Path $target $file.FullName.Substring($source.Length + 1)
    New-Item -ItemType Directory -Force (Split-Path $dest -Parent) | Out-Null
    Copy-Item $file.FullName $dest -Force
  }}
{ru_part}  Write-Host ""
  Write-Host "{done1}" -ForegroundColor Green
  Write-Host "{done2}"
  Done 0
}} catch {{
  Write-Host ""
  Write-Host "{failed}" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  Write-Host "{log_hint}"
  Done 1
}}
"""

RU_PART = r"""  # the Russian engine interface (the russifier): some editions (GOG) have none; any old one is kept
  $uiRu = Join-Path $Warband "languages\ru"
  if (Test-Path $uiRu) {
    $uiBackup = "$uiRu.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")
    Rename-Item $uiRu $uiBackup
    Write-Host "Прежняя папка languages\ru сохранена как $uiBackup"
  }
  Copy-Item (Join-Path $here "languages\ru") $uiRu -Recurse
  Write-Host "Установлен русский интерфейс игры (languages\ru)."
"""

MESSAGES = {
  "en": dict(
    title="CoopWorld installer", press_enter="Press Enter to close this window",
    not_unpacked="Unpack the whole archive into a folder first and run install.bat from there (the CoopWorld folder must be next to it).",
    found_ask="Install into $candidate ? [Y/n]", pick_folder="Choose the Mount & Blade Warband folder (the one with mb_warband.exe)",
    no_folder="No Warband folder chosen.", no_exe="There is no mb_warband.exe in $Warband",
    no_native=r"There is no Modules\Native in $Warband",game_running="Close Mount & Blade Warband first, then run the installer again.",
    installing="Installing CoopWorld into $Warband ...", kept_old="The old CoopWorld is kept as $backup",
    done1="CoopWorld is installed in $target",
    done2="Start Warband and choose the CoopWorld module in the launcher.",
    failed="Installation failed:", log_hint="Everything the installer did is in install.log next to it.",
    ru_part=""),
  "ru": dict(
    title="Установщик CoopWorld (русская версия)", press_enter="Нажмите Enter, чтобы закрыть окно",
    not_unpacked="Сначала распакуйте весь архив в папку и запускайте install.bat оттуда (рядом должна быть папка CoopWorld).",
    found_ask="Установить в $candidate ? [Д/н]", pick_folder="Выберите папку Mount & Blade Warband (ту, где лежит mb_warband.exe)",
    no_folder="Папка Warband не выбрана.", no_exe="В папке $Warband нет mb_warband.exe",
    no_native=r"В папке $Warband нет Modules\Native",game_running="Сначала закройте Mount & Blade Warband, затем запустите установщик снова.",
    installing="Устанавливаю CoopWorld в $Warband ...", kept_old="Прежний CoopWorld сохранён как $backup",
    done1="CoopWorld установлен в $target",
    done2="Запустите Warband, в лаунчере выберите модуль CoopWorld, а в Configure - Game - Language выберите ru.",
    failed="Установка не удалась:", log_hint="Всё, что делал установщик, записано в install.log рядом с ним.",
    ru_part=RU_PART),
}

INSTALL_PS1 = INSTALL_TEMPLATE.format(**MESSAGES["en"])
INSTALL_RU_PS1 = INSTALL_TEMPLATE.format(**MESSAGES["ru"])

# a double click on a .ps1 opens Notepad or is blocked by the execution policy; this one works
INSTALL_BAT = r"""@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
"""

# host.bat / join.bat: ASCII only (cmd misreads Cyrillic in batch files even after chcp 65001) and
# they only start PowerShell scripts, which ask for what is missing, check Python, keep the window
# open when the bridge stops, and log to bridge.log next to them.
LAUNCHER_TEMPLATE = r"""# {title}
param([string]$First, [string]$Second)
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot

function Wait-Close {{
  Write-Host ""
  try {{ Read-Host "{press_enter}" | Out-Null }} catch {{}}
}}

try {{
  $python = $null
  foreach ($candidate in "python", "py") {{
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch "WindowsApps") {{ $python = $cmd.Source; break }}
  }}
  if (-not $python) {{ throw "{no_python}" }}
{body}
  Write-Host ""
  Write-Host "{starting}" -ForegroundColor Green
  Write-Host "{stop_hint}"
  & $python -I (Join-Path $here "coop_bridge.py") @bridgeArgs --log (Join-Path $here "bridge.log")
  Write-Host ""
  Write-Host "{stopped}" -ForegroundColor Yellow
}} catch {{
  Write-Host ""
  Write-Host "{failed}" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
}}
Wait-Close
"""

HOST_BODY = r"""  $key = $First
  if (-not $key) {{ $key = Read-Host "{ask_key}" }}
  $bridgeArgs = @("host")
  if ($key) {{ $bridgeArgs += @("--key", $key) }} else {{ Write-Host "{no_key}" -ForegroundColor Yellow }}"""

JOIN_BODY = r"""  $hostAddress = $First
  $key = $Second
  if (-not $hostAddress) {{ $hostAddress = Read-Host "{ask_host}" }}
  if (-not $hostAddress) {{ throw "{no_host}" }}
  if (-not $key) {{ $key = Read-Host "{ask_key_join}" }}
  if (-not $key) {{ throw "{no_key_join}" }}
  $bridgeArgs = @("join", $hostAddress, "--key", $key, "--fetch-save")
  Write-Host "{save_hint}" """

LAUNCHER_TEXT = {
  "en": dict(
    press_enter="Press Enter to close this window",
    no_python="Python 3 is not installed (or not in PATH). Install it from python.org, tick 'Add python.exe to PATH', then try again.",
    starting="Starting the CoopWorld bridge. Keep this window open while you play.",
    stop_hint="To stop it: Ctrl+C or close the window. Its log is bridge.log next to this file.",
    stopped="The bridge has stopped. If it stopped by itself, the reason is in the lines above and in bridge.log.",
    failed="The bridge could not start:",
    ask_key="Password for your friends (Enter = play on this PC only)",
    no_key="No password: only games on this PC can join.",
    ask_host="Host address (for example 26.12.34.56 from Radmin VPN)",
    no_host="No host address given.",
    ask_key_join="Password the host gave you",
    no_key_join="No password given.",
    save_hint="The host's newest save goes into your CoopWorld saves (the window shows which slot): load it in the game.",
  ),
  "ru": dict(
    press_enter="Нажмите Enter, чтобы закрыть окно",
    no_python="Python 3 не установлен (или его нет в PATH). Установите его с python.org, отметьте 'Add python.exe to PATH' и попробуйте снова.",
    starting="Запускаю мост CoopWorld. Не закрывайте это окно, пока играете.",
    stop_hint="Остановить: Ctrl+C или закрыть окно. Журнал моста - bridge.log рядом с этим файлом.",
    stopped="Мост остановлен. Если он остановился сам, причина в строках выше и в bridge.log.",
    failed="Мост не запустился:",
    ask_key="Пароль для друзей (Enter - играть только на этом компьютере)",
    no_key="Без пароля: подключиться смогут только игры на этом компьютере.",
    ask_host="Адрес хоста (например 26.12.34.56 из Radmin VPN)",
    no_host="Адрес хоста не указан.",
    ask_key_join="Пароль, который дал хост",
    no_key_join="Пароль не указан.",
    save_hint="Свежее сохранение хоста попадёт в ваши сохранения CoopWorld (в окне будет видно, в какой слот) - загрузите его в игре.",
  ),
}


def launcher(kind, lang):
    m = LAUNCHER_TEXT[lang]
    title = {"host": {"en": "CoopWorld: host the game (the world lives on this PC)", "ru": "CoopWorld: запуск игры у хоста"},
             "join": {"en": "CoopWorld: join a friend's game", "ru": "CoopWorld: подключение к игре друга"}}[kind][lang]
    body = (HOST_BODY if kind == "host" else JOIN_BODY).format(**m)
    return LAUNCHER_TEMPLATE.format(title=title, body=body, **m)


def launcher_bat(kind):
    return f'@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0{kind}.ps1" %*\r\n'


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
  1. Распакуйте весь архив в любую папку (не запускайте из самого архива).
  2. Закройте Warband и дважды щёлкните install.bat.
     Он сам найдёт игру (GOG, Steam) и спросит, туда ли ставить; если не найдёт - откроет окно
     выбора папки. Окно установщика не закроется, пока вы не нажмёте Enter, так что ошибку
     можно прочитать. Всё, что он делал, записано в install.log.
  Если install.bat не запускается: откройте PowerShell и выполните
    powershell -ExecutionPolicy Bypass -File "<папка пакета>\\install.ps1" "<папка с Warband>"
  Установщик ставит полный русификатор: интерфейс игры (папка languages\ru, прежняя
  сохраняется как резервная копия) и русские тексты модуля CoopWorld. Ваш Native не меняется.
  В лаунчере Warband: модуль CoopWorld, Configure - Game - Language: ru.

ХОСТ (на его компьютере живёт мир)
  1. Дважды щёлкните host.bat - запустится мост. Он спросит пароль: придумайте любой и сообщите
     друзьям (Enter без пароля - играть только на этом компьютере). Окно не закрывайте.
  2. Запустите Warband с модулем CoopWorld, загрузите свою кампанию,
       Лагерь - "CoopWorld: сделать эту игру СЕРВЕРОМ МИРА и играть в ней (хост)".
     Вы играете прямо в этом окне: мир живёт в нём, друзья видят ваш отряд на карте.
  3. Для каждого подключающегося игрока:
       Лагерь - "CoopWorld: удержать мир для подключения игрока", затем сохраните игру (Esc - Сохранить).
     Сохранение отдайте другу (join.bat скачает его сам). Как только друг подключится, мир пойдёт дальше.
  Можно и по-старому: отдельное окно - только сервер мира ("...только СЕРВЕРОМ МИРА (без игры в ней)"),
  а играть во втором окне клиентом. Это тяжелее для компьютера, зато мир не зависит от ваших меню.

ДРУГ
  1. Дважды щёлкните join.bat. Он спросит адрес хоста и пароль, скачает свежее сохранение хоста
     в ваши сохранения CoopWorld и будет держать связь. Окно моста не закрывайте, пока играете.
  2. Запустите Warband с модулем CoopWorld, загрузите это сохранение,
     Лагерь - "CoopWorld: сделать эту игру КЛИЕНТОМ". Мир хоста пойдёт дальше, как только вы подключитесь.

КАК ЭТО РАБОТАЕТ
  - Мир (лорды, бандиты, торговля, время) живёт в отдельной игре-сервере у хоста.
    Игры игроков показывают этот мир; у каждого свой отряд, остальные игроки видны на карте.
  - Пока кто-то в бою, во встрече или в меню (город, инвентарь), мир стоит у всех.
  - Бои можно вести вместе на сервере мультиплеера (см. "Совместные бои").
  - Итоги ваших боёв уходят на сервер: разбитые отряды исчезают у всех.
  - До 4 игроков.

СОВМЕСТНЫЕ БОИ (сервер мультиплеера)
  Бой из кампании можно провести на сервере мультиплеера Warband: каждый игрок сражается сам,
  его отряды - боты под его командованием.
  1. Хост запускает второе окно Warband (модуль CoopWorld) - сервер боя, и сам в нём сражается:
       Мультиплеер - Создать игру, режим "Битва" (Battle), карта - любое поле, боты - 0.
     Мост сам находит этот сервер; без него кнопка совместного боя скажет, что сервера нет.
  2. Каждый друг заходит на этот сервер из второго окна Warband (модуль CoopWorld):
       Мультиплеер - список серверов (локальная сеть) или Избранное с адресом хоста, например 26.x.x.x:7240.
     Имя в мультиплеере должно совпадать с именем вашего героя в кампании: тогда мост сам ставит
     вас в нужную команду и отдаёт вам ваших солдат. Окно игры остаётся на сервере между боями.
  3. Во встрече с отрядом на карте выберите "CoopWorld: сразиться вместе с друзьями".
     Игроки поблизости получают приглашение ("В бой!" или "Отказаться"); через несколько секунд
     раунд на сервере боя начинается заново с армиями из кампании. Переключитесь в окно мультиплеера.
  4. Встреча с отрядом другого игрока: "CoopWorld: сразиться с этим игроком". Его вызывают в бой,
     отказаться нельзя; если он не зайдёт на сервер, его отряды сражаются без него.
  5. Когда одна из сторон перебита, потери возвращаются в кампанию: из павших бойцов игрока половина
     ранена, половина убита; разбитый отряд мира исчезает у всех. Пока идёт бой, мир стоит.
  Вы сражаетесь своим героем: его снаряжение (оружие, броня, конь), атрибуты, боевые навыки и
  владение оружием переносятся на сервер боя (до 4 героев в бою). После боя герой и отряд получают
  опыт за павших врагов (проигравшие - треть). Компаньоны пока в бой не выходят.
  Большие армии уменьшаются до 150 ботов на поле, потери пересчитываются обратно.
  Для мультиплеера Warband нужен серийный ключ игры (GOG: в библиотеке у игры, Steam: выдаётся сам).

ОСТАНОВКА
  В своей игре: Лагерь - "CoopWorld: остановить кооператив", затем закройте окно моста.

ЕСЛИ ЧТО-ТО НЕ ТАК
  - Мост пишет журнал в bridge.log в папке пакета и каждые 5 секунд выводит строку состояния.
  - Если окно моста пишет, что Python не найден: установите Python 3 с python.org и отметьте
    "Add python.exe to PATH".
  - "cannot reach the host": проверьте адрес хоста, пароль и что Radmin VPN/ZeroTier включён у обоих.
'''

README = '''CoopWorld - co-op campaign for Mount & Blade: Warband 1.174
=============================================================

Needs: Warband 1.174 (Steam or GOG) and Python 3 (python.org) on every PC.
Install: unpack the archive, close Warband, double-click install.bat. It finds the game
(GOG, Steam) or asks for the folder, and waits for Enter so you can read any error.
Everything it did is in install.log.

The PCs must reach each other: the same LAN, or a virtual LAN such as Radmin VPN or ZeroTier
(both free). The host's address is then the one that program shows (e.g. 26.x.x.x).
The host's PC must let Python accept connections on TCP port 7350 (Windows asks once).

HOST (runs the world):
  1. Double-click host.bat: it asks for a password (any, tell it your friends; Enter without one
     = this PC only) and starts the bridge. Keep its window open.
  2. Start Warband with CoopWorld, load your campaign,
     Camp - "run this game as the WORLD SERVER and play in it (host)". You play in this window.
  3. For each joining player: Camp - "hold the world for a joining client", then save the game
     (Esc - Save). The world runs on as soon as that player joined.
  (Or the old way: one window only the world server ("...WORLD SERVER only (unattended)"),
  and you play in a second window as a CLIENT. Heavier, but the world does not wait for your menus.)

FRIEND:
  1. Double-click join.bat: it asks for the host's address and password, fetches the host's
     newest save into your CoopWorld saves and keeps the link. Keep its window open.
  2. Start Warband with CoopWorld, load that save, Camp - "run this game as a CLIENT".
     The host's world runs on as soon as you joined.

JOINT BATTLES (multiplayer server):
  1. The host starts a second Warband window (CoopWorld) and fights in it: Multiplayer -
     Host a game, game type Battle, any field map, 0 bots. The bridge finds it by itself.
  2. Every friend joins that server from a second Warband window (CoopWorld):
     the LAN server list, or Favorites with the host's address, e.g. 26.x.x.x:7240.
     Use your campaign hero's name as your multiplayer name: the bridge then puts you on your
     side and gives you command of your soldiers.
  3. In an encounter: "CoopWorld: fight together with your friends". Players nearby are invited;
     the battle server restarts its round with the campaign's armies. Switch to that window.
  4. Meeting another player's party: "CoopWorld: fight this player" (that player cannot decline).
  5. When one side is wiped out, the losses go back to the campaign (half of a player's fallen
     are wounded); a defeated world party is gone for everybody. The world stands still meanwhile.
  You fight as your hero: equipment (weapons, armour, horse), attributes, combat skills and
  weapon proficiencies go to the battle server (up to 4 heroes a battle). Afterwards the hero and
  the troops gain experience for the fallen enemies (the losers a third). Companions stay behind for now.

Stopping: Camp - "CoopWorld: stop co-op" in your game, then close the bridge window.
'''


BOM = "\ufeff"


def build(name, files, russian=False):
    out = ROOT / "dist" / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(MODULE.glob("*.txt")):
            if f.name not in BUILD_ONLY:
                z.write(f, f"{name}/CoopWorld/{f.name}")
        z.write(ROOT / "tools" / "coop_bridge.py", f"{name}/coop_bridge.py")
        for arcname, text in files.items():
            z.writestr(f"{name}/{arcname}", text.encode("utf-8"))
        if russian:
            # the module's Russian texts, complete (the russifier's Native plus CoopWorld's), and the
            # russifier's engine interface for the game's own languages folder
            for f in sorted((MODULE / "languages" / "ru").glob("*.csv")):
                z.write(f, f"{name}/CoopWorld/languages/ru/{f.name}")
            for f in sorted(RUSSIFIER_UI.glob("*.csv")):
                z.write(f, f"{name}/languages/ru/{f.name}")
    print(f"{out} ({out.stat().st_size // 1024} KB)")


def main():
    if not (MODULE / "scripts.txt").exists():
        raise SystemExit("build the module first: python build.py")
    (ROOT / "dist").mkdir(exist_ok=True)
    day = f"{datetime.date.today():%Y%m%d}"
    launchers = {lang: {"host.ps1": BOM + launcher("host", lang), "join.ps1": BOM + launcher("join", lang),
                        "host.bat": launcher_bat("host"), "join.bat": launcher_bat("join")} for lang in ("en", "ru")}
    build(f"CoopWorld-{day}", {"install.ps1": BOM + INSTALL_PS1, "install.bat": INSTALL_BAT,
                               "README.txt": README, **launchers["en"]})
    if not RUSSIFIER_UI.exists() or not (MODULE / "languages" / "ru" / "dialogs.csv").exists():
        raise SystemExit("no Russian: put the russifier in vendor/l10n_ru and run python tools/make_ru.py")
    # PowerShell 5 reads a script without BOM in the ANSI code page: every .ps1 gets one
    build(f"CoopWorld-ru-{day}", {"install.ps1": BOM + INSTALL_RU_PS1, "install.bat": INSTALL_BAT,
                                  "README.txt": BOM + README_RU, **launchers["ru"]}, russian=True)


if __name__ == "__main__":
    main()
