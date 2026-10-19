"""models.py - the database table that stores the blocks of the custody ledger.

BlockRecord is the ONLY stored copy of block data. The columns `previous_hash` and
`block_index` repeat two values that are also inside `block_data`; this is
intentional (they make the table easy to read and query) and the validator checks
that the copies agree, so the duplicates cannot silently drift apart.
"""
from django.db import models
from django.utils import timezone


class BlockRecord(models.Model):
    """One block of the blockchain, saved as a row in SQLite."""

    # Position in the chain: 0 = genesis, then 1, 2, 3 ... Unique, so no two blocks
    # can share a position.
    block_index = models.PositiveIntegerField(unique=True)
    # The canonical JSON text of the block data (exactly the text that was hashed).
    block_data = models.TextField()
    previous_hash = models.CharField(max_length=64)
    current_hash = models.CharField(max_length=64, unique=True)
    # Each custody event has exactly one block (OneToOne). The genesis block belongs
    # to no event, so this is empty only for block 0.
    custody_event = models.OneToOneField(
        "evidence.CustodyEvent",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="block_record",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["block_index"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(block_index=0, custody_event__isnull=True)
                    | models.Q(block_index__gt=0, custody_event__isnull=False)
                ),
                name="only_genesis_block_has_no_custody_event",
            ),
        ]

    def __str__(self):
        return f"Block #{self.block_index} ({self.current_hash[:10]}...)"
