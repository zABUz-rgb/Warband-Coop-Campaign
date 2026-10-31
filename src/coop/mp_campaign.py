from header_common import *
from header_operations import *
from header_game_menus import *
from header_presentations import *
from header_triggers import *
from header_troops import *
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
#   9 the hero's blows bid|n|(weapon proficiency, hits, damage)*n
#   13 the host stormed a center bid|center (the host's game takes it as Native does)
#   10 aftermath bid|health|captor (health in percent or -1; captor: the world party that takes
#      the defeated player prisoner, or -1)   11 prisoners for the winner bid|n|(troop, count)*n
#   26 a joint event ended bid|event|won|value|bonus|town|n|(troop, count)*n
# Invite type 7 is a duel: the slot says who calls, the party number what is at stake.
#
# Joint events: an arena, a tournament, a training together, started from Native's own places in a
# town or at a training ground, and a duel between two players, fought by the players' heroes on the
# battle server. They change nothing in the world and hurt nobody; each player's game gives its prize
# as Native would.
# $coop_mp_event: 0 a battle of the campaign, else coop_event_arena, _tournament, _training, _duel
# $coop_mp_kind: what a battle of the map is about (coop_kind_lair, _caravan, _village), for its starter
# $coop_mp_return_menu: the menu the player started the event from (0: an invited player, back to the map)
# $coop_mp_bet, $coop_mp_bet_win: the stake on the team, and what it wins on top of it


def first_dynamic():
  from coop.triggers import first_dynamic_party
  return first_dynamic_party()


def puppet_end():
  from coop.triggers import puppet_range
  return puppet_range()[1]


mp_campaign_scripts = [
  # script_coop_client_mp_invite: kind 6 reply
  # An invitation to fight one's own allies (the world party is friendly, or the inviting player
  # serves an enemy kingdom) is declined at once; an attacked player is always called in.
  ("coop_client_mp_invite",
   [
     (try_begin),
       (eq, "$coop_mp_state", 0),
       (party_get_slot, "$coop_mp_bid", "p_coop_buf", 2),
       (party_get_slot, "$coop_mp_inv_type", "p_coop_buf", 3),
       (party_get_slot, "$coop_mp_inv_slot", "p_coop_buf", 4),
       (party_get_slot, ":sid", "p_coop_buf", 5),
       (call_script, "script_coop_client_mp_no_event"),
       (try_begin),
         (ge, "$coop_mp_inv_type", 4), #4 an arena, 5 a tournament, 6 a training, 7 a duel
         (store_sub, "$coop_mp_event", "$coop_mp_inv_type", 3),
       (try_end),
       (try_begin),
         (eq, "$coop_mp_event", coop_event_duel),
         (assign, "$coop_mp_bet", ":sid"), #the stake
       (try_end),
       (assign, ":refuse", 0),
       (try_begin),
         (eq, "$coop_mp_inv_type", 1),
         (try_begin),
           (ge, ":sid", 0),
           (try_begin),
             (this_or_next|eq, "$coop_role", coop_role_server), #the host: the world's own party
             (is_between, ":sid", walled_centers_begin, walled_centers_end), #a siege: the same center everywhere
             (assign, ":enemy", ":sid"),
           (else_try),
             (party_get_slot, ":enemy", "p_coop_map", ":sid"), #a client: its mirror, + 1
             (val_sub, ":enemy", 1),
           (try_end),
           (gt, ":enemy", 0),
           (party_is_active, ":enemy"),
           (store_faction_of_party, ":enemy_faction", ":enemy"),
           (this_or_next|eq, ":enemy_faction", "fac_player_supporters_faction"),
           (eq, ":enemy_faction", "$players_kingdom"), #only the player's own kingdom; neutrals may be fought
           (assign, ":refuse", 1),
           (str_store_party_name, s1, ":enemy"),
         (try_end),
         (try_begin),
           (eq, ":refuse", 0),
           (is_between, "$coop_mp_inv_slot", 0, coop_max_players),
           (store_add, ":puppet", "p_coop_puppet_1", "$coop_mp_inv_slot"),
           (party_is_active, ":puppet"),
           (store_faction_of_party, ":inviter_faction", ":puppet"),
           (is_between, ":inviter_faction", npc_kingdoms_begin, npc_kingdoms_end),
           (store_relation, ":relation", ":inviter_faction", "fac_player_supporters_faction"),
           (lt, ":relation", 0),
           (assign, ":refuse", 1),
           (str_store_party_name, s1, ":puppet"),
         (try_end),
       (try_end),
       (try_begin),
         (eq, "$g_player_is_captive", 1), #a prisoner fights in nobody's battle (Native's captivity must run its course)
         (assign, "$coop_mp_state", 4),
         (display_message, "@CoopWorld: a call to a joint battle - declined: you are a prisoner.", 0xFFDD66),
       (else_try),
         (eq, ":refuse", 1),
         (assign, "$coop_mp_state", 4), #the decline goes out with the next request
         (display_message, "@CoopWorld: a call to arms against your allies ({s1}) - declined.", 0xFFDD66),
       (else_try),
         (assign, "$coop_mp_invite_pending", 1),
         (call_script, "script_coop_signal_battle"),
       (try_end),
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
         (try_begin),
           (eq, ":status", 3),
           (display_message, "@CoopWorld: no battle server is running (Multiplayer - Host a game, game type Battle).", 0xFF6666),
         (else_try),
           (display_message, "@CoopWorld: not started - the bridge's window says why.", 0xFF6666),
         (try_end),
       (else_try),
         (eq, ":status", 1),
         (display_message, "@CoopWorld: fight now - switch to the multiplayer window, the battle is on.", 0x66FF66),
       (try_end),
     (try_end),
    ]),

  # script_coop_client_mp_result: kind 8 reply, the player's losses
  ("coop_client_mp_result",
   [
     (party_get_slot, ":bid", "p_coop_buf", 2),
     (party_get_slot, ":won", "p_coop_buf", 3),
     (assign, "$coop_mp_last_won", ":won"),
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
         (troop_is_hero, ":troop"), #a companion who fell: badly wounded, as after a Native battle
         (store_add, ":fell", ":killed", ":wounded"),
         (gt, ":fell", 0),
         (troop_set_health, ":troop", coop_hero_knocked_out_health),
         (str_store_troop_name, s1, ":troop"),
         (display_message, "@CoopWorld: {s1} fell in the joint battle and is badly wounded.", 0xFFDD66),
       (else_try),
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
     (try_end),
     (try_begin),
       (gt, ":xp", 0),
       (add_xp_as_reward, ":xp"), #the hero learns from the battle
     (try_end),
     # the troops too, as after a Native battle: by the enemies the winner's share holds (kind 21), a
     # loser by the experience above. add_xp_as_reward alone left them with nothing.
     (try_begin),
       (le, "$coop_mp_troops_xp", 0),
       (assign, "$coop_mp_troops_xp", ":xp"),
     (try_end),
     (try_begin),
       (gt, "$coop_mp_troops_xp", 0),
       (party_add_xp, "p_main_party", "$coop_mp_troops_xp"),
       (assign, reg1, "$coop_mp_troops_xp"),
       (display_message, "@CoopWorld: your troops gain {reg1} experience from the joint battle.", 0x66FF66),
     (try_end),
     (call_script, "script_coop_note", coop_note_troops_xp, "$coop_mp_troops_xp", ":won", 0),
     (assign, "$coop_mp_troops_xp", 0),
     (assign, reg1, ":killed_all"),
     (assign, reg2, ":wounded_all"),
     (try_begin),
       (eq, ":won", 1),
       (display_message, "@CoopWorld: the joint battle is WON. Your losses: {reg1} killed, {reg2} wounded.", 0x66FF66),
     (else_try),
       (display_message, "@CoopWorld: the joint battle is LOST. Your losses: {reg1} killed, {reg2} wounded.", 0xFF6666),
     (try_end),
     (call_script, "script_coop_after_battle", ":won"),
     (call_script, "script_coop_client_mp_over", ":bid"),
    ]),

  # script_coop_client_mp_over: arg1 = the battle whose outcome came: nothing more to wait for
  ("coop_client_mp_over",
   [
     (store_script_param, ":bid", 1),
     (try_begin),
       (eq, ":bid", "$coop_mp_bid"),
       (assign, "$coop_mp_status", 4),
       (assign, "$coop_mp_dirty", 1),
       (try_begin),
         (is_presentation_active, "prsnt_coop_mp_wait"),
         (assign, "$coop_mp_state", 5),
       (else_try),
         (assign, "$coop_mp_state", 0),
       (try_end),
     (try_end),
    ]),

  # script_coop_client_mp_event_result: kind 26 reply, a joint event ended for this player
  ("coop_client_mp_event_result",
   [
     (party_get_slot, ":bid", "p_coop_buf", 2),
     (party_get_slot, ":event", "p_coop_buf", 3),
     (party_get_slot, ":won", "p_coop_buf", 4),
     (party_get_slot, ":value", "p_coop_buf", 5),
     (party_get_slot, ":bonus", "p_coop_buf", 6),
     (party_get_slot, ":town", "p_coop_buf", 7),
     (assign, "$coop_mp_last_won", ":won"),
     (try_begin),
       (eq, ":event", coop_event_arena),
       (call_script, "script_coop_client_arena_prize", ":won", ":value"),
     (else_try),
       (eq, ":event", coop_event_tournament),
       (call_script, "script_coop_client_tournament_prize", ":won", ":value", ":bonus", ":town"),
     (else_try),
       (eq, ":event", coop_event_training),
       (call_script, "script_coop_client_training_result", ":value", ":bonus", ":town"),
     (else_try),
       (eq, ":event", coop_event_duel),
       (call_script, "script_coop_client_duel_result", ":won", ":value"),
     (try_end),
     (call_script, "script_coop_client_mp_over", ":bid"),
    ]),

  # script_coop_client_arena_prize: arg1 = this hero stood last, arg2 = the opponents it beat: the prize
  # the arena master gives in Native (a player beaten gets the prize of its kills)
  ("coop_client_arena_prize",
   [
     (store_script_param, ":won", 1),
     (store_script_param, ":kills", 2),
     (assign, ":prize", 0),
     (assign, ":xp", coop_arena_xp),
     (try_begin),
       (eq, ":won", 1),
       (assign, ":prize", arena_grand_prize),
       (assign, ":xp", coop_arena_grand_xp),
     (else_try),
       (ge, ":kills", arena_tier4_opponents_to_beat),
       (assign, ":prize", arena_tier4_prize),
     (else_try),
       (ge, ":kills", arena_tier3_opponents_to_beat),
       (assign, ":prize", arena_tier3_prize),
     (else_try),
       (ge, ":kills", arena_tier2_opponents_to_beat),
       (assign, ":prize", arena_tier2_prize),
     (else_try),
       (ge, ":kills", arena_tier1_opponents_to_beat),
       (assign, ":prize", arena_tier1_prize),
       (val_div, ":xp", 2),
     (try_end),
     (assign, reg1, ":kills"),
     (assign, reg2, ":prize"),
     (try_begin),
       (gt, ":prize", 0),
       (troop_add_gold, "trp_player", ":prize"),
       (add_xp_to_troop, ":xp", "trp_player"),
       (display_message, "@CoopWorld: the arena fight is over. You beat {reg1} opponents: {reg2} denars.", 0x66FF66),
     (else_try),
       (display_message, "@CoopWorld: the arena fight is over. You beat {reg1} opponents: not enough for a prize.", 0xFFDD66),
     (try_end),
     (call_script, "script_coop_note", coop_note_arena, ":kills", ":prize", ":won"),
    ]),

  # script_coop_client_tournament_prize: arg1 = the team won, arg2 = the rounds it won, arg3 = what the
  # bets win for every player, arg4 = the town. Every player of a winning team gets Native's prize and
  # the bets' winnings; the stake leaves only the game of the player who bet, and only here, so a
  # tournament cancelled on its way costs nothing.
  ("coop_client_tournament_prize",
   [
     (store_script_param, ":won", 1),
     (store_script_param, ":rounds", 2),
     (store_script_param, ":bonus", 3),
     (store_script_param, ":town", 4),
     (party_set_slot, ":town", slot_town_has_tournament, 0),
     (party_get_slot, ":odds", ":town", slot_town_player_odds),
     (try_begin),
       (eq, ":won", 1),
       (store_add, ":gold", coop_tournament_prize, ":bonus"),
       (troop_add_gold, "trp_player", ":gold"),
       (add_xp_to_troop, coop_tournament_xp, "trp_player"),
       (call_script, "script_change_troop_renown", "trp_player", coop_tournament_renown),
       (call_script, "script_change_player_relation_with_center", ":town", 1),
       (assign, reg1, coop_tournament_prize),
       (assign, reg2, ":bonus"),
       (str_store_party_name, s1, ":town"),
       (display_message, "@CoopWorld: your team won the tournament of {s1}! Prize {reg1} denars, and {reg2} from the bets.", 0x66FF66),
       (store_div, ":odds_sub", "$coop_mp_bet_win", 5),
       (val_sub, ":odds", ":odds_sub"),
       (val_max, ":odds", 250),
     (else_try),
       (assign, reg1, ":rounds"),
       (display_message, "@CoopWorld: your team is out of the tournament after {reg1} rounds won.", 0xFFDD66),
       (gt, "$coop_mp_bet", 0),
       (store_troop_gold, ":gold", "trp_player"),
       (val_min, ":gold", "$coop_mp_bet"),
       (troop_remove_gold, "trp_player", ":gold"),
       (assign, reg2, "$coop_mp_bet"),
       (display_message, "@CoopWorld: your bet of {reg2} denars is lost.", 0xFF6666),
       (store_div, ":odds_add", "$coop_mp_bet", 5),
       (val_add, ":odds", ":odds_add"),
       (val_min, ":odds", 4000),
     (try_end),
     (try_begin),
       (gt, "$coop_mp_bet", 0),
       (party_set_slot, ":town", slot_town_player_odds, ":odds"),
     (try_end),
     (try_begin),
       (eq, ":won", 1),
       (store_add, ":gold", coop_tournament_prize, ":bonus"),
       (call_script, "script_coop_note", coop_note_tournament, ":rounds", ":gold", 0),
     (else_try),
       (call_script, "script_coop_note", coop_note_tournament, ":rounds", 0, "$coop_mp_bet"),
     (try_end),
     (assign, "$coop_mp_bet", 0),
     (assign, "$coop_mp_bet_win", 0),
    ]),

  # script_coop_client_training_result: arg1 = the share of the opponents beaten in percent (100: the
  # players stood), arg2 = opponents for each player, arg3 = players; the reply holds n|(troop, count)*n
  # from slot 8, the opponents. As Native's training_ground_training_result: all who are fit learn,
  # those who fought learn more, and the harder the fight the more.
  ("coop_client_training_result",
   [
     (store_script_param, ":ratio", 1),
     (store_script_param, ":each", 2),
     (store_script_param, ":players", 3),
     (party_get_slot, ":foes", "p_coop_buf", 8),
     (assign, ":old_mode", "$g_mt_mode"),
     (assign, "$g_mt_mode", ctm_melee),
     (assign, "$g_training_ground_used_weapon_proficiency", wpt_one_handed_weapon),
     (assign, ":difficulty", 0),
     (try_for_range, ":k", 0, ":foes"),
       (store_mul, ":at", ":k", 2),
       (val_add, ":at", 9),
       (party_get_slot, ":troop", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":count", "p_coop_buf", ":at"),
       (store_character_level, ":level", ":troop"),
       (val_add, ":level", 10),
       (val_mul, ":level", ":level"),
       (val_mul, ":level", ":count"),
       (val_add, ":difficulty", ":level"),
     (try_end),
     (val_max, ":players", 1),
     (val_div, ":difficulty", ":players"), #what one player faced
     (store_add, ":multiplier", ":each", 4),
     (store_mul, "$g_training_ground_training_hardness", ":difficulty", ":multiplier"),
     (val_div, "$g_training_ground_training_hardness", 2400),
     (store_skill_level, ":trainer_skill", "skl_trainer", "trp_player"),
     (val_add, ":trainer_skill", 5),
     (call_script, "script_write_fit_party_members_to_stack_selection", "p_main_party", 1),
     (troop_get_slot, ":num_fit", "trp_stack_selection_amounts", 1),
     (troop_get_slot, ":num_slots", "trp_stack_selection_amounts", 0),
     (assign, ":earned", 0),
     (try_begin),
       (gt, ":ratio", 0),
       (store_mul, ":xp_ratio", ":ratio", ":ratio"),
       (try_begin),
         (eq, ":ratio", 100),
         (val_mul, ":xp_ratio", 2), #2x when perfect
       (try_end),
       (val_div, ":xp_ratio", 2),
       (val_div, ":xp_ratio", 10), # value over 1000
       (try_begin),
         (gt, ":num_fit", 8),
         (set_fixed_point_multiplier, 1000),
         (val_mul, ":xp_ratio", 3),
         (assign, ":divisor", ":num_fit"),
         (convert_to_fixed_point, ":divisor"),
         (store_sqrt, ":divisor", ":divisor"),
         (convert_to_fixed_point, ":xp_ratio"),
         (val_div, ":xp_ratio", ":divisor"),
       (try_end),
       (store_mul, ":xp_ratio_all", ":xp_ratio", ":trainer_skill"),
       (val_div, ":xp_ratio_all", 10),
       (party_get_num_companion_stacks, ":num_stacks", "p_main_party"),
       (store_add, ":end_slot", ":num_slots", 2),
       (try_for_range, ":i_slot", 2, ":end_slot"),
         (troop_get_slot, ":amount", "trp_stack_selection_amounts", ":i_slot"),
         (troop_get_slot, ":troop", "trp_stack_selection_ids", ":i_slot"),
         (assign, ":end_stack", ":num_stacks"),
         (try_for_range, ":stack_no", 0, ":end_stack"),
           (party_stack_get_troop_id, ":stack_troop", "p_main_party", ":stack_no"),
           (eq, ":stack_troop", ":troop"),
           (assign, ":end_stack", 0), #break
           (call_script, "script_cf_training_ground_sub_routine_for_training_result", ":troop", ":stack_no", ":amount", ":xp_ratio_all"),
           (val_add, ":earned", reg0),
         (try_end),
       (try_end),
       (store_mul, ":xp_ratio_fought", ":xp_ratio", 3),
       (val_div, ":xp_ratio_fought", 2),
       (try_for_range, ":k", 0, ":foes"),
         (store_mul, ":at", ":k", 2),
         (val_add, ":at", 9),
         (party_get_slot, ":troop", "p_coop_buf", ":at"),
         (val_add, ":at", 1),
         (party_get_slot, ":count", "p_coop_buf", ":at"),
         (assign, ":end_stack", ":num_stacks"),
         (try_for_range, ":stack_no", 0, ":end_stack"),
           (party_stack_get_troop_id, ":stack_troop", "p_main_party", ":stack_no"),
           (eq, ":stack_troop", ":troop"),
           (assign, ":end_stack", 0), #break
           (call_script, "script_cf_training_ground_sub_routine_for_training_result", ":troop", ":stack_no", ":count", ":xp_ratio_fought"),
           (val_add, ":earned", reg0),
         (try_end),
       (try_end),
       (try_begin),
         (call_script, "script_cf_training_ground_sub_routine_for_training_result", "trp_player", -1, 1, ":xp_ratio"),
         (assign, reg2, reg0),
         (display_message, "@CoopWorld: you earned {reg2} experience in the training.", 0x66FF66),
       (try_end),
     (try_end),
     (assign, "$g_mt_mode", ":old_mode"),
     (assign, reg1, ":ratio"),
     (assign, reg2, ":earned"),
     (display_message, "@CoopWorld: the training is over: {reg1}% of the opponents beaten, your troops earned {reg2} experience.", 0x66FF66),
     (call_script, "script_coop_note", coop_note_training, ":ratio", ":earned", 0),
    ]),

  # script_coop_client_mp_weapons: kind 9 reply, how the hero fought: (wpt, hits, damage)*n.
  # Each weapon proficiency grows as Native's does in battle: by the blows that hit, and less the
  # better the hero already is with it; troop_raise_proficiency keeps it within the weapon master limit.
  ("coop_client_mp_weapons",
   [
     (party_get_slot, ":n", "p_coop_buf", 3),
     (try_for_range, ":k", 0, ":n"),
       (store_mul, ":at", ":k", 3),
       (val_add, ":at", 4),
       (party_get_slot, ":wpt", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":hits", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":damage", "p_coop_buf", ":at"),
       (is_between, ":wpt", 0, coop_hero_profs),
       (store_proficiency_level, ":before", "trp_player", ":wpt"),
       (store_mul, ":points", ":hits", coop_wpt_hit_bonus),
       (val_add, ":points", ":damage"),
       (val_mul, ":points", coop_wpt_gain),
       (store_add, ":softness", ":before", coop_wpt_softness),
       (val_div, ":points", ":softness"),
       (gt, ":points", 0),
       (troop_raise_proficiency, "trp_player", ":wpt", ":points"),
       (store_proficiency_level, ":after", "trp_player", ":wpt"),
       (store_sub, reg1, ":after", ":before"),
       (assign, reg2, ":after"),
       (assign, reg3, ":hits"),
       (try_begin),
         (eq, ":wpt", wpt_one_handed_weapon),
         (str_store_string, s1, "@One handed weapons"),
       (else_try),
         (eq, ":wpt", wpt_two_handed_weapon),
         (str_store_string, s1, "@Two handed weapons"),
       (else_try),
         (eq, ":wpt", wpt_polearm),
         (str_store_string, s1, "@Polearms"),
       (else_try),
         (eq, ":wpt", wpt_archery),
         (str_store_string, s1, "@Archery"),
       (else_try),
         (eq, ":wpt", wpt_crossbow),
         (str_store_string, s1, "@Crossbows"),
       (else_try),
         (eq, ":wpt", wpt_throwing),
         (str_store_string, s1, "@Throwing"),
       (else_try),
         (str_store_string, s1, "@Firearms"),
       (try_end),
       (try_begin),
         (gt, reg1, 0),
         (display_message, "@{s1}: +{reg1} ({reg2}) for {reg3} hits in the joint battle.", 0x66FF66),
       (else_try),
         (display_message, "@{s1}: {reg2}, no gain ({reg3} hits; the weapon master skill limits it).", 0xCCCCCC),
       (try_end),
     (try_end),
    ]),

  # script_coop_client_mp_aftermath: kind 10 reply. The hero's wounds come back to the map; a
  # player who lost to a party of the world is taken prisoner by it, as after a Native defeat.
  ("coop_client_mp_aftermath",
   [
     (party_get_slot, ":health", "p_coop_buf", 3),
     (party_get_slot, ":captor", "p_coop_buf", 4),
     (try_begin),
       (ge, ":health", 0),
       (try_begin),
         (eq, ":health", 0),
         (assign, ":health", coop_hero_knocked_out_health),
         (display_message, "@CoopWorld: your hero fell in the joint battle and is badly wounded.", 0xFF6666),
       (else_try),
         (assign, reg1, ":health"),
         (display_message, "@CoopWorld: your hero comes out of the joint battle with {reg1}% health.", 0xFFDD66),
       (try_end),
       (troop_set_health, "trp_player", ":health"),
     (try_end),
     (try_begin),
       (ge, ":captor", 0),
       (try_begin),
         (eq, "$coop_role", coop_role_server), #the host: the world's own party
         (assign, ":party_no", ":captor"),
       (else_try),
         (party_get_slot, ":party_no", "p_coop_map", ":captor"), #a client: the mirror of that party, + 1
         (val_sub, ":party_no", 1),
       (try_end),
       (gt, ":party_no", 0),
       (party_is_active, ":party_no"),
       (assign, "$coop_mp_captor", ":party_no"), #the capture starts back on the map or from the menu
     (try_end),
    ]),

  # script_coop_client_mp_taken: kind 13 reply, the host stormed this center (the host's game is the
  # world: it takes it through Native's own victory, from the waiting menu)
  ("coop_client_mp_taken",
   [
     (party_get_slot, "$coop_mp_taken_center", "p_coop_buf", 3),
     (str_store_party_name, s1, "$coop_mp_taken_center"),
     (display_message, "@CoopWorld: the walls of {s1} are yours!", 0x66FF66),
    ]),

  # script_coop_client_mp_prisoners: kind 11 reply, the defeated player's troops become ours
  ("coop_client_mp_prisoners",
   [
     (party_get_slot, ":n", "p_coop_buf", 3),
     (assign, ":taken", 0),
     (try_for_range, ":k", 0, ":n"),
       (store_mul, ":at", ":k", 2),
       (val_add, ":at", 4),
       (party_get_slot, ":troop", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":count", "p_coop_buf", ":at"),
       (party_add_prisoners, "p_main_party", ":troop", ":count"),
       (val_add, ":taken", reg0),
     (try_end),
     (assign, reg1, ":taken"),
     (display_message, "@CoopWorld: you take {reg1} prisoners from the defeated side.", 0x66FF66),
    ]),

  # script_coop_client_mp_capture: the defeated player is taken prisoner, through Native's own defeat:
  # the captor takes the troops and the companions prisoner, loots some of the hero's items, and the
  # captivity begins
  ("coop_client_mp_capture",
   [
     (assign, ":captor", "$coop_mp_captor"),
     (assign, "$coop_mp_captor", 0),
     (try_begin),
       (party_is_active, ":captor"),
       (assign, "$g_encountered_party", ":captor"),
       (assign, "$g_enemy_party", ":captor"),
       (assign, "$g_ally_party", -1),
       (assign, "$g_player_surrenders", 0),
       (assign, "$g_next_menu", "mnu_captivity_start_wilderness"),
       (jump_to_menu, "mnu_total_defeat"),
     (else_try),
       (change_screen_return), #the captor is gone: back to the map
     (try_end),
    ]),

  # script_coop_client_mp_text: s1 = what the waiting window says now
  ("coop_client_mp_text",
   [
     (str_clear, s2),
     (try_begin),
       (eq, "$coop_mp_name_known", 1),
       (str_store_party_name, s3, "p_coop_buf"),
       (str_store_string, s2, "@^^Your name on the battle server must be {s3} (Multiplayer - Profiles); then your soldiers obey you."),
     (try_end),
     (store_add, reg1, "$coop_mp_team", 1),
     (try_begin),
       (eq, "$coop_mp_status", 1),
       (eq, "$coop_mp_event", coop_event_duel),
       (str_store_string, s1, "@The duel is on!^^Switch to the multiplayer window (the CoopWorld battle server): you stand against each other in your own gear, without troops. Nobody is hurt in earnest.^^This window waits for the outcome. The world stands still meanwhile.{s2}"),
     (else_try),
       (eq, "$coop_mp_status", 1),
       (gt, "$coop_mp_event", 0),
       (str_store_string, s1, "@The fight is on!^^Switch to the multiplayer window (the CoopWorld battle server): all players stand on one side, in practice gear.^^This window waits for the outcome. The world stands still meanwhile.{s2}"),
     (else_try),
       (eq, "$coop_mp_status", 1),
       (str_store_string, s1, "@The battle is on!^^Switch to the multiplayer window (the CoopWorld battle server) and fight: your side is team {reg1}. Your troops are on the field and obey your orders.^^This window waits for the outcome. The world stands still meanwhile.{s2}"),
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
       (eq, "$coop_mp_event", coop_event_duel),
       (str_store_string, s1, "@Waiting for the other player's answer...^^The duel starts as soon as you both stand on the battle server: switch to the multiplayer window now.{s2}"),
     (else_try),
       (gt, "$coop_mp_event", 0),
       (str_store_string, s1, "@Gathering the players...^^Players nearby are invited. The fight starts as soon as every player who agreed stands on the battle server: switch to the multiplayer window now.{s2}"),
     (else_try),
       (str_store_string, s1, "@Gathering the players for a joint battle...^^Players nearby are invited. The battle starts in a few seconds.{s2}"),
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
     # beside the lord the player serves: his party fights on the players' side, with its troops as
     # this game sees them (the bridge prefers the world server's view)
     (try_begin),
       (eq, reg6, 1),
       (ge, "$coop_mp_ally_sid", 0),
       (assign, reg14, "$coop_mp_ally_sid"),
       (str_store_string, s16, "@{s16}&mpa={reg14}"),
       (try_begin),
         (eq, "$coop_role", coop_role_server), #the host: the world's own party
         (assign, ":ally", "$coop_mp_ally_sid"),
       (else_try),
         (party_get_slot, ":ally", "p_coop_map", "$coop_mp_ally_sid"),
         (val_sub, ":ally", 1),
       (try_end),
       (gt, ":ally", 0),
       (party_is_active, ":ally"),
       (call_script, "script_coop_troops_to_s12", ":ally", 1),
       (str_store_string, s16, "@{s16}&mpat={s12}"),
     (try_end),
     # what the battle is about; a village's militia is no party of the world, its men are named here
     (try_begin),
       (eq, reg6, 1),
       (gt, "$coop_mp_kind", 0),
       (assign, reg14, "$coop_mp_kind"),
       (str_store_string, s16, "@{s16}&mpk={reg14}"),
       (eq, "$coop_mp_kind", coop_kind_village),
       (assign, reg14, "$coop_mp_village"),
       (assign, reg15, "trp_farmer"),
       (assign, reg16, coop_village_militia),
       (str_store_string, s16, "@{s16}&mpa={reg14}&mpat=,{reg15},{reg16}"),
     (try_end),
     # a village's bandits and its men, as its menu counted them
     (try_begin),
       (eq, reg6, 1),
       (eq, "$coop_mp_kind", coop_kind_bandits),
       (party_get_slot, reg14, "$coop_mp_village", slot_village_infested_by_bandits),
       (assign, reg15, "$qst_eliminate_bandits_infesting_village_num_bandits"),
       (val_max, reg15, 1),
       (assign, reg16, "$coop_mp_village"),
       (assign, reg17, "trp_farmer"),
       (assign, reg18, "$qst_eliminate_bandits_infesting_village_num_villagers"),
       (val_max, reg18, 1),
       (str_store_string, s16, "@{s16}&mpt=,{reg14},{reg15}&mpa={reg16}&mpat=,{reg17},{reg18}"),
     (try_end),
     # a joint event: which, its choice (a training's opponents for each player), the town, the first
     # arena fighter (the bridge knows no troop numbers), what the bet wins
     (try_begin),
       (eq, reg6, 1),
       (gt, "$coop_mp_event", 0),
       (assign, reg14, "$coop_mp_event"),
       (assign, reg15, "$coop_mp_event_param"),
       (assign, reg16, "$current_town"),
       (assign, reg17, "trp_arena_training_fighter_1"),
       (assign, reg18, "$coop_mp_bet_win"),
       (str_store_string, s16, "@{s16}&mpx={reg14},{reg15},{reg16},{reg17},{reg18}"),
     (try_end),
     (str_clear, s18),
     (str_clear, s20),
     (try_begin),
       (neq, reg6, 2), #starting or accepting: the hero goes to the battle server, the companions follow
       (call_script, "script_coop_client_mp_hero_to_s18"),
       (assign, "$coop_comp_next", 0),
       (call_script, "script_coop_client_mp_companions"),
       (assign, reg12, reg0),
       (party_get_current_terrain, reg13, "p_main_party"),
       (str_store_string, s18, "@{s18}&compn={reg12}&ter={reg13}"),
     (else_try),
       (str_clear, s20),
       (call_script, "script_coop_client_mp_companion_to_s20"),
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
     (assign, reg10, "$coop_mp_target_center"),
     (assign, reg11, "$coop_mp_defend"),
     (str_clear, s17),
     (call_script, "script_coop_note_to_s17"), #what happened in the battle reaches the log at once
     (str_store_string, s10, "@" + coop_client_url + "/cli?seq={reg1}&h={reg5}&free=0&x={reg2}&y={reg3}&busy=1&mp={reg6}&bid={reg7}&mpe={reg8}&mpp={reg9}&mpc={reg10}&mpd={reg11}{s16}{s18}{s20}{s17}&me={s12}&name={s15}"),
     (assign, "$coop_net_pending", 1),
     (send_message_to_url, s10, 0),
     (val_add, "$coop_mp_dbg_sent", 1),
    ]),

  # script_coop_client_mp_hero_to_s18: s18 = "&hero=..." the player's hero for the battle server:
  # equipment (ek_item_0 .. ek_horse), attributes, combat skills, weapon proficiencies
  ("coop_client_mp_hero_to_s18",
   [
     (str_store_string, s18, "@&hero="),
     (call_script, "script_coop_troop_numbers_to_s18", "trp_player"),
    ]),

  # script_coop_troop_numbers_to_s18: arg1 = a hero (the player or a companion): its equipment,
  # attributes, combat skills, proficiencies and hit points (now, at most) appended to s18, comma separated
  ("coop_troop_numbers_to_s18",
   [
     (store_script_param, ":troop", 1),
     (assign, ":first", 1),
     (try_for_range, ":ek", 0, coop_hero_items),
       (troop_get_inventory_slot, reg20, ":troop", ":ek"),
       (call_script, "script_coop_append_s18", ":first"),
       (assign, ":first", 0),
     (try_end),
     (try_for_range, ":attribute", 0, 4),
       (store_attribute_level, reg20, ":troop", ":attribute"),
       (call_script, "script_coop_append_s18", 0),
     (try_end),
     ] + [op for skill in coop_hero_skills for op in [
     (store_skill_level, reg20, skill, ":troop"),
     (call_script, "script_coop_append_s18", 0),
     ]] + [
     (try_for_range, ":wpt", 0, coop_hero_profs),
       (store_proficiency_level, reg20, ":troop", ":wpt"),
       (call_script, "script_coop_append_s18", 0),
     (try_end),
     # hit points now and at most (full health for a moment, then the same hit points again)
     (store_troop_health, ":hp", ":troop", 1),
     (troop_set_health, ":troop", 100),
     (store_troop_health, ":max", ":troop", 1),
     (troop_set_health, ":troop", ":hp", 1),
     (assign, reg20, ":hp"),
     (call_script, "script_coop_append_s18", 0),
     (assign, reg20, ":max"),
     (call_script, "script_coop_append_s18", 0),
    ]),

  # script_coop_client_mp_companion_to_s20: s20 = "&comp=troop,numbers" of the next companion fit
  # to fight that has not gone to the bridge yet ($coop_comp_next counts them), or empty
  ("coop_client_mp_companion_to_s20",
   [
     (str_clear, s20),
     (assign, ":k", 0),
     (assign, ":found", -1),
     (party_get_num_companion_stacks, ":stacks", "p_main_party"),
     (try_for_range, ":stack", 0, ":stacks"),
       (eq, ":found", -1),
       (party_stack_get_troop_id, ":troop", "p_main_party", ":stack"),
       (troop_is_hero, ":troop"),
       (neq, ":troop", "trp_player"),
       (neg|troop_is_wounded, ":troop"),
       (try_begin),
         (eq, ":k", "$coop_comp_next"),
         (assign, ":found", ":troop"),
       (try_end),
       (val_add, ":k", 1),
     (try_end),
     (try_begin),
       (ge, ":found", 0),
       (val_add, "$coop_comp_next", 1),
       (assign, reg20, ":found"),
       (str_store_string, s18, "@&comp={reg20},"),
       (call_script, "script_coop_troop_numbers_to_s18", ":found"),
       (str_store_string, s20, s18),
     (try_end),
    ]),

  # script_coop_client_mp_companions: reg0 = companions fit to fight
  ("coop_client_mp_companions",
   [
     (assign, reg0, 0),
     (party_get_num_companion_stacks, ":stacks", "p_main_party"),
     (try_for_range, ":stack", 0, ":stacks"),
       (party_stack_get_troop_id, ":troop", "p_main_party", ":stack"),
       (troop_is_hero, ":troop"),
       (neq, ":troop", "trp_player"),
       (neg|troop_is_wounded, ":troop"),
       (val_add, reg0, 1),
     (try_end),
    ]),

  # script_coop_client_mp_loot_take: the player's share of the spoils (kind 21, kept on
  # trp_tutorial_student_1: n, (troop, count)*n) looted as Native loots after a battle, then shown
  ("coop_client_mp_loot_take",
   [
     (assign, "$coop_loot_ready", 0),
     (troop_clear_inventory, "trp_temp_troop"),
     (party_get_skill_level, ":looting", "p_main_party", "skl_looting"),
     (store_add, ":probability", ":looting", 10),
     (val_mul, ":probability", 3),
     (troop_get_slot, ":n", "trp_tutorial_student_1", 0),
     (try_for_range, ":k", 0, ":n"),
       (store_mul, ":at", ":k", 2),
       (val_add, ":at", 1),
       (troop_get_slot, ":troop", "trp_tutorial_student_1", ":at"),
       (val_add, ":at", 1),
       (troop_get_slot, ":count", "trp_tutorial_student_1", ":at"),
       (neg|troop_is_hero, ":troop"), #a lord's or a hero's own gear is not spoils
       (val_clamp, ":count", 0, 201),
       (try_for_range, ":unused", 0, ":count"),
         (troop_loot_troop, "trp_temp_troop", ":troop", ":probability"),
       (try_end),
     (try_end),
     (change_screen_loot, "trp_temp_troop"),
    ]),

  # script_coop_client_mp_loot: kind 21 reply, the player's share of the fallen enemies: bid|n|(troop, count)*n
  ("coop_client_mp_loot",
   [
     (party_get_slot, ":n", "p_coop_buf", 3),
     (troop_set_slot, "trp_tutorial_student_1", 0, ":n"),
     (store_mul, ":numbers", ":n", 2),
     (try_for_range, ":k", 0, ":numbers"),
       (store_add, ":src", ":k", 4),
       (store_add, ":dst", ":k", 1),
       (party_get_slot, ":v", "p_coop_buf", ":src"),
       (troop_set_slot, "trp_tutorial_student_1", ":dst", ":v"),
     (try_end),
     (try_begin),
       (gt, ":n", 0),
       (assign, "$coop_loot_ready", 1),
       (display_message, "@CoopWorld: the spoils of the joint battle are waiting for you (the joint battle menu, or Camp - CoopWorld: co-op...).", 0x66FF66),
     (try_end),
     (call_script, "script_coop_client_mp_fallen_prisoners"),
     (call_script, "script_coop_client_mp_fallen_xp"),
    ]),

  # script_coop_client_mp_fallen_prisoners: the same kind 21 reply: every fallen enemy of this player's
  # share, killed or wounded, may be taken prisoner, by the hero's Prisoner Management
  # (coop_prisoner_chance_first at skill 1, coop_prisoner_chance_step more for each further point; at
  # skill 0 none), as far as the party has room for prisoners.
  ("coop_client_mp_fallen_prisoners",
   [
     (store_skill_level, ":skill", "skl_prisoner_management", "trp_player"),
     (party_get_slot, ":n", "p_coop_buf", 3),
     (try_begin),
       (gt, ":skill", 0),
       (store_sub, ":chance", ":skill", 1),
       (val_mul, ":chance", coop_prisoner_chance_step),
       (val_add, ":chance", coop_prisoner_chance_first),
       (assign, ":taken", 0),
       (assign, ":no_room", 0),
       (try_for_range, ":k", 0, ":n"),
         (store_mul, ":at", ":k", 2),
         (val_add, ":at", 4),
         (party_get_slot, ":troop", "p_coop_buf", ":at"),
         (val_add, ":at", 1),
         (party_get_slot, ":count", "p_coop_buf", ":at"),
         (neg|troop_is_hero, ":troop"),
         (assign, ":caught", 0),
         (try_for_range, ":unused", 0, ":count"),
           (store_random_in_range, ":roll", 0, 100),
           (lt, ":roll", ":chance"),
           (val_add, ":caught", 1),
         (try_end),
         (party_get_free_prisoners_capacity, ":room", "p_main_party"),
         (try_begin),
           (gt, ":caught", ":room"),
           (store_sub, ":left", ":caught", ":room"),
           (val_add, ":no_room", ":left"),
           (assign, ":caught", ":room"),
         (try_end),
         (gt, ":caught", 0),
         (party_add_prisoners, "p_main_party", ":troop", ":caught"),
         (val_add, ":taken", reg0),
       (try_end),
       (assign, reg1, ":skill"),
       (assign, reg2, ":chance"),
       (assign, reg3, ":taken"),
       (display_message, "@CoopWorld: Prisoner Management {reg1} ({reg2}% of the fallen): you take {reg3} prisoners.", 0x66FF66),
       (call_script, "script_coop_note", coop_note_prisoners, ":taken", ":chance", ":no_room"),
       (gt, ":no_room", 0),
       (assign, reg1, ":no_room"),
       (display_message, "@CoopWorld: no room for {reg1} more prisoners.", 0xFFDD66),
     (try_end),
     (try_begin),
       (le, ":skill", 0),
       (call_script, "script_coop_note", coop_note_prisoners, 0, 0, 0),
     (try_end),
    ]),

  # script_coop_client_mp_fallen_xp: the same kind 21 reply: what the troops learn from the fallen
  # enemies of this player's share, as in Native's script_party_give_xp_and_gold; given with the
  # outcome (kind 8)
  ("coop_client_mp_fallen_xp",
   [
     (party_get_slot, ":n", "p_coop_buf", 3),
     (assign, ":xp", 0),
     (try_for_range, ":k", 0, ":n"),
       (store_mul, ":at", ":k", 2),
       (val_add, ":at", 4),
       (party_get_slot, ":troop", "p_coop_buf", ":at"),
       (val_add, ":at", 1),
       (party_get_slot, ":count", "p_coop_buf", ":at"),
       (neg|troop_is_hero, ":troop"),
       (store_character_level, ":gain", ":troop"),
       (val_add, ":gain", 10),
       (val_mul, ":gain", ":gain"),
       (val_div, ":gain", 10),
       (val_mul, ":gain", ":count"),
       (val_add, ":xp", ":gain"),
     (try_end),
     (val_min, ":xp", 40000),
     (store_random_in_range, ":r", 50, 100),
     (val_mul, ":xp", ":r"),
     (val_div, ":xp", 100),
     (assign, "$coop_mp_troops_xp", ":xp"),
    ]),

  # script_coop_client_mp_leave_battle: the joint battle is over and the player goes back to the map
  ("coop_client_mp_leave_battle",
   [
     (try_begin),
       (gt, "$coop_mp_target_center", 0), #a siege that ended: the walls are someone else's now
       (eq, "$coop_mp_defend", 0), #(a defence leaves the world's siege to the world)
       (call_script, "script_lift_siege", "$coop_mp_target_center", 0),
       (assign, "$g_player_besiege_town", -1),
       (assign, "$coop_mp_target_center", -1),
     (try_end),
     (assign, "$coop_busy", 2), #back on the map: the first map frame ends the battle's hold on the world
     (assign, "$coop_profile_frames", coop_profile_period_frames), #what the battle changed goes to the host
     (call_script, "script_coop_client_mp_no_event"),
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

  # script_coop_client_mp_begin_defence: arg1 = a besieged center on the player's side: defend it
  # against its besiegers (their party and the army camped with it)
  ("coop_client_mp_begin_defence",
   [
     (store_script_param, ":center", 1),
     (call_script, "script_coop_client_mp_no_event"),
     (assign, "$coop_mp_target_center", ":center"),
     (assign, "$coop_mp_target_slot", -1),
     (assign, "$coop_mp_defend", 1),
     (assign, "$coop_mp_enemy_party", -1),
     (assign, "$coop_mp_ally_sid", -1),
     (try_begin),
       (eq, "$coop_srv_player", 1),
       (party_get_slot, "$coop_mp_target_sid", ":center", slot_center_is_besieged_by),
       (assign, "$coop_mp_enemy_party", "$coop_mp_target_sid"),
     (else_try),
       (party_get_slot, "$coop_mp_target_sid", ":center", slot_center_coop_besieger),
       (val_sub, "$coop_mp_target_sid", 1),
       (party_get_slot, ":mirror", "p_coop_map", "$coop_mp_target_sid"), #its mirror's troops, if the server has none
       (val_sub, ":mirror", 1),
       (gt, ":mirror", 0),
       (assign, "$coop_mp_enemy_party", ":mirror"),
     (try_end),
     (assign, "$coop_mp_bid", 0),
     (assign, "$coop_mp_status", 0),
     (assign, "$coop_mp_state", 1),
     (assign, "$coop_mp_hidden", 0),
     (assign, "$coop_mp_dbg_sent", 0),
     (assign, "$coop_mp_dbg_answers", 0),
     (assign, "$coop_mp_dbg_shown", -100000),
     # the start goes to the bridge right now: switching to the multiplayer window at once may stop
     # this game (a background window), and the battle must not wait for it
     (call_script, "script_coop_client_mp_send"),
     (display_message, "@CoopWorld: request for a joint battle sent to the bridge.", 0x66CCFF),
     (jump_to_menu, "mnu_coop_mp_wait"),
    ]),

  # script_coop_client_mp_begin: arg1 = the party met (a mirror of the server's world, or another
  # player's party): start a joint battle against it
  ("coop_client_mp_begin",
   [
     (store_script_param, ":party_no", 1),
     (call_script, "script_coop_client_mp_no_event"),
     (assign, "$coop_mp_kind", "$coop_mp_next_kind"),
     (assign, "$coop_mp_next_kind", 0),
     (assign, "$coop_mp_enemy_party", ":party_no"),
     (store_sub, "$coop_mp_ally_sid", "$coop_mp_next_ally", 1), #who is defended: its id on the server, -1 nobody
     (assign, "$coop_mp_next_ally", 0),
     (assign, "$coop_mp_target_sid", -1),
     (assign, "$coop_mp_target_slot", -1),
     (assign, "$coop_mp_target_center", -1),
     (assign, "$coop_mp_defend", 0),
     (try_begin),
       (is_between, ":party_no", walled_centers_begin, walled_centers_end), #a siege: storm its walls
       (assign, "$coop_mp_target_center", ":party_no"),
     (else_try),
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
     (assign, "$coop_mp_dbg_sent", 0),
     (assign, "$coop_mp_dbg_answers", 0),
     (assign, "$coop_mp_dbg_shown", -100000),
     # the start goes to the bridge right now: switching to the multiplayer window at once may stop
     # this game (a background window), and the battle must not wait for it
     (call_script, "script_coop_client_mp_send"),
     (display_message, "@CoopWorld: request for a joint battle sent to the bridge.", 0x66CCFF),
     (jump_to_menu, "mnu_coop_mp_wait"),
    ]),

  # script_coop_client_mp_no_event: a battle of the campaign starts, or the event is done: no leftovers
  ("coop_client_mp_no_event",
   [
     (assign, "$coop_mp_event", 0),
     (assign, "$coop_mp_kind", 0),
     (assign, "$coop_mp_return_menu", 0),
     (assign, "$coop_mp_bet", 0),
     (assign, "$coop_mp_bet_win", 0),
    ]),

  # script_coop_client_mp_begin_event: arg1 = coop_event_..., arg2 = its choice (a training's opponents
  # for each player), arg3 = the menu to come back to, arg4 = the stake on the team. Another player
  # who starts the same event while it gathers joins it (the team's bets add up).
  ("coop_client_mp_begin_event",
   [
     (store_script_param, "$coop_mp_event", 1),
     (store_script_param, "$coop_mp_event_param", 2),
     (store_script_param, "$coop_mp_return_menu", 3),
     (store_script_param, "$coop_mp_bet", 4),
     (assign, "$coop_mp_kind", 0),
     (assign, "$coop_mp_bet_win", 0),
     (try_begin),
       (eq, "$coop_mp_event", coop_event_duel),
       (assign, "$coop_mp_bet_win", "$coop_mp_bet"), #the stake: it only changes hands
     (else_try),
       (gt, "$coop_mp_bet", 0),
       (assign, "$g_tournament_cur_tier", 0), #the whole tournament: the best odds, as a first round's bet
       (call_script, "script_get_win_amount_for_tournament_bet"),
       (store_mul, "$coop_mp_bet_win", reg0, "$coop_mp_bet"),
       (val_div, "$coop_mp_bet_win", 100),
       (val_sub, "$coop_mp_bet_win", "$coop_mp_bet"),
     (try_end),
     (assign, "$coop_mp_enemy_party", -1),
     (assign, "$coop_mp_ally_sid", -1),
     (assign, "$coop_mp_target_sid", -1),
     (assign, "$coop_mp_target_slot", -1),
     (assign, "$coop_mp_target_center", -1),
     (assign, "$coop_mp_defend", 0),
     (assign, "$coop_mp_bid", 0),
     (assign, "$coop_mp_status", 0),
     (assign, "$coop_mp_state", 1),
     (assign, "$coop_mp_hidden", 0),
     (assign, "$coop_mp_dbg_sent", 0),
     (assign, "$coop_mp_dbg_answers", 0),
     (assign, "$coop_mp_dbg_shown", -100000),
     (call_script, "script_coop_client_mp_send"),
     (display_message, "@CoopWorld: request for a joint fight sent to the bridge.", 0x66CCFF),
     (jump_to_menu, "mnu_coop_mp_wait"),
    ]),

  # script_cf_coop_lord_enemy: the lord this player serves (Freelancer) is in a field battle.
  # reg0 = the enemy party in this game (-1: none here), reg1 = its id on the world server,
  # reg2 = the lord's party on the world server
  ("cf_coop_lord_enemy",
   [
     (assign, reg0, -1),
     (assign, reg1, -1),
     (assign, reg2, -1),
     (try_begin),
       (eq, "$coop_role", coop_role_client), #the bridge tells (kind 25): a mirror fights nobody here
       (ge, "$coop_lord_enemy_sid", 0),
       (ge, "$coop_lord_sid", 0),
       (assign, reg1, "$coop_lord_enemy_sid"),
       (assign, reg2, "$coop_lord_sid"),
       (party_get_slot, reg0, "p_coop_map", reg1),
       (val_sub, reg0, 1),
     (else_try),
       (eq, "$coop_srv_player", 1), #the host: the world's own battle
       (gt, "$enlisted_party", 0),
       (party_is_active, "$enlisted_party"),
       (party_get_battle_opponent, ":enemy", "$enlisted_party"),
       (ge, ":enemy", first_dynamic()), #a field battle (not a siege's walls, not a player)
       (party_is_active, ":enemy"),
       (assign, reg0, ":enemy"),
       (assign, reg1, ":enemy"),
       (assign, reg2, "$enlisted_party"),
     (try_end),
     (ge, reg1, 0),
    ]),

  # script_coop_client_mp_begin_lord: a joint battle beside the lord this player serves, against
  # the party he fights; his men fight on the players' side
  ("coop_client_mp_begin_lord",
   [
     (call_script, "script_coop_client_mp_no_event"),
     (try_begin),
       (call_script, "script_cf_coop_lord_enemy"),
       (assign, "$coop_mp_enemy_party", -1),
       (try_begin),
         (gt, reg0, 0),
         (party_is_active, reg0),
         (assign, "$coop_mp_enemy_party", reg0), #its troops as this game sees them
       (try_end),
       (assign, "$coop_mp_target_sid", reg1),
       (assign, "$coop_mp_ally_sid", reg2),
       (assign, "$coop_mp_target_slot", -1),
       (assign, "$coop_mp_target_center", -1),
       (assign, "$coop_mp_defend", 0),
       (assign, "$coop_mp_bid", 0),
       (assign, "$coop_mp_status", 0),
       (assign, "$coop_mp_state", 1),
       (assign, "$coop_mp_hidden", 0),
       (assign, "$coop_mp_dbg_sent", 0),
       (assign, "$coop_mp_dbg_answers", 0),
       (assign, "$coop_mp_dbg_shown", -100000),
       (call_script, "script_coop_client_mp_send"),
       (display_message, "@CoopWorld: request for a joint battle beside your commander sent to the bridge.", 0x66CCFF),
       (jump_to_menu, "mnu_coop_mp_wait"),
     (else_try),
       (display_message, "@CoopWorld: your commander is no longer in battle.", 0xFFDD66),
     (try_end),
    ]),
]


# Freelancer's soldier menu: the lord the player serves is in a field battle - fight it together, the
# players and the lord's men against his enemy (the host's game sees the lord's battle itself, a
# client's hears of it from the bridge)
coop_mp_lord_option = (
  "coop_mp_lord_battle",
  [
    (this_or_next|eq, "$coop_role", coop_role_client),
    (eq, "$coop_srv_player", 1),
    (eq, "$coop_mp_state", 0),
    (neg|troop_is_wounded, "trp_player"),
    (neq, "$g_player_is_captive", 1),
    (call_script, "script_cf_coop_lord_enemy"),
  ],
  "CoopWorld: fight beside your commander together with your friends (joint battle on the multiplayer server).",
  [
    (call_script, "script_coop_client_mp_begin_lord"),
  ])


# a besieged center on the player's side: defend its walls together (inside, or arriving outside)
coop_mp_defend_option = (
  "coop_mp_defend",
  [
    (this_or_next|eq, "$coop_role", coop_role_client),
    (eq, "$coop_srv_player", 1),
    (neg|troop_is_wounded, "trp_player"),
    (neq, "$g_player_is_captive", 1),
    (store_encountered_party, ":center"),
    (is_between, ":center", walled_centers_begin, walled_centers_end),
    (store_faction_of_party, ":faction", ":center"),
    (store_relation, ":relation", ":faction", "fac_player_supporters_faction"),
    (ge, ":relation", 0),
    (try_begin),
      (eq, "$coop_srv_player", 1), #the host: the world's own siege
      (party_get_slot, ":besieger", ":center", slot_center_is_besieged_by),
    (else_try),
      (party_get_slot, ":besieger", ":center", slot_center_coop_besieger), #a client: as the server reports it, + 1
      (val_sub, ":besieger", 1),
    (try_end),
    (gt, ":besieger", 0),
  ],
  "CoopWorld: defend the walls together (joint siege on the multiplayer server).",
  [
    (store_encountered_party, ":center"),
    (call_script, "script_coop_client_mp_begin_defence", ":center"),
  ])


# the siege menu: storm the walls together, on the battle server's Siege. Native's own conditions
# for leading the assault (ladders or a tower ready, men fit to fight); a client needs a kingdom to
# give the center to (only the host holds fiefs)
coop_mp_siege_option = (
  "coop_mp_siege",
  [
    (this_or_next|eq, "$coop_role", coop_role_client),
    (eq, "$coop_srv_player", 1),
    (neg|troop_is_wounded, "trp_player"),
    (neq, "$g_player_is_captive", 1),
    (ge, "$g_siege_method", 1),
    (gt, "$g_friend_fit_for_battle", 3),
    (store_current_hours, ":cur_hours"),
    (ge, ":cur_hours", "$g_siege_method_finish_hours"),
    (this_or_next|eq, "$coop_srv_player", 1),
    (is_between, "$players_kingdom", npc_kingdoms_begin, npc_kingdoms_end),
  ],
  "CoopWorld: storm the walls together (joint siege on the multiplayer server).",
  [
    (call_script, "script_coop_client_mp_begin", "$g_encountered_party"),
  ])


# the conditions of a joint event: a co-op player on its feet, not waiting for a battle already
coop_mp_event_ready = [
  (this_or_next|eq, "$coop_role", coop_role_client),
  (eq, "$coop_srv_player", 1),
  (eq, "$coop_mp_state", 0),
  (neg|troop_is_wounded, "trp_player"),
  (neq, "$g_player_is_captive", 1),
]


# the town menu, beside Native's way into the arena
coop_mp_arena_option = (
  "coop_mp_arena",
  coop_mp_event_ready + [
    (party_slot_eq, "$current_town", slot_party_type, spt_town),
    (eq, "$sneaked_into_town", disguise_none),
    (neq, "$all_doors_locked", 1),
    (neq, "$town_nighttime", 1),
  ],
  "CoopWorld: fight in the arena together (on the multiplayer server).",
  [
    (call_script, "script_coop_client_mp_begin_event", coop_event_arena, 0, "mnu_town", 0),
  ])


# the town menu, beside Native's "Join the tournament": the bet first
coop_mp_tournament_option = (
  "coop_mp_tournament",
  coop_mp_event_ready + [
    (neg|is_currently_night),
    (party_slot_ge, "$current_town", slot_town_has_tournament, 1),
    (eq, "$entry_to_town_forbidden", 0),
  ],
  "CoopWorld: join the tournament together (on the multiplayer server).",
  [
    (jump_to_menu, "mnu_coop_tournament_bet"),
  ])


# the training ground, beside Native's sparring: how many opponents first
coop_mp_training_option = (
  "coop_mp_training",
  coop_mp_event_ready,
  "CoopWorld: train together with your friends (on the multiplayer server).",
  [
    (jump_to_menu, "mnu_coop_training_pick"),
  ])


coop_mp_encounter_option = (
  "coop_mp_battle",
  [
    (this_or_next|eq, "$coop_role", coop_role_client),
    (eq, "$coop_srv_player", 1),
    (neg|troop_is_wounded, "trp_player"),
    (neq, "$g_player_is_captive", 1),
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
  ("coop_tournament_bet", 0,
   "CoopWorld: the tournament of {s1}.^^Your team fights {reg2} rounds in a row, as many against as many as it has players; it stands as long as one of its heroes does. If it wins the last round every player gets the prize of the tournament.^^Whoever bets stakes on the whole team: 100 denars win {reg1} more, for every player, and if the team is beaten only the stake is lost. How much do you bet?",
   "none",
   [
     (str_store_party_name, s1, "$current_town"),
     (assign, "$g_tournament_cur_tier", 0),
     (call_script, "script_get_win_amount_for_tournament_bet"),
     (store_sub, reg1, reg0, 100),
     (assign, reg2, coop_mp_tournament_rounds),
   ],
   [
     ("coop_bet_" + str(amount),
      [(store_troop_gold, ":gold", "trp_player"), (ge, ":gold", amount)],
      str(amount) + " denars.",
      [(call_script, "script_coop_client_mp_begin_event", coop_event_tournament, 0, "mnu_town", amount)])
     for amount in (5, 10, 20, 50, 100)
   ] + [
     ("coop_bet_none", [], "No bet.",
      [(call_script, "script_coop_client_mp_begin_event", coop_event_tournament, 0, "mnu_town", 0)]),
     ("coop_bet_back", [], "Go back.", [(jump_to_menu, "mnu_town")]),
   ]),

  ("coop_training_pick", 0,
   "CoopWorld: the training together.^^All players fight side by side, in practice gear, against your own men. How many opponents for each player?",
   "none",
   [],
   [
     ("coop_train_" + str(number), [], text + ".",
      [(call_script, "script_coop_client_mp_begin_event", coop_event_training, number, "mnu_training_ground", 0)])
     for number, text in ((1, "One"), (2, "Two"), (3, "Three"), (4, "Four"))
   ] + [
     ("coop_train_back", [], "Cancel.", [(jump_to_menu, "mnu_training_ground")]),
   ]),

  # the spoils as Native's victory menu shows them: the loot screen from the menu's own code (set
  # $coop_loot_step 1 and jump here), and when it closes the menu's code runs again and leaves for
  # the map. A loot screen opened from an option left that menu's options dead afterwards.
  ("coop_loot", 0,
   "CoopWorld: your share of the spoils of the joint battle.",
   "none",
   [
     (try_begin),
       (eq, "$coop_loot_step", 1),
       (assign, "$coop_loot_step", 2),
       (call_script, "script_coop_client_mp_loot_take"),
     (else_try),
       (eq, "$coop_loot_step", 2),
       (assign, "$coop_loot_step", 0),
       (leave_encounter),
       (call_script, "script_coop_client_drop_gone"),
       (change_screen_return),
     (try_end),
   ],
   [
     ("coop_loot_leave", [], "Back to the map.",
      [(assign, "$coop_loot_step", 0), (leave_encounter), (call_script, "script_coop_client_drop_gone"),
       (change_screen_map)]),
   ]),

  ("coop_mp_wait", 0,
   "CoopWorld: joint battle.",
   "none",
   [
     (try_begin),
       (is_between, "$coop_mp_state", 1, 4),
       # whether the window is up, not a saved flag: a window ended any other way than by its
       # button (a load, a jump to another menu) left the flag set, and no window ever came again
       (neg|is_presentation_active, "prsnt_coop_mp_wait"),
       (eq, "$coop_mp_hidden", 0), #closed by the player: the menu shows instead
       (start_presentation, "prsnt_coop_mp_wait"),
     (try_end),
   ],
   [
     ("coop_mp_show", [(is_between, "$coop_mp_state", 1, 4)], "Show the battle.",
      [(assign, "$coop_mp_hidden", 0), (start_presentation, "prsnt_coop_mp_wait")]),
     ("coop_mp_cancel", [(eq, "$coop_mp_state", 2), (eq, "$coop_mp_status", 0)], "Cancel the joint battle.",
      [(assign, "$coop_mp_state", 4), (call_script, "script_coop_client_mp_no_event"),
       (leave_encounter), (change_screen_return)]),
     ("coop_mp_loot", [(neg|is_between, "$coop_mp_state", 1, 4), (eq, "$coop_loot_ready", 1),
                       (le, "$coop_mp_captor", 0), (le, "$coop_mp_taken_center", 0)],
      "Take your share of the spoils (then back to the map).",
      [
        (call_script, "script_coop_client_mp_leave_battle"),
        (assign, "$coop_loot_step", 1),
        (jump_to_menu, "mnu_coop_loot"),
      ]),
     ("coop_mp_taken", [(neg|is_between, "$coop_mp_state", 1, 4), (gt, "$coop_mp_taken_center", 0)],
      "Enter the stormed walls.",
      [
        # the host's own game: Native's victory and the center's capture, as after its own assault
        (party_clear, "$coop_mp_taken_center"),
        (assign, "$coop_mp_taken_center", 0),
        (assign, "$g_next_menu", "mnu_castle_taken"),
        (jump_to_menu, "mnu_total_victory"),
      ]),
     ("coop_mp_siege_on", [(neg|is_between, "$coop_mp_state", 1, 4), (le, "$coop_mp_taken_center", 0),
                           (eq, "$coop_mp_defend", 0),
                           (eq, "$coop_mp_last_won", 0), #the storm failed: the siege goes on
                           (le, "$coop_mp_captor", 0), (gt, "$coop_mp_target_center", 0),
                           (party_is_active, "$coop_mp_target_center"),
                           (store_faction_of_party, ":faction", "$coop_mp_target_center"),
                           (store_relation, ":relation", ":faction", "fac_player_supporters_faction"),
                           (lt, ":relation", 0)],
      "Back to the siege.",
      [(assign, "$coop_mp_target_center", -1), (jump_to_menu, "mnu_castle_besiege")]),
     # a joint event started in a town or at a training ground: back there
     ("coop_mp_back_menu", [(neg|is_between, "$coop_mp_state", 1, 4), (gt, "$coop_mp_return_menu", 0)], "Back.",
      [
        (assign, ":menu", "$coop_mp_return_menu"),
        (call_script, "script_coop_client_mp_no_event"),
        (assign, "$coop_profile_frames", coop_profile_period_frames), #what the fight changed goes to the host
        (jump_to_menu, ":menu"),
      ]),
     ("coop_mp_back", [(neg|is_between, "$coop_mp_state", 1, 4), (le, "$coop_mp_captor", 0),
                       (le, "$coop_mp_return_menu", 0),
                       (le, "$coop_mp_taken_center", 0)], "Back to the map.",
      [
        (call_script, "script_coop_client_mp_leave_battle"),
        (leave_encounter),
        (call_script, "script_coop_client_drop_gone"),
        # change_screen_map, not _return: after the spoils' loot screen this menu's return did nothing
        (change_screen_map),
      ]),
     ("coop_mp_captured", [(neg|is_between, "$coop_mp_state", 1, 4), (gt, "$coop_mp_captor", 0)],
      "You are taken prisoner...",
      [(call_script, "script_coop_client_mp_capture")]),
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
       (eq, "$coop_mp_inv_type", 7),
       (assign, reg1, "$coop_mp_bet"),
       (store_troop_gold, reg2, "trp_player"),
       (str_store_string, s2, "@{s1} challenges you to a duel. The stake: {reg1} denars; you carry {reg2}.^^You fight each other on the multiplayer server, in your own gear, without troops. Nobody is hurt in earnest, nobody is taken. The winner takes the stake from the loser."),
     (else_try),
       (eq, "$coop_mp_inv_type", 4),
       (str_store_string, s2, "@{s1} calls you to fight in the arena together.^^You fight side by side on the multiplayer server, in practice gear. Nobody is hurt in earnest, and each player gets the prize for the opponents they beat."),
     (else_try),
       (eq, "$coop_mp_inv_type", 5),
       (str_store_string, s2, "@{s1} calls you to the tournament together.^^You fight side by side on the multiplayer server, in practice gear, round after round. If your team wins, every player gets the prize and what the bets won."),
     (else_try),
       (eq, "$coop_mp_inv_type", 6),
       (str_store_string, s2, "@{s1} calls you to train together.^^You fight side by side on the multiplayer server, in practice gear, against your own men, and your troops learn from it."),
     (else_try),
       (eq, "$coop_mp_inv_type", 3),
       (str_store_string, s2, "@{s1}, whose party you follow, goes into battle - you are called!^^The battle is fought on the multiplayer server: your troops fight on {s1}'s side. Join it there; if you do not, your troops fight without you."),
     (else_try),
       (eq, "$coop_mp_inv_type", 2),
       (str_store_string, s2, "@{s1} attacks you!^^The battle is fought on the multiplayer server. Join it there; if you do not, your troops fight without you."),
     (else_try),
       (str_store_string, s2, "@{s1} begins a battle nearby and calls you to arms.^^The battle is fought on the multiplayer server: your troops fight on {s1}'s side."),
     (try_end),
   ],
   [
     ("coop_mp_join",
      [(store_troop_gold, ":gold", "trp_player"), #a duel: the stake must be there to lose
       (this_or_next|neq, "$coop_mp_inv_type", 7),
       (ge, ":gold", "$coop_mp_bet")],
      "To battle!",
      [
        (assign, "$coop_signal_menu", 0),
        (assign, "$coop_mp_status", 0),
        (assign, "$coop_mp_state", 3),
        (assign, "$coop_mp_hidden", 0),
        (jump_to_menu, "mnu_coop_mp_wait"),
      ]),
     ("coop_mp_decline", [(this_or_next|eq, "$coop_mp_inv_type", 1), (ge, "$coop_mp_inv_type", 4)], "Decline.",
      [
        (assign, "$coop_mp_state", 4),
        (call_script, "script_coop_client_mp_no_event"),
        (try_begin),
          (gt, "$coop_signal_menu", 0), #it came over a town's or a village's menu: back there
          (assign, ":menu", "$coop_signal_menu"),
          (assign, "$coop_signal_menu", 0),
          (call_script, "script_coop_decline_now"),
          (jump_to_menu, ":menu"),
        (else_try),
          (eq, "$coop_ping_on", 1), #the camp's: no map request comes for a while either
          (call_script, "script_coop_decline_now"),
          (change_screen_return),
        (else_try),
          (change_screen_return),
        (try_end),
      ]),
   ]),
]


mp_campaign_presentations = [
  ("coop_mp_wait", prsntf_manual_end_only, 0,
   [
     (ti_on_presentation_load,
      [
        (set_fixed_point_multiplier, 1000),
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
        # every few seconds: what the window does (to find where a joint battle gets stuck)
        (try_begin),
          (store_sub, ":since", ":now", "$coop_mp_dbg_shown"),
          (this_or_next|lt, ":since", 0),
          (ge, ":since", 3000),
          (assign, "$coop_mp_dbg_shown", ":now"),
          (assign, reg20, "$coop_mp_state"),
          (assign, reg21, "$coop_mp_dbg_sent"),
          (assign, reg22, "$coop_mp_dbg_answers"),
          (assign, reg23, "$coop_net_pending"),
          (assign, reg24, "$coop_mp_bid"),
          (display_message, "@CoopWorld [wait]: state {reg20}, sent {reg21}, answers {reg22}, pending {reg23}, battle {reg24}", 0xFFDD66),
        (try_end),
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
      (try_begin),
        (map_free),
        (assign, "$coop_mp_invite_pending", 0),
        (assign, "$coop_signal_menu", 0),
        (call_script, "script_coop_note", coop_note_signal, coop_signal_map, "$coop_mp_inv_type", 0),
        (jump_to_menu, "mnu_coop_mp_invite"),
      (else_try),
        (neq, "$freelancer_state", 1), #serving in a lord's party, or a prisoner: that rest is not the player's
        (neq, "$g_player_is_captive", 1),
        (rest_for_hours, 0, 0, 0), #a rest hides the map until a click: the call ends it
      (try_end),
    (try_end),
    # lost a joint battle while away from its window: the capture begins on the map
    (try_begin),
      (gt, "$coop_mp_captor", 0),
      (map_free),
      (call_script, "script_coop_client_mp_capture"),
    (try_end),
    # the world is held: a click on the map is cancelled. At 1% speed the player hardly moved, but
    # a player on the move keeps the clock running: the pause was only on the screen (session
    # 20:19, 30.10: 11 game hours a minute on a client while the world stood still)
    (try_begin),
      (eq, "$coop_world_paused", 1),
      (map_free),
      (neq, "$freelancer_state", 1),
      (neq, "$g_player_is_captive", 1),
      (eq, "$coop_leader", 0),
      (party_get_attached_to, ":attached_to", "p_main_party"),
      (lt, ":attached_to", 0),
      (party_set_ai_behavior, "p_main_party", ai_bhvr_hold),
    (try_end),
  ]


def client_request_suffix():
  """Ops building s17 for the client's map request (and the host's own player request)."""
  from coop.players import request_suffix as players_request_suffix
  from coop.together import request_suffix as together_request_suffix
  return [
    (str_clear, s17),
    (try_begin),
      (eq, "$coop_mp_state", 4),
      (assign, "$coop_mp_state", 0),
      (assign, reg7, "$coop_mp_bid"),
      (str_store_string, s17, "@&mp=4&bid={reg7}"),
    (try_end),
  ] + players_request_suffix() + together_request_suffix() + [
    # a soldier in a lord's party (Freelancer): which world party that is, so the bridge can tell
    # when he goes into battle
    (try_begin),
      (eq, "$coop_role", coop_role_client),
      (eq, "$freelancer_state", 1),
      (gt, "$enlisted_party", 0),
      (party_is_active, "$enlisted_party"),
      (party_get_slot, reg7, "$enlisted_party", slot_party_coop_sid),
      (gt, reg7, 0),
      (val_sub, reg7, 1),
      (str_store_string, s17, "@{s17}&lord={reg7}"),
    (try_end),
    # what this game is doing, for the bridge's log when it goes quiet (a hung game sends nothing
    # more): parties here (counted now and then), mirrors spawned and swept, Freelancer's state,
    # the clock against the world's, the party the player's is attached to
    (try_begin),
      (eq, "$coop_role", coop_role_client),
      (try_begin),
        (store_mod, ":turn", "$coop_net_seq", 50),
        (eq, ":turn", 0),
        (assign, "$coop_dbg_parties", 0),
        (try_for_parties, ":unused"),
          (val_add, "$coop_dbg_parties", 1),
        (try_end),
      (try_end),
      (assign, reg7, "$coop_dbg_parties"),
      (assign, reg8, "$coop_net_spawned"),
      (str_store_string, s17, "@{s17}&dbg={reg7},{reg8}"),
      (assign, reg7, "$coop_net_swept"),
      (assign, reg8, "$freelancer_state"),
      (str_store_string, s17, "@{s17},{reg7},{reg8}"),
      (assign, reg7, "$coop_clock_sync"),
      (party_get_attached_to, reg8, "p_main_party"),
      (str_store_string, s17, "@{s17},{reg7},{reg8}"),
    (try_end),
  ]


def reply_branches():
  """else_try branches for net_reply_handler: kinds 6 to 11, 13 and 26."""
  return [
    (else_try),
      (eq, ":kind", 26),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1),
      (call_script, "script_coop_client_mp_event_result"),
    (else_try),
      (eq, ":kind", 6),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1), #the host's own player requests
      (call_script, "script_coop_client_mp_invite"),
    (else_try),
      (eq, ":kind", 7),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1), #the host's own player requests
      (val_add, "$coop_mp_dbg_answers", 1),
      (try_begin),
        (ge, ":num_strings", 1), #the name this player is expected under on the battle server
        (party_set_name, "p_coop_buf", s0), #kept as a party name: string registers do not last
        (neq, "$coop_mp_name_known", 1),
        (assign, "$coop_mp_name_known", 1),
        (assign, "$coop_mp_dirty", 1),
      (try_end),
      (call_script, "script_coop_client_mp_status"),
    (else_try),
      (eq, ":kind", 10),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1),
      (call_script, "script_coop_client_mp_aftermath"),
    (else_try),
      (eq, ":kind", 11),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1),
      (call_script, "script_coop_client_mp_prisoners"),
    (else_try),
      (eq, ":kind", 21),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1),
      (call_script, "script_coop_client_mp_loot"),
    (else_try),
      (eq, ":kind", 25), #the lord this player serves fights a world party (-1: no longer)
      (eq, "$coop_role", coop_role_client),
      (party_get_slot, "$coop_lord_sid", "p_coop_buf", 2),
      (party_get_slot, "$coop_lord_enemy_sid", "p_coop_buf", 3),
      (try_begin),
        (lt, "$coop_lord_enemy_sid", 0),
        (assign, "$coop_lord_asked", -1), #the next battle asks again, even against the same party
      (try_end),
    (else_try),
      (eq, ":kind", 13),
      (eq, "$coop_srv_player", 1),
      (call_script, "script_coop_client_mp_taken"),
    (else_try),
      (eq, ":kind", 9),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1),
      (call_script, "script_coop_client_mp_weapons"),
    (else_try),
      (eq, ":kind", 8),
      (this_or_next|eq, "$coop_role", coop_role_client),
      (eq, "$coop_srv_player", 1), #the host's own player requests
      (call_script, "script_coop_client_mp_result"),
  ]
