from header_common import *
from header_operations import *
from module_constants import *


# Simple triggers a client keeps: they act on the player, not on the world (auto menus after a rest,
# such as the escape from captivity; food; lodging; Freelancer's pay, promotion and following).
CLIENT_KEEPS = ("$g_check_autos_at_hour", "script_consume_food", "@You pay for accommodation.",
                "$player_cur_troop", "$enlisted_party")


def gate_world_triggers(orig_simple_triggers):
  """A client shows the server's world, so its own world simulation stays off."""
  from coop.constants import coop_role_client
  found = {k: 0 for k in CLIENT_KEEPS}
  for t in orig_simple_triggers:
    text = repr(t[1])
    keys = [k for k in CLIENT_KEEPS if k in text]
    for k in keys:
      found[k] += 1
    if keys:
      continue
    t[1][0:0] = [(neq, "$coop_role", coop_role_client)]
  missing = [k for k, n in found.items() if n == 0]
  if missing or sum(found.values()) > 2 * len(CLIENT_KEEPS):
    from coop_merge import MergeError
    raise MergeError(f"client keeps simple triggers by {found}: a key matched nothing or too much")


# Simple triggers whose window the host sees only when asking for it (Camp - "read the news"): the
# notification menus (war, lost fiefs, diplomacy, a lady's invitation, deserters), companions who
# want a word, the marshal's messengers. A window would stop the world for everybody at a moment
# nobody chose. Rare daily ones (the offer to join a kingdom, the end of a mercenary contract) join
# the notification queue instead, so they are not missed; the banner choice (once) still shows.
HELD_BACK_OPS = (
  (jump_to_menu, ":menu_type"),
  (jump_to_menu, "mnu_kingdom_army_quest_report_to_army"),
  (jump_to_menu, "mnu_kingdom_army_quest_join_siege_order"),
  (jump_to_menu, "mnu_kingdom_army_quest_messenger"),
  (jump_to_menu, "mnu_kingdom_army_follow_failed"),
)


QUEUED_MENUS = ("mnu_invite_player_to_faction", "mnu_invite_player_to_faction_without_center",
                "mnu_oath_fulfilled")


def queue_for_host(block):
  """(jump_to_menu, a daily menu) -> the host gets it as a notification instead. Returns how many."""
  count = 0
  i = 0
  while i < len(block):
    op = block[i]
    if isinstance(op, tuple) and op[0] == jump_to_menu and op[1] in QUEUED_MENUS:
      block[i:i + 1] = [(try_begin), (eq, "$coop_srv_player", 1),
                        (call_script, "script_add_notification_menu", op[1], 0, 0),
                        (else_try), op, (try_end)]
      i += 6
      count += 1
    else:
      i += 1
  return count


def hold_back_for_host(orig_simple_triggers):
  """The triggers that open such a window wait while the host plays on and run when the host asks.
  Returns how many."""
  count = 0
  for t in orig_simple_triggers:
    ops = [op for op in t[1] if isinstance(op, tuple)]
    if any(op in HELD_BACK_OPS or op[0] == start_map_conversation for op in ops):
      t[1][0:0] = [(this_or_next | neq, "$coop_srv_player", 1), (eq, "$coop_read_news", 1)]
      count += 1
  return count


def merge(orig_simple_triggers):
  """Native's nightly accommodation trigger takes the last coins when the player cannot pay;
  CoopWorld turns the player out until dawn instead."""
  from coop_merge import find_line, MergeError
  paying = [t for t in orig_simple_triggers
            if any(op == (display_message, "@You pay for accommodation.") for op in t[1])]
  if len(paying) != 1:
    raise MergeError(f"expected one accommodation trigger, found {len(paying)}")
  block = paying[0][1]
  pos = find_line(block, (gt, ":gold", 0))
  if block[pos + 1] != (troop_remove_gold, "trp_player", ":gold"):
    raise MergeError("accommodation trigger: unexpected code after (gt, :gold, 0)")
  block[pos:pos + 2] = [(call_script, "script_coop_evict_from_town")]
  gate_world_triggers(orig_simple_triggers)
  # the host playing on the server: news that opens a window waits until the host asks for it
  held = hold_back_for_host(orig_simple_triggers)
  queued = sum(queue_for_host(t[1]) for t in orig_simple_triggers)
  if held < 4 or queued < 3:
    raise MergeError(f"host's news: {held} triggers held back (expected 4), {queued} menus queued (expected 3)")
  # the unattended world server opens no windows (weekly report, budget, notifications)
  from coop.quiet import quiet_block
  quieted = sum(quiet_block(t[1]) for t in orig_simple_triggers)
  if quieted == 0:
    raise MergeError("no window operations found in the simple triggers")
