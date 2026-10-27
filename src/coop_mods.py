"""CoopWorld: one entry point that every Native module_*.py calls at its end.

    import coop_mods; coop_mods.merge("scripts", scripts)

Each mod package exposes <kind>.merge(list, **extra); they run in the order of MODS.
"""
import importlib

MODS = ["dplmc_fix", "freelancer", "coop"]


def merge(kind, records, **extra):
    for mod in MODS:
        try:
            part = importlib.import_module(f"{mod}.{kind}")
        except ModuleNotFoundError as e:
            if e.name != f"{mod}.{kind}":
                raise
            continue
        part.merge(records, **extra)
