"""Run one module-system step under Python 3 with the Python 2 `string` helpers it expects.

    python tools/run_step.py process_strings     (cwd = src)
"""
import os
import runpy
import string
import sys

# Python 2 string-module functions removed in Python 3, used throughout process_*.py
string.replace = lambda s, old, new, *n: s.replace(old, new, *n)
string.lower = lambda s: s.lower()
string.upper = lambda s: s.upper()
string.strip = lambda s, *c: s.strip(*c)
string.find = lambda s, sub, *a: s.find(sub, *a)
string.split = lambda s, *a: s.split(*a)
string.join = lambda words, sep=" ": sep.join(words)
string.atoi = int

sys.path.insert(0, os.getcwd())
runpy.run_path(sys.argv[1] + ".py", run_name="__main__")
