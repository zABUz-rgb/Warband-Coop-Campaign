# История изменений

## 1.2

Меняются мост (`coop_bridge.py`) и игра. Хост и друзья должны поставить один и тот же пакет: мост версии 1.1
получит отказ с просьбой поставить тот же пакет. Кампанию 1.1 можно продолжать: новых войск и отрядов в игре нет,
новые меню и переменные добавлены в конец.

### Новое
- Обучение по тирам: Джон спрашивает, какой тир учить, и уровень растёт сразу у пехоты, лучников и всадников этого
  тира (рекрут - отдельный тир). Цена прежняя, как раньше за один вид. Если виды одного тира раньше учились по
  отдельности, тир стоит на уровне самого низкого из них, и обучение поднимает тех, кто на нём стоит.
- Шахта в своём полевом лагере за 2000 динаров. Любой игрок отправляет туда пленных (кроме лордов), каждый приносит
  10 динаров в казну раз в неделю игрового времени. Свернутый лагерь хранит шахту для следующего лагеря владельца.
- Войска можно оставлять в любом полевом лагере, до 80 человек, через экран обмена; брать и оставлять может любой
  игрок, по одному за раз. Казна раз в неделю платит им половину жалования, если не хватает - уходят самые дешёвые.
  Лагерь с людьми свернуть нельзя.
- Торговые караваны игроков: в лагере и у гильдмастера в городе. Бесплатно: 5 ближних городов или 18 городов по
  всему миру, до трёх в пути у каждого игрока. Шаги: охрана, деньги (выйти можно в любой момент), отправка; на каждом
  шаге «Отменить караван» возвращает деньги и людей. Караван - настоящий отряд в мире хоста: в каждом городе
  покупает товар, выгоднее всего продающийся в другом доступном городе, везёт и продаёт там (цены меняются, как от
  торговли игрока), обходит города королевств, воюющих с владельцем или с хостом. В конце пути деньги идут в казну,
  выжившие - в лагерь владельца (или хоста) от высшего тира к низшему, до 80 человек; остальные распускаются.
  Разбитый караван пропадает, все игроки получают сообщение.
- Кузнец в каждом городе: оружие и доспехи всех лавок Кальрадии по видам и ценам, на 20% дороже лавок.
- Совместная осада и оборона на службе у лорда (Freelancer). Лорд осаждает замок или город - в меню солдата
  «CoopWorld: штурмовать ... рядом с командиром»: игроки, лорд и армия, стоящая с ним лагерем, штурмуют вместе;
  взятый центр переходит королевству лорда, неудачный штурм оставляет осаду лорда идти дальше. Лорд внутри
  осаждённого центра своей стороны - «CoopWorld: держать стены ... рядом с командиром»: игроки, гарнизон и люди
  лорда на стенах. Лорд не погибает как отряд, даже если пали все его люди.
- Наделы друзей. Клиент с присягой королевству (вассал) держит замки, города и деревни в мире хоста через
  "заместителя" - лорда без отряда с его именем (до трёх вассалов). Центр, взятый им в совместной осаде, сразу
  становится его наделом; король может пожаловать центр королевства без лорда (новая реплика в разговоре с королём,
  решает известность + отношение x 20 >= 200 + 250 за каждый имеющийся надел). Раз в неделю мир хоста считает подати
  и пошлины наделов минус жалование гарнизонов, мост кладёт разницу другу в кошелёк (ждёт, пока друг не в игре).
  Гарнизоном друг распоряжается через экран обмена ("CoopWorld: гарнизон вашего надела"), изменение применяется в
  мире хоста, недостающие люди снова уходят из отряда друга. У клиента обычные пункты управления наделом скрыты,
  его копии этих центров не держат гарнизона и подати (бюджет не платит дважды). Наделы хоста у друзей больше не
  выглядят как свои: они показаны под именем хоста. Отношения с королями и лордами и присяга теперь хранятся в
  герое друга (профиль версии 3; старый профиль загружается без них).
- Подкрепления в совместных боях, как в одиночной игре: на поле одновременно до 150 бойцов кампании (каждая
  сторона по своей доле, не меньше 30 или всех, что у неё есть), остальные ждут в резерве. Сторона, потерявшая
  четверть своего места на поле, получает волну подкреплений из резерва, сообщение говорит, сколько ещё осталось.
  Бой кончается, когда у стороны нет ни стоящих, ни резерва. В бой теперь идёт до 1500 человек (было 150): большие
  армии сжимаются меньше, потери пересчитываются как раньше. Сообщение о волне - не чаще раза в 30 секунд на
  сторону, раунд кампании длится до двух часов.
- В совместной осаде стены держат и лорды, стоящие в замке или городе (как в одиночной игре), а не только гарнизон;
  в совместной обороне тоже. Отряды мировых партий одной стороны идут в бой общими стеками по типу войск, потери
  делятся между партиями пропорционально. Если стеков больше, чем берёт сервер боя (60), каждая сторона сохраняет
  не меньше 15 своих самых больших, а не попавшие в бой люди остаются у своих партий целыми (раньше часть
  осаждающих в большой обороне просто отрезалась, а не попавшие стеки вражеской партии пропадали).
- Клиент может сам начать совместный штурм: у стен вражеского замка или города (меню у ворот и меню города) есть
  пункт "CoopWorld: штурмовать стены ... вместе". Враг - тот, с кем воюет сам клиент, а для друга, не присягавшего
  ни одному королевству, - тот, с кем воюет сторона хоста (мир хоста сообщает свои войны). Лагерь осады у клиента
  для этого не нужен: лестницы ставит сервер боя. Штурм из меню осады тоже больше не требует от клиента присяги.
  Совместная оборона клиентом работает как раньше.
- Передача наделов другу: при встрече с отрядом друга на карте ("CoopWorld: передать этому игроку один из ваших
  наделов") или в лагере, "CoopWorld: другие игроки" - "Передать надел игроку ...". Хост передаёт свои наделы, а как
  король собственного государства - и его центры без лорда; клиент - свои наделы (другу или хосту). Друг, не
  присягавший ни одному королевству, становится по наделу вассалом государства хоста: его "заместитель" служит этому
  государству, доход и гарнизон работают как у других наделов друзей. Друг, присягнувший другому королевству, надел
  не получит; присяга королевству позже возвращает наделы государства хоста его королю.
- Упрощённый китайский (languages/cns, tools/make_zh.py, lang/zh.csv): китайский Native игры плюс переводы
  всех текстов CoopWorld, Freelancer и войска Джона, а также 2572 текстов Diplomacy, которых нет в китайском Native
  (меню, строки, диалоги, предметы, страницы справки); непереведённых текстов не осталось. Папка cns входит в оба
  пакета, в английском - краткое руководство 从这里开始.txt.
- Совместная осада, как полевой бой: павший герой через обычное время возрождения (настройка сервера «возрождаться
  ботом») берёт под управление одного из своих солдат, а когда тот падает - следующего. Сначала свои бойцы, потом
  бойцы ИИ своей стороны; солдат друга не берётся. Играя за солдата, можно командовать своими людьми: любой приказ
  движения (стоять, за мной, вперёд, отступить и т. д.) снимает их со штурма или обороны стен, приказ «В атаку!»
  возвращает их к штурму (или к обороне).
- Из любого совместного боя кампании (полевого боя, штурма, обороны) можно отступить: в меню Esc у каждого игрока
  боя - хоста и клиентов - есть кнопка «Отступить», второе нажатие («Отступить: точно?») подтверждает. Бой
  кончается без победителя, как по истечении времени: в плен никого не берут, уцелевшие у всех остаются, потери
  считаются как обычно. Штурм проваливается, и осада продолжается; при обороне стены остаются осаждающим; в поле враг
  остаётся на карте со своими уцелевшими. Кнопка такая же, как остальные в меню; если строк много, они стоят чуть
  плотнее и помещаются в рамку.
- Пинг до хоста: мост друга раз в 5 секунд измеряет связь с хостом и раз в минуту пишет в своё окно и в оба лога
  строку «link: ping to the host … ms, worst … ms». Если худший пинг 250 мс и больше или замеры теряются, строка
  добавляет по-русски, что карта и ответы хоста запаздывают, и что обычно в этом виновато (Wi-Fi, загрузки, VPN через
  ретранслятор). С хостом на мосте прежней версии замеров нет (он на них не отвечает).

- Арена и турнир на сервере боя: три карты по очереди (Арена, Лесное убежище, Нордский город), у каждой стороны
  три места появления вместо одного, боты расходятся по ним. Вверху экрана счётчик: сколько противников осталось
  и сколько убил ваш герой. У наборов с луком и арбалетом вместо кинжала дубинка и щит.
- Совместные действия у стен любого осаждённого замка или города: пункт «CoopWorld: совместные действия у стен …
  (осаждает …)» у стен, в меню города и в меню осады Native («осаждён», «лагерь осаждающих»), и там выбор:
  «Оборона» - держать стены с гарнизоном и лордами внутри, или «Атака» - штурмовать вместе с осаждающими и армией при
  них (взятые стены отходят королевству осаждающих). Ни то, ни другое не портит отношений с королевствами.
  Уведомление об осаде теперь зовёт к этому пункту.
- Счётчик живых во всех совместных боях, не только на арене: «Ваша сторона: … в строю, … в резерве  Враг: … в строю,
  … в резерве  Ваши убийства: …» вверху экрана, обновляется раз в секунду.
- Павший игрок в любом совместном бою (а не только при осаде) встаёт в строй за любого бойца своей стороны: сначала
  из своих войск, потом из войск под управлением ИИ, потом из войск друга (кроме бойца, которым друг сейчас
  управляет).
- Меню, разговоры и торговля друга больше не ставят мир на паузу: стоит только отряд друга и отряд, с которым он
  говорит, остальной мир идёт дальше. Мир по-прежнему стоит, пока открыто меню у хоста (его игра и есть мир, Warband
  останавливает карту в меню), во время совместного боя и во время обычного боя у друга («Атаковать» в его игре).
- Ближайшие отряды присоединяются к совместным боям, как в одиночной игре («… присоединяется на стороне …»): лорды
  рядом, воюющие с одной стороной и в мире с другой, и разбойники к разбойникам (когда герой выше 6 уровня); с отрядом
  приходит его армия. В поле вместе с врагом приходит и его армия. У стен замка или города друзья осаждающих идут на
  штурм с ними, друзья гарнизона - на помощь обороне. Состав отряда берётся у хоста, а если хост его ещё не
  присылал - из игры того, кто начал бой.
  Побеждённые помощники врага разбиты вместе с ним, помощники игроков сохраняют уцелевших.
- Штурм ИИ становится совместным боем: если осаждающие в мире хоста идут на штурм, а у стен стоит игрок, автобой ждёт
  до 6 часов, все игроки получают сообщение, и «совместные действия у стен» (оборона или атака) превращают штурм в бой
  на сервере. Если у стен никого нет или время вышло, штурм идёт как в Native.
- Конница в осадах: треть конников гарнизона появляется верхом снаружи стен (несколько точек на каждой карте) и
  бьётся в поле, остальные держат стены пешими. Хергитские города штурмуются на карте с самым большим полем:
  атакующие начинают у дальнего края, две трети гарнизона выезжают верхом, треть держит стены.
- Треть конников атакующих в осаде скачет к стенам верхом и в нескольких метрах от лестницы, осадной башни или
  флага спешивается (конь падает, всадник встаёт и идёт на штурм пешим, туша не загораживает проход).
- Конные лучники со стрелами держат дистанцию: враг ближе 22 м - отъезжают и стреляют; без стрел идут в рукопашную.
- Игрок, начавший бой, командует войсками ИИ своей стороны (отряды мира, люди лорда, присоединившиеся). Если на
  стороне ИИ есть лорд, его войско воюет как в одиночной игре: лучники стоят и стреляют, конница атакует, пехота
  держится у лучников, пока враг не подойдёт или не пройдёт минута, потом атакует.
- Торговля между игроками: в одном окне можно предложить игроку поблизости войска (окно обмена), предметы (окно
  добычи) и деньги (+100 / +1000 / +10000 динаров). Получатель видит всё предложение и принимает его целиком или
  отказывается; отвергнутое возвращается. Предмет, которому нет места в инвентаре, приходит его ценой в динарах.
- Бой за стены можно принять на противоположной стороне: в приглашении на штурм или оборону есть пункт «В бой на
  противоположной стороне!» - друзья одного боя сражаются в нём друг против друга (одни держат стены, другие
  штурмуют). Если зовут против ваших союзников, приглашение не отклоняется, а предлагает встать на их сторону.
- Меньше опыта за помощь: в обороне или штурме за чужое королевство (вы пришли на помощь, а не воюете за своё)
  игрок получает половину опыта.

### Исправлено
- Гарнизон иногда не защищал стены в совместной обороне, а ближайшие отряды не присоединялись к штурму: мост знал
  состав только тех отрядов, что недавно были рядом с игроками, остальные оставались в стороне («its men are not
  known»). Теперь игра того, кто начал бой, присылает состав гарнизона, лордов в замке, армий и присоединившихся
  отрядов, и мост берёт его, когда своего нет (у хоста - всегда его, его игра и есть мир).
- Клиенты не видели счётчика воинов в бою и пункта «Отступить» в меню Esc, а их «Отступить» не доходило до
  сервера: номера этих сетевых событий были больше 127. Теперь 125 и 126. В китайской версии счётчик по-китайски.
- Канал между мостами отправляет каждое сообщение сразу: раньше мелкое сообщение могло ждать подтверждения
  предыдущего, и Windows добавляла к ответу до 200 мс сверх настоящего пинга (карта у друзей с медленным
  интернетом дёргалась сильнее, чем нужно).
- Совместная осада: после победы замок не переходил игрокам. Хост: сообщение "стены ваши" приходило после итога боя,
  и игрок, сразу вернувшийся на карту, ничего не получал; теперь оно приходит первым, и в меню боя есть пункт
  "Войти во взятые стены". Клиент без присяги королевству: взятые им стены уходили "никому" (гарнизон пропадал,
  замок оставался прежним). Теперь они отходят королевству клиента, а если его нет - королевству хоста, в том числе
  собственному государству хоста (раньше мир хоста принимал только королевства Native). Вассал государства хоста
  получает взятые стены себе в надел. Партии других королевств, оставшиеся во взятых стенах, их покидают.
- Город или замок, взятый в совместной осаде, когда никто из игроков ещё не служит королевству и наделов нет,
  снова уходил «никому». Теперь он отходит хосту: игра хоста основывает его собственное государство (как Native при
  первом взятом замке), ставит гарнизон и, если прежний владелец был с хостом в мире, объявляет ему войну.
- Мост на всё время совместного боя переставал считать хоста хостом: запросы игры из боя не несут пометки хоста.
  Поэтому стены, взятые при игроках без королевства, всё равно уходили «никому» (11-05, после первого исправления),
  а собственный штурм хоста не получал сообщения «стены ваши» первым. Теперь хост остаётся хостом и в бою.
- Бойцы у осадной башни подолгу стояли у её подножия толпой: точка подхода к башне шире, на подъём дано больше
  времени, стоящий на месте боец через 6 секунд заново ищет путь, а на одну башню идёт не больше 24 человек
  (на лестницу - 8), остальные выбирают другой путь.
- После падения героя бой больше не принимал его солдата за героя: смерть этого солдата не объявлялась снова
  «герой пал», его удары не тренировали героя, а его здоровье не уходило в кампанию как здоровье героя.
- Войска, оставленные в полевом лагере, пропадали у игрока и не попадали в лагерь, а у друга, открывшего войска
  лагеря, игра вылетала. Экран обмена теперь показывает постоянную служебную партию игры (как экран пленных после
  боя), люди переходят на неё только перед экраном и снимаются сразу после; новая партия на карте больше не
  создаётся. То же для охраны каравана. Пропавших раньше людей игра возвращает сама при входе в меню лагеря.
- Русская сборка: диалоги, меню и сообщения 1.2.0 переведены, переводы изменившихся строк (меню лагеря, обучение по
  тирам, свёртывание лагеря) обновлены; пакет больше не собирается со старыми русскими файлами.
- У героя друга после загрузки было больше очков навыков, чем положено: его герой собирается поверх героя хоста из
  сохранения, и уровни, заново набранные при восстановлении опыта, давали очки навыков второй раз. Теперь столько же
  уровней навыков (с самых высоких, которые можно поднять снова) возвращаются в свободные очки - распределите их
  заново в окне персонажа; игра пишет, сколько. То же для компаньонов.
- Совместный бой с ботами, не уместившимися на сервер боя: отряды мира сохраняют стеки, которые в бой не вошли.
- Сохранение хоста идёт друзьям сжатым (примерно в 18 раз меньше) и по частям, каждому другу отдельно. Раньше
  целый файл стоял между игрой друга и ответами моста до минуты: мир вставал на паузу, связь рвалась, а друг
  оставался без свежего сохранения.
- Игра друга, загрузившая сохранение хоста, сразу становится клиентом: мост друга сам отвечает ей на адресе хоста.
  Раньше, пока связь была прервана, такая копия жила как отдельный мир с героем хоста, а остальным писало, что этот
  игрок в бою.
- После перезапуска host.bat хост снова получает слот 0, даже если друзья подключились раньше.
- Новая игра хоста начинает кампанию с чистого листа: лагеря, казна, склад, войско и герои друзей прошлой кампании
  не переносятся. Их файлы остаются в папке `old campaign <дата>` рядом с `profiles.json`, а если хост загрузит
  сохранение прошлой кампании, всё вернётся.
- Бой игрока против игрока, где у обоих только герои без бойцов, больше не отменяется.
- Ошибки моста записываются в `bridge.log` / `join.log`, а мост после ошибки продолжает работу.
- После совместной победы рядом с лордом (Freelancer) хоста и друзей больше не зовёт второй раз в бой с тем же,
  уже разбитым отрядом, и нет ошибок скрипта «Invalid Party ID» с воинами лорда на карте: игра хоста ждала, пока мост
  удалит разбитый отряд, а лорд всё ещё числился в бою с ним.
- Кнопка «Back to the map» в полевом лагере снова выводит на карту после разговора с Джоном и после склада.
- Обученные бойцы, поднимаясь до уровня своего вида, больше не пропадают из войска: раньше при таком переходе
  часть людей терялась (11-04 - 5 из 91 ополченца).
- После победы в обычном полевом бою и экрана добычи игра выходит прямо на карту, а разбитый отряд убирается с неё.
  Раньше игра хоста могла остаться без экрана: сообщения «плыли» поверх последней картинки, потом чёрный экран.
- Кнопка «Уйти» в меню встречи и прощание в разговоре («Ступайте», «Езжайте») снова выводят на карту.
- Встреча с отрядом, в котором никого не осталось, больше не открывает разговор (он давал чёрный экран): отряд
  убирается, игрок остаётся на карте.
- Разговор со своим караваном на карте - короткая реплика каравана и «Езжайте», вместо разговора как с отрядом,
  на который нападают («Сдавайтесь или умрите!»), после которого игра хоста закрылась.
- Отступление с прикрытием («оставить часть бойцов»): кнопка «Продолжить…» снова выводит на карту (раньше она
  переставала реагировать, как раньше «Уйти» в меню встречи).
- Двойной плен: после поражения в совместном бою встреча с победителем закрывается до плена, поэтому его разговор
  больше не открывается заново и не берёт в плен второй раз. Отряд, взявший игрока в плен, не трогает его во время
  плена и ещё сутки после побега (раньше у клиента тот же отряд сразу нападал снова: его копия на карте создавалась
  заново и забывала передышку Native). Повторный итог боя больше не начинает второй плен.
- Плен после проигранного совместного боя (11-06, хост против разбойников): мост сообщал, кто берёт в плен, уже после
  итога, и меню боя успевало показать «Вернуться на карту»; на карте те же разбойники снова заговаривали и брали в плен
  по-обычному, а экран «Ваши враги берут вас в плен» не отвечал на «Продолжить…». Теперь плен приходит раньше итога
  (меню сразу показывает «Вас берут в плен…»), отряд, с которым бились, 6 часов не трогает игрока после боя,
  а «Продолжить…» на экранах плена и побега выводит на карту. Нужны новый мост и игра у всех.
- Счётчик арены и турнира виден с первого бота (раньше появлялся, только когда выходил последний) и стоит по центру
  экрана (раньше от центра начинался его левый край).

## 1.1

Большое обновление после 1.0. **Сохранения версии 1.0 не подходят: нужна новая кампания** (в игре появилось
собственное войско). Перед новой кампанией удалите `profiles.json`, `shared.json`, `sync.json` и `army.json` из папки
`Документы\Warband Coop Campaign`. Всем игрокам нужен один и тот же пакет версии 1.1. В лаунчере включите
**Start windowed** у всех игроков: два полноэкранных окна могут зависать.

### Новое

**Собственное войско**
- Рекрут и три ветви (пехота, лучники, всадники) до 5 тира. Тир растёт только от опыта: в боях и на тренировочном поле.
- Джон Блэкборн в полевом лагере и в ваших городах и замках нанимает по 1, 5, 10 или 20 бойцов, продаёт уровни
  характеристик (1-3, тир от них не меняется), одевает бойцов и переименовывает войско и отряды.
- Снаряжение своё у каждого тира и покупается без бойцов в отряде. Уровень покупается один раз на весь вид бойцов.
- В кооперативе войско создаёт хост, оно одно на всех. На сервере боя боты носят купленное снаряжение.

**Вместе без встречи на карте**
- Следовать за другом: отряд едет за ним, и пока мир стоит на паузе тоже.
- Полевой лагерь у каждого игрока. Поездка идёт к своему лагерю, затем к лагерю хоста, затем к чужому.
- Общая казна и общий склад в лагере. Они хранятся у хоста и не зависят от перезапуска моста.

**Новые совместные события и бои**
- Арена: по 20 соперников на игрока, от слабых к сильным.
- Турнир: четыре раунда, от 2 до 4 команд, ставка на команду, приз каждому игроку.
- Тренировка с вашими бойцами, от 1 до 4 соперников на игрока.
- Логова бандитов, защита караванов и крестьян, деревни под набегом, бандиты в деревне.
- Дуэли между игроками на ставку: без ран, плена и потерь.

**Совместные бои**
- Победитель берёт пленных по навыку «Содержание пленных» (10% на уровне 1, дальше +5% за уровень).
- Войска получают опыт, как после обычного боя.
- Приглашение в бой приходит со звуком и открывается даже в меню города, деревни и лагеря.
- Дальность приглашения выросла в 4 раза.

**Древо войск**
- Ветви королевств, горожан и наёмников, женщин, разбойников и ваше войско, с портретами.
- По щелчку открывается карточка бойца: характеристики, навыки, владение оружием, развитие и снаряжение.

**Сохранения**
- Мост точно знает, какое сохранение загрузил хост, даже в пределах одного игрового часа.
- При загрузке герои, казна, склад и лагеря возвращаются к этому сохранению. Хранятся последние 24 сохранения.
- Названия, снаряжение и уровни войска лежат отдельно в `army.json` и не теряются при загрузке.
- Хост хранит героя друга вместе со здоровьем и компаньонами, их навыками и снаряжением.
- Если загружено не самое новое сохранение, игра попросит сохраниться, чтобы друзья получили этот мир.


### Исправлено

**Вылеты и зависания**
- Вылет друга при загрузке сохранения хоста: герой и склад использовали одну и ту же область данных, и в снаряжение
  попадал номер несуществующего предмета. Теперь у них свои области, а номера предметов проверяются.
- Вылет и ошибки скриптов, когда отряды оставались привязанными к исчезнувшему отряду другого игрока.
- Случайный клик по строке в меню города больше не зовёт друзей на арену: приглашение нужно подтвердить.
- Мост хоста теперь тоже предупреждает о полноэкранном режиме. Раньше это делал только мост друга.

**Синхронизация**
- Карта у клиента обновляется чаще и точнее, в том числе на службе у лорда.
- Пока мир стоит, клик по карте отменяется: часы клиента больше не убегают вперёд.
- Бой не начинается, если врага уже нет.

**Полевой лагерь**
- Лагерь не пропадает после остановки кооператива и возвращается при новом запуске без повторной оплаты.
- 1000 динаров списываются только тогда, когда лагерь действительно поставлен.
- Кнопки казны больше не выбрасывают из меню лагеря.

**Арена и турнир**
- Убраны ошибки скриптов на арене и турнире, в том числе «Invalid Team ID» при 3 и 4 командах.
- Боты выходят на второй и следующие раунды турнира, команды 3 и 4 сражаются.

**Диалоги и меню**
- Около 50 разговоров Diplomacy и Native, которые могли оборваться, теперь имеют последнюю реплику с выходом.
- У лорда Freelancer появился ответ на просьбу об отпуске при низком отношении.
- В русской версии меню проникновения в город показывает настоящие пункты, а не три раза «Продолжить...».
- Передача войск и остановка поездки возвращают в то меню, откуда начались.

**Прочее**
- Портреты в древе показывают снаряжение войска.
- Склад открывается сразу.
- Хост видит сообщения о раундах и новости деревень, как и клиент.

### Убрано
- Вступление в отряд другого игрока. Вместо него — следование за другом и лагеря.

### Известные ограничения
- Хост должен играть с запущенным `host.bat`: без моста войско после загрузки вернётся к стандартному виду.
- Прогресс после загруженного сохранения теряется, как и в обычной игре.
- У войск клиента между сессиями пропадает опыт до следующего повышения, а нераспределённые очки не сохраняются.
- Задания и отношения клиента не сохраняются.
- Владения (замки, города, деревни) и дипломатия Diplomacy пока только у хоста.
- Качество предметов («закалённый», «ржавый» и т. п.) на сервер боя не переносится.
- При двух полноэкранных окнах картинка может застыть, особенно при переключении между ними.
  Причина ещё не выяснена, поэтому используйте Start windowed.

---
- Совместная осада: гарнизон больше не появляется в закрытых комнатах башен и донжона, откуда боты не выходят. Он
  появляется только в точках, куда могут дойти штурмующие (по карте ИИ каждой из четырёх карт осады), а двери комнат
  открываются, как только первые отряды на поле (бот двери не открывает; закрытую игроком дверь игра снова открывает).
- Совместная осада: боты больше не стоят под стеной. Осадные башни сразу стоят у стен с опущенным мостом (раньше их
  двигали только игроки), лестницы подняты. Штурмующие идут к подножию ближайшей лестницы или башни (на занятую
  идут меньше), поднимаются на стену, а оттуда к флагу; лучники сначала 40 секунд стреляют. Бой с врагом на своём
  уровне всегда важнее; бот, застрявший у врага за решёткой ворот, идёт дальше своей дорогой. Упавшая лестница или
  неудачный подъём - другой путь. Гарнизон держит верх лестниц, башен и флаг, а не бежит к воротам: дерётся с
  врагом на своём уровне ближе 15 м, потом возвращается на пост.

# Changelog

## 1.2

The bridge (`coop_bridge.py`) and the game change. The host and the friends must install the same package: a bridge of
version 1.1 is refused and told to install the same package.

### Fixed
- The garrison sometimes did not hold the walls in a joint defence, and parties nearby did not join a storm: the bridge
  knew the men only of the parties seen near players lately, the others stayed out ("its men are not known"). Now the
  game of the player who began the battle tells the men of the garrison, the lords inside, the armies and the
  parties that join, and the bridge takes them when it has none (the host's always: its game is the world).
- Clients saw no count of the living in a battle and no "Retreat" in the Esc menu, and their Retreat never reached the
  server: those network events were numbered above 127. Now 125 and 126. The Chinese version shows the count in
  Chinese.
- Joint sieges: walls taken went to nobody. The host: word that the walls were its own came after the battle's result,
  and a player back on the map at once got nothing; now it comes first, and the battle's menu offers "Enter the
  stormed walls". A client sworn to no kingdom: walls it took went to nobody (the garrison gone, the center as it
  was). Now they go to the client's kingdom, or else to the host's, the host's own realm too (the host's world took
  only Native's kingdoms). A vassal of the host's realm holds them as its fief. The parties of other kingdoms left
  inside leave them.
- The host's save goes to the friends packed (about 18 times smaller) and in parts, to each friend on its own.
  A whole file used to stand between a friend's game and the bridge's replies for up to a minute: the world paused,
  links broke, and the friend was left without the fresh save.
- A friend's game that loaded the host's save becomes a client at once: the friend's bridge answers it at the host's
  address itself. While the link was down, such a copy used to go on as a world of its own with the host's hero,
  and the others were told this player was in battle.
- After host.bat starts again the host gets slot 0, even when the friends came back first.
- A new game of the host starts the campaign afresh: the last campaign's camps, treasury, store, army and the
  friends' heroes do not carry over. Their files stay in an `old campaign <date>` folder next to `profiles.json`,
  and loading a save of that campaign brings it all back.
- A battle of one player against another with heroes alone, no soldiers, is no longer called off.
- The bridge's errors go to `bridge.log` / `join.log`, and the bridge goes on after one.
- After a joint victory beside a lord (Freelancer) the host and the friends are no longer called a second time against
  the same, already beaten party, and there are no "Invalid Party ID" script errors with the lord's men on the map: the
  host's game waited for the bridge to remove the beaten party while the lord still stood in battle with it.
- "Back to the map" in the field camp leaves for the map again after a talk with John and after the store.
- Trained men rising to their kind's level no longer vanish from the army: some were lost on the way (11-04, 5 of
  91 militia).
- After a won field battle and its loot screen the game goes straight to the map, and the beaten party leaves it. The
  host's game could be left with no screen: messages drifting over the last picture, then black.
- "Leave" in the encounter menu and a farewell in a talk ("Carry on", "Ride on") lead to the map again.
- Meeting a party nobody is left in no longer opens a talk (it went black): the party goes, the player stays on the map.
- Talking to a players' caravan on the map is a short word from it and "Ride on", not the talk of a party one
  attacks ("Surrender or die!"), after which the host's game went out.
- Joint sieges: the garrison no longer spawns in closed rooms of towers and the keep that bots never leave. It spawns
  only at points the attackers can reach (by the AI mesh of each of the four siege maps), and the room doors open as
  soon as the first troops are on the field (a bot never opens a door; one a player shuts again the game opens again).
- Joint sieges: bots no longer stand under the walls. The siege towers stand at the walls at once with their bridges
  down (players alone used to move them), the ladders are up. The attackers go to the foot of the nearest ladder or
  tower (fewer to a crowded one), climb to the wall and on to the flag; archers shoot for 40 seconds first. A fight with
  an enemy on its own level always comes first; a bot stuck at an enemy behind the bars of a gate goes its way. A
  ladder pushed down or a climb that fails: another way. The garrison holds the tops of the ladders and towers and the
  flag instead of running to the gate: it fights an enemy on its level within 15 m, then goes back to its post.

- "Retreat, leaving some men behind": its Continue... goes to the map again (it stood dead, as Leave once did).
- A second captivity: after a joint battle lost, the encounter with the winner ends before the captivity, so its talk
  no longer opens again and takes the player a second time. The party that took a player prisoner leaves it alone during
  the captivity and a day after the escape (a client's copy of that party was made anew and forgot Native's respite).
  The same outcome told twice no longer starts a second captivity.
- Captivity after a joint battle lost: the bridge told who takes the player prisoner after the result, the battle's
  menu offered "Back to the map" meanwhile, the same bandits met the player there and took it prisoner the Native way,
  and that captivity's Continue... stood dead. The capture now comes before the result, the party fought leaves the
  player alone 6 hours after a battle, and Continue... on the captivity and escape screens goes to the map.
- The arena's counter shows from the first bot and stands in the middle of the screen.

### New
- Reinforcements in joint battles, as in the single player game: up to 150 of the campaign's men on the field at
  once (each side by its share, at least 30 or all it has), the others wait in reserve. A side that has lost a quarter
  of its place on the field gets a wave from its reserve; a message says how many are left. The battle ends when a side
  has nobody standing and no reserve. A battle now takes up to 1500 men (was 150): big armies are scaled down less,
  losses are scaled up as before. A side's wave is told at most once in 30 seconds; a campaign round lasts up to two
  hours.
- In a joint siege the lords inside the town or castle hold the walls beside the garrison (as in the single player
  game); in a joint defence too. The world parties of one side go into the battle in shared stacks by troop, their
  losses split in proportion. When there are more stacks than the battle server takes (60), each side keeps at least
  its 15 biggest, and the men left out stay with their parties unhurt (a big defence used to cut off part of the
  besiegers, and an enemy party's stacks left out were lost).
- A client may start a joint storm itself: before the walls of an enemy town or castle (the gate's menu and the
  town's) there is "CoopWorld: storm the walls of ... together". An enemy is one the client is at war with, or, for a
  friend sworn to no kingdom, one the host's side is at war with (the host's world reports its wars). The client
  needs no siege camp of its own: the battle server raises the ladders. The siege menu's storm no longer asks a
  client for an oath either. A client's joint defence works as before.
- Fiefs given to a friend: on meeting the friend's party on the map ("CoopWorld: give one of your fiefs to this
  player") or in the camp, "CoopWorld: the other players" - "Give one of your fiefs to ...". The host gives its own
  fiefs, and as the king of its own realm the realm's lordless centers; a client its own fiefs (to a friend or the
  host). A friend sworn to no kingdom becomes a vassal of the host's realm by it: its stand-in serves that realm, rents
  and garrison work as for the other friends' fiefs. A friend sworn to another kingdom gets none; swearing to a kingdom
  later sends the realm's fiefs back to its king.
- The arena and the tournament on the battle server: three maps in turn (The Arena, Forest Hideout, Nord Town), three
  spawn places for each side instead of one, a counter at the top (opponents left, your kills). The bow and crossbow
  sets carry a cudgel and a shield instead of a dagger.
- Joint actions at the walls of any besieged castle or town: "CoopWorld: joint actions at the walls of ... (besieged
  by ...)" before the walls, in the town's menu and in Native's siege menus ("besieged", "the besiegers' camp"), with
  a choice: "Defend" - hold the walls with the garrison and the lords inside, or "Attack" - storm them beside the
  besiegers and their army (stormed walls go to the besiegers' kingdom). Neither changes how the kingdoms see you.
  The siege notice now points there.
- A count of the living in every joint battle, not only the arena: "Your side: ... standing, ... in reserve  Enemy:
  ... standing, ... in reserve  Your kills: ..." at the top, once a second.
- A fallen player in any joint battle (not only a siege) takes over any soldier of its side: its own men first, then
  those the AI leads, then a friend's (but not the one that friend controls now).
- A friend's menus, talks and trades no longer pause the world: only that friend's party and the party it meets stand
  still, the rest of the world goes on. The world still stops while the host is in a menu (its game is the world, and
  Warband stops the map in a menu), during a joint battle, and during a friend's own Native battle ("Charge").
- Parties nearby join joint battles as in the single player game ("... has joined the battle on ... side"): lords
  near at war with one side and at peace with the other, bandits with bandits (once the hero is past level 6); each
  comes with its army. In the field the enemy's army comes with it. At a town's or castle's walls the besiegers'
  friends storm with them, the garrison's come to its help. A party's men are the host's view of it, or, when the
  host has not reported them yet, the view of the game of the player who began the battle.
  The beaten enemy's helpers are beaten with it; the players' helpers keep their survivors.
- The AI's storm becomes a joint battle: when the besiegers in the host's world storm walls with a player at them,
  the autocalc waits up to 6 hours, every player hears of it, and the joint actions at the walls (defend or attack)
  fight it on the battle server. With nobody at the walls, or once the wait is over, it goes as in Native.
- Horsemen in sieges: a third of a garrison's horsemen come mounted outside the walls (a few spots on each map) and
  fight in the open, the others hold the walls on foot. Khergit towns are stormed on the map with the most open
  ground: the attackers start at its far edge, two thirds of the garrison ride out, a third holds the walls.
- A third of the attackers' horsemen in a siege ride up to the walls and get off a few metres before a ladder, a
  siege tower or the flag (the horse falls, the rider gets up and storms on foot; the body does not block the way).
- Horse archers with arrows keep their distance: an enemy closer than 22 m and they ride away shooting; with no
  arrows left they go into melee.
- The player who started a battle commands the AI's men of its side (world parties, a lord's men, those who joined).
  A side the AI leads with a lord on it fights as in the single player game: archers hold and shoot, horsemen charge,
  infantry holds by the archers until the enemy comes near or a minute has gone, then charges.
- Trade between players: one window offers a player nearby troops (the exchange screen), items (the loot screen) and
  denars (+100 / +1000 / +10000). The receiver sees the whole offer and accepts it all or declines; what is declined
  comes back. An item with no room in the inventory comes as its price in denars.
- A siege battle may be taken on the other side: an invitation to a storm or a defence offers "To battle on the
  opposite side!" - friends fight one battle against each other (some hold the walls, others storm them). An
  invitation against your allies is no longer declined at once: it offers their side instead.
- Less experience for helping: a player who defends or storms walls for another's kingdom (who came to help, not to
  fight for its own) gets half the experience.

## 1.1

A big update after 1.0. **Saves of version 1.0 do not work: start a new campaign** (the game now has your own army).
Before it delete `profiles.json`, `shared.json`, `sync.json` and `army.json` from `Documents\Warband Coop Campaign`.
All players need the same 1.1 package. Turn on **Start windowed** in the launcher for every player: two full-screen
windows can hang.

### New

**Your own army**
- A recruit and three branches (infantry, archers, riders) to tier 5. A tier rises only by experience, in battles and at
  the training field.
- John Blackborn, in a field camp and in your towns and castles, hires 1, 5, 10 or 20 men, sells stat levels (1-3, the
  tier does not change), equips the soldiers and renames the army and its units.
- Each tier has its own gear, bought with no men needed. A level is bought once for the whole kind.
- In co-op the host creates the army and it is shared. Bots on the battle server wear the gear you bought.

**Together without meeting on the map**
- Ride after a friend: your party follows, also while the world is paused.
- A field camp for every player. Riding goes to your own camp, then the host's, then another's.
- A shared treasury and store in the camp, kept by the host through bridge restarts.

**New joint events and battles**
- Arena: 20 fighters per player, from weak to strong.
- Tournament: four rounds, 2 to 4 teams, a bet on the team, a prize for every player.
- Training with your own men, 1 to 4 opponents per player.
- Bandit lairs, defending caravans and farmers, villages under a raid, bandits in a village.
- Duels between players on a stake: no wounds, capture or losses.

**Joint battles**
- Winners take prisoners by Prisoner Management (10% at level 1, then 5% more per level).
- Troops gain experience as after a normal battle.
- The call to battle comes with a sound and opens even over a town's, a village's or a camp's menu.
- Invitations reach four times as far.

**Troop tree**
- Branches of the kingdoms, townsfolk and mercenaries, women, outlaws and your own army, with portraits.
- A click opens a soldier's card: attributes, skills, proficiencies, upgrades and gear.

**Saves**
- The bridge knows exactly which save the host loaded, even within one game hour.
- On a load, heroes, the treasury, the store and camps go back to that save. The last 24 saves are kept.
- The army's names, gear and levels live apart in `army.json` and survive a load.
- The host keeps a friend's hero with health and companions, their skills and gear.
- If the loaded save is not the newest, the game asks you to save so that friends get that world.

### Fixed

**Crashes and hangs**
- A friend's crash on loading the host's save: the hero and the store shared one data area, and the number of an item
  that does not exist reached the gear. Each now has its own area and item numbers are checked.
- A crash and script errors when parties stayed attached to another player's party that was gone.
- A stray click on a town menu row no longer calls friends to the arena: the invitation must be confirmed.
- The host's bridge now warns of full-screen mode too. Only the friend's did before.

**Sync**
- A client's map updates more often and more closely, also in a lord's service.
- A click on the map is cancelled while the world stands, so a client's clock no longer runs ahead.
- A battle no longer starts when the enemy is already gone.

**Field camp**
- A camp stays after co-op stops and comes back at the next start with no second payment.
- The 1000 denars are taken only once the camp really stands.
- Treasury buttons no longer throw you out of the camp's menu.

**Arena and tournament**
- Script errors in the arena and the tournament are gone, including "Invalid Team ID" with 3 and 4 teams.
- Bots come out in the second and later tournament rounds, and teams 3 and 4 fight.

**Talks and menus**
- About 50 talks of Diplomacy and Native that could stop dead now have a last line that leads out.
- Freelancer's lord now answers a request for leave at a low relation.
- In Russian the disguise menu shows its real options instead of "Continue..." three times.
- Giving troops and stopping a ride come back to the menu they started from.

**Other**
- Portraits in the tree show the army's gear.
- The store opens at once.
- The host sees round messages and village news, as a client does.

### Removed
- Joining another player's party. Riding after a friend and camps replace it.

### Known limitations
- The host must play with `host.bat` running: without the bridge the army returns to its default look after a load.
- Progress after the loaded save is lost, as in a normal game.
- A client's troops lose their experience towards the next upgrade between sessions, and unspent points are not kept.
- A client's quests and relations are not kept.
- Fiefs (castles, towns, villages) and Diplomacy's diplomacy stay with the host for now.
- Item quality (tempered, rusty and so on) does not reach the battle server.
- With two full-screen windows the picture can freeze, above all when switching between them. The cause is not known
  yet, so use Start windowed.
