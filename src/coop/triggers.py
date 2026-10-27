from header_common import *
from header_operations import *
from module_constants import *
from coop.constants import *


def first_dynamic_party():
  """Parties spawned during the game get ids after every party defined in module_parties."""
  from module_parties import parties
  return len(parties)


def net_triggers(first_dynamic):
  return [
  # World server held for a joining client: only asks whether the client has joined.
  (0, 0, 0,
   [
     (eq, "$coop_role", coop_role_held),
   ],
   [
     (val_add, "$coop_net_frames", 1),
     (try_begin),
       (this_or_next|eq, "$coop_net_pending", 0),
       (ge, "$coop_net_frames", coop_net_resend_frames),
       (assign, "$coop_net_pending", 1),
       (assign, "$coop_net_frames", 0),
       (val_add, "$coop_net_seq", 1),
       (assign, reg1, "$coop_net_seq"),
       (str_store_string, s10, "@" + coop_server_url + "/srv?seq={reg1}&hold=1"),
       (send_message_to_url, s10, 0),
     (try_end),
    ]),

  # World server: report the next batch of spawned parties, round robin, and learn where the client is.
  (0, 0, 0,
   [
     (eq, "$coop_role", coop_role_server),
   ],
   [
     # resting keeps the world's time flowing; a click on the server's map (or a menu) ends the
     # rest, so the server goes back to resting after a moment on the free map, unless paused
     (try_begin),
       (eq, "$coop_srv_paused", 0),
       (map_free),
       (val_add, "$coop_srv_idle_frames", 1),
       (ge, "$coop_srv_idle_frames", coop_client_idle_frames),
       (assign, "$coop_srv_idle_frames", 0),
       (rest_for_hours_interactive, 24 * 365, coop_world_time_speed, 0),
     (else_try),
       (assign, "$coop_srv_idle_frames", 0),
     (try_end),
     (val_add, "$coop_net_frames", 1),
     (try_begin),
       (this_or_next|eq, "$coop_net_pending", 0),
       (ge, "$coop_net_frames", coop_net_resend_frames), #the reply was lost: send again
       (assign, "$coop_net_pending", 1),
       (assign, "$coop_net_frames", 0),
       (val_add, "$coop_net_seq", 1),
       (set_fixed_point_multiplier, 100),
       (str_clear, s11),
       (assign, ":count", 0),
       # try_for_parties does not go in id order, so walk the ids up to the highest active one
       (try_begin),
         (lt, "$coop_net_cursor", 0), #a new sweep
         (assign, "$coop_net_max_party", 0),
         (try_for_parties, ":party_no"),
           (val_max, "$coop_net_max_party", ":party_no"),
         (try_end),
         (assign, "$coop_net_cursor", first_dynamic - 1),
       (try_end),
       # parties close to the client's puppet first: they are the ones the client sees move
       (try_begin),
         (party_is_active, "p_coop_puppet_1"),
         (party_get_position, pos3, "p_coop_puppet_1"),
         (position_get_x, ":puppet_x", pos3),
         (position_get_y, ":puppet_y", pos3),
         (store_add, ":from", "$coop_near_cursor", 1),
         (val_max, ":from", first_dynamic),
         (store_add, ":end", "$coop_net_max_party", 1),
         (assign, ":near", 0),
         (try_for_range, ":party_no", ":from", ":end"),
           (assign, "$coop_near_cursor", ":party_no"),
           (party_is_active, ":party_no"),
           (party_get_position, pos4, ":party_no"),
           (position_get_x, ":dx", pos4),
           (position_get_y, ":dy", pos4),
           (val_sub, ":dx", ":puppet_x"),
           (val_sub, ":dy", ":puppet_y"),
           (val_abs, ":dx"),
           (val_abs, ":dy"),
           (le, ":dx", coop_net_near_radius),
           (le, ":dy", coop_net_near_radius),
           (call_script, "script_coop_append_entry", ":party_no"),
           (val_add, ":near", 1),
           (val_add, ":count", 1),
           (ge, ":near", coop_net_batch_near),
           (assign, ":end", 0), #break
         (try_end),
         (try_begin),
           (ge, "$coop_near_cursor", "$coop_net_max_party"),
           (assign, "$coop_near_cursor", -1), #all near parties sent: start over
         (try_end),
       (try_end),
       # then the rest of the world, round robin
       (store_add, ":from", "$coop_net_cursor", 1),
       (store_add, ":end", "$coop_net_max_party", 1),
       (assign, ":far", 0),
       (try_for_range, ":party_no", ":from", ":end"),
         (assign, "$coop_net_cursor", ":party_no"),
         (party_is_active, ":party_no"),
         (call_script, "script_coop_append_entry", ":party_no"),
         (val_add, ":far", 1),
         (val_add, ":count", 1),
         (ge, ":far", coop_net_batch_far),
         (assign, ":end", 0), #break
       (try_end),
       (try_begin),
         (ge, "$coop_net_cursor", "$coop_net_max_party"),
         (assign, "$coop_net_cursor", -1), #reached the end: start over
       (try_end),
       # troops of the next party close to the client's puppet: the client fights these
       (str_clear, s13),
       (try_begin),
         (party_is_active, "p_coop_puppet_1"),
         (party_get_position, pos3, "p_coop_puppet_1"),
         (position_get_x, ":puppet_x", pos3),
         (position_get_y, ":puppet_y", pos3),
         (assign, ":found", -1),
         (store_add, ":from", "$coop_troops_cursor", 1),
         (val_max, ":from", first_dynamic),
         (store_add, ":end", "$coop_net_max_party", 1),
         (try_for_range, ":party_no", ":from", ":end"),
           (party_is_active, ":party_no"),
           (party_get_position, pos4, ":party_no"),
           (position_get_x, ":dx", pos4),
           (position_get_y, ":dy", pos4),
           (val_sub, ":dx", ":puppet_x"),
           (val_sub, ":dy", ":puppet_y"),
           (val_abs, ":dx"),
           (val_abs, ":dy"),
           (le, ":dx", coop_srv_troops_radius),
           (le, ":dy", coop_srv_troops_radius),
           (assign, ":found", ":party_no"),
           (assign, ":end", 0), #break
         (try_end),
         (try_begin),
           (lt, ":found", 0),
           (assign, "$coop_troops_cursor", -1), #none left: start over
         (else_try),
           (assign, "$coop_troops_cursor", ":found"),
           (call_script, "script_coop_troops_to_s12", ":found", 0),
           (assign, reg15, ":found"),
           (str_store_string, s13, "@&c={reg15}{s12}"),
         (try_end),
       (try_end),
       (assign, reg1, "$coop_net_seq"),
       (assign, reg2, ":count"),
       (store_current_hours, reg3),
       (str_store_string, s10, "@" + coop_server_url + "/srv?seq={reg1}&h={reg3}&n={reg2}&d={s11}{s13}"),
       (send_message_to_url, s10, 0),
     (try_end),
    ]),

  # Client: send where the player is; the reply carries the server's parties near the player.
  (0, 0, 0,
   [
     (eq, "$coop_role", coop_role_client),
   ],
   [
     # time on the map flows only while the player moves or rests: rest when standing still,
     # a click on the map ends the rest as in Native "Wait here"
     (try_begin),
       (map_free),
       (set_fixed_point_multiplier, 100),
       (party_get_position, pos2, "p_main_party"),
       (position_get_x, ":x", pos2),
       (position_get_y, ":y", pos2),
       (try_begin),
         (eq, ":x", "$coop_last_x"),
         (eq, ":y", "$coop_last_y"),
         (val_add, "$coop_idle_frames", 1),
       (else_try),
         (assign, "$coop_idle_frames", 0),
       (try_end),
       (assign, "$coop_last_x", ":x"),
       (assign, "$coop_last_y", ":y"),
       (ge, "$coop_idle_frames", coop_client_idle_frames),
       (assign, "$coop_idle_frames", 0),
       (rest_for_hours_interactive, 24 * 365, coop_world_time_speed, 1), #rest while attackable
     (try_end),
     (val_add, "$coop_net_frames", 1),
     (try_begin),
       (this_or_next|eq, "$coop_net_pending", 0),
       (ge, "$coop_net_frames", coop_net_resend_frames),
       (assign, "$coop_net_pending", 1),
       (assign, "$coop_net_frames", 0),
       (val_add, "$coop_net_seq", 1),
       (set_fixed_point_multiplier, 100),
       # back on the map after an encounter: the world may run again, and what the battle
       # changed goes to the server, one party per request
       # busy: 1 = an encounter started, 2 = its menu or battle is open, 0 = back on the map.
       # The map is still free in the very frame the encounter starts, so 1 only ends once the
       # menu was seen, or after a while when no menu opened at all.
       (try_begin),
         (eq, "$coop_busy", 1),
         (neg|map_free),
         (assign, "$coop_busy", 2),
       (else_try),
         (eq, "$coop_busy", 1),
         (val_add, "$coop_busy_frames", 1),
         (ge, "$coop_busy_frames", coop_busy_timeout_frames),
         (assign, "$coop_busy", 0),
       (else_try),
         (eq, "$coop_busy", 2),
         (map_free),
         (assign, "$coop_busy", 0),
       (else_try),
         # time flows again although the map is not free: the encounter ended in a rest
         # (captivity, serving in a lord's army, waiting); the world may run
         (eq, "$coop_busy", 2),
         (store_current_hours, ":hours"),
         (gt, ":hours", "$coop_busy_hours"),
         (assign, "$coop_busy", 0),
       (try_end),
       (str_clear, s13),
       (try_begin),
         (map_free),
         (eq, "$coop_busy", 0),
         (party_slot_ge, "p_coop_enc", 0, 1),
         (call_script, "script_coop_client_next_result"),
       (try_end),
       (try_begin),
         (eq, "$coop_hello", 1),
         (assign, "$coop_hello", 0),
         (str_store_string, s13, "@{s13}&hello=1"),
       (try_end),
       (str_clear, s14),
       (val_add, "$coop_own_troops_frames", 1),
       (try_begin),
         (ge, "$coop_own_troops_frames", coop_own_troops_frames),
         (assign, "$coop_own_troops_frames", 0),
         (call_script, "script_coop_troops_to_s12", "p_main_party", 1),
         (str_store_string, s14, "@&me={s12}"),
       (try_end),
       (party_get_position, pos1, "p_main_party"),
       (position_get_x, reg2, pos1),
       (position_get_y, reg3, pos1),
       (assign, reg1, "$coop_net_seq"),
       (assign, reg4, "$coop_busy"),
       (store_current_hours, reg5),
       (assign, reg6, 0),
       (try_begin),
         (map_free),
         (assign, reg6, 1),
       (try_end),
       (str_store_string, s10, "@" + coop_client_url + "/cli?seq={reg1}&h={reg5}&free={reg6}&x={reg2}&y={reg3}&busy={reg4}{s13}{s14}"),
       (send_message_to_url, s10, 0),
     (try_end),
    ]),
  ]


def merge(orig_triggers):
  # a client shows the server's world: its own world triggers stay off
  from coop.quiet import quiet_block
  for t in orig_triggers:
    if "$freelancer_state" not in repr(t):  # Freelancer's triggers act on the player: keep them
      t[3][0:0] = [(neq, "$coop_role", coop_role_client)]
    quiet_block(t[3])  # the unattended world server opens no windows (tutorial hints)
    quiet_block(t[4])
  orig_triggers.extend(net_triggers(first_dynamic_party()))
