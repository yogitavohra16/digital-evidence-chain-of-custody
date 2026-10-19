"""validation.py - checking whether a chain of blocks is still trustworthy.

This module is "pure Python": it knows nothing about Django or the database. It
receives a list of Block objects and returns a human-readable result. Keeping it
separate makes it easy to test (the tests build chains in memory and tamper with
copies) and easy to explain in a viva.

VALIDATION RULES (Formulas 3 and 4 in the documentation):
    For every block i:
        1. RecalculatedHash_i == StoredHash_i          (the data was not edited)
        2. block_i.previous_hash == block_(i-1).hash   (the link is intact)
    Plus:
        3. Block 0 must equal the genuine genesis block.
        4. Block numbers must run 0, 1, 2, 3 ... without gaps.

LIMITATION: if an attacker edits a block AND recalculates its hash AND every later
block's previous_hash and hash, the chain becomes valid again. A single local copy
of the chain cannot prevent that; real blockchains add many independent copies and a
consensus protocol, which this prototype intentionally does not have.
"""
from dataclasses import dataclass, field

from django.utils import timezone

from .block import create_genesis_block


@dataclass
class BlockCheck:
    """The validation result for ONE block."""

    index: int
    problems: list = field(default_factory=list)

    @property
    def is_valid(self):
        """A block is valid when no problem was recorded for it."""
        return not self.problems

    @property
    def status(self):
        """Short label used in the ledger table: 'VALID' or a list of problems."""
        return "VALID" if self.is_valid else "INVALID"


@dataclass
class ChainValidationResult:
    """The validation result for the WHOLE chain."""

    block_checks: list
    checked_at: object = field(default_factory=timezone.now)
    # Problems that do not belong to one block (e.g. an event with no block).
    general_problems: list = field(default_factory=list)

    @property
    def total_blocks(self):
        """How many blocks were examined."""
        return len(self.block_checks)

    @property
    def invalid_checks(self):
        """The BlockCheck objects that have at least one problem."""
        return [check for check in self.block_checks if not check.is_valid]

    @property
    def is_valid(self):
        """The chain is valid only if every block AND every general check passed."""
        return not self.invalid_checks and not self.general_problems

    @property
    def all_problems(self):
        """Every problem as readable text, block problems first."""
        lines = []
        for check in self.invalid_checks:
            for problem in check.problems:
                lines.append(f"Block #{check.index}: {problem}")
        lines.extend(self.general_problems)
        return lines

    @property
    def message(self):
        """A human-readable summary of the result."""
        if self.is_valid:
            return (
                f"BLOCKCHAIN VALID - all {self.total_blocks} block(s) passed the hash "
                "and link checks."
            )
        return (
            f"BLOCKCHAIN INVALID - {len(self.all_problems)} problem(s) found. "
            "Do not trust the custody history until the cause is investigated."
        )

    def check_for(self, block_index):
        """Return the BlockCheck for a given block index, or None."""
        for check in self.block_checks:
            if check.index == block_index:
                return check
        return None


def validate_blocks(blocks):
    """Validate a list of Block objects (ordered from genesis onward).

    Why it is needed:
        This is the tamper detector. It never trusts a stored hash. It recalculates
        each hash from the block's data and compares.

    Input:  blocks - list of Block objects, oldest first.
    Returns: ChainValidationResult describing every block.
    Security note: it only READS the blocks. It never repairs or rewrites anything.
    """
    checks = []
    genuine_genesis = create_genesis_block()

    for position, block in enumerate(blocks):
        check = BlockCheck(index=block.index)

        # Rule 4: the block number must match its position (0, 1, 2, ...).
        if block.index != position:
            check.problems.append(
                f"expected block number {position} but found {block.index} "
                "(a block is missing, duplicated or reordered)"
            )

        # Rule 1: recalculate the hash from the data and compare with the stored one.
        recalculated_hash = block.calculate_hash()
        if recalculated_hash != block.hash:
            check.problems.append(
                "hash mismatch - the block data no longer produces the stored hash "
                "(data was modified)"
            )

        if position == 0:
            # Rule 3: the first block must be the genuine, deterministic genesis block.
            if block.hash != genuine_genesis.hash or block.serialize() != genuine_genesis.serialize():
                check.problems.append("block 0 is not the genuine genesis block")
        else:
            # Rule 2: the link to the previous block must be intact.
            previous_block = blocks[position - 1]
            if block.previous_hash != previous_block.hash:
                check.problems.append(
                    "broken link - previous_hash does not equal the hash of block "
                    f"#{previous_block.index}"
                )

        checks.append(check)

    result = ChainValidationResult(block_checks=checks)
    if not blocks:
        result.general_problems.append("The chain is empty (the genesis block is missing).")
    return result
