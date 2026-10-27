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
       (assign, ":last", -1),
       (try_for_parties, ":party_no"),
         (lt, ":count", coop_net_batch),
         (ge, ":party_no", first_dynamic),
         (gt, ":party_no", "$coop_net_cursor"),
         (assign, reg11, ":party_no"),
         (party_get_template_id, reg12, ":party_no"),
         (party_get_position, pos1, ":party_no"),
         (position_get_x, reg13, pos1),
         (position_get_y, reg14, pos1),
         (str_store_string, s11, "@{s11}{reg11},{reg12},{reg13},{reg14};"),
         (val_add, ":count", 1),
         (assign, ":last", ":party_no"),
       (try_end),
       (try_begin),
         (lt, ":count", coop_net_batch),
         (assign, "$coop_net_cursor", -1), #reached the end: start over
       (else_try),
         (assign, "$coop_net_cursor", ":last"),
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
