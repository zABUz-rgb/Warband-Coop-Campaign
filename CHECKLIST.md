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
- install.bat first lists PowerShell 7, Python 3 and Radmin VPN (found or not) and, with one answer,
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
