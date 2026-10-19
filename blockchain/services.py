"""services.py - connects the pure blockchain code to the SQLite database.

HOW THE DATABASE-BACKED LEDGER WORKS
    * Each block is one row in the BlockRecord table.
    * To validate, we READ all rows in order, rebuild Block objects from the stored
      JSON, and run validate_blocks() (which recalculates every hash).
    * We then run a few extra database cross-checks (e.g. "does the block still agree
      with its CustodyEvent row?").
    * We NEVER repair, regenerate or overwrite existing blocks. If something is wrong,
      the problem is reported to the user so it can be investigated.

CONSISTENCY WITH CUSTODY EVENTS
    A custody event and its block are saved inside ONE database transaction (see
    evidence/services.py). If creating the block fails, the whole transaction is
    rolled back, so an event is never reported as recorded without its block.
"""
from datetime import timezone as dt_timezone

from django.db import transaction

from evidence.models import CustodyEvent

from .block import Block, create_genesis_block
from .chain import create_next_block
from .models import BlockRecord
from .validation import ChainValidationResult, validate_blocks


class LedgerInvalidError(Exception):
    """Raised when the stored ledger fails validation and new blocks must not be added."""


def format_block_timestamp(moment):
    """Convert a datetime to the exact UTC text stored inside blocks.

    Example: '2026-10-12T09:30:15.123456+00:00'. Using one function everywhere means
    the block and the custody event can be compared reliably.
    """
    return moment.astimezone(dt_timezone.utc).isoformat(timespec="microseconds")


def build_event_details(custody_event):
    """Return the small details dictionary that is stored in the block for an event."""
    return {
        "from": custody_event.from_party,
        "to": custody_event.to_party,
        "remarks": custody_event.remarks,
        "recorded_by": custody_event.recorded_by.get_username(),
    }


def _save_block(block, custody_event=None):
    """Write one sealed Block to the database as a BlockRecord row."""
    return BlockRecord.objects.create(
        block_index=block.index,
        block_data=block.serialize(),
        previous_hash=block.previous_hash,
        current_hash=block.hash,
        custody_event=custody_event,
    )


def ensure_genesis_block():
    """Create the genesis block ONLY if the ledger is completely empty.

    Safe to call many times. It never creates a second genesis block and never
    "repairs" a ledger that already has blocks (even a damaged one).
    Returns: the BlockRecord for block 0 if it was just created, otherwise None.
    """
    with transaction.atomic():
        if BlockRecord.objects.exists():
            return None
        return _save_block(create_genesis_block())


def block_from_record(record):
    """Rebuild a Block object from a stored BlockRecord.

    The block keeps the STORED hash so the validator can compare it with a freshly
    recalculated one. If the stored JSON is unreadable (corrupted), we return a
    placeholder block; its recalculated hash cannot match, so validation reports it.
    """
    try:
        return Block.from_stored_data(record.block_data, record.current_hash)
    except (ValueError, KeyError, TypeError):
        return Block(
            index=record.block_index,
            timestamp="",
            evidence_id="UNREADABLE",
            custody_event_id=None,
            event_type="UNREADABLE",
            actor="",
            details={"error": "stored block data could not be read"},
            evidence_hash="",
            previous_hash=record.previous_hash,
            hash=record.current_hash,
        )


def _is_readable(record):
    """True if the record's JSON text can be parsed into a block."""
    try:
        Block.from_stored_data(record.block_data, record.current_hash)
        return True
    except (ValueError, KeyError, TypeError):
        return False


def get_ledger_rows():
    """Validate the stored chain and return (rows, result).

    rows   - list of dicts: {'record': BlockRecord, 'block': Block, 'check': BlockCheck}
    result - ChainValidationResult for the whole chain.

    Steps:
      1. Load every block row in order (oldest first).
      2. Rebuild Block objects and run the pure validator (hash + link checks).
      3. Run database cross-checks and add any problems to the result.
    """
    records = list(
        BlockRecord.objects.select_related("custody_event__evidence", "custody_event__recorded_by")
        .order_by("block_index")
    )
    blocks = [block_from_record(record) for record in records]
    result = validate_blocks(blocks)

    for record, block, check in zip(records, blocks, result.block_checks):
        _cross_check_record(record, block, check)

    # An event that has no block at all means a block was deleted (or never made).
    for event in CustodyEvent.objects.filter(block_record__isnull=True).select_related("evidence"):
        result.general_problems.append(
            f"Custody event #{event.pk} for {event.evidence.evidence_id} has no blockchain block."
        )

    rows = [
        {"record": record, "block": block, "check": check}
        for record, block, check in zip(records, blocks, result.block_checks)
    ]
    return rows, result


def _cross_check_record(record, block, check):
    """Add database-consistency problems for one block to its BlockCheck.

    Checks:
      * the duplicated columns (block_index, previous_hash) agree with block_data;
      * the stored JSON is readable;
      * the block still agrees with its CustodyEvent row and the evidence's
        original hash (so editing the database tables directly is also noticed).
    """
    if not _is_readable(record):
        check.problems.append("stored block data is unreadable (corrupted JSON)")
        return

    if record.block_index != block.index:
        check.problems.append("database column block_index differs from the block data")
    if record.previous_hash != block.previous_hash:
        check.problems.append("database column previous_hash differs from the block data")

    event = record.custody_event
    if event is None:
        return  # genesis block: nothing more to compare

    comparisons = [
        ("custody event id", block.custody_event_id, event.pk),
        ("evidence id", block.evidence_id, event.evidence.evidence_id),
        ("event type", block.event_type, event.action_type),
        ("actor", block.actor, event.handler_name),
        ("timestamp", block.timestamp, format_block_timestamp(event.timestamp)),
        ("details", block.details, build_event_details(event)),
        ("evidence hash (event row)", block.evidence_hash, event.evidence_hash),
        ("original evidence hash (evidence row)", block.evidence_hash, event.evidence.sha256_hash),
    ]
    for label, block_value, database_value in comparisons:
        if block_value != database_value:
            check.problems.append(
                f"the {label} in the block differs from the database record"
            )


def validate_stored_chain():
    """Validate the whole stored ledger. Returns a ChainValidationResult."""
    _rows, result = get_ledger_rows()
    return result


def require_valid_ledger():
    """Raise LedgerInvalidError if the stored ledger fails validation.

    Why: appending new blocks onto a damaged chain would hide the damage. New custody
    events are refused until the problem is investigated by a human.
    """
    result = validate_stored_chain()
    if not result.is_valid:
        raise LedgerInvalidError(result.message)
    return result


def append_custody_event_block(custody_event):
    """Create the block for a custody event and save it. MUST run inside a transaction.

    Input:  custody_event - a CustodyEvent that has already been saved (so it has an id).
    Returns: the new BlockRecord.
    Steps:
      1. Make sure the genesis block exists.
      2. Find the newest block (the one we must link to).
      3. Create the next block (index + 1, previous_hash = newest block's hash).
      4. Save it, linked to the custody event.
    """
    ensure_genesis_block()
    last_record = BlockRecord.objects.order_by("-block_index").first()
    last_block = block_from_record(last_record)

    new_block = create_next_block(
        last_block,
        timestamp=format_block_timestamp(custody_event.timestamp),
        evidence_id=custody_event.evidence.evidence_id,
        custody_event_id=custody_event.pk,
        event_type=custody_event.action_type,
        actor=custody_event.handler_name,
        details=build_event_details(custody_event),
        evidence_hash=custody_event.evidence_hash,
    )
    return _save_block(new_block, custody_event)


def load_chain_as_blocks():
    """Return all stored blocks as a list of Block objects (read-only copy)."""
    return [block_from_record(record) for record in BlockRecord.objects.order_by("block_index")]


