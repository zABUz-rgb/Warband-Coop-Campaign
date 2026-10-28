# What must keep working

The best working version is tagged (`git tag`, newest `stable-*`). Before a package goes out:
`python build.py` (with tools/check_module.py), `python tools/test_coop_bridge.py`,
`python tools/make_ru.py` (0 untranslated). After a session, bridge.log and trace.log in
Documents\CoopWorld tell what happened. A fix that touches one of these is checked against all of them.

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

Known and not fixed in code: two full-screen Warband windows hang when switching (launchers set
Warband to a window); a weak PC with both windows open may run out of memory.
