def merge(presentations, **unused):
  # the waiting window of a joint battle (coop/mp_campaign.py)
  from coop.mp_campaign import mp_campaign_presentations
  presentations.extend(mp_campaign_presentations)
  # a joint event's counter in the battle window (coop/mp.py)
  from coop.mp import mp_presentations
  presentations.extend(mp_presentations)
  # the troop tree (coop/tree.py)
  from coop.tree import tree_presentations
  presentations.extend(tree_presentations)
  # the weekly budget: the host's and the clients' money changes as always, the window closes at
  # once and the outcome is a message (a window would stop the world for everybody)
  from header_operations import (store_troop_gold, store_sub, try_begin, try_end, else_try, eq, ge, lt, this_or_next, store_trigger_param_1,
                                 assign, display_message, presentation_set_duration, val_mul)
  from header_triggers import ti_on_presentation_load
  from header_common import reg1
  from coop_merge import get_by_id, MergeError
  budget = get_by_id(presentations, "budget_report")
  load = [t for t in budget[3] if t[0] == ti_on_presentation_load]
  if len(load) != 1:
    raise MergeError("budget_report: expected one load trigger")
  block = load[0][1]
  block[0:0] = [(store_troop_gold, ":coop_gold_before", "trp_player")]
  block.extend([
      (try_begin),
        (this_or_next|eq, "$coop_srv_player", 1),
        (eq, "$coop_role", 2), #a client
        (eq, "$g_apply_budget_report_to_gold", 1),
        (store_troop_gold, ":coop_gold_after", "trp_player"),
        (store_sub, reg1, ":coop_gold_after", ":coop_gold_before"),
        (try_begin),
          (ge, reg1, 0),
          (display_message, "@CoopWorld: weekly budget settled: +{reg1} denars (Reports - budget for details).", 0xFFEECC),
        (else_try),
          (val_mul, reg1, -1),
          (display_message, "@CoopWorld: weekly budget settled: -{reg1} denars (Reports - budget for details).", 0xFFEECC),
        (try_end),
        (presentation_set_duration, 0),
      (try_end),
  ])
  # a battle of the campaign: every player's escape menu offers the retreat, which ends the battle with nobody the
  # winner (coop_mp_retreat; 11-05, the user's ask: a way to leave a siege, then every joint battle). The first click
  # arms it, the second sounds it, so a slip of the mouse does not end the battle for everybody. A button like the
  # others (white, a short word); with it the rows stand closer when they would run out of the menu's frame.
  from header_operations import (create_button_overlay, overlay_set_color, overlay_set_position, overlay_set_text,
                                 position_set_x, position_set_y, val_sub, val_add, store_sub, store_div, gt,
                                 multiplayer_get_my_team, multiplayer_is_server, multiplayer_get_my_player, call_script,
                                 multiplayer_send_message_to_server, set_container_overlay)
  from header_triggers import ti_on_presentation_event_state_change
  from header_common import pos1, escape_menu_item_height, multi_team_spectator
  from coop.constants import coop_mp_event_retreat
  menu = get_by_id(presentations, "multiplayer_escape_menu")
  load = [t for t in menu[3] if t[0] == ti_on_presentation_load]
  click = [t for t in menu[3] if t[0] == ti_on_presentation_event_state_change]
  if len(load) != 1 or len(click) != 1:
    raise MergeError("multiplayer_escape_menu: expected one load and one click trigger")
  block = load[0][1]
  shown = (presentation_set_duration, 999999)
  quit_color = (overlay_set_color, "$g_presentation_obj_escape_menu_10", 0xFFFFFF)
  step = (val_sub, ":cur_y", escape_menu_item_height)
  if block.count(shown) != 1 or block[-1] != shown or block.count(quit_color) != 1:
    raise MergeError("multiplayer_escape_menu: the load trigger no longer looks as expected")
  at = block.index(quit_color) + 1  # every button is made; their places come next
  steps = [i for i in range(at, len(block)) if block[i] == step]
  if len(steps) != 12:
    raise MergeError(f"multiplayer_escape_menu: expected 12 rows placed after the buttons, found {len(steps)}")
  for i in steps:
    block[i] = (val_sub, ":cur_y", ":coop_step")
  rows = ["$g_presentation_obj_escape_menu_%d" % k for k in range(1, 14)] + ["$coop_obj_retreat"]
  block[at:at] = [
      (try_begin),
        (eq, "$coop_mp_campaign_on", 1),
        (multiplayer_get_my_team, ":coop_team"),
        (lt, ":coop_team", multi_team_spectator),
        (create_button_overlay, "$coop_obj_retreat", "@Retreat", 0),
        (overlay_set_color, "$coop_obj_retreat", 0xFFFFFF),
      (try_end),
      # the first row stands at 460, the lowest is to stand at 20 or above (below, the frame cuts it)
      (assign, ":coop_rows", 0),
      ] + [op for var in rows for op in [
      (try_begin),
        (ge, var, 0),
        (val_add, ":coop_rows", 1),
      (try_end),
      ]] + [
      (assign, ":coop_step", escape_menu_item_height),
      (try_begin),
        (gt, ":coop_rows", 1),
        (store_sub, ":coop_gaps", ":coop_rows", 1),
        (store_div, ":coop_fit", 440, ":coop_gaps"),
        (lt, ":coop_fit", ":coop_step"),
        (assign, ":coop_step", ":coop_fit"),
      (try_end),
  ]
  block[0:0] = [(assign, "$coop_obj_retreat", -1), (assign, "$coop_retreat_armed", 0)]
  block[-1:-1] = [
      (try_begin),
        (ge, "$coop_obj_retreat", 0),
        (val_sub, ":cur_y", ":coop_step"),
        (position_set_x, pos1, 130),
        (position_set_y, pos1, ":cur_y"),
        (overlay_set_position, "$coop_obj_retreat", pos1),
      (try_end),
      (set_container_overlay, -1),  # Native leaves the menu's container open
  ]
  block = click[0][1]
  if not block or block[0][0] != store_trigger_param_1 or block[0][1] != ":object":
    raise MergeError("multiplayer_escape_menu: the click trigger no longer starts with the object")
  block[1:1] = [
      (try_begin),
        (ge, "$coop_obj_retreat", 0),
        (eq, ":object", "$coop_obj_retreat"),
        (try_begin),
          (eq, "$coop_retreat_armed", 0),
          (assign, "$coop_retreat_armed", 1),
          (overlay_set_text, "$coop_obj_retreat", "@Retreat: sure?"),
        (else_try),
          (presentation_set_duration, 0),
          (try_begin),
            (multiplayer_is_server),
            (multiplayer_get_my_player, ":coop_me"),
            (call_script, "script_coop_mp_retreat", ":coop_me"),
          (else_try),
            (multiplayer_send_message_to_server, coop_mp_event_retreat),
          (try_end),
        (try_end),
      (try_end),
  ]
