"""Tests for the pure in-memory blockchain (Formulas 2, 3 and 4)."""
from django.test import SimpleTestCase

from blockchain.block import ZERO_HASH, canonical_json, create_genesis_block, sha256_text
from blockchain.chain import Blockchain
from blockchain.demo import build_demo_chain, run_tamper_demo


def make_chain():
    """Chain with genesis + 3 blocks."""
    chain = Blockchain()
    for number in range(1, 4):
        chain.add_block(timestamp=f"2026-02-0{number}T00:00:00+00:00", evidence_id="EV-0001",
                        custody_event_id=number, event_type="ACCESSED", actor="Tester",
                        details={"remarks": f"event {number}"}, evidence_hash="a" * 64)
    return chain


class GenesisTests(SimpleTestCase):
    """The genesis block must be fixed and identical every time."""

    def test_genesis_is_deterministic(self):
        """Two genesis blocks have the same hash."""
        self.assertEqual(create_genesis_block().hash, create_genesis_block().hash)

    def test_genesis_fields(self):
        """Genesis has index 0 and the all-zero previous hash."""
        genesis = create_genesis_block()
        self.assertEqual(genesis.index, 0)
        self.assertEqual(genesis.previous_hash, ZERO_HASH)
        self.assertEqual(genesis.hash, genesis.calculate_hash())

    def test_new_chain_starts_with_genesis(self):
        """A new Blockchain contains exactly one block: the genesis block."""
        self.assertEqual(len(Blockchain().blocks), 1)


class CanonicalJsonTests(SimpleTestCase):
    """Canonical JSON must not depend on key order."""

    def test_key_order_does_not_matter(self):
        """Same data in a different key order gives the same text and hash."""
        first, second = {"a": 1, "b": 2}, {"b": 2, "a": 1}
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(sha256_text(canonical_json(first)), sha256_text(canonical_json(second)))


class ChainTests(SimpleTestCase):
    """Linking and validation."""

    def test_blocks_are_linked(self):
        """Each block's previous_hash equals the previous block's hash."""
        chain = make_chain()
        for position in range(1, len(chain.blocks)):
            self.assertEqual(chain.blocks[position].previous_hash, chain.blocks[position - 1].hash)

    def test_valid_chain_passes(self):
        """An untouched chain validates."""
        result = make_chain().validate()
        self.assertTrue(result.is_valid)
        self.assertEqual(result.total_blocks, 4)

    def test_modified_block_data_fails(self):
        """Editing data without re-hashing is detected as a hash mismatch."""
        tampered = make_chain().copy()
        tampered.blocks[2].actor = "Intruder"
        result = tampered.validate()
        self.assertFalse(result.is_valid)
        self.assertIn("hash mismatch", " ".join(result.check_for(2).problems))

    def test_broken_previous_hash_fails(self):
        """A wrong previous_hash is detected as a broken link."""
        tampered = make_chain().copy()
        tampered.blocks[2].previous_hash = "f" * 64
        tampered.blocks[2].seal()                     # attacker fixes this block's own hash
        result = tampered.validate()
        self.assertFalse(result.is_valid)
        self.assertIn("broken link", " ".join(result.check_for(2).problems))

    def test_edit_and_rehash_breaks_next_link(self):
        """Even if the edited block is re-hashed, the NEXT block's link breaks."""
        tampered = make_chain().copy()
        tampered.blocks[1].actor = "Intruder"
        tampered.blocks[1].seal()
        result = tampered.validate()
        self.assertFalse(result.is_valid)
        self.assertIn("broken link", " ".join(result.check_for(2).problems))

    def test_fake_genesis_fails(self):
        """A genesis block that is not the genuine one is rejected."""
        tampered = make_chain().copy()
        tampered.blocks[0].actor = "FAKE"
        tampered.blocks[0].seal()
        self.assertFalse(tampered.validate().is_valid)

    def test_copy_does_not_change_original(self):
        """Tampering with a copy leaves the original chain valid."""
        original = make_chain()
        copy = original.copy()
        copy.blocks[1].actor = "Intruder"
        self.assertTrue(original.validate().is_valid)
        self.assertFalse(copy.validate().is_valid)

    def test_demo_scenarios_detect_tampering(self):
        """The safe demo detects each scenario (for blocks that have a successor)."""
        self.assertTrue(build_demo_chain().validate().is_valid)
        for scenario in ("edit_data", "edit_and_rehash", "break_link"):
            self.assertFalse(run_tamper_demo(scenario, 2)["tampered_result"].is_valid, scenario)
