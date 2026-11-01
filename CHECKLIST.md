# What must keep working

The best working version is tagged (`git tag`, newest `stable-*`). Before a package goes out:
`python build.py` (with tools/check_module.py), `python tools/test_coop_bridge.py`,
`python tools/make_ru.py` (0 untranslated), `python tools/test_coop_logs.py`. After a session,
`python tools/coop_logs.py` (check_logs.bat in the package) reads bridge.log and trace.log in
Documents\Warband Coop Campaign and reports the battles, the silences and what did not arrive (`--all`: every session). A fix that touches one of these is checked against all of them.

Confirmed in game at `stable-2026-10-28`:

1. host.bat / join.bat over Radmin; the friend's join.bat fetches the host's newest save, and every
   later save of the host.
2. The friend loads the host's save: the game becomes a CLIENT by itself (kind 24); Camp - CoopWorld:
   co-op - CLIENT is there too.
3. Heroes are named as in host.bat / join.bat.
4. Meeting another player's party opens the co-op choices (joint battle, ask to join, give troops).
5. Battle server: Multiplayer - Host a game, Battle; host and friend pick a side.
6. Joint battle started by either player: the other is invited (45 s to answer), the battle starts,
   heroes come with their gear, sides are set, proficiencies grow, wounds come back.
7. After the battle: result, the world's parties stay (no ghosts, none lost), the spoils from
   Camp - CoopWorld: co-op, back to the map.
8. Defeat: captivity; a prisoner is not called into joint battles.
9. Troops given to a player are no longer the giver's in battles.

Open (build 941871141, not confirmed yet): the spoils as Native's victory menu shows them - the loot
screen from the coop_loot menu's own code, then back to the map by itself (an option that opened the
loot screen left the camp's and the battle menu's options dead). The spoils (kind 21) now come before
the result (kind 8), so the joint battle menu offers them. A client drops a mirror the host has not
mentioned for 900 requests (about 1.5 min) instead of 1500.
Confirmed (build 247370558, session 19:45): a client whose hero stands still no longer pauses the world
"in an encounter or battle" (no short holds in the report).
Open (build 297015227, not confirmed yet): a new mirror appears where the server's party is, not on
the client's hero (parties seemed to come out of the client); the party met (until the encounter's
result went out) and the captor in captivity are never removed under the game, other mirrors the
server dropped are (the sweep no longer keeps the last party met for good). The bridge logs a
captor that is gone. Ctrl+Space on a client in captivity hung the game once (19:58) - cause unknown.
Confirmed (build 139875334, tag `stable-2026-10-28-b`, packages kept in dist/stable): the friend's game
no longer hangs near midnight of its game time (a mirror is no longer attached in a loop of parties
or to a non-center static party). The bridge logs a quiet player's last request and replies.
Open (next build, not confirmed yet): session 20:10, 30.10 (build 282377703) - a client hung again at
20:37:28 and detaching mirrors did not stop it. Both hangs of 30.10 came right after a 5|0 reply (the
world runs again; such a reply comes 1 time in 50 otherwise); that friend's Warband runs full screen
(2560x1440, start_windowed 0) on 4 GB, 688 MB free when its log began. join.bat now warns of it.
While the world is held a click on the map is cancelled (party_set_ai_behavior on the hero, not tried
in game): the report's "cli" must stand still while PAUSED with a client on the map, it ran 11 h/min.
Open: session 19:16, 30.10 - a client on the map hung again (picture
frozen, process running, no error) 7 s after the world ran on, the second window stayed on the server.
The host's save only coincided: the game went quiet 4 s before the save was sent. Cause not proven.
A client now lets go of a mirror's attached parties before removing it (an old script error showed
parties attached to a removed one). If it hangs again: a dump (Task Manager - Create dump file).
Open (build 590170735, not confirmed yet):
- serving a lord (Freelancer) on a client: no SCRIPT ERROR "Invalid Party ID" in
  coop_client_apply_positions (a mirror destroyed here no longer stands for the army it was in);
- the world paused (another player in battle or a menu): a client's clock stands still too, its rest
  (standing still, serving a lord, captivity) stops and starts again once the world runs; Freelancer's
  rests run at the world's time speed (they ran 4-5 times faster); the host and a client serving a
  lord rest by themselves like a player standing still;
- the clocks (build 999149789): never a pause any more - build 590170735 held a client 2 h ahead at
  1% speed, and its clock ran on whenever it tried to move: it waited minutes (session 21:46, 28.10).
  Now a client 3 h ahead only stops resting (standing still it waits, moving is free), 3 h behind
  rests 3x faster, both until within 1 h; the bridge logs start and end ("after N s"), the report
  marks a catch-up over 2 min. The host's Native waits (captivity, towns) run the world faster
  (30 h/min seen): clients fall behind and catch up standing still. A client crashed at 22:03 that
  session: a hang, not a crash (picture frozen, process alive, no Windows error), at 20:00 of its
  clock, no new parties before it - not the midnight pattern. Build 931815951 sends the client's state
  (dbg=parties,spawned,swept,Freelancer,clock,attached-to) with every request: the quiet note shows it;
- serving one lord: when he goes into a field battle, a client's soldier menu opens ("your commander
  goes into battle!"), the host's as Freelancer does; "CoopWorld: fight beside your commander" starts a
  joint battle - the players and the lord's men (bots, team of the players) against his enemy; a
  second soldier choosing it joins the same battle; the lord keeps the men who survived, the enemy is
  beaten as in any joint battle. Freelancer's own "Follow the commander" (single player) stays.
Open (build 157847662, not confirmed yet) - the joint siege on the battle server:
- maps: only Siege maps whose AI mesh climbs the walls (3, 10, 13, 16); 8 and 15 have no AI mesh
  at all (read from their .sco), their bots could only walk at the walls and stand;
- the ladders lie on the ground when a round starts and the AI mesh goes up the wall where they stand
  raised: the battle server raises them once all troops are on the field (in every player's game
  too), and again every 30 s if one was pushed off; a storming bot (team 1) that stands 8 s with no
  enemy within 4 m (archers excepted) is sent to a raised ladder, let go at its foot, and tries the
  next ladder after 20 s;
- the bots spawn without horses in a siege (spawn point override, given back when the battle ends);
  if some came on horses all the same the server says "N bots came on horses all the same";
- a hero (and a companion) spawns with its campaign hit points, now and at most (the campaign sends
  them after the proficiencies: 31 hero numbers instead of 29), so Ironflesh and Strength count.
Open (build 912679594, not confirmed yet) - after the first joint siege test (157847662):
- the team window no longer comes up again and again on a client: a hero gets its side and the
  hero's troop from the server without a window (the server opened one every time the side was off);
  only a player without a hero picks in the window;
- a siege ends when one side has nobody standing, the heroes counted (it ended with the friend's hero
  still alive when the bots were gone);
- a hero who falls stays out of the battle ("... hero has fallen and does not come back"), Siege
  and Battle alike (Native's spawn checks slot_player_coop_fallen); it comes back to the campaign
  wounded.
Open (Warband Coop Campaign 1.0, packages Warband-Coop-Campaign-1.0[-ru].zip, build 912679594):
- install.bat first lists Python 3 and Radmin VPN (found or not; PowerShell 7 is no longer offered,
  the scripts run in Windows PowerShell 5.1 of Windows 10/11) and, with one answer,
  runs the missing installers from the package's Programs folder (Python passive, with PATH);
- the project is named Warband Coop Campaign, and so are the module folder (Modules\Warband Coop Campaign),
  its saves and Documents\Warband Coop Campaign; the mod's menu entries keep the prefix "CoopWorld:". Saves and
  kept heroes of the CoopWorld test builds are not carried over: a new campaign.
Confirmed (session 16:11, 29.10, battle server only): over Radmin the friend's second window was
refused by the battle server ("invalid authorization number"), on the same Wi-Fi it got in. Now it
finds the battle server on its own PC, 127.0.0.1:7240, in the Local Area Network list (Warband's
list takes no typed address; join.bat offers look_for_server_on_this_machine = 1 in rgl_config.txt)
and gets in: the bridges carry the datagrams (UDP 7350) and the host's bridge hands them to the
battle server from the host's local address (192.168.x first), one port per friend's game.
Open: a joint battle from the campaign through the relay (lag, a whole battle). The logs say
"battle relay: ... is on the battle server through the bridge" and, 2 min after it leaves, how long
and how many datagrams; the host's log lists who is on the battle server whenever it changes.
A weak PC with both Warband windows open may run out of memory.
Open (build 693039160, not confirmed yet) - after the first campaign battle through the relay
(session 16:27, 29.10: the host accepted 22 s after the start, was refused "too late" and fought
on the battle server as a plain multiplayer player, with the gear picked there):
- while a campaign battle is on, only a player with a hero spawns (script_cf_coop_mp_may_spawn):
  one without a hero watches, never fights with multiplayer gear;
- a late acceptance (the invited player, after the armies left) joins as the hero on the
  starter's side, its troops and companions stay out ("accepted late - joins the battle as its hero");
- a hero the battle server did not get at the start (the player came to the server late, or
  accepted late) goes there while the battle runs: kind 5, then kind 9 (its side), and spawns
  even after Battle's first seconds ("is on the battle server now - its hero joins the battle");
- item modifiers (tempered, heavy...) are still not carried to the battle server;
- a save of the host made while a friend's link was down goes to that friend when it connects
  again ("a save the player did not have");
- the packages offer only Python 3 and Radmin VPN (PowerShell 7 dropped); README: keep only the
  current campaign's saves on every PC (the newest save by time is the one sent).
Confirmed (session 19:xx, 29.10): the joint battle fixes of build 693039160 work. That session the
friend's first join.bat ended in "getaddrinfo failed" and a traceback of the battle relay (a
mistyped host address). Now join reads a dot typed as 'ю'/'б' or ',' and spaces as slips, stops
at once with what to type when the address is no address, and the battle relay goes on (says
once) when it cannot reach the host's bridge.
Open (1.0.1, nothing of this was played yet: the bridge's side is tested in test_coop_bridge.py,
the game's side only compiles):
- after a won joint battle: "Prisoner Management N (X% of the fallen)", the prisoners are in the party
  (none at skill 0, "no room" when the party is full); a lost battle takes none;
- after a joint battle "your troops gain N experience" and the troops' experience really grows, for
  the winner by its share of the fallen, for the loser by the bridge's number;
- arena: 20 fighters per player, in blue practice gear, 3 per player at a time, the next one comes
  when one falls; the heroes in red, at full health; the round ends after the last fighter;
- tournament: a bet, round after round without the team window in between, the bots stronger each
  round, the team window after the last; gold, renown, relation and odds; a lost bet leaves the
  player who bet only;
- training: the player's own men in practice gear on Field by the River; the experience;
- "Back." returns to the town or training ground, an invited player to the map; a campaign battle
  right after an event spawns the bots with their own gear again (script_coop_mp_gear_back);
- entry overrides on the multiplayer server: if the fighters come with no weapons, the override
  does not reach bots there: script_coop_mp_arm_fighters is the fallback.
Open (1.0.1, second part, nothing of this was played either; the report's "Совместные дела" lists each
item as it happens):
- ride after a friend: the party really goes by the march order (party_set_ai_behavior on the main
  party is the unverified step); no "the march order did not take" message; a click ends the ride;
  the follower stops close to the friend, rests there, rides on when the friend moves;
- treasury: a deposit, a withdrawal, both at once from two players; survives a bridge restart;
- store: food and ammunition keep their amounts, modified items their modifier; a second player is
  refused; survives a bridge restart;
- call to battle in a town's, a village's and the camp's menu: the sound, the window over the menu
  (jump_to_menu from a reply is the unverified step), Decline comes back and reaches the bridge at
  once; on a walk through a town only the message; during a rest the rest ends and the window opens;
- the world stays held while a game in a menu pings (the ping must not count as a request);
- report: a menu shows "alive" (это меню), a hang does not;
- lair: the option shows on a client's mirror and on the host; won: the lair goes, the template's
  slot is free again, the quest succeeds; a lost storm keeps the lair;
- caravan or farmers: kind 32 reaches a client, the mirror opens coop_map_fight; the host's pre_join
  option; the caravan's survivors stay, a caravan with nobody left goes;
- village: "being raided" reaches a client (cf for a village carries slot_village_raided_by), the
  option shows, 15 villagers fight, the raid ends, also when a lord's party lives on without men;
- duel: two players on opposite sides in their own gear, no bots, the round ends at the first death;
  stake moves, xp; declining, no answer, one player not on the server; both gone: a draw;
- sneaking into a town in Russian: the disguise menu shows items, money and "Попытаться проникнуть...",
  not three "Продолжить..."; the next screen names the chosen disguise;
- a joint battle invites a player 30 map units away; none past 40;
- troop tree: portraits and names fit their cells, lines meet the portraits, the army's branch shows its
  text until there is an army, a click opens the card, Back and Esc return to the tree, Close leaves it;
- sync: on a lord's service the client's map keeps up with the host; no crash when armies gather;
- arena: bots fight each other (team 1 hostile to itself), the fight does not end while fighters are to come;
- tournament: 2-4 teams in their colours from different sides (bots on teams 3 and 4 appear and fight),
  a round ends only with one team left; a new gear set each round;
- camp: build, seen by both, reopens after a restart, treasury and store inside, John Blackborn's dialog
  in Russian, take down.

Open (the debug build, dist/1.0.1-debug: its game side was compiled, never played):
- trail.log appears in Documents\Warband Coop Campaign at the host and at the friend, the friend's lines at the host too;
- menus, options, lines and screens show as they happen, and the regular requests go on as in a plain build
  (no new silences, joint battles, invitations and the store work);
- the unverified step: a second request while one is held (a ping in a menu); if requests stall, look there first;
- a save of the plain build loads in the debug build and back;
- after a hang, the last actions in report.txt are the real last ones (how many are lost is the question to answer).

Open (1.0.1, third part, nothing of this was played either; a new campaign is needed: 40 new troops):
- John Blackborn: "Talk" opens his talk at once, in the camp and in a town and a castle of the player's;
  a client with no army hears "nothing I can do"; the talk ends back in the menu it started from;
- army: raised with the usual names and with typed ones (Russian too); the tree's last button bears its name, a
  soldier shows once, at the highest level the party has;
- recruits: 5, 10 and 20 at 20 dinars, an option goes when dinars or room are short;
- John asks whom to equip or train: recruits at once; infantry, archers, riders then the tier; a renamed soldier
  shows under its name there; one line to rename, then the army's common name and the units' own apart;
- gear screen: opens from the talk (the menu's load starting a presentation is the unverified step), a click
  buys and the list stays on the same soldier and sort; item windows open and close with the mouse; a soldier in
  battle really wears what was bought (non-hero troops take it from their inventory); each tier keeps its own: what
  a recruit got, no other tier has; what a soldier started with sells for nothing;
- training at John's: the men stay, the wounded stay wounded, the stack goes last; level names and prices in the
  menu; the tier never changes there; a training field gives footmen their full share in melee and raises tiers;
- riders: militia footmen and archers offer a horse on the party screen once they have the experience, and the
  tree's lines show it; the tree's card of an army soldier says tier and level of stats;
- co-op: a client sees the host's names and gear within seconds of joining; a client's purchase reaches the host and
  stays in the host's save; bots on the battle server wear the bought gear (their names stay the usual ones);
- removed: marks are gone from the menus; no chat line for lords raiding villages;
- bandits in a village: the message when entering, the joint fight, the village free for all afterwards;
- host: round messages of the tournament and arena, village news, as on a client;
- store: opens at once from the camp; tournament: round 2 starts with its bots.
