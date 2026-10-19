"""chain.py - a small in-memory blockchain made of Block objects.

WHY HAVE PREVIOUS-HASH LINKS?
    Each new block stores the hash of the block before it:

        PreviousHash_i = Hash_(i-1)           (Formula 3)

    Because block i's own hash is calculated from data that INCLUDES previous_hash,
    changing an old block changes its hash, which no longer matches the
    previous_hash saved inside the next block. The chain is "broken" at that point
    and validation notices.

This class is used by the unit tests and the safe tamper demonstration. The real
application stores the same blocks in SQLite (see services.py) and rebuilds Block
objects from those rows when it needs to validate them.
"""
import copy

from .block import Block, create_genesis_block
from .validation import validate_blocks


def create_next_block(previous_block, *, timestamp, evidence_id, custody_event_id,
                      event_type, actor, details, evidence_hash):
    """Create the block that comes right after `previous_block`.

    Inputs: the previous Block plus the event information for the new block.
    Returns: a new, sealed Block (its hash is already calculated).
    Why: both the in-memory chain and the database service need the exact same
         rule ("index = previous index + 1, previous_hash = previous hash"), so it
         lives in one function.
    """
    block = Block(
        index=previous_block.index + 1,
        timestamp=timestamp,
        evidence_id=evidence_id,
        custody_event_id=custody_event_id,
        event_type=event_type,
        actor=actor,
        details=details,
        evidence_hash=evidence_hash,
        previous_hash=previous_block.hash,
    )
    return block.seal()


class Blockchain:
    """A list of blocks that always starts with the genesis block."""

    def __init__(self, blocks=None):
        """Start a new chain (genesis only) or wrap an existing list of blocks."""
        self.blocks = list(blocks) if blocks else [create_genesis_block()]

    @property
    def last_block(self):
        """The newest block in the chain."""
        return self.blocks[-1]

    def add_block(self, *, timestamp, evidence_id, custody_event_id, event_type,
                  actor, details, evidence_hash):
        """Append a new block linked to the current last block. Returns the block."""
        block = create_next_block(
            self.last_block,
            timestamp=timestamp,
            evidence_id=evidence_id,
            custody_event_id=custody_event_id,
            event_type=event_type,
            actor=actor,
            details=details,
            evidence_hash=evidence_hash,
        )
        self.blocks.append(block)
        return block

    def validate(self):
        """Validate this chain. Returns a ChainValidationResult."""
        return validate_blocks(self.blocks)

    def copy(self):
        """Return an independent deep copy.

        Why: the tamper demonstration modifies a COPY so the original data is never
        touched.
        """
        return Blockchain(copy.deepcopy(self.blocks))
