# История изменений

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

# Changelog

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
