"""Build the Warband Coop Campaign packages for players: dist/<version>/Warband-Coop-Campaign-<version>.zip
(English) and dist/<version>/Warband-Coop-Campaign-<version>-ru.zip (Russian: game texts, installer and
instructions). The module folder, its saves and the logs folder in Documents are named like the
project; only the mod's entries in the game's menus keep the prefix "CoopWorld:".

They hold only what the mod adds: the compiled module files (*.txt), Diplomacy's textures and
changed scenes (tools/dplmc_assets.py), the bridge and an installer, and in Programs the installers
of the programs the mod needs (vendor/prereqs: Python, Radmin VPN), which install.bat
offers to run for what is missing. The scripts run in Windows PowerShell 5.1, part of Windows 10/11.
dist/<version>/nexus gets the same two packages for Nexus Mods without Programs: install.bat and the texts send
the player to the programs' own sites instead.
No game files: the installer copies each player's own Modules/Native to Modules/Warband Coop Campaign and puts
the compiled files over it. The Russian one also adds the mod's Russian texts
(tools/make_ru.py) to the copy of Native's languages/ru.

    python tools/make_ru.py && python tools/make_package.py
"""
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tools/dplmc_assets.py, also under python -I
from dplmc_assets import assets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "Warband Coop Campaign"  # also the module folder in Modules and the logs folder in Documents
MODULE = ROOT / "game" / "Modules" / PROJECT
RUSSIFIER_UI = ROOT / "vendor" / "l10n_ru" / "languages" / "ru"  # the russifier's engine interface
BUILD_ONLY = {"variables.txt", "variable_uses.txt", "tag_uses.txt"}  # compiler state; quick_strings.txt is read by the game
PREREQS = ROOT / "vendor" / "prereqs"  # installers of the programs the mod needs (not in git)
VERSION = "1.0.1"
DIST = ROOT / "dist" / VERSION  # every version keeps its own folder
DEBUG = ROOT / "dist" / f"{VERSION}-debug"  # python tools/make_package.py --trail
DISCORD = "https://discord.gg/nfmWC5SWfp"
BOOSTY = "https://boosty.to/zabuz_0"
PYTHON_URL = "https://www.python.org/downloads/windows/"
RADMIN_URL = "https://www.radmin-vpn.com/"

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

function Has-Command($name) {{
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  return $cmd -and $cmd.Source -notmatch "WindowsApps"  # the Store's python.exe stub is no Python
}}

function Has-Radmin {{
  foreach ($dir in "${{env:ProgramFiles(x86)}}\Radmin VPN", "$env:ProgramFiles\Radmin VPN") {{
    if ($dir -and (Test-Path $dir)) {{ return $true }}
  }}
  foreach ($key in "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*", "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*") {{
    if (Get-ItemProperty $key -ErrorAction SilentlyContinue | Where-Object {{ $_.DisplayName -like "Radmin VPN*" }}) {{ return $true }}
  }}
  return $false
}}

# The programs the mod needs, from the Programs folder: what is there already, and, if the player
# agrees, the installers of what is missing (Python by itself, with PATH; the others show their own window).
# A package without the Programs folder (Nexus Mods) says where to get them.
function Install-Programs {{
  $programs = Join-Path $here "Programs"
  $list = @(
    @{{ Name = "{py_name}"; Have = ((Has-Command "python") -or (Has-Command "py")); File = "python-*.exe"; Arguments = "/passive PrependPath=1 Include_launcher=1"; Url = "{python_url}" }},
    @{{ Name = "{radmin_name}"; Have = (Has-Radmin); File = "Radmin_VPN*.exe"; Arguments = ""; Url = "{radmin_url}" }}
  )
  Write-Host "{programs_title}"
  $missing = @()
  foreach ($p in $list) {{
    if ($p.Have) {{ Write-Host ("  " + $p.Name + ": {installed}") -ForegroundColor Green }}
    else {{ Write-Host ("  " + $p.Name + ": {not_installed}") -ForegroundColor Yellow; $missing += $p }}
  }}
  if ($missing.Count -eq 0) {{ Write-Host ""; return }}
  if (-not (Test-Path $programs)) {{
    Write-Host "{programs_download}" -ForegroundColor Yellow
    foreach ($p in $missing) {{ Write-Host ("  " + $p.Name + ": " + $p.Url) -ForegroundColor Cyan }}
    Write-Host ""
    return
  }}
  $answer = Read-Host "{programs_ask}"
  if (-not ($answer -eq "" -or $answer -match '^[yYдДнН]')) {{ Write-Host "{programs_skipped}"; Write-Host ""; return }}
  foreach ($p in $missing) {{
    $file = Get-ChildItem $programs -Filter $p.File | Select-Object -First 1
    if (-not $file) {{ Write-Host ("  " + $p.Name + ": {program_no_file} - " + $p.Url) -ForegroundColor Yellow; continue }}
    Write-Host ("{program_installing} " + $p.Name + " ...")
    try {{
      if ($p.Arguments) {{ $proc = Start-Process $file.FullName -ArgumentList $p.Arguments -Wait -PassThru }}
      else {{ $proc = Start-Process $file.FullName -Wait -PassThru }}
      if ($proc.ExitCode) {{ Write-Host ("  " + $p.Name + ": {program_code} " + $proc.ExitCode) -ForegroundColor Yellow }}
      else {{ Write-Host ("  " + $p.Name + ": {program_done}") -ForegroundColor Green }}
    }} catch {{
      Write-Host ("  " + $p.Name + ": {program_failed} " + $_.Exception.Message) -ForegroundColor Yellow
    }}
  }}
  Write-Host ""
}}

try {{
  if (-not (Test-Path (Join-Path $here "Warband Coop Campaign\scripts.txt"))) {{
    throw "{not_unpacked}"
  }}
  Write-Host "{title}" -ForegroundColor Cyan
  Write-Host ""
  if ((Split-Path -Leaf (Split-Path -Parent $here)) -eq "Modules") {{
    Write-Host "{in_modules}" -ForegroundColor Yellow
    Write-Host ""
  }}
  Install-Programs
  if (-not $Warband) {{
    foreach ($candidate in @(Find-Warband)) {{
      $answer = Read-Host "{found_ask}"
      if ($answer -eq "" -or $answer -match '^[yYдДнН]') {{ $Warband = $candidate; break }}
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
  $target = Join-Path $Warband "Modules\Warband Coop Campaign"
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
  $source = Join-Path $here "Warband Coop Campaign"
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

PROGRAM_TEXT = {
  "en": dict(
    py_name="Python 3 (runs the bridge)", radmin_name="Radmin VPN (the players' network)",
    programs_title="Programs the mod needs:", installed="installed", not_installed="not found",
    programs_ask="Install the missing ones from the Programs folder? [Y/n]",
    programs_skipped="Skipped: install them later from the Programs folder.",
    program_no_file="no installer in the Programs folder", program_installing="Installing",
    program_done="done", program_code="the installer ended with code", program_failed="did not install:",
    programs_download="Install them from their sites before running host.bat / join.bat (Python: tick 'Add python.exe to PATH'):"),
  "ru": dict(
    py_name="Python 3 (нужен для моста)", radmin_name="Radmin VPN (сеть игроков)",
    programs_title="Программы, нужные моду:", installed="установлен", not_installed="не найден",
    programs_ask="Установить недостающие из папки Programs? [Д/н]",
    programs_skipped="Пропущено: их можно установить позже из папки Programs.",
    program_no_file="нет установщика в папке Programs", program_installing="Устанавливаю",
    program_done="готово", program_code="установщик завершился с кодом", program_failed="не установлен:",
    programs_download="Установите их с официальных сайтов до запуска host.bat / join.bat (Python: отметьте 'Add python.exe to PATH'):"),
}
for _text in PROGRAM_TEXT.values():
  _text.update(python_url=PYTHON_URL, radmin_url=RADMIN_URL)

MESSAGES = {
  "en": dict(
    title=f"{PROJECT} {VERSION} - installer", press_enter="Press Enter to close this window",
    in_modules="The package lies in the game's Modules folder, where the launcher looks for modules. It works, but better move this folder into the game's folder (next to mb_warband.exe).",
    not_unpacked="Unpack the whole archive into a folder first and run install.bat from there (the Warband Coop Campaign folder must be next to it).",
    found_ask="Install into $candidate ? [Y/n]", pick_folder="Choose the Mount & Blade Warband folder (the one with mb_warband.exe)",
    no_folder="No Warband folder chosen.", no_exe="There is no mb_warband.exe in $Warband",
    no_native=r"There is no Modules\Native in $Warband",game_running="Close Mount & Blade Warband first, then run the installer again.",
    installing="Installing Warband Coop Campaign into $Warband ...", kept_old="The old Warband Coop Campaign is kept as $backup",
    done1="Warband Coop Campaign is installed in $target",
    done2="Start Warband and choose the Warband Coop Campaign module in the launcher. Before playing, open Radmin VPN and check that the network is up.",
    failed="Installation failed:", log_hint="Everything the installer did is in install.log next to it.",
    ru_part=""),
  "ru": dict(
    title=f"{PROJECT} {VERSION} - установщик (русская версия)", press_enter="Нажмите Enter, чтобы закрыть окно",
    in_modules="Пакет лежит в папке Modules игры, где лаунчер ищет модули. Работать будет, но лучше перенесите эту папку в папку с игрой (рядом с mb_warband.exe).",
    not_unpacked="Сначала распакуйте весь архив в папку и запускайте install.bat оттуда (рядом должна быть папка Warband Coop Campaign).",
    found_ask="Установить в $candidate ? [Д/н]", pick_folder="Выберите папку Mount & Blade Warband (ту, где лежит mb_warband.exe)",
    no_folder="Папка Warband не выбрана.", no_exe="В папке $Warband нет mb_warband.exe",
    no_native=r"В папке $Warband нет Modules\Native",game_running="Сначала закройте Mount & Blade Warband, затем запустите установщик снова.",
    installing="Устанавливаю Warband Coop Campaign в $Warband ...", kept_old="Прежний Warband Coop Campaign сохранён как $backup",
    done1="Warband Coop Campaign установлен в $target",
    done2="Запустите Warband, в лаунчере выберите модуль Warband Coop Campaign, а в Configure - Game - Language выберите ru. Перед игрой откройте Radmin VPN и убедитесь, что сеть работает.",
    failed="Установка не удалась:", log_hint="Всё, что делал установщик, записано в install.log рядом с ним.",
    ru_part=RU_PART),
}

INSTALL_PS1 = INSTALL_TEMPLATE.format(**MESSAGES["en"], **PROGRAM_TEXT["en"])
INSTALL_RU_PS1 = INSTALL_TEMPLATE.format(**MESSAGES["ru"], **PROGRAM_TEXT["ru"])

# a double click on a .ps1 opens Notepad or is blocked by the execution policy; this one works
INSTALL_BAT = r"""@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
"""

# host.bat / join.bat: ASCII only (cmd misreads Cyrillic in batch files even after chcp 65001) and
# they only start PowerShell scripts, which ask for what is missing, check Python, keep the window
# open when the bridge stops, and log to Documents\Warband Coop Campaign (bridge.log / join.log).
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
  # logs (and the host's kept heroes, profiles.json) in Documents\Warband Coop Campaign: they outlive the package folder
  $logDir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Warband Coop Campaign"
  New-Item -ItemType Directory -Force $logDir | Out-Null
  Write-Host "{log_where} $logDir"
  & $python -I (Join-Path $here "coop_bridge.py") @bridgeArgs --log (Join-Path $logDir "{log_name}")
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

# both launchers: the player's name on the battle server, remembered in mp_name.txt
MP_NAME_BODY = r"""
  $mpFile = Join-Path $here "mp_name.txt"
  $mpName = ""
  if (Test-Path $mpFile) {{ $mpName = (Get-Content $mpFile -Raw -Encoding UTF8).Trim() }}
  Write-Host "{mp_name_hint}"
  $answer = Read-Host "{ask_mp_name} [$mpName]"
  if ($answer) {{ $mpName = $answer.Trim(); Set-Content -Path $mpFile -Value $mpName -Encoding UTF8 }}
  if ($mpName) {{
    $bridgeArgs += @("--mp-name", $mpName)
    Write-Host "{mp_name_set} $mpName" -ForegroundColor Green
  }} else {{
    Write-Host "{no_mp_name}" -ForegroundColor Yellow
  }}"""

JOIN_BODY = r"""  $hostAddress = $First
  $key = $Second
  if (-not $hostAddress) {{ $hostAddress = Read-Host "{ask_host}" }}
  if (-not $hostAddress) {{ throw "{no_host}" }}
  if (-not $key) {{ $key = Read-Host "{ask_key_join}" }}
  if (-not $key) {{ throw "{no_key_join}" }}
  $bridgeArgs = @("join", $hostAddress, "--key", $key, "--fetch-save")
  Write-Host "{save_hint}"
  # the battle server shows up in the second window's server list only with this option on
  $rgl = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Mount&Blade Warband\rgl_config.txt"
  if ((Test-Path $rgl) -and ((Get-Content $rgl -Raw) -match "look_for_server_on_this_machine\s*=\s*0")) {{
    Write-Host ""
    Write-Host "{lan_hint}" -ForegroundColor Cyan
    $answer = Read-Host "{lan_ask}"
    if ($answer -eq "" -or $answer -match '^[yYдДнН]') {{
      if (Get-Process mb_warband -ErrorAction SilentlyContinue) {{
        Write-Host "{lan_close}" -ForegroundColor Yellow
      }} else {{
        Copy-Item $rgl "$rgl.bak" -Force
        $text = (Get-Content $rgl -Raw) -replace "look_for_server_on_this_machine\s*=\s*0", "look_for_server_on_this_machine = 1"
        [IO.File]::WriteAllText($rgl, $text)
        Write-Host "{lan_done}" -ForegroundColor Green
      }}
    }}
  }}
  Write-Host "{battle_hint}" -ForegroundColor Cyan """

LAUNCHER_TEXT = {
  "en": dict(
    press_enter="Press Enter to close this window",
    no_python="Python 3 is not installed (or not in PATH). Install it from python.org, tick 'Add python.exe to PATH', then try again.",
    starting="Starting the Warband Coop Campaign bridge. Keep this window open while you play.",
    stop_hint="To stop it: Ctrl+C or close the window.",
    log_where="Logs (bridge.log and trace.log at the host, join.log at a friend; a friend's log also reaches the host's):",
    stopped="The bridge has stopped. If it stopped by itself, the reason is in the lines above and in bridge.log.",
    failed="The bridge could not start:",
    ask_key="Password for your friends (Enter = play on this PC only)",
    no_key="No password: only games on this PC can join.",
    ask_host="Host address (for example 26.12.34.56 from Radmin VPN)",
    no_host="No host address given.",
    ask_key_join="Password the host gave you",
    no_key_join="No password given.",
    save_hint="The host's newest save goes into your Warband Coop Campaign saves (the window shows which slot): load it in the game.",
    lan_hint="Joint battles go through the bridge: for the battle server to show up in your server list (Local Area Network), Warband's option look_for_server_on_this_machine must be on (Documents\\Mount&Blade Warband\\rgl_config.txt; a copy is kept as rgl_config.txt.bak).",
    lan_ask="Turn it on? (Enter or Y - yes, N - no)",
    lan_close="Warband is open and would undo this on exit: close every Warband window and run join.bat again.",
    lan_done="Turned on.",
    battle_hint="Joint battles: in the second Warband window - Multiplayer - Join a Game - Local Area Network - Refresh. If two identical servers show up, one goes straight over Radmin and says 'invalid authorization number': join the other one and Add to Favorites. Keep this window open.",
    mp_name_hint="Joint battles: the name you use on the battle server (Multiplayer - Profiles). Your soldiers obey you only under this name.",
    ask_mp_name="Your multiplayer name (Enter = keep the one in brackets)",
    mp_name_set="Multiplayer name:",
    no_mp_name="No multiplayer name: the bridge looks for your hero's name on the battle server.",
  ),
  "ru": dict(
    press_enter="Нажмите Enter, чтобы закрыть окно",
    no_python="Python 3 не установлен (или его нет в PATH). Установите его с python.org, отметьте 'Add python.exe to PATH' и попробуйте снова.",
    starting="Запускаю мост Warband Coop Campaign. Не закрывайте это окно, пока играете.",
    stop_hint="Остановить: Ctrl+C или закрыть окно.",
    log_where="Журналы (у хоста bridge.log и trace.log, у друга join.log; журнал друга приходит и хосту):",
    stopped="Мост остановлен. Если он остановился сам, причина в строках выше и в bridge.log.",
    failed="Мост не запустился:",
    ask_key="Пароль для друзей (Enter - играть только на этом компьютере)",
    no_key="Без пароля: подключиться смогут только игры на этом компьютере.",
    ask_host="Адрес хоста (например 26.12.34.56 из Radmin VPN)",
    no_host="Адрес хоста не указан.",
    ask_key_join="Пароль, который дал хост",
    no_key_join="Пароль не указан.",
    save_hint="Свежее сохранение хоста попадёт в ваши сохранения Warband Coop Campaign (в окне будет видно, в какой слот) - загрузите его в игре.",
    lan_hint="Совместные бои идут через мост: чтобы сервер боя появился у вас в списке серверов (Локальная сеть), в настройках Warband нужно включить look_for_server_on_this_machine (Документы\\Mount&Blade Warband\\rgl_config.txt; копия останется как rgl_config.txt.bak).",
    lan_ask="Включить? (Enter или Y - да, N - нет)",
    lan_close="Warband сейчас открыт и при выходе отменит эту настройку: закройте все окна Warband и запустите join.bat снова.",
    lan_done="Включено.",
    battle_hint="Совместные бои: во втором окне Warband - Сетевая игра - Присоединиться к игре - Локальная сеть - Обновить. Если там два одинаковых сервера, один ведёт напрямую через Radmin и пишет 'неправильный номер авторизации': заходите в другой и нажмите 'Добавить в избранное'. Это окно не закрывайте.",
    mp_name_hint="Совместные бои: имя, под которым вы заходите на сервер боя (Мультиплеер - Профили). Только под этим именем ваши солдаты будут вас слушаться.",
    ask_mp_name="Ваше имя в мультиплеере (Enter - оставить то, что в скобках)",
    mp_name_set="Имя в мультиплеере:",
    no_mp_name="Имя в мультиплеере не задано: мост будет искать на сервере боя имя вашего героя.",
  ),
}


def launcher(kind, lang):
    m = LAUNCHER_TEXT[lang]
    title = {"host": {"en": f"{PROJECT}: host the game (the world lives on this PC)", "ru": f"{PROJECT}: запуск игры у хоста"},
             "join": {"en": f"{PROJECT}: join a friend's game", "ru": f"{PROJECT}: подключение к игре друга"}}[kind][lang]
    body = (HOST_BODY if kind == "host" else JOIN_BODY).format(**m) + MP_NAME_BODY.format(**m)
    log_name = "bridge.log" if kind == "host" else "join.log"
    return LAUNCHER_TEMPLATE.format(title=title, body=body, log_name=log_name, **m)


START_HERE_RU = f'''{PROJECT} {VERSION} - С ЧЕГО НАЧАТЬ
==========================================

1. Один раз:
   - Распакуйте весь архив в любую папку, лучше всего - в папку с игрой (не запускайте из архива).
   - Закройте Warband и дважды щёлкните install.bat. Он предложит установить недостающие
     программы (Python 3, Radmin VPN) из папки Programs и сам поставит мод.
   - В лаунчере Warband выберите модуль Warband Coop Campaign, Configure - Game - Language: ru,
     и включите оконный режим (Start windowed).
   - Radmin VPN: войдите в сеть, которую создал хост.
2. Каждый раз перед игрой:
   - Откройте Radmin VPN и убедитесь, что сеть работает стабильно.
   - Хост: host.bat, затем Warband - своя кампания - Лагерь - "CoopWorld: кооператив..." -
     "...СЕРВЕРОМ МИРА и играть в ней (хост)".
   - Друг: join.bat (адрес хоста из Radmin VPN, пароль хоста, ваше имя в мультиплеере).
     Окно моста не закрывайте. Запустите Warband (Warband Coop Campaign) и загрузите сохранение, которое
     скачал join.bat. Подождите около 5 секунд - игра сама станет КЛИЕНТОМ. Если нет:
     Лагерь - "CoopWorld: кооператив..." - "CoopWorld: пустить мир дальше (перестать удерживать)".
3. Совместные бои: второе окно Warband (Warband Coop Campaign). Хост: Мультиплеер - Создать игру, "Битва".
   Друг: Сетевая игра - Присоединиться к игре - Локальная сеть (через мост, окно join.bat открыто).
Сохранения: и у хоста, и у друга в папке сохранений Warband Coop Campaign держите только сохранения
этой совместной кампании - мост отдаёт другу самое свежее из них (подробно - README.txt, "СОХРАНЕНИЯ").
Подробности - README.txt. Вопросы и ошибки: {DISCORD}
'''

START_HERE = f'''{PROJECT} {VERSION} - START HERE
===========================================

1. Once: unpack the whole archive (best into the game's folder), close Warband, double-click
   install.bat: it offers to install the missing programs (Python 3, Radmin VPN) from
   the Programs folder and installs the mod. In the launcher pick the Warband Coop Campaign module and Start
   windowed. In Radmin VPN join the host's network.
2. Every time: open Radmin VPN and check the network is up.
   Host: host.bat, then Warband - your campaign - Camp - "CoopWorld: co-op..." - "...WORLD SERVER and
   play in it (host)".
   Friend: join.bat (the host's address, the host's password, your multiplayer name); keep its
   window open. Start Warband (Warband Coop Campaign), load the save join.bat fetched and wait about 5 seconds:
   the game becomes a CLIENT by itself. If not: Camp - "CoopWorld: co-op..." - "let the world run again".
3. Joint battles: a second Warband window (Warband Coop Campaign). Host: Multiplayer - Host a game, Battle.
   Friends: Multiplayer - Join a Game - Local Area Network (through the bridge, join.bat's window open).
Saves: host and friends keep only this co-op campaign's saves in the Warband Coop Campaign saves
folder - the bridge sends the friends the newest one (README.txt, SAVES).
More in README.txt. Questions and bugs: {DISCORD}
'''


def launcher_bat(kind):
    return f'@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0{kind}.ps1" %*\r\n'


# check_logs.bat: the report on the last session, from the host's logs (tools/coop_logs.py)
CHECK_LOGS_TEMPLATE = r"""# Warband Coop Campaign: a report on the last session from Documents\Warband Coop Campaign\bridge.log and trace.log
$python = $null
foreach ($candidate in "python", "py") {{
  $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source -notmatch "WindowsApps") {{ $python = $cmd.Source; break }}
}}
if ($python) {{
  & $python -I (Join-Path $PSScriptRoot "coop_logs.py") @args
}} else {{
  Write-Host "{no_python}" -ForegroundColor Red
}}
Write-Host ""
try {{ Read-Host "{press_enter}" | Out-Null }} catch {{}}
"""


def check_logs(lang):
    text = LAUNCHER_TEXT[lang]
    return CHECK_LOGS_TEMPLATE.format(no_python=text["no_python"], press_enter=text["press_enter"])


README_RU = f'''{PROJECT} {VERSION} - кооперативная кампания для Mount & Blade: Warband 1.174
=====================================================================================
Неофициальный фанатский мод, не связан с TaleWorlds Entertainment. Бесплатный.
Основа - Diplomacy 1.174 с Freelancer. Пункты мода в меню игры подписаны "CoopWorld:" (рабочее
название мода). Нужна новая кампания.

  Discord (вопросы, ошибки, поиск напарников): {DISCORD}
  Поддержать разработку (по желанию, ничего не даёт сверх бесплатной версии): {BOOSTY}

ЧТО НУЖНО
  - У каждого игрока своя лицензионная Warband 1.174 (Steam или GOG) с серийным ключом: без ключа
    мультиплеер не пускает, а с одним ключом вдвоём на сервер боя не зайти. Ключ Steam-версии:
    Steam - Библиотека - правый клик по Warband - Управление - Ключи продукта.
  - Python 3 и Radmin VPN. Их установщики лежат в папке Programs, install.bat предложит
    поставить недостающие. Больше ничего ставить не нужно: PowerShell уже есть в Windows 10/11.
  - Компьютеры должны видеть друг друга: одна сеть Radmin VPN (или ZeroTier, или локальная сеть).
  - У хоста Windows один раз спросит, разрешить ли Python принимать подключения (порт 7350, TCP и
    UDP): разрешите и для частных, и для общественных сетей - сеть Radmin Windows часто считает
    общественной.

УСТАНОВКА (у каждого игрока)
  1. Распакуйте весь архив в любую папку, лучше всего - в папку с игрой, чтобы установщик быстрее
     определил нужную папку (не запускайте из самого архива).
  2. Закройте Warband и дважды щёлкните install.bat.
     - Сначала он покажет, какие программы уже есть (Python 3, Radmin VPN), и спросит,
       установить ли недостающие. Python ставится сам (и сразу попадает в PATH), у Radmin VPN
       откроется его обычный установщик.
     - Затем он найдёт игру (папка с архивом, GOG, Steam) и спросит, туда ли ставить; если не
       найдёт - откроет окно выбора папки.
     - Он ставит модуль Warband Coop Campaign (копия вашего Native с файлами мода; сам Native не меняется)
       и русский интерфейс игры (прежняя папка languages\\ru сохраняется как резервная копия).
     Окно не закроется, пока вы не нажмёте Enter, так что ошибку можно прочитать. Всё, что
     делал установщик, записано в install.log.
  3. В лаунчере Warband: модуль Warband Coop Campaign, Configure - Game - Language: ru, и включите
     Start windowed (оконный режим): для совместных боёв нужны два окна игры, а полноэкранная
     игра при переключении сворачивается и замирает.
  Если install.bat не открывается или окно сразу закрывается, запустите установщик вручную:
  Пуск - Windows PowerShell, и в нём:
    powershell -ExecutionPolicy Bypass -File "<папка пакета>\\install.ps1" "<папка с Warband>"

ПЕРЕД ИГРОЙ (для всех игроков)
  Откройте Radmin VPN и убедитесь, что сеть работает стабильно: все в сети хоста, хост в сети
  (зелёный значок), его адрес виден (например 26.x.x.x).

ХОСТ (на его компьютере живёт мир)
  1. Дважды щёлкните host.bat - запустится мост. Он спросит пароль: придумайте любой и сообщите
     друзьям (Enter без пароля - играть только на этом компьютере), и ваше имя в мультиплеере.
     Окно моста не закрывайте.
  2. Запустите Warband с модулем Warband Coop Campaign, загрузите свою кампанию,
       Лагерь - "CoopWorld: кооператив..." - "CoopWorld: сделать эту игру СЕРВЕРОМ МИРА и играть в ней (хост)".
     Вы играете прямо в этом окне: мир живёт в нём, друзья видят ваш отряд на карте.
     Окна, которые мир открывает сам, у хоста мир не останавливают: сообщения и недельный бюджет
     приходят строкой в журнал, а известия с выбором (война, приглашения, спутники, гонцы маршала)
     копятся - откройте их, когда удобно: Лагерь - "CoopWorld: кооператив..." - "прочитать отложенные известия".
  3. Для каждого подключающегося игрока:
       Лагерь - "CoopWorld: кооператив..." - "CoopWorld: удержать мир для подключения игрока", затем
       сохраните игру (Esc - Сохранить). join.bat друга скачает это сохранение сам.
     Как только друг подключится, мир пойдёт дальше; можно и самому: там же "пустить мир дальше".
  Можно и по-старому: отдельное окно - только сервер мира ("...только СЕРВЕРОМ МИРА (без игры в ней)"),
  а играть во втором окне клиентом. Это тяжелее для компьютера, зато мир не зависит от ваших меню.

ДРУГ
  1. Дважды щёлкните join.bat. Он спросит адрес хоста (из Radmin VPN), пароль и ваше имя в
     мультиплеере, скачает свежее сохранение хоста в ваши сохранения Warband Coop Campaign и будет держать
     связь. Окно моста не закрывайте, пока играете. Если хост ещё не сохранял игру (новая кампания),
     окно подождёт: сохранение придёт само, как только хост сохранится.
  2. Запустите Warband с модулем Warband Coop Campaign и загрузите это сохранение. Подождите около 5 секунд:
     игра сама станет КЛИЕНТОМ мира хоста. Если этого не произошло, нажмите
       Лагерь - "CoopWorld: кооператив..." - "CoopWorld: пустить мир дальше (перестать удерживать)",
     и вас синхронизирует.
  Каждое новое сохранение хоста join.bat сам кладёт в тот же слот ваших сохранений (старое - .bak),
  а игра пишет "хост сохранил игру". В следующий раз загружайте этот слот - мир будет самым свежим.
  Герой получает имя, которое вы ввели в join.bat (у хоста - в host.bat).

СОХРАНЕНИЯ (важно для хоста и друзей)
  Мост отдаёт друзьям самое свежее по времени сохранение из папки хоста
    Документы\\Mount&Blade Warband Savegames\\Warband Coop Campaign
  Если там лежат сохранения другой кампании или старых проб, друг может получить не то сохранение
  (так и было в одной из проверок). Поэтому и у хоста, и у каждого друга в этой папке должны быть
  только сохранения текущей совместной кампании: остальные перенесите в другую папку (или
  удалите), прежде чем запускать host.bat / join.bat.
  - Хост: перед подключением друга сохранитесь (Esc - Сохранить) - уйдёт именно это сохранение.
  - Каждое сохранение хоста сразу уходит всем подключённым друзьям. Сохранение, сделанное, пока
    связь с другом прерывалась, приходит, как только мост друга подключится снова.
  - Друг загружает тот слот, который назвал join.bat ("... now holds it"), а не другой.

КАК ЭТО РАБОТАЕТ
  - Мир (лорды, бандиты, торговля, войны, время) живёт у хоста. Игры игроков показывают этот мир;
    у каждого свой отряд, остальные игроки видны на карте. До 4 игроков.
  - Пока кто-то в бою, во встрече или в меню (город, инвентарь), мир стоит у всех: отряды на
    карте замирают, часы останавливаются. Сообщение подскажет, из-за кого пауза.
  - Время у всех общее. Если ваши часы ушли вперёд мира на 3 часа и больше, отдых стоя не идёт,
    пока мир не догонит (двигаться можно); отстали на 3 часа и больше - отдых идёт втрое быстрее.
  - Итоги ваших боёв уходят хосту: разбитые отряды исчезают у всех.

ИГРОКИ ВМЕСТЕ
  Лагерь - "CoopWorld: кооператив..." - "CoopWorld: другие игроки": кто в мире и как далеко;
  попроситься в отряд (откуда угодно), передать войска (если игрок рядом, до 3 км), записать
  своего героя у хоста прямо сейчас.
  Встретив на карте отряд другого игрока, сразу открывается меню (без разговора), где можно:
  - "сразиться с этим игроком" (совместный бой; второй игрок отказаться не может);
  - "попроситься в отряд этого игрока": он примет или откажет. Принятый следует за лидером по карте
    и вызывается во все его совместные бои. Покинуть отряд - Лагерь - "CoopWorld: кооператив..."
    (или "другие игроки"); лидер может отпустить всех последователей там же.
  - "передать войска этому игроку": выберите бойцов в окне обмена и отправьте; получатель примет
    или откажется, отвергнутые бойцы вернутся (даже если вы успели выйти - при следующем входе).

СЛУЖБА ЛОРДУ (Freelancer)
  Поступить на службу к лорду можно обычным разговором с ним. Пока вы служите, ваш отряд идёт
  за лордом, отдых идёт со скоростью мира, а общая пауза останавливает и вас.
  Если вы служите тому же лорду, что и другой игрок, и лорд вступает в полевой бой, у вас
  откроется меню солдата ("ваш командир вступает в бой!"). Пункт "CoopWorld: сражаться рядом с
  командиром вместе с друзьями" начнёт совместный бой: игроки и люди лорда против его врага;
  второй солдат, выбравший этот пункт, попадает в тот же бой. Лорд сохраняет уцелевших.

СОВМЕСТНЫЕ БОИ (сервер мультиплеера)
  Ограничение - из-за движка игры, есть возможность совместного сражения ТОЛЬКО через второе окно
  игры, соответственно, перед каждым боем вам потребуется либо каждый раз запустить второе окно
  игры для захода в бой, либо держать второе окно постоянно открытым на сетевом бое.
  Бой из кампании можно провести на сервере мультиплеера Warband: каждый игрок сражается сам
  своим героем, его отряды - боты под его командованием.
  Важно:
  - У каждого игрока своя лицензия Warband (см. "Что нужно").
  - Сервер боя создавайте в только что запущенном окне Warband, где не загружалась кампания.
  1. Хост запускает второе окно Warband (модуль Warband Coop Campaign) - сервер боя, и сам в нём сражается:
       Мультиплеер - Создать игру, режим "Битва" (Battle), карта - любое поле, боты - 0. Далее
       выбираете сторону и снаряжение (без разницы какое и какую сторону) и забываете об этом
       окне до сражения.
     Мост сам находит этот сервер; без него кнопка совместного боя скажет, что сервера нет.
  2. Каждый друг заходит на этот сервер из второго окна Warband (модуль Warband Coop Campaign)
     через мост (окно join.bat открыто): Сетевая игра - Присоединиться к игре - Локальная сеть -
     Обновить. Мост передаёт бой хосту, и сервер пускает друга как игрока своей локальной сети.
     Чтобы сервер через мост был в списке, join.bat один раз предложит включить в настройках
     Warband look_for_server_on_this_machine - соглашайтесь (Warband при этом закрыт).
     Если в списке два одинаковых сервера: один из них - напрямую через Radmin, туда Warband
     не пускает ("неправильный номер авторизации"). Заходите в другой и нажмите "Добавить в
     избранное" - дальше он будет во вкладке Избранное.
     Заходите ровно под тем именем, которое ввели в host.bat / join.bat (оно запоминается в
     mp_name.txt): тогда мост сам ставит вас в нужную команду и отдаёт вам ваших солдат. Мост пишет
     в своём окне, кого он узнал на сервере ("recognised") и кого нет ("NOT found"). Имена у всех
     разные! Окно игры остаётся на сервере между боями.
  3. Во встрече с отрядом на карте выберите "CoopWorld: сразиться вместе с друзьями". Игроки
     в пределах 40 единиц карты получают приглашение ("В бой!" или "Отказаться"); через несколько секунд раунд на
     сервере боя начинается заново с армиями из кампании. Переключитесь в окно мультиплеера.
     Сторона и герой выдаются сами; если всё же открылось окно выбора команды - закройте его (Esc).
     На приглашение есть 45 секунд. Кто ответил позже, всё равно попадает в бой своим героем, но
     его отряды в этом бою не участвуют. Игрок, для которого у сервера боя ещё нет героя (зашёл на
     сервер позже или под другим именем), в бой кампании не выходит со снаряжением мультиплеера:
     он ждёт, пока мост его узнает и пришлёт героя, и тогда появляется на своей стороне.
  4. Бой идёт, пока у одной из сторон не останется никого: ни ботов, ни героев. Павший герой в
     этот бой не возвращается (как в одиночной игре) и смотрит бой со стороны.
  5. Потери возвращаются в кампанию: из павших бойцов игрока половина ранена, половина убита;
     разбитый отряд мира исчезает у всех. Пока идёт бой, мир стоит.
  Ваш герой: снаряжение (оружие, броня, конь), атрибуты, боевые навыки, владение оружием и
  здоровье (текущее и наибольшее - Сила и Железная кожа учитываются) переносятся на сервер боя,
  до 4 героев в бою. Раненый в кампании герой выходит в бой раненым. После боя здоровье
  сохраняется (павший герой возвращается тяжело раненым), владение оружием растёт за попадания и
  урон тем видом оружия, которым вы сражались, герой и отряд получают опыт за павших врагов
  (проигравшие - треть). Компаньоны выходят в бой ботами со своим снаряжением, навыками и
  здоровьем и подчиняются вам; павший компаньон возвращается тяжело раненым, но живым.
  Победители делят добычу с павших врагов (окно добычи, как после обычного боя). Они же берут
  пленных: каждый павший враг их доли, убитый или раненый, попадает в плен с шансом по навыку
  "Содержание пленных" героя: 10% на уровне 1 и ещё по 5% за каждый следующий (на уровне 0 пленных
  нет), пока хватает места. Карта полевого
  боя подбирается по местности: степь, лес, горы, снег, пустыня, река. Большие армии уменьшаются
  до 150 ботов на поле, потери пересчитываются обратно.
  Пока не переносится: качество предметов ("закалённый", "тяжёлый", "ржавый" и т.п.) - на сервере
  боя у героя те же предметы, но обычного качества.
  Проигравший отряду мира попадает в плен, как в обычной игре: его войска и компаньоны уходят к
  победителю пленными, часть вещей забирают. Проигравший другому игроку в плен не попадает, но
  его уцелевшие войска становятся пленными победителя.
  СОВМЕСТНАЯ ОСАДА: в меню осады (когда лестницы или башня готовы) - "CoopWorld: штурмовать стены
  вместе". Сервер боя сам переходит в режим "Осада" на одной из карт с замком: гарнизон (команда 1)
  держит стены, игроки (команда 2) штурмуют. Боты в осаде сражаются пешими; лестницы сервер
  поднимает сам, когда все войска на поле (сброшенную лестницу - снова через 30 секунд), а
  штурмующие, застрявшие под стеной, идут к лестницам. Штурм удался, если взят флаг или пал весь
  гарнизон: хост берёт замок как в обычной игре, а замок, взятый клиентом, переходит его
  королевству (клиенту без присяги штурм недоступен). Не удался - гарнизон теряет павших, осаду
  можно продолжить. Кому принадлежат замки и города, видно у всех игроков.
  СОВМЕСТНАЯ ОБОРОНА: когда армия мира осаждает замок или город вашей стороны, все игроки получают
  сообщение. Въехав в него или подъехав к воротам, выберите "CoopWorld: защищать стены вместе":
  игроки и гарнизон (команда 1) на стенах, осаждающий лорд и его армия (команда 2) штурмуют.
  Отбились - осаждающие теряют павших; не удержали стены - центр переходит их королевству,
  а защитники попадают в плен, как в обычной игре.

АРЕНА, ТУРНИР И ТРЕНИРОВКА ВМЕСТЕ
  Они идут на том же сервере боя, во втором окне. Сражаются только герои игроков, все на одной
  стороне, в тренировочном снаряжении и с полным здоровьем, без войск и компаньонов. На кампанию
  влияет только награда: ни ран, ни потерь, мир о них не знает.
  Игроки поблизости получают приглашение (см. СИГНАЛ К БОЮ). Друг, стоящий в том же городе, может
  и сам выбрать тот же пункт, пока событие собирается, и попадёт в него.
  Событие начинается, когда все согласившиеся стоят на сервере боя; кого нет через 1 мин 45 с,
  оно оставляет без него. Войдите на сервер боя заранее.
  АРЕНА: меню города - "CoopWorld: сразиться на арене вместе" (днём, не тайком). По 20 соперников на
  игрока, от слабых к сильным, одновременно не больше 3 на игрока. Кто устоял до конца - главный
  приз арены (250 динаров), павший - награда за своих побеждённых, как в одиночной игре. Карта
  The Arena.
  ТУРНИР: меню города, когда в нём идёт турнир - "CoopWorld: участвовать в турнире вместе". Сначала
  ставка на всю команду (5-100 динаров или без неё). Четыре раунда подряд, в каждом соперников
  столько же, сколько игроков (NxN), с каждым раундом они сильнее; команда держится, пока стоит
  хоть один герой, а в следующем раунде вернутся все. Победа: каждому игроку приз 200 динаров,
  250 опыта, 20 известности, +1 к отношению с городом и выигрыш со всех ставок команды. Поражение:
  сделавший ставку теряет только её. Ставка списывается в конце, отменённый турнир ничего не стоит.
  Карта The Arena.
  ТРЕНИРОВКА: тренировочный лагерь - "CoopWorld: тренироваться вместе с друзьями", выберите от 1 до
  4 соперников на игрока. Соперники - ваши собственные бойцы (если их мало, бойцы арены) с
  тренировочным оружием. Опыт как в одиночной тренировке: зависит от доли побеждённых, сложности и
  навыка "Тренер", бойцы, вышедшие на поле, получают больше. Карта Field by the River.

ВМЕСТЕ БЕЗ ВСТРЕЧИ НА КАРТЕ
  Всё это - в меню Лагерь - CoopWorld: кооператив.
  СЛЕДОВАТЬ ЗА ДРУГОМ: "другие игроки" - "Следовать за игроком ...". Отряд сам едет к другу и
  держится рядом, друг получает сообщение. Свой щелчок по карте останавливает поход. Если отряд не
  слушается приказа идти, игра сама переносит его к другу и пишет об этом.
  ЛАГЕРЬ ОТРЯДА: один на всех, виден на карте у каждого. Лагерь - CoopWorld - "разбить здесь лагерь
  отряда" (1000 динаров), потом "поехать в лагерь" или щелчок по нему на карте. Внутри казна, склад
  и Джон Блэкборн; лагерь можно свернуть, казна и склад при этом сохраняются.
  ОБЩАЯ КАЗНА И СКЛАД: теперь только в лагере отряда. Склад
  открыт только у одного игрока: взятое вдвоём существовало бы дважды. Вещей до 96 (сколько вмещает
  окно добычи). Всё хранится у хоста в файле shared.json в "Документы\\Warband Coop Campaign" и
  остаётся от сессии к сессии, поэтому без хоста казна и склад недоступны.
  СИГНАЛ К БОЮ: приглашение приходит со звуком и сообщением сразу, окно боя открывается на карте и
  поверх меню города, деревни или лагеря; отказ возвращает в то же меню. На прогулке по городу и в
  бою будет только звук и сообщение, окно откроется при выходе в меню. После согласия из города
  игрок окажется на карте. В окне моста при этом тоже появляется строка, с коротким сигналом.

НОВЫЕ СОВМЕСТНЫЕ БОИ
  ЛОГОВА БАНДИТОВ: подъехав к логову, выберите "CoopWorld: взять логово вместе". Бой идёт на сервере
  боя (не на карте логова из одиночной игры: на ней не могут ходить боты), на равнине карта лесная.
  Победа убирает логово из мира и засчитывает задание на него тому, кто начал бой.
  КАРАВАНЫ И КРЕСТЬЯНЕ: у кого рядом идёт бой с караваном или крестьянами, тот получает сообщение.
  Подъехав к бою, выберите "защитить вместе": выжившие защитники остаются на карте.
  ДЕРЕВНИ: когда напали на деревню, не враждебную вам, игроки получают сообщение. В меню деревни -
  "CoopWorld: прогнать налётчиков вместе". Рядом с вами бьются 15 крестьян. Победа снимает налёт, а
  начавшему бой даёт +3 к отношению с деревней. Бандиты, засевшие в деревне, этим не прогоняются.
  ДУЭЛИ: "другие игроки" - "Вызвать на дуэль", ставка 0-1000 динаров. Соперник видит ставку и может
  отказаться, при нехватке денег согласиться нельзя. Бой один на один на карте The Arena, в своём
  снаряжении, с полным здоровьем, без войск. Ни ран, ни плена, ни потерь; победитель забирает ставку,
  100 опыта победителю и 50 проигравшему. Если оба ушли с сервера, ничья и ставка остаётся.

ДРЕВО ВОЙСК
  "CoopWorld: древо войск". Слева ветви: шесть королевств, горожане и наёмники, женщины, разбойники
  и ваше собственное войско. Бойцы показаны портретами
  с линиями развития. Щелчок по портрету откроет карточку: уровень, здоровье, характеристики, жалованье, навыки, владение оружием, развитие и снаряжение.

СОБСТВЕННОЕ ВОЙСКО
  Отдельная ветвь войск, не привязанная к фракциям: рекрут и три ветви (пехота, лучники, всадники) до 5 тира,
  у каждого рода три уровня характеристик. Нужна новая кампания. В кооперативе войско создаёт хост, оно одно на
  всех: клиенты тоже нанимают, обучают и одевают, а если хост войска не создал, Джону им сказать нечего.
  ДЖОН БЛЭКБОРН: в лагере отряда и в любом вашем городе или замке. Он спросит название отряда и воинов,
  дальше нанимает рекрутов (5, 10 или 20, по 20 динаров), обучает, одевает, переименовывает (только хост).
  РОСТ: рекрут и воины растут в бою как обычно, в пехоту или лучников. Движок даёт войску только два пути,
  поэтому всадниками рекруты становятся у Джона, за 100 динаров с человека.
  СНАРЯЖЕНИЕ: слева что можно купить, справа что есть; щелчок покупает или продаёт. Тир воина ограничивает выбор,
  коней получают только всадники. Цена - стоимость предмета, умноженная на 4, Торговля её снижает; продажа - половина
  стоимости, Торговля её повышает. Снаряжение общее на всех воинов одного рода и одного тира (так устроен движок),
  и у всех игроков; пока для старшего тира ничего не покупали, он носит то же, что младший. За то, что досталось
  от младшего тира, при продаже денег нет.
  ОБУЧЕНИЕ: уровень 2 и 3 за всех воинов одного рода на этом уровне, цена зависит от тира, Торговля на неё не влияет.
  Игра не даёт скрипту прочитать опыт отряда, поэтому накопленный к следующему тиру опыт обучение обнуляет.

ФРАКЦИИ
  Каждый игрок может присягнуть своему королевству обычным разговором с королём или лордом.
  Мир знает, кому служит каждый игрок: лорды его королевства его не трогают, враги королевства на
  него охотятся, другие игроки видят на карте цвет его фракции. Игроки враждующих королевств
  сражаются друг с другом в совместных боях; приглашение в бой против ваших союзников отклоняется
  само. Владения (замки, города, деревни) пока получает только хост: клиенту король их не выдаёт -
  игра сообщит об этом, присяга и звание при этом остаются. Дипломатия (договоры между
  королевствами, послы, дары, патрули, вербовщики) - тоже только у хоста.

ВАШ ГЕРОЙ МЕЖДУ СЕССИЯМИ
  Друг каждый раз загружает свежее сохранение хоста, но играет своим героем: мост хоста хранит
  героя каждого игрока (profiles.json рядом с host.bat) под его именем в мультиплеере из join.bat -
  деньги, опыт, известность, честь, присягу, атрибуты, навыки, владение оружием, весь инвентарь,
  войска (и раненых), пленных, место на карте. При подключении герой возвращается сам. Имя в
  join.bat должно оставаться тем же. Опыт можно только добавить: уровень не станет ниже, чем у
  героя хоста. Нераспределённые очки навыков и атрибутов не сохраняются - распределите их до
  выхода. Клиенты тоже получают недельный бюджет (жалованье войскам, доходы) и читают книги.

ОСТАНОВКА
  В своей игре: Лагерь - "CoopWorld: кооператив..." - "CoopWorld: остановить кооператив", затем закройте окно моста.

ЕСЛИ ЧТО-ТО НЕ ТАК
  - Мост пишет журналы в Документы\\Warband Coop Campaign (у хоста bridge.log и trace.log, у друга join.log;
    строки журнала друга попадают и в bridge.log хоста) и каждые 5 секунд выводит строку состояния.
  - После сессии хост дважды щёлкает check_logs.bat: отчёт о сессии (бои, кто и когда замолчал,
    что не дошло) - на экране и в Документы\\Warband Coop Campaign\\report.txt.
  - Сообщая об ошибке в Discord ({DISCORD}), приложите report.txt, rgl_log.txt из папки Warband
    (скопируйте его до перезапуска игры) и опишите, что делали и у кого (хост или друг) случилось.
    При зависании напишите, нагружает ли игра процессор (Диспетчер задач).
  - Окно моста пишет, что Python не найден: запустите install.bat ещё раз и согласитесь
    установить программы (или Programs\\python-...exe, отметив "Add python.exe to PATH");
    если не помогло - перезагрузите компьютер.
  - "cannot reach the host": проверьте адрес хоста, пароль и что Radmin VPN включён у обоих.
'''

README = f'''{PROJECT} {VERSION} - co-op campaign for Mount & Blade: Warband 1.174
=========================================================================
Unofficial free fan mod, not affiliated with TaleWorlds Entertainment. Built on Diplomacy 1.174
with Freelancer. The mod's entries in the game's menus start with "CoopWorld:" (its working name).
It needs a new campaign.

  Discord (questions, bugs, finding players): {DISCORD}
  Support the development (optional, gives nothing beyond the free mod): {BOOSTY}

NEEDS: every player's own Warband 1.174 (Steam or GOG) with its serial key (multiplayer needs it,
  and two players cannot join with one key); Python 3 and Radmin VPN - their installers are in the
  Programs folder and install.bat offers the missing ones (PowerShell is part of Windows 10/11, nothing
  to install). The host's PC must
  let Python accept connections on port 7350, TCP and UDP (Windows asks once: allow on private and
  public networks - Windows often counts Radmin's network as public).

INSTALL (every player):
  1. Unpack the whole archive, best into the game's folder (the installer finds the game faster);
     do not run it from inside the archive.
  2. Close Warband and double-click install.bat. It shows which programs are there (Python 3,
     Radmin VPN) and offers to install the missing ones (Python by itself, with PATH; Radmin VPN in
     its own installer), then finds the game (the package's folder, GOG, Steam) or asks
     for the folder, and installs the Warband Coop Campaign module (a copy of your Native with the mod's files).
     It waits for Enter so you can read any error; everything it did is in install.log.
  3. In the launcher pick the Warband Coop Campaign module and Start windowed (joint battles need two windows).
  If install.bat does not open, run the installer by hand: Start - Windows PowerShell, then
    powershell -ExecutionPolicy Bypass -File "<package folder>\\install.ps1" "<Warband folder>"

BEFORE PLAYING (everybody): open Radmin VPN and check that the network is up and stable.

HOST (runs the world):
  1. Double-click host.bat: it asks for a password (any, tell it your friends; Enter without one
     = this PC only) and your multiplayer name, and starts the bridge. Keep its window open.
  2. Start Warband with Warband Coop Campaign, load your campaign,
     Camp - "CoopWorld: co-op..." - "run this game as the WORLD SERVER and play in it (host)".
  3. For each joining player: Camp - "CoopWorld: co-op..." - "hold the world for a joining client",
     then save the game (Esc - Save). The friend's join.bat fetches it; the world runs on as soon
     as that player joined.

FRIEND:
  1. Double-click join.bat: the host's address (from Radmin VPN), password and your multiplayer
     name. It fetches the host's newest save into your Warband Coop Campaign saves and keeps the link.
     If the host has not saved yet (a new campaign), it waits: the save comes once the host saves.
  2. Start Warband with Warband Coop Campaign and load that save. Wait about 5 seconds: the game becomes a
     CLIENT of the host's world by itself. If it does not: Camp - "CoopWorld: co-op..." -
     "let the world run again (stop holding it)", and you are synchronised.
  Every later save of the host lands in the same slot (the old one becomes .bak).

SAVES (host and friends): the bridge sends the friends the host's newest save (by time) from
    Documents\\Mount&Blade Warband Savegames\\Warband Coop Campaign
  Saves of another campaign or old tests in that folder may make it send the wrong one, so on the
  host's PC and on every friend's PC keep only the current co-op campaign's saves there: move the
  others elsewhere (or delete them) before starting host.bat / join.bat.
  - Host: save (Esc - Save) before a friend joins - that save is the one sent.
  - Every save of the host goes to all friends connected; one made while a friend's link was down
    comes as soon as that friend's bridge is back.
  - A friend loads the slot join.bat names ("... now holds it"), no other.

HOW IT WORKS: the world lives at the host; every player has a party on the same map (up to 4).
  While anybody is in a battle, an encounter or a menu, the world stands still for all. A player
  whose clock ran 3 hours ahead of the world does not rest until the world catches up (moving is
  free); one 3 hours behind rests three times faster.

SERVING A LORD (Freelancer): two players serving the same lord fight beside him together: when he
  goes into a field battle the soldier menu opens - "CoopWorld: fight beside your commander".

JOINT BATTLES (multiplayer server):
  A limit of the game's engine: joint battles are fought ONLY in a second game window. So before
  each battle either start a second window to join the battle, or keep the second window open on
  the battle server all the time.
  1. The host starts a second Warband window (Warband Coop Campaign) and fights in it: Multiplayer -
     Host a game, game type Battle, any field map, 0 bots. Then pick any side and any equipment
     and forget about that window until the battle. The bridge finds it by itself.
  2. Every friend joins it from a second Warband window through the bridge (join.bat's window
     open): Multiplayer - Join a Game - Local Area Network - Refresh. For the bridge's server to
     show up there, join.bat offers once to turn on Warband's look_for_server_on_this_machine:
     agree (with Warband closed). If two identical servers show up, one goes straight over Radmin,
     where Warband refuses with "invalid authorization number": join the other and Add to
     Favorites. Join under exactly the multiplayer name given to host.bat / join.bat. Every
     player needs a different name.
  3. In an encounter: "CoopWorld: fight together with your friends". Players within 40 map units are invited;
     the battle server restarts its round with the campaign's armies. Sides and heroes are given
     by the server (if a team window opens all the same, close it with Esc).
     The invitation waits 45 s. A player who answers later still fights as the hero, but without
     the troops. A player the battle server has no hero for yet (came to the server late, or under
     another name) does not spawn with multiplayer gear: the bridge sends the hero once it finds
     the player, who then spawns on the right side.
  4. The battle lasts until one side has nobody left, bots and heroes. A fallen hero does not come
     back into that battle. The losses go back to the campaign.
  You fight as your hero: equipment, attributes, combat skills, proficiencies and health (now and
  at most) go to the battle server; health, experience and proficiency gains come back, and your
  troops gain experience as after a Native battle. The winners may take prisoners: every fallen
  enemy of a player's share, killed or wounded, is taken with a chance by the hero's Prisoner
  Management: 10% at level 1, 5% more for each further level (none at level 0), room permitting.
  Companions fight as bots under your command. Big armies are scaled down to 150 bots.
  Not carried yet: item quality (tempered, heavy, rusty...) - the hero has the same items on the
  battle server, of plain quality.
  JOINT SIEGES: in the siege menu - "CoopWorld: storm the walls together". The battle server
  switches to Siege on a castle map: the garrison (team 1) holds the walls, the players (team 2)
  storm them. Bots fight on foot; the server raises the ladders and sends storming bots stuck
  under a wall to them. JOINT DEFENCE: "CoopWorld: defend the walls together" when a world army
  besieges a center of your side.

ARENA, TOURNAMENT AND TRAINING TOGETHER: on the same battle server, in the second window. Only the
  players' heroes fight, all on one side, in practice gear and at full health, without troops or
  companions. Only the prize reaches the campaign: no wounds, no losses. Players nearby are invited
  (see CALL TO BATTLE); a friend in the same town may also pick the same option
  while the event gathers. It starts when all who agreed stand on the battle server; after 1 min 45 s
  it goes on without those who did not come. Be on the battle server beforehand.
  ARENA: town menu - "CoopWorld: fight in the arena together" (by day, not in disguise). 20 opponents
  per player, the weak ones first, 3 per player at a time. Who stands at the end gets the arena's
  grand prize (250 denars), who falls the prize for the opponents beaten, as in the single player
  game. Map: The Arena.
  TOURNAMENT: town menu, when the town holds one - "CoopWorld: join the tournament together". First a
  bet on the whole team (5-100 denars, or none). Four rounds in a row, as many opponents as players
  (NxN), stronger each round; the team stands while one hero does, and all come back next round.
  Won: every player gets 200 denars, 250 experience, 20 renown, +1 with the town and what all the
  team's bets won. Lost: who bet loses the stake only (taken at the end: a cancelled tournament
  costs nothing). Map: The Arena.
  TRAINING: training ground - "CoopWorld: train together with your friends", then 1 to 4 opponents
  per player: your own men (arena fighters if you have too few) with practice weapons. Experience
  as in a single player training: by the share beaten, how hard it was and the Trainer skill; the
  men who fought gain more. Map: Field by the River.

TOGETHER WITHOUT MEETING ON THE MAP: all in Camp - CoopWorld: co-op.
  RIDE AFTER A FRIEND: "the other players" - "Ride after ...". Your party rides to the friend and stays
  close; a click of your own on the map stops it. If the party ignores the order, the game moves it
  to the friend and says so.
  THE COMPANY'S CAMP: one for all, on everybody's map. Camp - CoopWorld - "set up the company's camp here"
  (1000 denars), then ride there or click it. It holds the treasury, the store and John Blackborn.
  SHARED TREASURY AND PARTY STORE: in the company's camp only. The store is open for one
  player at a time; up to 96 things (what the loot window holds). They are kept at the host, in
  shared.json in "Documents\\Warband Coop Campaign", from session to session: no host, no treasury.
  CALL TO BATTLE: an invitation comes with a sound and a message at once; its window opens on the map
  and over a town's, a village's or the camp's menu, and declining goes back to that menu. Walking in
  a town or in a battle you get the sound and the message, the window waits for the next menu.
  Accepting from a town leaves you on the map afterwards. The bridge's window shows it too, with a beep.

NEW JOINT BATTLES
  BANDIT LAIRS: at a lair - "CoopWorld: storm the hideout together". Fought on the battle server (not on
  the single player lair's map: bots cannot walk there). Won: the lair is gone from the world and the
  quest on it counts for who began the battle.
  CARAVANS AND FARMERS: a message tells of a fight beside you. Ride up and choose to defend them; the
  defenders who live go on.
  VILLAGES: a message tells of a raid on a village not hostile to you. Village menu - "CoopWorld: drive the
  raiders off together": 15 villagers fight beside you. Won: the raid ends, +3 relation with the village
  for who began the battle. Bandits settled inside a village are not covered by this.
  DUELS: "the other players" - "Challenge ... to a duel", stake 0-1000 denars. The other player sees the
  stake, may decline, and cannot accept without the money. One against one on The Arena, in your own
  gear, at full health, no troops. No wounds, no prisoners, no losses; the winner takes the stake, 100
  experience for the winner, 50 for the loser. If both leave the server it is a draw.

TROOP TREE: "CoopWorld: the troop tree". The kingdoms, townsfolk and mercenaries, women, outlaws, and your own
  army. Troops are portraits joined by
  upgrade lines; click one for its card: level, hit
  points, attributes, wage, skills, proficiencies, upgrades and equipment.

YOUR OWN ARMY: a branch of troops of no faction: a recruit and three branches (infantry, archers, riders) up to
  tier 5, each kind in three levels of stats. It needs a new campaign. In co-op the host raises it and it is the same
  for everyone: clients hire, train and equip too; if the host has not raised it, John has nothing to say to them.
  JOHN BLACKBORN: at the company's camp and in any town or castle of yours. He asks for the names, then hires
  recruits (5, 10 or 20 at 20 denars), trains, equips, renames (the host only).
  GROWTH: recruits and soldiers rise by battle as usual, into infantry or archers. The engine gives a troop two
  paths, so recruits become riders at John's, for 100 denars a man.
  GEAR: what can be bought on the left, what the soldier has on the right; a click buys or sells. The tier limits the
  choice, only riders get horses. An item costs 4 times its value, less with Trade; it sells for half its value,
  more with Trade. Gear is shared by all soldiers of a kind and tier (the engine works so) and by all players; a
  higher tier wears what the lower one wears until something is bought for it. What came from a lower tier sells
  for nothing.
  TRAINING: levels 2 and 3, for all the men of a kind at that level, at a price set by the tier, Trade does not
  change it. No script can read a party's experience, so training clears what was gathered towards the next tier.

FACTIONS: each player may swear fealty to a kingdom as usual; its lords leave the player alone, its
  enemies hunt the player. Fiefs and Diplomacy's diplomacy go only to the host for now.

YOUR HERO BETWEEN SESSIONS: the host's bridge keeps each player's hero (profiles.json next to
  host.bat) under the multiplayer name given to join.bat and puts it back on joining. Keep the name.

Stopping: Camp - "CoopWorld: co-op..." - "CoopWorld: stop co-op", then close the bridge window.

Something went wrong: after the session the host double-clicks check_logs.bat - a report in
Documents\\Warband Coop Campaign\\report.txt (in Russian). Post it on Discord ({DISCORD}) with rgl_log.txt from
the Warband folder (copied before the game restarts) and what happened, and to whom.
'''

BOM = "\ufeff"


# Nexus Mods (dist/<version>/nexus): the same packages without the other programs' installers (Programs): Nexus
# takes only what the mod needs, and an installer that downloads things is not welcome there. The player
# gets Python and Radmin VPN from their sites; these passages of the texts say so instead. Nexus has
# its own donations, and its rules frown on asking for others: no Boosty link there.
UNBUNDLED = [
  (f"""  Поддержать разработку (по желанию, ничего не даёт сверх бесплатной версии): {BOOSTY}
""", ""),
  (f"""  Support the development (optional, gives nothing beyond the free mod): {BOOSTY}
""", ""),
  ("""   - Закройте Warband и дважды щёлкните install.bat. Он предложит установить недостающие
     программы (Python 3, Radmin VPN) из папки Programs и сам поставит мод.
""", f"""   - Установите Python 3 ({PYTHON_URL}, отметьте "Add python.exe to PATH")
     и Radmin VPN ({RADMIN_URL}), если их ещё нет. Закройте Warband и дважды щёлкните
     install.bat: он проверит программы и сам поставит мод.
"""),
  ("""   install.bat: it offers to install the missing programs (Python 3, Radmin VPN) from
   the Programs folder and installs the mod.""", f"""   install.bat: it checks for Python 3 and Radmin VPN (if missing, install them from
   {PYTHON_URL} - tick "Add python.exe to PATH" - and {RADMIN_URL})
   and installs the mod."""),
  ("""  - Python 3 и Radmin VPN. Их установщики лежат в папке Programs, install.bat предложит
    поставить недостающие. Больше ничего ставить не нужно: PowerShell уже есть в Windows 10/11.
""", f"""  - Python 3 ({PYTHON_URL}; при установке отметьте "Add python.exe to PATH")
    и Radmin VPN ({RADMIN_URL}); install.bat проверит, есть ли они. Больше ничего
    ставить не нужно: PowerShell уже есть в Windows 10/11.
"""),
  ("""     - Сначала он покажет, какие программы уже есть (Python 3, Radmin VPN), и спросит,
       установить ли недостающие. Python ставится сам (и сразу попадает в PATH), у Radmin VPN
       откроется его обычный установщик.
""", """     - Сначала он покажет, какие программы уже есть (Python 3, Radmin VPN), а для
       недостающих - откуда их скачать.
"""),
  ("""  - Окно моста пишет, что Python не найден: запустите install.bat ещё раз и согласитесь
    установить программы (или Programs\\python-...exe, отметив "Add python.exe to PATH");
    если не помогло - перезагрузите компьютер.
""", f"""  - Окно моста пишет, что Python не найден: установите Python 3 ({PYTHON_URL}),
    отметив "Add python.exe to PATH"; если не помогло - перезагрузите компьютер.
"""),
  ("""Python 3 and Radmin VPN - their installers are in the
  Programs folder and install.bat offers the missing ones (PowerShell is part of Windows 10/11, nothing
  to install).""", f"""Python 3 ({PYTHON_URL} -
  tick "Add python.exe to PATH") and Radmin VPN ({RADMIN_URL}); install.bat checks for them
  (PowerShell is part of Windows 10/11, nothing to install)."""),
  ("""It shows which programs are there (Python 3,
     Radmin VPN) and offers to install the missing ones (Python by itself, with PATH; Radmin VPN in
     its own installer), then finds the game""", """It shows which programs are there (Python 3,
     Radmin VPN) and where to get the missing ones, then finds the game"""),
]


def unbundled(text, used):
  """A README or START HERE for the Nexus packages: the UNBUNDLED passages replaced (their numbers go
  to `used`); none may still send the player to the Programs folder or to Boosty."""
  for k, (old, new) in enumerate(UNBUNDLED):
    if old in text:
      text = text.replace(old, new)
      used.add(k)
  if "Programs" in text:
    raise SystemExit("a text of the Nexus packages still sends players to the Programs folder: see UNBUNDLED")
  if BOOSTY in text:
    raise SystemExit("a text of the Nexus packages still has the Boosty link: see UNBUNDLED")
  return text


DEBUG_RU = r"""ОТЛАДОЧНАЯ СБОРКА Warband Coop Campaign

Это та же игра, но она сообщает мосту всё, что делает: меню, пункты меню, реплики, экраны, триггеры, начало
сцены. Такой след нужен, чтобы увидеть, что было последним перед зависанием или вылетом. Сохранения те же, что
у обычной сборки: играйте дальше с того же места.

1. Поставьте эту сборку (install.bat) и хост, и друг. Смешивать её с обычной нельзя: мост предупредит о разных сборках.
2. Играйте как всегда, запуская хост и друга обычными host.bat и join.bat.
3. Случился вылет или зависание: закройте игру, окно моста можно закрыть после этого.
4. Хост запускает check_logs.bat. В report.txt появятся раздел "След действий", последние действия перед каждым
   молчанием и журнал Windows с кодами вылетов.
5. Пришлите из папки Документы\Warband Coop Campaign: хост - report.txt и trail.log, друг - join.log и trail.log.

Чтобы вернуться к обычной сборке, поставьте обычный пакет поверх этого.

Самое последнее действие перед зависанием может не дойти: движок мог зависнуть, не успев отправить запрос.
Бои на сервере боя в след не входят, их показывает trace.log. Без моста, в одиночной игре, следа нет.
"""

DEBUG_EN = r"""DEBUG BUILD of Warband Coop Campaign

The same game, but it tells the bridge all it does: menus, their options, lines of talk, screens, triggers, the
start of a scene. That trail shows what came last before a hang or a crash. It plays the same saves as the
usual build: go on from where you are.

1. Both the host and the friend install this build (install.bat). Do not mix it with the usual one: the bridge
   warns about different builds.
2. Play as always, starting with the usual host.bat and join.bat.
3. After a crash or a hang close the game; the bridge's window may be closed after that.
4. The host runs check_logs.bat. report.txt gets a section with the trail, the last actions before each silence
   and Windows' own log with the crash codes.
5. Send from Documents\Warband Coop Campaign: the host's report.txt and trail.log, the friend's join.log and trail.log.

To go back, install the usual package over this one.

The very last action before a hang may not arrive: the engine may hang before it sends the request. Battles on the
battle server are not in the trail, trace.log shows them. With no bridge, in a single-player game, there is no trail.
"""


def build(name, files, russian=False, programs=True, out=None, also=()):
    """dist/<name>.zip (or `out`), everything in the folder <name>; programs: with the Programs folder;
    also: more files for the folder of coop_bridge.py."""
    out = out or DIST / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(MODULE.glob("*.txt")):
            if f.name not in BUILD_ONLY:
                z.write(f, f"{name}/Warband Coop Campaign/{f.name}")
        for source, rel in assets():  # Diplomacy's textures and changed scenes
            z.write(source, f"{name}/Warband Coop Campaign/{rel}")
        z.write(ROOT / "tools" / "coop_bridge.py", f"{name}/coop_bridge.py")
        z.write(ROOT / "tools" / "coop_logs.py", f"{name}/coop_logs.py")
        for f in also:
            z.write(f, f"{name}/{f.name}")
        for arcname, text in files.items():
            z.writestr(f"{name}/{arcname}", text.encode("utf-8"))
        if russian:
            # the module's Russian texts, complete (the russifier's Native plus Warband Coop Campaign's), and the
            # russifier's engine interface for the game's own languages folder
            for f in sorted((MODULE / "languages" / "ru").glob("*.csv")):
                z.write(f, f"{name}/Warband Coop Campaign/languages/ru/{f.name}")
            for f in sorted(RUSSIFIER_UI.glob("*.csv")):
                z.write(f, f"{name}/languages/ru/{f.name}")
        for f in prereqs() if programs else ():  # installers are compressed already
            z.write(f, f"{name}/Programs/{f.name}", compress_type=zipfile.ZIP_STORED)
    print(f"{out} ({out.stat().st_size // 1024} KB)")


def prereqs():
    """The installers for the Programs folder: Python, Radmin VPN (vendor/prereqs)."""
    found = []
    for pattern in ("python-*.exe", "Radmin_VPN*.exe"):
        files = sorted(PREREQS.glob(pattern))
        if files:
            found.append(files[-1])
        else:
            print(f"warning: no {pattern} in {PREREQS}: the package has no installer for it")
    return found


def debug_packages(base, en, ru):
    """dist/<version>-debug: the game telling the bridge what it does (src/trail). The module's folder
    goes back to the plain build afterwards."""
    DEBUG.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "build.py"), "--trail"], check=True, stdout=subprocess.DEVNULL)
    try:
        names = [MODULE / "trail_names.json"]
        build(f"{base}-debug", {**en, "DEBUG.txt": DEBUG_EN}, out=DEBUG / f"{base}-debug.zip", also=names)
        build(f"{base}-debug-ru", {**ru, "ОТЛАДКА.txt": BOM + DEBUG_RU}, russian=True,
              out=DEBUG / f"{base}-debug-ru.zip", also=names)
    finally:
        subprocess.run([sys.executable, str(ROOT / "build.py")], check=True, stdout=subprocess.DEVNULL)


def main():
    if not (MODULE / "scripts.txt").exists():
        raise SystemExit("build the module first: python build.py")
    DIST.mkdir(parents=True, exist_ok=True)
    base = f"{PROJECT.replace(' ', '-')}-{VERSION}"
    launchers = {lang: {"host.ps1": BOM + launcher("host", lang), "join.ps1": BOM + launcher("join", lang),
                        "host.bat": launcher_bat("host"), "join.bat": launcher_bat("join"),
                        "check_logs.ps1": BOM + check_logs(lang), "check_logs.bat": launcher_bat("check_logs")}
                 for lang in ("en", "ru")}
    if not RUSSIFIER_UI.exists() or not (MODULE / "languages" / "ru" / "dialogs.csv").exists():
        raise SystemExit("no Russian: put the russifier in vendor/l10n_ru and run python tools/make_ru.py")
    def english(texts):
        return {"install.ps1": BOM + INSTALL_PS1, "install.bat": INSTALL_BAT, "README.txt": texts(README),
                "START HERE.txt": texts(START_HERE), **launchers["en"]}

    def russian(texts):  # PowerShell 5 reads a script without BOM in the ANSI code page: every .ps1 gets one
        return {"install.ps1": BOM + INSTALL_RU_PS1, "install.bat": INSTALL_BAT, "README.txt": BOM + texts(README_RU),
                "НАЧНИТЕ ЗДЕСЬ.txt": BOM + texts(START_HERE_RU), **launchers["ru"]}

    if "--trail" in sys.argv:
        return debug_packages(base, english(str), russian(str))
    nexus = DIST / "nexus"
    nexus.mkdir(exist_ok=True)
    used = set()
    for programs in (True, False):  # the packages, then the same for Nexus Mods without Programs
        texts = (lambda text: text) if programs else (lambda text: unbundled(text, used))
        build(base, english(texts), programs=programs, out=None if programs else nexus / f"{base}-nexus.zip")
        build(f"{base}-ru", russian(texts), russian=True,
              programs=programs, out=None if programs else nexus / f"{base}-nexus-ru.zip")
    if len(used) != len(UNBUNDLED):
        raise SystemExit(f"UNBUNDLED passages no longer in the texts: {sorted(set(range(len(UNBUNDLED))) - used)}")


if __name__ == "__main__":
    main()
