from header_common import *
from header_operations import *
from module_constants import *
from coop.constants import *

# Link spike (switched on from the camp menu): sends the player's position to the local
# bridge with send_message_to_url and waits for the reply before sending again.
# "frames" counts how often this trigger ran since the last request, to measure the map tick.
triggers = [
  (0, 0, 0,
   [
     (eq, "$coop_link_test", 1),
   ],
   [
     (val_add, "$coop_link_frames", 1),
     (try_begin),
       (this_or_next|eq, "$coop_link_pending", 0),
       (ge, "$coop_link_frames", coop_link_resend_frames), #the reply was lost: send again
       (val_add, "$coop_link_seq", 1),
       (assign, "$coop_link_pending", 1),
       (assign, reg1, "$coop_link_seq"),
       (assign, reg2, "$coop_link_frames"),
       (store_current_hours, reg3),
       (assign, reg4, 0),
       (try_begin),
         (map_free),
         (assign, reg4, 1),
       (try_end),
       (set_fixed_point_multiplier, 100),
       (party_get_position, pos1, "p_main_party"),
       (position_get_x, reg5, pos1),
       (position_get_y, reg6, pos1),
       (assign, reg7, coop_link_port),
       (str_store_string, s10, "@http://127.0.0.1:{reg7}/tick?seq={reg1}&frames={reg2}&hours={reg3}&free={reg4}&x={reg5}&y={reg6}"),
       (assign, "$coop_link_frames", 0),
       (send_message_to_url, s10, 0),
       # diagnostics: the first sends, then every 50th, with how often this trigger ran
       (store_mod, ":every_50th", "$coop_link_seq", 50),
       (try_begin),
         (this_or_next|le, "$coop_link_seq", 3),
         (eq, ":every_50th", 0),
         (display_message, "@CoopWorld link: sent #{reg1} (trigger ran {reg2} times since the last send)", 0xAAAAAA),
       (try_end),
     (try_end),
    ]),
]


def merge(orig_triggers):
  orig_triggers.extend(triggers)
