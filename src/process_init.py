from module_info import *
from process_operations import *
import os

print("Initializing...")

try:
  os.remove(export_dir + 'tag_uses.txt')
except:
  a = []
try:
  os.remove(export_dir + 'quick_strings.txt')
except:
  a = []
# CoopWorld: the last build's variables.txt stays: process_global_variables keeps its order (saves of
# the last version keep their globals). Only a first build starts from Diplomacy's list.
_keep_order = os.path.exists(export_dir + 'variables.txt')
if not _keep_order:
  try:
    os.remove(export_dir + 'variable_uses.txt')
  except:
    a = []

variables = []
variable_uses = []
try:
  if _keep_order:
    raise IOError("the last build's order is kept")
  file = open("variables.txt","r")
  var_list = file.readlines()
  file.close()
  for v in var_list:
    vv = string.strip(v)
    if vv:
      variables.append(vv)
      variable_uses.append(int(1))
  save_variables(export_dir, variables, variable_uses)
except:
  if not _keep_order:
    print("variables.txt not found. Creating new variables.txt file")
