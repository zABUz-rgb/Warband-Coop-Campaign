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
  # World server: report the next batch of spawned parties, round robin, and learn where the client is.
  (0, 0, 0,
   [
     (eq, "$coop_role", coop_role_server),
   ],
   [
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
       (store_add, ":from", "$coop_net_cursor", 1),
       (store_add, ":end", "$coop_net_max_party", 1),
       (try_for_range, ":party_no", ":from", ":end"),
         (assign, "$coop_net_cursor", ":party_no"),
         (party_is_active, ":party_no"),
         (assign, reg11, ":party_no"),
         (party_get_template_id, reg12, ":party_no"),
         (party_get_position, pos1, ":party_no"),
         (position_get_x, reg13, pos1),
         (position_get_y, reg14, pos1),
         (str_store_string, s11, "@{s11}{reg11},{reg12},{reg13},{reg14};"),
         (val_add, ":count", 1),
         (ge, ":count", coop_net_batch),
         (assign, ":end", 0), #break
       (try_end),
       (try_begin),
         (ge, "$coop_net_cursor", "$coop_net_max_party"),
         (assign, "$coop_net_cursor", -1), #reached the end: start over
       (try_end),
       (assign, reg1, "$coop_net_seq"),
       (assign, reg2, ":count"),
       (str_store_string, s10, "@" + coop_server_url + "/srv?seq={reg1}&n={reg2}&d={s11}"),
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
       (party_get_position, pos1, "p_main_party"),
       (position_get_x, reg2, pos1),
       (position_get_y, reg3, pos1),
       (assign, reg1, "$coop_net_seq"),
       (str_store_string, s10, "@" + coop_client_url + "/cli?seq={reg1}&x={reg2}&y={reg3}"),
       (send_message_to_url, s10, 0),
     (try_end),
    ]),
  ]


def merge(orig_triggers):
  # a client shows the server's world: its own world triggers stay off
  for t in orig_triggers:
    t[3][0:0] = [(neq, "$coop_role", coop_role_client)]
  orig_triggers.extend(net_triggers(first_dynamic_party()))
