"""The trail of a debug build (python build.py --trail): every menu, option, line of a talk, screen and
timed trigger tells the bridge it ran, so a hang or a crash shows what the game did last. A process of
its own holds the record: it outlives the game, and a second window does not write over it as it does
rgl_log.txt. A plain build has none of this: coop_mods adds this package only under COOP_TRAIL=1.
"""
