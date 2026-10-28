from header_common import *
from header_operations import *
from module_constants import *
from coop.constants import *


def first_dynamic_party():
  """Parties spawned during the game get ids after every party defined in module_parties."""
  from module_parties import parties
  return len(parties)


def puppet_range():
  """(first, end) party ids of the players' parties coop_puppet_1..coop_max_players"""
  from module_parties import parties
  first = [p[0] for p in parties].index("coop_puppet_1")
  return first, first + coop_max_players


def net_triggers(first_dynamic):
  from coop.mp_campaign import client_map_tick, client_request_suffix
  from coop.profile import client_tick as profile_tick
  from coop.players import map_tick as players_tick
  puppets_end = puppet_range()[1]
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
       # the host's game hears back at once; a friend's game that loaded the held save never does
       (val_sub, "$coop_hold_alive", 1),
       (val_max, "$coop_hold_alive", 0),
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
     # rest, so the server goes back to resting after a moment on the free map, unless paused.
     # The host playing here rests like a player: only while standing still.
     # (The count is reset only by moving, a menu or the pause: a failed condition inside a try
     # block falls through to its else_try, so the threshold check has a block of its own.)
     (assign, ":still", 0),
     (try_begin),
       (eq, "$coop_srv_paused", 0),
       (map_free),
       (assign, ":still", 1),
       (eq, "$coop_srv_player", 1),
       (eq, "$coop_leader", 0), #following another player: carried along, the host still rests
       (neq, "$freelancer_state", 1), #serving in a lord's party: the same
       (set_fixed_point_multiplier, 100),
       (party_get_position, pos2, "p_main_party"),
       (position_get_x, ":x", pos2),
       (position_get_y, ":y", pos2),
       (this_or_next|neq, ":x", "$coop_last_x"),
       (neq, ":y", "$coop_last_y"),
       (assign, ":still", 0), #the host moved
       (assign, "$coop_last_x", ":x"),
       (assign, "$coop_last_y", ":y"),
     (try_end),
     (try_begin),
       (eq, ":still", 1),
       (val_add, "$coop_srv_idle_frames", 1),
     (else_try),
       (assign, "$coop_srv_idle_frames", 0),
     (try_end),
     (try_begin),
       (ge, "$coop_srv_idle_frames", coop_client_idle_frames),
       (assign, "$coop_srv_idle_frames", 0),
       (assign, ":attackable", "$coop_srv_player"), #the host may be attacked
       (try_begin),
         (eq, "$freelancer_state", 1),
         (assign, ":attackable", 0),
       (try_end),
       (rest_for_hours_interactive, 24 * 365, coop_world_time_speed, ":attackable"),
     (try_end),
     (try_begin),
       (eq, "$coop_srv_player", 1),
       # news held back: say so when more arrives; reading ends once the map was free a while
       (try_begin),
         (call_script, "script_coop_count_news"),
         (gt, reg0, "$coop_news_told"),
         (eq, "$coop_read_news", 0),
         (display_message, "@CoopWorld: news held back ({reg0}): Camp - read the news, when it suits you.", 0xFFDD66),
       (try_end),
       (assign, "$coop_news_told", reg0),
       # reading lasts until the queue is empty and three game hours have passed (companions and
       # the marshal's messengers come at such intervals)
       (try_begin),
         (eq, "$coop_read_news", 1),
         (call_script, "script_coop_count_news"),
         (eq, reg0, 0),
         (store_current_hours, ":now"),
         (store_sub, ":reading", ":now", "$coop_news_since"),
         (ge, ":reading", 3),
         (assign, "$coop_read_news", 0),
         (display_message, "@CoopWorld: all news read.", 0xFFDD66),
       (try_end),
       ] + client_map_tick() + players_tick() + [
       # the world is held by another player: remind now and then why nothing moves
       (try_begin),
         (eq, "$coop_world_paused", 1),
         (val_add, "$coop_pause_reminder", 1),
         (ge, "$coop_pause_reminder", coop_pause_reminder_frames),
         (assign, "$coop_pause_reminder", 0),
         (call_script, "script_coop_client_pause_message", "$coop_pause_slot", "$coop_pause_why"),
       (try_end),
     (try_end),
     (val_add, "$coop_net_frames", 1),
     (try_begin),
       (this_or_next|eq, "$coop_net_pending", 0),
       (ge, "$coop_net_frames", coop_net_resend_frames), #the reply was lost: send again
       # the host's game hears back at once; a friend's game that loaded the host's save never does
       (val_sub, "$coop_hold_alive", 1),
       (val_max, "$coop_hold_alive", 0),
       (assign, "$coop_net_pending", 1),
       (assign, "$coop_net_frames", 0),
       (val_add, "$coop_net_seq", 1),
       (store_mod, ":turn", "$coop_net_seq", coop_host_cli_every),
     (try_begin),
       (eq, "$coop_srv_player", 1),
       (eq, ":turn", 0),
       # the host as a player: position, troops, name, joint battles
       ] + client_request_suffix() + [
       (call_script, "script_coop_host_player_request"),
       (send_message_to_url, s10, 0),
     (else_try),
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
       # the players take turns: this report looks around one of them
       (assign, ":puppet", -1),
       (try_for_range, ":unused", 0, coop_max_players),
         (lt, ":puppet", 0),
         (val_add, "$coop_turn_slot", 1),
         (val_mod, "$coop_turn_slot", coop_max_players),
         (store_add, ":candidate", "p_coop_puppet_1", "$coop_turn_slot"),
         (party_is_active, ":candidate"),
         (assign, ":puppet", ":candidate"),
       (try_end),
       # parties close to that player first: they are the ones the player sees move
       (assign, ":lb_party", -1), #one of them in a field battle: the bridge tells the lord's soldiers
       (assign, ":lb_opponent", -1),
       (try_begin),
         (ge, ":puppet", 0),
         (party_get_position, pos3, ":puppet"),
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
           (try_begin),
             (lt, ":lb_party", 0),
             (party_get_battle_opponent, ":opponent", ":party_no"),
             (ge, ":opponent", first_dynamic), #a field battle with a world party
             (party_is_active, ":opponent"),
             (assign, ":lb_party", ":party_no"),
             (assign, ":lb_opponent", ":opponent"),
           (try_end),
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
       # troops of the next party close to that player: the player fights these
       (str_clear, s13),
       (try_begin),
         (ge, ":puppet", 0),
         (party_get_position, pos3, ":puppet"),
         (position_get_x, ":puppet_x", pos3),
         (position_get_y, ":puppet_y", pos3),
         (assign, ":found", -1),
         (store_add, ":from", "$coop_troops_cursor", 1),
         (val_max, ":from", centers_begin), #towns and castles too: their garrisons hold sieges
         (store_add, ":end", "$coop_net_max_party", 1),
         (try_for_range, ":party_no", ":from", ":end"),
           (this_or_next|is_between, ":party_no", walled_centers_begin, walled_centers_end),
           (ge, ":party_no", first_dynamic),
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
       # whom one center belongs to, round robin: the players' maps follow conquests
       (val_add, "$coop_center_cursor", 1),
       (try_begin),
         (neg|is_between, "$coop_center_cursor", centers_begin, centers_end),
         (assign, "$coop_center_cursor", centers_begin),
       (try_end),
       (assign, reg16, "$coop_center_cursor"),
       (store_faction_of_party, reg17, "$coop_center_cursor"),
       (party_get_slot, reg18, "$coop_center_cursor", slot_town_lord),
       (party_get_slot, reg19, "$coop_center_cursor", slot_center_is_besieged_by),
       (val_max, reg19, -1),
       (val_add, reg19, 1), #+ 1: 0 when nobody besieges it
       (str_store_string, s13, "@{s13}&cf={reg16},{reg17},{reg18},{reg19}"),
       (try_begin),
         (ge, ":lb_party", 0),
         (assign, reg16, ":lb_party"),
         (assign, reg17, ":lb_opponent"),
         (str_store_string, s13, "@{s13}&lb={reg16},{reg17}"),
       (try_end),
       (assign, reg1, "$coop_net_seq"),
       (assign, reg2, ":count"),
       (store_current_hours, reg3),
       (str_store_string, s10, "@" + coop_server_url + "/srv?seq={reg1}&h={reg3}&n={reg2}&d={s11}{s13}"),
       (send_message_to_url, s10, 0),
     (try_end),
     (try_end),
    ]),

  # Client: send where the player is; the reply carries the server's parties near the player.
  (0, 0, 0,
   [
     (eq, "$coop_role", coop_role_client),
   ],
   client_map_tick() + players_tick() + [
     # time on the map flows only while the player moves or rests: rest when standing still,
     # a click on the map ends the rest as in Native "Wait here"
     (try_begin),
       (map_free),
       (set_fixed_point_multiplier, 100),
       (party_get_position, pos2, "p_main_party"),
       (position_get_x, ":x", pos2),
       (position_get_y, ":y", pos2),
       (assign, ":carried", 0), #serving in a lord's party, or a prisoner: moved along, never by the player
       (try_begin),
         (this_or_next|eq, "$freelancer_state", 1),
         (eq, "$g_player_is_captive", 1),
         (assign, ":carried", 1),
       (try_end),
       (try_begin),
         (eq, ":x", "$coop_last_x"),
         (eq, ":y", "$coop_last_y"),
         (val_add, "$coop_idle_frames", 1),
       (else_try),
         (eq, ":carried", 1),
         (val_add, "$coop_idle_frames", 1),
       (else_try),
         (assign, "$coop_idle_frames", 0),
       (try_end),
       (assign, "$coop_last_x", ":x"),
       (assign, "$coop_last_y", ":y"),
       (eq, "$coop_world_paused", 0), #the world stands still: so does this player's clock
       (ge, "$coop_idle_frames", coop_client_idle_frames),
       (assign, "$coop_idle_frames", 0),
       (store_sub, ":attackable", 1, ":carried"), #rest while attackable, standing on the map
       (call_script, "script_coop_rest_interactive", 24 * 365, coop_world_time_speed, ":attackable"),
     (try_end),
     (try_begin),
       (eq, "$freelancer_state", 1),
       (ge, "$coop_lord_enemy_sid", 0),
       (neq, "$coop_lord_enemy_sid", "$coop_lord_asked"),
       (eq, "$coop_mp_state", 0),
       (eq, "$coop_busy", 0),
       (neq, "$g_player_is_captive", 1),
       (store_troop_health, ":health", "trp_player"),
       (ge, ":health", 50), #as Freelancer's own call to battle
       (assign, "$coop_lord_asked", "$coop_lord_enemy_sid"),
       (display_message, "@CoopWorld: your commander goes into battle!", 0xFFDD66),
       (jump_to_menu, "mnu_world_map_soldier"),
     (try_end),
     # menu: off the map while time stands still (inventory, reports, a town's menus). The world
     # pauses on the server too. A rest (time flows) is not a menu; a rest this game did not start
     # (captivity, Freelancer) counts as a menu only until its first game hour has passed.
     (store_current_hours, ":hours_now"),
     (try_begin),
       # the frame our rest began the map still counts as free: that must not end the rest's mark,
       # or the next frame took the rest for a menu and paused the world until a game hour passed
       (eq, "$coop_rest_frame", 1),
       (assign, "$coop_rest_frame", 0),
     (else_try),
       (map_free),
       (assign, "$coop_menu", 0),
       (assign, "$coop_menu_hours", -1),
     (else_try),
       (eq, "$coop_menu_hours", -2),
       (assign, "$coop_menu", 0),
     (else_try),
       (lt, "$coop_menu_hours", 0),
       (assign, "$coop_menu_hours", ":hours_now"),
       (assign, "$coop_menu", 1),
     (else_try),
       (gt, ":hours_now", "$coop_menu_hours"),
       (assign, "$coop_menu", 0),
       (assign, "$coop_menu_hours", ":hours_now"),
     (try_end),
     # the world is held by another player: remind now and then why nothing moves
     (try_begin),
       (eq, "$coop_world_paused", 1),
       (val_add, "$coop_pause_reminder", 1),
       (ge, "$coop_pause_reminder", coop_pause_reminder_frames),
       (assign, "$coop_pause_reminder", 0),
       (call_script, "script_coop_client_pause_message", "$coop_pause_slot", "$coop_pause_why"),
     (try_end),
     # a mirror the server has not mentioned for a long while is gone there (destroyed while this
     # game was away, or a party of the loaded save the world no longer has): it goes here too
     (val_add, "$coop_sweep_frames", 1),
     (try_begin),
       (ge, "$coop_sweep_frames", coop_mirror_sweep_frames),
       (assign, "$coop_sweep_frames", 0),
       (store_sub, ":old", "$coop_net_seq", coop_mirror_stale_requests),
       (assign, ":last", 0),
       (try_for_parties, ":party_no"),
         (val_max, ":last", ":party_no"),
       (try_end),
       (val_add, ":last", 1),
       (try_for_range, ":party_no", first_dynamic, ":last"), #by id, not try_for_parties: parties go meanwhile
         (party_is_active, ":party_no"),
         (party_slot_ge, ":party_no", slot_party_coop_sid, 1),
         (assign, ":kept", 0),
         (try_begin),
           (call_script, "script_cf_coop_mirror_kept", ":party_no"),
           (assign, ":kept", 1),
         (try_end),
         (eq, ":kept", 0),
         (party_get_slot, ":seen", ":party_no", slot_party_coop_seen),
         (lt, ":seen", ":old"),
         (party_get_slot, ":sid", ":party_no", slot_party_coop_sid),
         (val_sub, ":sid", 1),
         (try_begin),
           (store_add, ":mapped", ":party_no", 1),
           (party_slot_eq, "p_coop_map", ":sid", ":mapped"),
           (party_set_slot, "p_coop_map", ":sid", 0),
         (try_end),
         (remove_party, ":party_no"),
         (val_add, "$coop_net_swept", 1),
       (try_end),
     (try_end),
     # another player's party not updated for a while: that player left
     (try_for_range, ":puppet", "p_coop_puppet_1", puppets_end),
       (party_is_active, ":puppet"),
       (party_get_slot, ":last_seen", ":puppet", slot_party_coop_sid),
       (store_sub, ":silent", "$coop_net_seq", ":last_seen"),
       (gt, ":silent", coop_player_stale_requests),
       (disable_party, ":puppet"),
     (try_end),
     # a prisoner stays with the captor (Native does this in a world trigger the client has off)
     (try_begin),
       (eq, "$g_player_is_captive", 1),
       (gt, "$capturer_party", 0),
       (party_is_active, "$capturer_party"),
       (party_relocate_near_party, "p_main_party", "$capturer_party", 0),
     (try_end),
     (val_add, "$coop_net_frames", 1),
     (try_begin),
       (this_or_next|eq, "$coop_net_pending", 0),
       (ge, "$coop_net_frames", coop_net_resend_frames),
       (try_begin),
         (eq, "$coop_net_pending", 1), #the game never answered the last one either
         (call_script, "script_coop_client_no_answer"),
       (try_end),
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
         (assign, reg19, coop_build_id),
         (str_store_string, s13, "@{s13}&hello=1&ver={reg19}"),
         (assign, "$coop_own_troops_frames", coop_own_troops_frames), #the name goes with the hello: the bridge finds the player's hero by it
       (try_end),
       (str_clear, s14),
       (val_add, "$coop_own_troops_frames", 1),
       (try_begin),
         (ge, "$coop_own_troops_frames", coop_own_troops_frames),
         (assign, "$coop_own_troops_frames", 0),
         (call_script, "script_coop_troops_to_s12", "p_main_party", 1),
         (str_store_troop_name, s15, "trp_player"),
         (str_store_string, s14, "@&me={s12}&name={s15}"), #name last: it may hold spaces
       (try_end),
       (party_get_position, pos1, "p_main_party"),
       (position_get_x, reg2, pos1),
       (position_get_y, reg3, pos1),
       (assign, reg1, "$coop_net_seq"),
       (assign, reg4, "$coop_busy"),
       (val_max, reg4, "$coop_menu"), #the world pauses for a battle or a menu
       (store_current_hours, reg5),
       (assign, reg6, 0),
       (try_begin),
         (map_free),
         (assign, reg6, 1),
       (try_end),
       ] + client_request_suffix() + profile_tick() + [
       (call_script, "script_coop_player_kingdom"),
       (assign, reg8, reg0),
       (str_store_string, s10, "@" + coop_client_url + "/cli?seq={reg1}&h={reg5}&free={reg6}&x={reg2}&y={reg3}&busy={reg4}&fac={reg8}{s17}{s19}{s13}{s14}"),
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
