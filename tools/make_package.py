"""Build the CoopWorld packages for players: dist/CoopWorld-<date>.zip (English) and
dist/CoopWorld-ru-<date>.zip (Russian: game texts, installer and instructions).

They hold only what CoopWorld adds: the compiled module files (*.txt), Diplomacy's textures and
changed scenes (tools/dplmc_assets.py), the bridge and an installer.
No game files: the installer copies each player's own Modules/Native to Modules/CoopWorld and puts
the compiled files over it. The Russian one also adds CoopWorld's Russian texts
(tools/make_ru.py) to the copy of Native's languages/ru.

    python tools/make_ru.py && python tools/make_package.py
"""
import datetime
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tools/dplmc_assets.py, also under python -I
from dplmc_assets import assets  # noqa: E402

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
    mp_name_hint="Joint battles: the name you use on the battle server (Multiplayer - Profiles). Your soldiers obey you only under this name.",
    ask_mp_name="Your multiplayer name (Enter = keep the one in brackets)",
    mp_name_set="Multiplayer name:",
    no_mp_name="No multiplayer name: the bridge looks for your hero's name on the battle server.",
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
    mp_name_hint="Совместные бои: имя, под которым вы заходите на сервер боя (Мультиплеер - Профили). Только под этим именем ваши солдаты будут вас слушаться.",
    ask_mp_name="Ваше имя в мультиплеере (Enter - оставить то, что в скобках)",
    mp_name_set="Имя в мультиплеере:",
    no_mp_name="Имя в мультиплеере не задано: мост будет искать на сервере боя имя вашего героя.",
  ),
}


def launcher(kind, lang):
    m = LAUNCHER_TEXT[lang]
    title = {"host": {"en": "CoopWorld: host the game (the world lives on this PC)", "ru": "CoopWorld: запуск игры у хоста"},
             "join": {"en": "CoopWorld: join a friend's game", "ru": "CoopWorld: подключение к игре друга"}}[kind][lang]
    body = (HOST_BODY if kind == "host" else JOIN_BODY).format(**m) + MP_NAME_BODY.format(**m)
    return LAUNCHER_TEMPLATE.format(title=title, body=body, **m)


START_HERE_RU = '''CoopWorld - С ЧЕГО НАЧАТЬ (для друга)
====================================

1. Нужно один раз:
   - Mount & Blade: Warband 1.174 (Steam или GOG) с серийным ключом (нужен для мультиплеера).
   - Python 3 с python.org (при установке отметьте "Add python.exe to PATH").
   - Radmin VPN (или ZeroTier): войдите в сеть, которую создал хост.
2. Распакуйте весь архив в любую папку, закройте Warband, дважды щёлкните install.bat.
   В лаунчере Warband выберите модуль CoopWorld (Configure - Game - Language: ru).
3. Каждый раз перед игрой:
   - дважды щёлкните join.bat: адрес хоста (из Radmin VPN), пароль хоста, ваше имя в мультиплеере
     (то же, что в игре: Мультиплеер - Профили; запомнится). Окно моста не закрывайте.
   - Запустите Warband (CoopWorld), загрузите свежее сохранение хоста (join.bat его скачал),
     Лагерь - "CoopWorld: кооператив..." - "CoopWorld: сделать эту игру КЛИЕНТОМ". Ваш герой вернётся сам.
4. Для совместных боёв запустите второе окно Warband (CoopWorld): Мультиплеер - Избранное -
   добавьте адрес хоста с портом 7240 (например 26.x.x.x:7240) и зайдите на сервер боя хоста.
Подробности - README.txt.
'''

START_HERE = '''CoopWorld - START HERE (for a friend)
=====================================

1. Once: Warband 1.174 (Steam or GOG) with its serial key (multiplayer needs it); Python 3 from
   python.org ("Add python.exe to PATH"); Radmin VPN or ZeroTier, in the host's network.
2. Unpack the whole archive, close Warband, double-click install.bat. Pick CoopWorld in the launcher.
3. Every time: double-click join.bat (the host's address, the host's password, your multiplayer
   name - the one of your Multiplayer profile). Keep its window open. Start Warband (CoopWorld),
   load the host's save join.bat fetched, Camp - "CoopWorld: co-op..." - "run this game as a CLIENT". Your hero comes back.
4. For joint battles start a second Warband window (CoopWorld): Multiplayer - Favorites - add the
   host's address with port 7240 (e.g. 26.x.x.x:7240) and join the host's battle server.
More in README.txt.
'''


def launcher_bat(kind):
    return f'@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0{kind}.ps1" %*\r\n'


README_RU = '''CoopWorld - кооперативная кампания для Mount & Blade: Warband 1.174
====================================================================
Основа - мод Diplomacy 1.174 (с Freelancer). Нужна новая кампания: старые сохранения
CoopWorld без Diplomacy с этой версией не работают.

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
       Лагерь - "CoopWorld: кооператив..." - "CoopWorld: сделать эту игру СЕРВЕРОМ МИРА и играть в ней (хост)".
     Вы играете прямо в этом окне: мир живёт в нём, друзья видят ваш отряд на карте.
     Окна, которые мир открывает сам, у хоста мир не останавливают: сообщения и недельный бюджет
     приходят строкой в журнал, а известия с выбором (война, приглашения, спутники, гонцы маршала)
     копятся - откройте их, когда удобно: Лагерь - "CoopWorld: кооператив..." - "прочитать отложенные известия".
  3. Для каждого подключающегося игрока:
       Лагерь - "CoopWorld: кооператив..." - "CoopWorld: удержать мир для подключения игрока", затем сохраните игру (Esc - Сохранить).
     Сохранение отдайте другу (join.bat скачает его сам). Как только друг подключится, мир пойдёт дальше;
     можно и самому: там же "пустить мир дальше (перестать удерживать)".
  Можно и по-старому: отдельное окно - только сервер мира ("...только СЕРВЕРОМ МИРА (без игры в ней)"),
  а играть во втором окне клиентом. Это тяжелее для компьютера, зато мир не зависит от ваших меню.

ДРУГ
  1. Дважды щёлкните join.bat. Он спросит адрес хоста и пароль, скачает свежее сохранение хоста
     в ваши сохранения CoopWorld и будет держать связь. Окно моста не закрывайте, пока играете.
  2. Запустите Warband с модулем CoopWorld, загрузите это сохранение,
     Лагерь - "CoopWorld: кооператив..." - "CoopWorld: сделать эту игру КЛИЕНТОМ". Мир хоста пойдёт дальше, как только вы подключитесь.
  Каждое сохранение хоста join.bat сам кладёт в тот же слот ваших сохранений (старое - .bak), а игра
  пишет "хост сохранил игру". В следующий раз загружайте этот слот - мир будет самым свежим.
  Герой получает имя, которое вы ввели в join.bat (у хоста - в host.bat).

ИГРОКИ ВМЕСТЕ
  Всё это работает одинаково у друга и у хоста, который играет в окне сервера мира.
  Лагерь - "CoopWorld: кооператив..." - "CoopWorld: другие игроки": кто в мире и как далеко; попроситься в отряд (откуда угодно),
  передать войска (если игрок рядом, до 3 км), записать своего героя у хоста прямо сейчас.
  Встретив на карте отряд другого игрока, сразу открывается меню (без разговора), где можно:
  - "сразиться с этим игроком" (совместный бой);
  - "попроситься в отряд этого игрока": он примет или откажет. Принятый следует за лидером по карте
    и вызывается во все его совместные бои (отказаться нельзя). Покинуть отряд - Лагерь - "CoopWorld:
    кооператив..." (или "другие игроки"); лидер может отпустить всех последователей там же.
  - "передать войска этому игроку": выберите бойцов в окне обмена и отправьте; получатель примет
    или откажется, отвергнутые бойцы вернутся (даже если вы успели выйти - при следующем входе).

ВАШ ГЕРОЙ МЕЖДУ СЕССИЯМИ
  Каждый раз друг загружает свежее сохранение хоста, но играет своим героем: мост хоста хранит героя
  каждого игрока (profiles.json рядом с host.bat) под его именем в мультиплеере из join.bat - деньги,
  опыт, известность, честь, присягу, атрибуты, навыки, владение оружием, весь инвентарь, войска
  (и раненых), пленных, место на карте. При подключении герой возвращается сам. Имя в join.bat
  должно оставаться тем же. Опыт можно только добавить: уровень не станет ниже, чем у героя хоста.
  Нераспределённые очки навыков и атрибутов не сохраняются - распределите их до выхода.
  Клиенты теперь тоже получают недельный бюджет (жалованье войскам, доходы), читают книги.

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
  Важно:
  - У каждого игрока своя лицензия Warband (свой ключ / свой аккаунт Steam). С одним ключом на один
    сервер вдвоём не зайти - игра скажет, что ключ неверный. Ключ Steam-версии: Steam - Библиотека -
    правый клик по Warband - Управление - Ключи продукта; ключ GOG к Steam-версии не подходит.
  - Оба окна Warband запускайте в оконном режиме (лаунчер - Configure - Start windowed): полноэкранная
    игра при переключении сворачивается и замирает, мир встаёт у всех, а запросы не уходят.
  - Сервер боя создавайте в только что запущенном окне Warband, где не загружалась кампания.
  1. Хост запускает второе окно Warband (модуль CoopWorld) - сервер боя, и сам в нём сражается:
       Мультиплеер - Создать игру, режим "Битва" (Battle), карта - любое поле, боты - 0.
     Мост сам находит этот сервер; без него кнопка совместного боя скажет, что сервера нет.
  2. Каждый друг заходит на этот сервер из второго окна Warband (модуль CoopWorld):
       Мультиплеер - список серверов (локальная сеть) или Избранное с адресом хоста, например 26.x.x.x:7240.
     host.bat и join.bat спрашивают ваше имя в мультиплеере (запоминают его в mp_name.txt): заходите
     на сервер боя ровно под этим именем - тогда мост сам ставит вас в нужную команду и отдаёт вам
     ваших солдат. Мост пишет в своём окне, кого он узнал на сервере боя ("recognised") и кого нет
     ("NOT found"). Имена у всех разные! Это же имя получает и ваш герой в кампании.
     Окно игры остаётся на сервере между боями.
  3. Во встрече с отрядом на карте выберите "CoopWorld: сразиться вместе с друзьями". Запрос уходит
     сразу; приглашённым, кто стоит на сервере боя, сервер пишет, что ответить нужно в окне кампании.
     Игроки поблизости получают приглашение ("В бой!" или "Отказаться"); через несколько секунд
     раунд на сервере боя начинается заново с армиями из кампании. Переключитесь в окно мультиплеера.
  4. Встреча с отрядом другого игрока: "CoopWorld: сразиться с этим игроком". Его вызывают в бой,
     отказаться нельзя; если он не зайдёт на сервер, его отряды сражаются без него.
  5. Когда одна из сторон перебита, потери возвращаются в кампанию: из павших бойцов игрока половина
     ранена, половина убита; разбитый отряд мира исчезает у всех. Пока идёт бой, мир стоит.
  Вы сражаетесь своим героем: его снаряжение (оружие, броня, конь), атрибуты, боевые навыки и
  владение оружием переносятся на сервер боя (до 4 героев в бою). После боя герой и отряд получают
  опыт за павших врагов (проигравшие - треть). Компаньоны выходят в бой ботами со своим снаряжением
  и навыками и подчиняются вам; павший компаньон возвращается тяжело раненым, но живым. Победители
  делят добычу с павших врагов (окно добычи, как после обычного боя). Карта полевого боя подбирается
  по местности: степь, лес, горы, снег, пустыня, река. Владение оружием растёт, как в обычном бою: за
  попадания по врагам и нанесённый урон тем видом оружия, которым вы сражались; чем выше владение,
  тем медленнее рост, предел задаёт навык "Владение оружием".
  Здоровье героя после боя сохраняется (павший в бою герой возвращается тяжело раненым).
  Проигравший отряду мира попадает в плен, как в обычной игре: его войска и компаньоны уходят
  к победителю пленными, часть вещей забирают. Проигравший другому игроку в плен не попадает,
  но его уцелевшие войска становятся пленными победителя.
  Большие армии уменьшаются до 150 ботов на поле, потери пересчитываются обратно.
  СОВМЕСТНАЯ ОСАДА: в меню осады (когда лестницы или башня готовы) - "CoopWorld: штурмовать стены
  вместе". Сервер боя сам переходит в режим "Осада" на одной из карт с замком: гарнизон (команда 1)
  держит стены, игроки (команда 2) штурмуют; игроки рядом получают приглашение. Штурм удался, если
  взят флаг или пал весь гарнизон: хост берёт замок как в обычной игре, а замок, взятый клиентом,
  переходит его королевству (клиенту без присяги штурм недоступен). Не удался - гарнизон теряет
  павших, осаду можно продолжить. Кому принадлежат замки и города, видно у всех игроков.
  СОВМЕСТНАЯ ОБОРОНА: когда армия мира осаждает замок или город вашей стороны, все игроки получают
  сообщение. Въехав в него или подъехав к воротам, выберите "CoopWorld: защищать стены вместе":
  игроки и гарнизон (команда 1) на стенах, осаждающий лорд и его армия (команда 2) штурмуют.
  Отбились - осаждающие теряют павших; не удержали стены - центр переходит их королевству,
  а защитники попадают в плен, как в обычной игре.
  Для мультиплеера Warband нужен серийный ключ игры (GOG: в библиотеке у игры, Steam: выдаётся сам).

ФРАКЦИИ
  Каждый игрок может присягнуть своему королевству обычным разговором с королём или лордом.
  Мир сервера знает, кому служит каждый игрок: лорды его королевства его не трогают, враги
  королевства на него охотятся, другие игроки видят на карте цвет его фракции.
  Игроки враждующих королевств сражаются друг с другом в совместных боях; приглашение в бой
  против ваших союзников отклоняется само. Владения (замки, города, деревни) пока получает только
  хост: клиенту король их не выдаёт - игра сообщит об этом, присяга и звание при этом остаются.
  Дипломатия (договоры между королевствами, послы, дары, патрули, вербовщики) - тоже только у хоста.

ОСТАНОВКА
  В своей игре: Лагерь - "CoopWorld: кооператив..." - "CoopWorld: остановить кооператив", затем закройте окно моста.

ЕСЛИ ЧТО-ТО НЕ ТАК
  - Мост пишет журнал в bridge.log в папке пакета и каждые 5 секунд выводит строку состояния.
  - Если окно моста пишет, что Python не найден: установите Python 3 с python.org и отметьте
    "Add python.exe to PATH".
  - "cannot reach the host": проверьте адрес хоста, пароль и что Radmin VPN/ZeroTier включён у обоих.
'''

README = '''CoopWorld - co-op campaign for Mount & Blade: Warband 1.174
=============================================================
Built on the Diplomacy 1.174 mod (with Freelancer). It needs a new campaign: saves of CoopWorld
without Diplomacy do not work with this version.

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
     Camp - "CoopWorld: co-op..." - "run this game as the WORLD SERVER and play in it (host)". You play in this window.
  3. For each joining player: Camp - "CoopWorld: co-op..." - "hold the world for a joining client", then save the game
     (Esc - Save). The world runs on as soon as that player joined.
  (Or the old way: one window only the world server ("...WORLD SERVER only (unattended)"),
  and you play in a second window as a CLIENT. Heavier, but the world does not wait for your menus.)

FRIEND:
  1. Double-click join.bat: it asks for the host's address and password, fetches the host's
     newest save into your CoopWorld saves and keeps the link. Keep its window open.
  2. Start Warband with CoopWorld, load that save, Camp - "CoopWorld: co-op..." - "run this game as a CLIENT".
     The host's world runs on as soon as you joined.

JOINT BATTLES (multiplayer server):
  1. The host starts a second Warband window (CoopWorld) and fights in it: Multiplayer -
     Host a game, game type Battle, any field map, 0 bots. The bridge finds it by itself.
  2. Every friend joins that server from a second Warband window (CoopWorld):
     the LAN server list, or Favorites with the host's address, e.g. 26.x.x.x:7240.
     host.bat and join.bat ask for your multiplayer name (kept in mp_name.txt): join the battle
     server under exactly that name, and the bridge puts you on your side and gives you command of
     your soldiers. The bridge window tells who it recognised there and who it did not.
     Every player needs a different name (friends' heroes come from the host's save, same name).
  3. In an encounter: "CoopWorld: fight together with your friends". Players nearby are invited;
     the battle server restarts its round with the campaign's armies. Switch to that window.
  4. Meeting another player's party: "CoopWorld: fight this player" (that player cannot decline).
  5. When one side is wiped out, the losses go back to the campaign (half of a player's fallen
     are wounded); a defeated world party is gone for everybody. The world stands still meanwhile.
  JOINT SIEGES: in the siege menu (ladders or a tower ready) - "CoopWorld: storm the walls together".
  The battle server switches to Siege on a castle map: the garrison (team 1) holds the walls, the
  players (team 2) storm them. Taken by the flag or when the garrison falls: the host takes the
  center as in Native; a client's kingdom gets it (a client without a kingdom cannot storm).
  JOINT DEFENCE: when a world army besieges a center of your side, everybody is told. In it or at
  its gates: "CoopWorld: defend the walls together" - the players and the garrison (team 1) hold
  the walls, the besieging lord and his army (team 2) storm them. Held: the besiegers lose their
  fallen. Lost: the center goes to their kingdom and the defenders are captured, as in Native.
  You fight as your hero: equipment (weapons, armour, horse), attributes, combat skills and
  weapon proficiencies go to the battle server (up to 4 heroes a battle). Afterwards the hero and
  the troops gain experience for the fallen enemies (the losers a third). Weapon proficiencies grow
  as in a Native battle: by the hits and damage you did with each kind of weapon, slower the better
  you are, within the weapon master limit. Companions fight as bots with their own gear and skills,
  under your command; a fallen companion comes back badly wounded. The winners share the fallen
  enemies' spoils (the loot screen). The field map fits the terrain the battle was met on.
  The hero keeps the health the battle left (a fallen hero comes back badly wounded). A player
  defeated by a party of the world is taken prisoner as in Native: troops and companions become
  its prisoners. A player defeated by another player is not captured, but the surviving troops
  become the winner's prisoners.

FACTIONS: each player may swear fealty to a kingdom by the usual talk with its king or a lord.
  The world server knows whom each player serves: that kingdom's lords leave the player alone,
  its enemies hunt the player, the others see the player's faction colour on the map. Players of
  kingdoms at war fight each other in joint battles; a call to arms against your allies is declined
  by itself. Fiefs go only to the host for now: a client is told so, and keeps oath and rank.

PLAYERS TOGETHER: meeting another player's party on the map you may ask to join it (that player
  accepts or declines; a follower follows the leader on the map and is called into all the leader's
  joint battles; leave in the camp menu, where the leader may release followers too), or give that
  player troops (chosen on the exchange screen; declined troops come back).

YOUR HERO BETWEEN SESSIONS: a friend loads the host's save every time but plays their own hero: the
  host's bridge keeps each player's hero (profiles.json next to host.bat) under the multiplayer name
  given to join.bat - gold, experience, renown, honor, allegiance, attributes, skills, proficiencies,
  inventory, troops (wounded too), prisoners, map position - and puts it back on joining. Keep the
  same name. Experience only grows (the level stays at least the host's hero's); unspent points are
  not kept. Clients now get the weekly budget (wages, income) too and can read books.

Stopping: Camp - "CoopWorld: co-op..." - "CoopWorld: stop co-op" in your game, then close the bridge window.
'''


BOM = "\ufeff"


def build(name, files, russian=False):
    out = ROOT / "dist" / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(MODULE.glob("*.txt")):
            if f.name not in BUILD_ONLY:
                z.write(f, f"{name}/CoopWorld/{f.name}")
        for source, rel in assets():  # Diplomacy's textures and changed scenes
            z.write(source, f"{name}/CoopWorld/{rel}")
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
                               "README.txt": README, "START HERE.txt": START_HERE, **launchers["en"]})
    if not RUSSIFIER_UI.exists() or not (MODULE / "languages" / "ru" / "dialogs.csv").exists():
        raise SystemExit("no Russian: put the russifier in vendor/l10n_ru and run python tools/make_ru.py")
    # PowerShell 5 reads a script without BOM in the ANSI code page: every .ps1 gets one
    build(f"CoopWorld-ru-{day}", {"install.ps1": BOM + INSTALL_RU_PS1, "install.bat": INSTALL_BAT,
                                  "README.txt": BOM + README_RU, "НАЧНИТЕ ЗДЕСЬ.txt": BOM + START_HERE_RU,
                                  **launchers["ru"]}, russian=True)


if __name__ == "__main__":
    main()
