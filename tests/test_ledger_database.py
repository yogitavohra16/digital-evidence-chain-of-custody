"""Tests for the database-backed ledger: events <-> blocks consistency."""
from django.core.exceptions import ValidationError

from blockchain.models import BlockRecord
from blockchain.services import (LedgerInvalidError, ensure_genesis_block, load_chain_as_blocks,
                                 validate_stored_chain)
from evidence.models import CustodyEvent, Evidence
from evidence.services import add_custody_event

from .helpers import EvidenceTestCase

A = CustodyEvent.ActionType


class LedgerDatabaseTests(EvidenceTestCase):
    """Custody events create blocks and the stored chain validates."""

    def test_genesis_exists_once(self):
        """Genesis block is created at migrate time and never duplicated."""
        self.assertEqual(BlockRecord.objects.filter(block_index=0).count(), 1)
        self.assertIsNone(ensure_genesis_block())
        self.assertEqual(BlockRecord.objects.filter(block_index=0).count(), 1)

    def test_registration_creates_block(self):
        """Registering evidence creates a REGISTERED custody event with a linked block."""
        evidence = self.register()
        event = evidence.custody_events.get()
        self.assertEqual(event.action_type, A.REGISTERED)
        self.assertEqual(event.block_record.block_index, 1)
        self.assertEqual(event.block_record.previous_hash, BlockRecord.objects.get(block_index=0).current_hash)

    def test_each_event_gets_a_linked_block(self):
        """Every added event gets the next block, linked to the previous one."""
        evidence = self.register()
        event = add_custody_event(evidence=evidence, action_type=A.TRANSFERRED, user=self.user,
                                  handler_name="Officer Test", from_party="Alice", to_party="Bob", remarks="Move to lab")
        blocks = load_chain_as_blocks()
        self.assertEqual([block.index for block in blocks], [0, 1, 2])
        self.assertEqual(blocks[2].previous_hash, blocks[1].hash)
        self.assertEqual(event.block_record.block_index, 2)
        self.assertTrue(validate_stored_chain().is_valid)

    def test_status_follows_events(self):
        """Evidence status is updated by events."""
        evidence = self.register()
        for action, expected in ((A.ANALYSIS_STARTED, Evidence.Status.IN_ANALYSIS),
                                 (A.ANALYSIS_COMPLETED, Evidence.Status.ANALYSIS_COMPLETED),
                                 (A.ARCHIVED, Evidence.Status.ARCHIVED)):
            add_custody_event(evidence=evidence, action_type=action, user=self.user,
                              handler_name="Analyst", remarks="step")
            evidence.refresh_from_db()
            self.assertEqual(evidence.status, expected)

    def test_modified_block_row_detected(self):
        """Editing a stored block's data (bypassing the app) is detected."""
        self.register()
        record = BlockRecord.objects.get(block_index=1)
        record.block_data = record.block_data.replace("Officer Test", "Someone Else")
        record.save()
        result = validate_stored_chain()
        self.assertFalse(result.is_valid)
        self.assertIn("hash mismatch", " ".join(result.check_for(1).problems))

    def test_modified_custody_event_detected(self):
        """Editing a custody event row directly makes it disagree with its block."""
        evidence = self.register()
        CustodyEvent.objects.filter(evidence=evidence).update(remarks="rewritten history")
        self.assertFalse(validate_stored_chain().is_valid)

    def test_modified_original_hash_detected(self):
        """Changing the original evidence hash in the database is detected."""
        evidence = self.register()
        Evidence.objects.filter(pk=evidence.pk).update(sha256_hash="b" * 64)
        self.assertFalse(validate_stored_chain().is_valid)

    def test_deleted_block_detected(self):
        """A custody event whose block was deleted is reported."""
        evidence = self.register()
        BlockRecord.objects.filter(custody_event__evidence=evidence).delete()
        self.assertFalse(validate_stored_chain().is_valid)

    def test_new_events_refused_on_invalid_ledger(self):
        """Nothing is appended to a damaged ledger, and no event is saved."""
        evidence = self.register()
        record = BlockRecord.objects.get(block_index=1)
        record.block_data = record.block_data.replace("Officer Test", "X")
        record.save()
        before = CustodyEvent.objects.count()
        with self.assertRaises(LedgerInvalidError):
            add_custody_event(evidence=evidence, action_type=A.ACCESSED, user=self.user,
                              handler_name="Analyst", remarks="look")
        self.assertEqual(CustodyEvent.objects.count(), before)

    def test_transfer_needs_from_and_to(self):
        """A transfer without a receiver is rejected."""
        evidence = self.register()
        with self.assertRaises(ValidationError):
            add_custody_event(evidence=evidence, action_type=A.TRANSFERRED, user=self.user,
                              handler_name="Officer", from_party="Alice", remarks="move")

    def test_archived_evidence_rejects_events(self):
        """No events can be added after archiving."""
        evidence = self.register()
        add_custody_event(evidence=evidence, action_type=A.ARCHIVED, user=self.user,
                          handler_name="Officer", remarks="done")
        with self.assertRaises(ValidationError):
            add_custody_event(evidence=evidence, action_type=A.ACCESSED, user=self.user,
                              handler_name="Officer", remarks="again")
