"""Tests for evidence integrity verification (Formula 5) and PDF reports."""
import os

from django.urls import reverse

from verification.models import VerificationRecord
from verification.services import verify_evidence

from .helpers import EvidenceTestCase

R = VerificationRecord.Result


class VerificationTests(EvidenceTestCase):
    """MATCH / MISMATCH / FILE_MISSING outcomes."""

    def test_unchanged_file_verifies(self):
        """An untouched file gives MATCH."""
        evidence = self.register()
        record = verify_evidence(evidence, self.user)
        self.assertEqual(record.result, R.MATCH)
        self.assertEqual(record.current_hash, evidence.sha256_hash)

    def test_modified_file_is_detected_and_original_hash_kept(self):
        """Changing the stored file gives MISMATCH; the original hash is NOT overwritten."""
        evidence = self.register()
        original_hash = evidence.sha256_hash
        with open(evidence.stored_file.path, "ab") as handle:
            handle.write(b" tampered")
        record = verify_evidence(evidence, self.user)
        self.assertEqual(record.result, R.MISMATCH)
        self.assertNotEqual(record.current_hash, original_hash)
        evidence.refresh_from_db()
        self.assertEqual(evidence.sha256_hash, original_hash)

    def test_missing_file_reported(self):
        """A deleted file gives FILE_MISSING."""
        evidence = self.register()
        os.remove(evidence.stored_file.path)
        self.assertEqual(verify_evidence(evidence, self.user).result, R.FILE_MISSING)

    def test_verification_page_posts_and_stores_history(self):
        """The verification page runs a check and records it."""
        evidence = self.register()
        self.client.login(username="tester", password="Str0ng-Test-Pass!")
        response = self.client.post(reverse("verify"), {"evidence": evidence.evidence_id})
        self.assertContains(response, "INTEGRITY VERIFIED")
        self.assertEqual(VerificationRecord.objects.count(), 1)


class ReportTests(EvidenceTestCase):
    """PDF generation from real data."""

    def test_pdf_report_is_generated(self):
        """The report endpoint returns a real PDF containing the evidence ID."""
        evidence = self.register(name="a-very-long-filename-" + "x" * 80 + ".txt")
        self.client.login(username="tester", password="Str0ng-Test-Pass!")
        response = self.client.get(reverse("generate_report"), {"evidence": evidence.evidence_id, "verify_now": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertGreater(len(response.content), 1500)
        self.assertEqual(VerificationRecord.objects.count(), 1)

    def test_report_for_unknown_evidence_redirects(self):
        """An unknown evidence ID does not crash."""
        self.client.login(username="tester", password="Str0ng-Test-Pass!")
        self.assertEqual(self.client.get(reverse("generate_report"), {"evidence": "EV-9999"}).status_code, 302)
