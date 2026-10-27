"""CoopWorld network prototype: role switching, the world server's puppet, the client's mirror.

The wire format is described in tools/coop_bridge.py.
"""
from header_common import *
from header_operations import *
from module_constants import *
from header_parties import ai_bhvr_hold, ai_bhvr_travel_to_point
from coop.constants import *


def net_scripts(first_dynamic):
  return [
  # script_coop_become_server: this game owns the world; it rests so that time keeps flowing.
  ("coop_become_server",
   [
     (assign, "$coop_role", coop_role_server),
     (assign, "$coop_net_pending", 0),
     (assign, "$coop_net_cursor", -1),
     (display_message, "@CoopWorld: this game is now the WORLD SERVER. Leave it resting.", 0x66CCFF),
     (rest_for_hours_interactive, 24 * 365, coop_world_time_speed, 0), #rest while not attackable
    ]),

  # script_coop_become_client: the world simulation stops here; parties follow the server.
  # Assumes the client loaded the same save as the server, so spawned party ids match at the start.
  ("coop_become_client",
   [
     (assign, "$coop_role", coop_role_client),
     (assign, "$coop_net_pending", 0),
     (try_for_parties, ":party_no"),
       (ge, ":party_no", first_dynamic),
       (store_add, ":mapped", ":party_no", 1),
       (party_set_slot, "p_coop_map", ":party_no", ":mapped"),
       (party_set_ai_behavior, ":party_no", ai_bhvr_hold),
     (try_end),
     (display_message, "@CoopWorld: this game is now a CLIENT of the world server.", 0x66CCFF),
    ]),

  ("coop_stop",
   [
     (assign, "$coop_role", coop_role_single),
     (assign, reg1, "$coop_net_replies"),
     (assign, reg2, "$coop_net_spawned"),
     (display_message, "@CoopWorld: co-op stopped ({reg1} replies, {reg2} mirrors spawned). This game runs its own world again.", 0x66CCFF),
    ]),

  # script_coop_server_move_puppet: arg1, arg2 = client position (shifted by coop_net_offset)
  ("coop_server_move_puppet",
   [
     (store_script_param, ":x", 1),
     (store_script_param, ":y", 2),
     (val_sub, ":x", coop_net_offset),
     (val_sub, ":y", coop_net_offset),
     (set_fixed_point_multiplier, 100),
     (init_position, pos1),
     (position_set_x, pos1, ":x"),
     (position_set_y, pos1, ":y"),
     (enable_party, "p_coop_puppet_1"),
     (party_set_position, "p_coop_puppet_1", pos1),
    ]),

  # script_coop_client_apply: arg1 = entries stored in p_coop_buf slots (sid, tmpl, x, y each).
  # Keeps one mirror party per server party: the same id when the saves matched, a spawned copy otherwise.
  ("coop_client_apply",
   [
     (store_script_param, ":count", 1),
     (set_fixed_point_multiplier, 100),
     (try_for_range, ":k", 0, ":count"),
       (store_mul, ":base", ":k", 4),
       (party_get_slot, ":sid", "p_coop_buf", ":base"),
       (val_add, ":base", 1),
       (party_get_slot, ":tmpl", "p_coop_buf", ":base"),
       (val_add, ":base", 1),
       (party_get_slot, ":x", "p_coop_buf", ":base"),
       (val_add, ":base", 1),
       (party_get_slot, ":y", "p_coop_buf", ":base"),
       (val_sub, ":x", coop_net_offset),
       (val_sub, ":y", coop_net_offset),
       (party_get_slot, ":cid", "p_coop_map", ":sid"),
       (val_sub, ":cid", 1),
       (try_begin),
         (eq, ":tmpl", coop_net_removed),
         (try_begin),
           (ge, ":cid", first_dynamic),
           (party_is_active, ":cid"),
           (remove_party, ":cid"),
         (try_end),
         (party_set_slot, "p_coop_map", ":sid", 0),
       (else_try),
         (assign, ":have", 0),
         (try_begin),
           (ge, ":cid", first_dynamic),
           (party_is_active, ":cid"),
           (party_get_template_id, ":cur_tmpl", ":cid"),
           (eq, ":cur_tmpl", ":tmpl"),
           (assign, ":have", 1),
         (try_end),
         (try_begin),
           (eq, ":have", 0),
           (gt, ":tmpl", 0), #pt_none cannot be spawned
           (set_spawn_radius, 0),
           (spawn_around_party, "p_main_party", ":tmpl"),
           (assign, ":cid", reg0),
           (party_set_ai_behavior, ":cid", ai_bhvr_hold),
           # some templates spawn empty (lord parties get their troops by script): meeting an empty
           # party crashes the game, so a mirror always has someone in it
           (try_begin),
             (party_get_num_companions, ":members", ":cid"),
             (eq, ":members", 0),
             (party_add_members, ":cid", "trp_farmer", 1),
           (try_end),
           (store_add, ":mapped", ":cid", 1),
           (party_set_slot, "p_coop_map", ":sid", ":mapped"),
           (assign, ":have", 1),
           (val_add, "$coop_net_spawned", 1),
         (try_end),
         (eq, ":have", 1),
         (init_position, pos1),
         (position_set_x, pos1, ":x"),
         (position_set_y, pos1, ":y"),
         # near: walk there, so the map shows movement between updates; far: jump
         (party_get_position, pos2, ":cid"),
         (position_get_x, ":cur_x", pos2),
         (position_get_y, ":cur_y", pos2),
         (store_sub, ":dx", ":x", ":cur_x"),
         (store_sub, ":dy", ":y", ":cur_y"),
         (val_abs, ":dx"),
         (val_abs, ":dy"),
         (try_begin),
           (this_or_next|gt, ":dx", coop_mirror_snap),
           (gt, ":dy", coop_mirror_snap),
           (party_set_position, ":cid", pos1),
           (party_set_ai_behavior, ":cid", ai_bhvr_hold),
         (else_try),
           (party_set_ai_behavior, ":cid", ai_bhvr_travel_to_point),
           (party_set_ai_target_position, ":cid", pos1),
         (try_end),
       (try_end),
     (try_end),
    ]),
  ]


def net_reply_handler():
  """Appended to game_receive_url_response. Copies the reply numbers into p_coop_buf first,
  because registers cannot be indexed and the scripts called afterwards overwrite reg0."""
  copy = [(party_set_slot, "p_coop_buf", i, reg(3 + i)) for i in range(4 * coop_net_max_entries)]
  return [
    (try_begin),
      (neq, "$coop_role", coop_role_single),
      (assign, "$coop_net_pending", 0), #any reply, even a failed send, frees the next request
      (store_script_param, ":num_integers", 1),
      (ge, ":num_integers", 2),
      (eq, reg0, coop_net_marker),
      (val_add, "$coop_net_replies", 1),
      (try_begin),
        (eq, reg1, 1),
        (eq, "$coop_role", coop_role_server),
        (eq, reg2, 1),
        (call_script, "script_coop_server_move_puppet", reg3, reg4),
      (else_try),
        (eq, reg1, 2),
        (eq, "$coop_role", coop_role_client),
        (assign, ":count", reg2),
        (val_min, ":count", coop_net_max_entries),
      ] + copy + [
        (call_script, "script_coop_client_apply", ":count"),
      (try_end),
    (try_end),
  ]
