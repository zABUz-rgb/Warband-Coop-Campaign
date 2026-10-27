from header_common import *
from header_operations import *
from header_game_menus import *
from header_presentations import *
from header_triggers import *
from module_constants import *
from coop.constants import *

# Joint battles, the campaign side: a player starts one from an encounter; players nearby are
# invited, a player attacked by another player is called in. While the battle is fought on the
# multiplayer server this game shows a waiting window; the outcome comes back from the bridge.
#
# $coop_mp_state: 0 none   1 start to send   2 in a battle (waiting or fighting)   3 accept to send
#                 4 cancel or decline to send (from the map)   5 over, the window still open
# $coop_mp_status: what the bridge last said: 0 gathering, 1 fighting on the server,
#                  2 cancelled, 3 no battle server, 4 over
# Bridge replies (tools/coop_bridge.py): 6 invite bid|type|slot (type 1 may join, 2 attacked)
#   7 status bid|status|team   8 outcome bid|won|xp|n|(troop, killed, wounded)*n


def puppet_end():
  from coop.triggers import puppet_range
  return puppet_range()[1]


mp_campaign_scripts = [
  # script_coop_client_mp_invite: kind 6 reply
  ("coop_client_mp_invite",
   [
     (try_begin),
       (eq, "$coop_mp_state", 0),
       (party_get_slot, "$coop_mp_bid", "p_coop_buf", 2),
       (party_get_slot, "$coop_mp_inv_type", "p_coop_buf", 3),
       (party_get_slot, "$coop_mp_inv_slot", "p_coop_buf", 4),
       (assign, "$coop_mp_invite_pending", 1),
     (try_end),
    ]),

  # script_coop_client_mp_status: kind 7 reply
  ("coop_client_mp_status",
   [
     (party_get_slot, ":bid", "p_coop_buf", 2),
     (party_get_slot, ":status", "p_coop_buf", 3),
     (party_get_slot, ":team", "p_coop_buf", 4),
     (try_begin),
       (is_between, "$coop_mp_state", 1, 4),
       (this_or_next|eq, "$coop_mp_bid", 0),
       (eq, "$coop_mp_bid", ":bid"),
       (assign, "$coop_mp_bid", ":bid"),
       (assign, "$coop_mp_team", ":team"),
       (neq, ":status", "$coop_mp_status"),
       (assign, "$coop_mp_status", ":status"),
       (assign, "$coop_mp_dirty", 1),
       (try_begin),
         (ge, ":status", 2), #cancelled: nothing more comes
         (assign, "$coop_mp_state", 5),
       (try_end),
     (try_end),
    ]),

  # script_coop_client_mp_result: kind 8 reply, the player's losses
  ("coop_client_mp_result",
   [
     (party_get_slot, ":bid", "p_coop_buf", 2),
     (party_get_slot, ":won", "p_coop_buf", 3),
     (party_get_slot, ":xp", "p_coop_buf", 4),
     (party_get_slot, ":n", "p_coop_buf", 5),
     (assign, ":killed_all", 0),
     (assign, ":wounded_all", 0),
     (try_for_range, ":k", 0, ":n"),
       (store_mul, ":at", ":k", 3),
       (val_add, ":at", 6),
       (party_get_slot, ":troop", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":killed", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":wounded", "p_coop_buf", ":at"),
       (try_begin),
         (gt, ":killed", 0),
         (party_remove_members, "p_main_party", ":troop", ":killed"),
         (val_add, ":killed_all", reg0),
       (try_end),
       (try_begin),
         (gt, ":wounded", 0),
         (party_wound_members, "p_main_party", ":troop", ":wounded"),
         (val_add, ":wounded_all", ":wounded"),
       (try_end),
     (try_end),
     (try_begin),
       (gt, ":xp", 0),
       (add_xp_as_reward, ":xp"), #the hero and the troops learn from the battle, as after a Native one
     (try_end),
     (assign, reg1, ":killed_all"),
     (assign, reg2, ":wounded_all"),
     (try_begin),
       (eq, ":won", 1),
       (display_message, "@CoopWorld: the joint battle is WON. Your losses: {reg1} killed, {reg2} wounded.", 0x66FF66),
     (else_try),
       (display_message, "@CoopWorld: the joint battle is LOST. Your losses: {reg1} killed, {reg2} wounded.", 0xFF6666),
     (try_end),
     (try_begin),
       (eq, ":bid", "$coop_mp_bid"),
       (assign, "$coop_mp_status", 4),
       (assign, "$coop_mp_dirty", 1),
       (try_begin),
         (eq, "$coop_mp_open", 1),
         (assign, "$coop_mp_state", 5),
       (else_try),
         (assign, "$coop_mp_state", 0),
       (try_end),
     (try_end),
    ]),

  # script_coop_client_mp_text: s1 = what the waiting window says now
  ("coop_client_mp_text",
   [
     (store_add, reg1, "$coop_mp_team", 1),
     (try_begin),
       (eq, "$coop_mp_status", 1),
       (str_store_string, s1, "@The battle is on!^^Switch to the multiplayer window (the CoopWorld battle server) and fight: your side is team {reg1}. Your troops are on the field and obey your orders.^^This window waits for the outcome. The world stands still meanwhile."),
     (else_try),
       (eq, "$coop_mp_status", 2),
       (str_store_string, s1, "@The joint battle was cancelled (another one is being fought, or the player who began it left)."),
     (else_try),
       (eq, "$coop_mp_status", 3),
       (str_store_string, s1, "@No battle server is running. The host starts one: Multiplayer, Host a game, game type Battle, CoopWorld module."),
     (else_try),
       (eq, "$coop_mp_status", 4),
       (str_store_string, s1, "@The battle is over. The outcome is in the message log."),
     (else_try),
       (str_store_string, s1, "@Gathering the players for a joint battle...^^Players nearby are invited. The battle starts in a few seconds."),
     (try_end),
    ]),

  # script_coop_client_mp_send: one request from the waiting window
  ("coop_client_mp_send",
   [
     (assign, reg6, 2), #op: 1 start, 2 waiting, 3 accept
     (try_begin),
       (eq, "$coop_mp_state", 1),
       (assign, reg6, 1),
       (assign, "$coop_mp_state", 2),
     (else_try),
       (eq, "$coop_mp_state", 3),
       (assign, reg6, 3),
       (assign, "$coop_mp_state", 2),
     (try_end),
     (str_clear, s16),
     (try_begin),
       (eq, reg6, 1),
       (gt, "$coop_mp_enemy_party", 0),
       (party_is_active, "$coop_mp_enemy_party"),
       (call_script, "script_coop_troops_to_s12", "$coop_mp_enemy_party", 1),
       (str_store_string, s16, "@&mpt={s12}"),
     (try_end),
     (str_clear, s18),
     (try_begin),
       (neq, reg6, 2), #starting or accepting: the hero goes to the battle server
       (call_script, "script_coop_client_mp_hero_to_s18"),
     (try_end),
     (call_script, "script_coop_troops_to_s12", "p_main_party", 1),
     (str_store_troop_name, s15, "trp_player"),
     (val_add, "$coop_net_seq", 1),
     (assign, reg1, "$coop_net_seq"),
     (set_fixed_point_multiplier, 100),
     (party_get_position, pos1, "p_main_party"),
     (position_get_x, reg2, pos1),
     (position_get_y, reg3, pos1),
     (store_current_hours, reg5),
     (assign, reg7, "$coop_mp_bid"),
     (assign, reg8, "$coop_mp_target_sid"),
     (assign, reg9, "$coop_mp_target_slot"),
     (str_store_string, s10, "@" + coop_client_url + "/cli?seq={reg1}&h={reg5}&free=0&x={reg2}&y={reg3}&busy=1&mp={reg6}&bid={reg7}&mpe={reg8}&mpp={reg9}{s16}{s18}&me={s12}&name={s15}"),
     (assign, "$coop_net_pending", 1),
     (send_message_to_url, s10, 0),
    ]),

  # script_coop_client_mp_hero_to_s18: s18 = "&hero=..." the player's hero for the battle server:
  # equipment (ek_item_0 .. ek_horse), attributes, combat skills, weapon proficiencies
  ("coop_client_mp_hero_to_s18",
   [
     (str_store_string, s18, "@&hero="),
     (assign, ":first", 1),
     (try_for_range, ":ek", 0, coop_hero_items),
       (troop_get_inventory_slot, reg20, "trp_player", ":ek"),
       (call_script, "script_coop_append_s18", ":first"),
       (assign, ":first", 0),
     (try_end),
     (try_for_range, ":attribute", 0, 4),
       (store_attribute_level, reg20, "trp_player", ":attribute"),
       (call_script, "script_coop_append_s18", 0),
     (try_end),
     ] + [op for skill in coop_hero_skills for op in [
     (store_skill_level, reg20, skill, "trp_player"),
     (call_script, "script_coop_append_s18", 0),
     ]] + [
     (try_for_range, ":wpt", 0, coop_hero_profs),
       (store_proficiency_level, reg20, "trp_player", ":wpt"),
       (call_script, "script_coop_append_s18", 0),
     (try_end),
    ]),

  # script_coop_append_s18: reg20 onto s18, after a comma unless arg1 = 1
  ("coop_append_s18",
   [
     (store_script_param, ":first", 1),
     (try_begin),
       (eq, ":first", 1),
       (str_store_string, s18, "@{s18}{reg20}"),
     (else_try),
       (str_store_string, s18, "@{s18},{reg20}"),
     (try_end),
    ]),

  # script_coop_client_mp_begin: arg1 = the party met (a mirror of the server's world, or another
  # player's party): start a joint battle against it
  ("coop_client_mp_begin",
   [
     (store_script_param, ":party_no", 1),
     (assign, "$coop_mp_enemy_party", ":party_no"),
     (assign, "$coop_mp_target_sid", -1),
     (assign, "$coop_mp_target_slot", -1),
     (try_begin),
       (is_between, ":party_no", "p_coop_puppet_1", puppet_end()),
       (store_sub, "$coop_mp_target_slot", ":party_no", "p_coop_puppet_1"),
       (assign, "$coop_mp_enemy_party", -1), #a player brings his own troops
     (else_try),
       (eq, "$coop_role", coop_role_server), #the host meets the world's own party
       (assign, "$coop_mp_target_sid", ":party_no"),
     (else_try),
       (party_get_slot, ":sid", ":party_no", slot_party_coop_sid),
       (store_sub, "$coop_mp_target_sid", ":sid", 1),
     (try_end),
     (assign, "$coop_mp_bid", 0),
     (assign, "$coop_mp_status", 0),
     (assign, "$coop_mp_state", 1),
     (assign, "$coop_mp_hidden", 0),
     (jump_to_menu, "mnu_coop_mp_wait"),
    ]),
]


coop_mp_encounter_option = (
  "coop_mp_battle",
  [
    (this_or_next|eq, "$coop_role", coop_role_client),
    (eq, "$coop_srv_player", 1),
    (neg|troop_is_wounded, "trp_player"),
    (assign, ":ok", 0),
    (try_begin),
      (is_between, "$g_encountered_party", "p_coop_puppet_1", puppet_end()),
      (assign, ":ok", 1),
      (str_store_string, s1, "@CoopWorld: fight this player (joint battle on the multiplayer server)."),
    (else_try),
      (this_or_next|party_slot_ge, "$g_encountered_party", slot_party_coop_sid, 1), #a client's mirror
      (eq, "$coop_role", coop_role_server), #the host meets the world's own party
      (assign, ":ok", 1),
      (str_store_string, s1, "@CoopWorld: fight together with your friends (joint battle on the multiplayer server)."),
    (try_end),
    (eq, ":ok", 1),
  ],
  "{s1}",
  [
    (call_script, "script_coop_client_mp_begin", "$g_encountered_party"),
  ])


mp_campaign_menus = [
  ("coop_mp_wait", 0,
   "CoopWorld: joint battle.",
   "none",
   [
     (try_begin),
       (is_between, "$coop_mp_state", 1, 4),
       (eq, "$coop_mp_open", 0),
       (eq, "$coop_mp_hidden", 0), #closed by the player: the menu shows instead
       (start_presentation, "prsnt_coop_mp_wait"),
     (try_end),
   ],
   [
     ("coop_mp_show", [(is_between, "$coop_mp_state", 1, 4)], "Show the battle.",
      [(assign, "$coop_mp_hidden", 0), (start_presentation, "prsnt_coop_mp_wait")]),
     ("coop_mp_cancel", [(eq, "$coop_mp_state", 2), (eq, "$coop_mp_status", 0)], "Cancel the joint battle.",
      [(assign, "$coop_mp_state", 4), (leave_encounter), (change_screen_return)]),
     ("coop_mp_back", [(neg|is_between, "$coop_mp_state", 1, 4)], "Back to the map.",
      [(leave_encounter), (change_screen_return)]),
   ]),

  ("coop_mp_invite", 0,
   "{s2}",
   "none",
   [
     (str_store_string, s1, "@another player"),
     (try_begin),
       (is_between, "$coop_mp_inv_slot", 0, coop_max_players),
       (store_add, ":puppet", "p_coop_puppet_1", "$coop_mp_inv_slot"),
       (str_store_party_name, s1, ":puppet"),
     (try_end),
     (try_begin),
       (eq, "$coop_mp_inv_type", 2),
       (str_store_string, s2, "@{s1} attacks you!^^The battle is fought on the multiplayer server. Join it there; if you do not, your troops fight without you."),
     (else_try),
       (str_store_string, s2, "@{s1} begins a battle nearby and calls you to arms.^^The battle is fought on the multiplayer server: your troops fight on {s1}'s side."),
     (try_end),
   ],
   [
     ("coop_mp_join", [], "To battle!",
      [
        (assign, "$coop_mp_status", 0),
        (assign, "$coop_mp_state", 3),
        (assign, "$coop_mp_hidden", 0),
        (jump_to_menu, "mnu_coop_mp_wait"),
      ]),
     ("coop_mp_decline", [(eq, "$coop_mp_inv_type", 1)], "Decline.",
      [
        (assign, "$coop_mp_state", 4),
        (change_screen_return),
      ]),
   ]),
]


mp_campaign_presentations = [
  ("coop_mp_wait", prsntf_manual_end_only, 0,
   [
     (ti_on_presentation_load,
      [
        (set_fixed_point_multiplier, 1000),
        (assign, "$coop_mp_open", 1),
        (create_mesh_overlay, reg0, "mesh_load_window"),
        (position_set_x, pos1, 0),
        (position_set_y, pos1, 0),
        (overlay_set_position, reg0, pos1),
        (call_script, "script_coop_client_mp_text"),
        (create_text_overlay, "$coop_mp_text", s1, tf_center_justify|tf_double_space),
        (position_set_x, pos1, 500),
        (position_set_y, pos1, 420),
        (overlay_set_position, "$coop_mp_text", pos1),
        (position_set_x, pos1, 1200),
        (position_set_y, pos1, 1200),
        (overlay_set_size, "$coop_mp_text", pos1),
        (create_game_button_overlay, "$coop_mp_button", "@Close"),
        (position_set_x, pos1, 500),
        (position_set_y, pos1, 120),
        (overlay_set_position, "$coop_mp_button", pos1),
        (assign, "$coop_mp_dirty", 0),
        (assign, "$coop_mp_sent", -100000),
        (presentation_set_duration, 999999),
      ]),
     (ti_on_presentation_run,
      [
        (store_trigger_param_1, ":now"),
        (try_begin),
          (is_between, "$coop_mp_state", 1, 4),
          (store_sub, ":waited", ":now", "$coop_mp_sent"),
          (this_or_next|eq, "$coop_net_pending", 0),
          (ge, ":waited", coop_mp_resend_ms),
          (ge, ":waited", 250), #a few requests a second keep the world still and the news fresh
          (assign, "$coop_mp_sent", ":now"),
          (call_script, "script_coop_client_mp_send"),
        (try_end),
        (try_begin),
          (eq, "$coop_mp_dirty", 1),
          (assign, "$coop_mp_dirty", 0),
          (call_script, "script_coop_client_mp_text"),
          (overlay_set_text, "$coop_mp_text", s1),
        (try_end),
      ]),
     (ti_on_presentation_event_state_change,
      [
        (store_trigger_param_1, ":object"),
        (eq, ":object", "$coop_mp_button"),
        (try_begin),
          (eq, "$coop_mp_state", 5), #over
          (assign, "$coop_mp_state", 0),
        (try_end),
        # still running: the window closes, the battle goes on; "Show the battle" reopens it.
        # The menu is entered again so that its options fit the state.
        (assign, "$coop_mp_open", 0),
        (assign, "$coop_mp_hidden", 1),
        (presentation_set_duration, 0),
        (jump_to_menu, "mnu_coop_mp_wait"),
      ]),
   ]),
]


def client_map_tick():
  """Prepended to the client's map trigger: an invitation opens its menu; a decline or a
  cancel goes out with the next request (s17, appended to the request)."""
  return [
    (try_begin),
      (eq, "$coop_mp_invite_pending", 1),
      (map_free),
      (assign, "$coop_mp_invite_pending", 0),
      (jump_to_menu, "mnu_coop_mp_invite"),
    (try_end),
  ]


def client_request_suffix():
  """Ops building s17 for the client's map request."""
  return [
    (str_clear, s17),
    (try_begin),
      (eq, "$coop_mp_state", 4),
      (assign, "$coop_mp_state", 0),
      (assign, reg7, "$coop_mp_bid"),
      (str_store_string, s17, "@&mp=4&bid={reg7}"),
    (try_end),
  ]


def reply_branches():
  """else_try branches for net_reply_handler: kinds 6, 7, 8."""
  return [
    (else_try),
      (eq, ":kind", 6),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1), #the host's own player requests
      (call_script, "script_coop_client_mp_invite"),
    (else_try),
      (eq, ":kind", 7),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1), #the host's own player requests
      (call_script, "script_coop_client_mp_status"),
    (else_try),
      (eq, ":kind", 8),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1), #the host's own player requests
      (call_script, "script_coop_client_mp_result"),
  ]
