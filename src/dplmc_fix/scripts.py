def merge(scripts, **unused):
  """game_receive_network_message: Diplomacy 1.174 lost the else_try between the server's events and
  the clients' (Native 1.171 has it). The clients' events then sat inside the server's last event
  branch and no player's game handled any word from the server: the team window waited for its
  confirmation for good, the battle server's messages never showed."""
  from header_operations import try_begin, try_end, else_try, multiplayer_is_dedicated_server, neg, eq
  from header_common import multiplayer_event_return_renaming_server_allowed
  from coop_merge import script_block, MergeError
  block = script_block(scripts, "game_receive_network_message")

  def op(i):  # an operation as a tuple: a bare one such as (try_end) is just its code
    return tuple(block[i]) if isinstance(block[i], (list, tuple)) else (block[i],)

  clients = (neg | multiplayer_is_dedicated_server,)
  first_client_event = (eq, ":event_type", multiplayer_event_return_renaming_server_allowed)
  spots = [i for i in range(1, len(block) - 2)
           if op(i) == clients and op(i - 1) == (try_end,) and op(i + 1) == (try_begin,)
           and op(i + 2) == first_client_event]
  if len(spots) != 1:
    raise MergeError(f"dplmc_fix: expected one start of the clients' events, found {len(spots)}")
  block.insert(spots[0], else_try)
