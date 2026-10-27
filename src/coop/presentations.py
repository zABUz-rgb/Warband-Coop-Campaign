def merge(presentations, **unused):
  # the waiting window of a joint battle (coop/mp_campaign.py)
  from coop.mp_campaign import mp_campaign_presentations
  presentations.extend(mp_campaign_presentations)
  # the weekly budget: the host's and the clients' money changes as always, the window closes at
  # once and the outcome is a message (a window would stop the world for everybody)
  from header_operations import (store_troop_gold, store_sub, try_begin, try_end, else_try, eq, ge, lt, this_or_next,
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
