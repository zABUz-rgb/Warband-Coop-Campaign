"""CoopWorld merge layer: inserts mod code (Freelancer, CoopWorld) into the Native lists.

Replaces the ModMerger framework the Freelancer source was written for. Every anchor is
checked: if Native changes and an anchor is missing, the build stops with a clear error
instead of silently producing a broken module.
"""


class MergeError(Exception):
    pass


def find_by_id(records, rec_id):
    """Index of the record (script, menu, mission template, party, ...) whose id is rec_id."""
    for i, rec in enumerate(records):
        if rec[0] == rec_id:
            return i
    raise MergeError(f"record not found: {rec_id}")


def get_by_id(records, rec_id):
    return records[find_by_id(records, rec_id)]


def find_line(block, line, occurrence=1, start=0):
    """Index of the occurrence-th operation in block equal to line (tuple compare)."""
    want = tuple(line) if isinstance(line, (list, tuple)) else (line,)
    seen = 0
    for i in range(start, len(block)):
        op = block[i]
        cur = tuple(op) if isinstance(op, (list, tuple)) else (op,)
        if cur == want:
            seen += 1
            if seen == occurrence:
                return i
    raise MergeError(f"line not found (occurrence {occurrence}): {want}")


def insert_before(block, line, new_ops, occurrence=1):
    pos = find_line(block, line, occurrence)
    block[pos:pos] = list(new_ops)
    return pos


def insert_after(block, line, new_ops, occurrence=1):
    pos = find_line(block, line, occurrence) + 1
    block[pos:pos] = list(new_ops)
    return pos


def script_block(scripts, script_id):
    return get_by_id(scripts, script_id)[1]


def menu_block(menus, menu_id):
    return get_by_id(menus, menu_id)[4]


def menu_options(menus, menu_id):
    return get_by_id(menus, menu_id)[5]


def find_dialog(dialogs, partner, state, end_state, text_prefix=None):
    """Index of the dialog line with this partner, start state and end state (and text prefix)."""
    for i, d in enumerate(dialogs):
        if d[0] == partner and d[1] == state and d[4] == end_state:
            if text_prefix is None or text_prefix in d[3]:
                return i
    raise MergeError(f"dialog not found: {state} -> {end_state} {text_prefix or ''}")


def insert_records_before(records, rec_id, new_records):
    pos = find_by_id(records, rec_id)
    records[pos:pos] = list(new_records)
