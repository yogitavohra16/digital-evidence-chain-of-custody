"""Tests for evidence registration, custody forms and authentication of views."""
from django.test import override_settings
from django.urls import reverse

from evidence.hashing import calculate_sha256_of_bytes
from evidence.models import CustodyEvent, Evidence

from .helpers import EvidenceTestCase


class AuthenticationTests(EvidenceTestCase):
    """Protected pages require login."""

    def test_protected_pages_redirect_to_login(self):
        """Anonymous visitors are redirected to the login page for every protected view."""
        self.register()
        names_and_args = [
            ("dashboard", []), ("case_list", []), ("case_create", []), ("case_detail", [self.case.case_id]),
            ("evidence_list", []), ("evidence_register", []), ("evidence_detail", ["EV-0001"]),
            ("custody_history", ["EV-0001"]), ("custody_add", []), ("ledger", []), ("tamper_demo", []),
            ("verify", []), ("report_home", []), ("generate_report", []),
        ]
        for name, args in names_and_args:
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn(reverse("login"), response["Location"], name)

    def test_login_works_and_dashboard_loads(self):
        """A valid login reaches the dashboard."""
        self.assertTrue(self.client.login(username="tester", password="Str0ng-Test-Pass!"))
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total cases")

    def test_evidence_files_not_served_publicly(self):
        """There is no URL that exposes stored evidence files."""
        evidence = self.register()
        with self.assertRaises(ValueError):
            evidence.stored_file.url   # storage has no public URL


class RegistrationViewTests(EvidenceTestCase):
    """Evidence registration through the web form."""

    def setUp(self):
        super().setUp()
        self.client.login(username="tester", password="Str0ng-Test-Pass!")

    def post_registration(self, upload):
        return self.client.post(reverse("evidence_register"), {
            "case": self.case.pk, "evidence_file": upload, "handler_name": "Officer Test", "notes": "n",
        })

    def test_registration_stores_expected_hash(self):
        """The stored hash equals SHA-256 of the uploaded bytes; metadata is saved."""
        content = b"forensic sample content"
        response = self.post_registration(self.make_upload(content, "report.txt"))
        evidence = Evidence.objects.get()
        self.assertRedirects(response, reverse("evidence_detail", args=[evidence.evidence_id]))
        self.assertEqual(evidence.sha256_hash, calculate_sha256_of_bytes(content))
        self.assertEqual(evidence.file_size, len(content))
        self.assertEqual(evidence.original_filename, "report.txt")
        self.assertEqual(evidence.file_extension, "txt")
        self.assertEqual(evidence.evidence_id, "EV-0001")
        self.assertEqual(CustodyEvent.objects.filter(evidence=evidence).count(), 1)
        self.assertNotIn("report", evidence.stored_file.name)   # random safe storage name

    def test_evidence_ids_are_unique_and_sequential(self):
        """Two registrations get EV-0001 and EV-0002."""
        self.post_registration(self.make_upload(b"one", "a.txt"))
        self.post_registration(self.make_upload(b"two", "b.txt"))
        self.assertEqual(list(Evidence.objects.order_by("id").values_list("evidence_id", flat=True)), ["EV-0001", "EV-0002"])

    def test_disallowed_extension_rejected(self):
        """Executable files are refused."""
        response = self.post_registration(self.make_upload(b"MZ...", "virus.exe"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Evidence.objects.count(), 0)

    def test_oversized_file_rejected(self):
        """Files above the configured limit are refused."""
        with override_settings(MAX_EVIDENCE_UPLOAD_BYTES=10):
            response = self.post_registration(self.make_upload(b"x" * 50, "big.txt"))
        self.assertEqual(Evidence.objects.count(), 0)
        self.assertContains(response, "larger than")

    def test_empty_file_rejected(self):
        """Zero-byte files are refused."""
        self.post_registration(self.make_upload(b"", "empty.txt"))
        self.assertEqual(Evidence.objects.count(), 0)


class CustodyViewTests(EvidenceTestCase):
    """Custody event form."""

    def setUp(self):
        super().setUp()
        self.client.login(username="tester", password="Str0ng-Test-Pass!")
        self.evidence = self.register()

    def test_basic_custody_event_creation(self):
        """A valid transfer is saved and gets a block."""
        response = self.client.post(reverse("custody_add"), {
            "evidence": self.evidence.evidence_id, "action_type": "TRANSFERRED", "handler_name": "Officer",
            "from_party": "Alice", "to_party": "Bob", "remarks": "Moved to lab"})
        self.assertRedirects(response, reverse("custody_history", args=[self.evidence.evidence_id]))
        event = CustodyEvent.objects.get(action_type="TRANSFERRED")
        self.assertEqual(event.block_record.block_index, 2)
        self.assertEqual(event.evidence_hash, self.evidence.sha256_hash)

    def test_invalid_transfer_shows_error_and_saves_nothing(self):
        """A transfer with no receiver is rejected by the form."""
        response = self.client.post(reverse("custody_add"), {
            "evidence": self.evidence.evidence_id, "action_type": "TRANSFERRED", "handler_name": "Officer",
            "from_party": "Alice", "to_party": "", "remarks": "Moved"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "needs both")
        self.assertEqual(CustodyEvent.objects.count(), 1)

    def test_all_pages_render(self):
        """Every main page returns HTTP 200 for a logged-in user."""
        for name, args in [("dashboard", []), ("case_list", []), ("case_create", []), ("case_detail", [self.case.case_id]),
                           ("evidence_list", []), ("evidence_register", []), ("evidence_detail", [self.evidence.evidence_id]),
                           ("custody_history", [self.evidence.evidence_id]), ("custody_add", []), ("ledger", []),
                           ("tamper_demo", []), ("verify", []), ("report_home", [])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)

    def test_search_filters(self):
        """Evidence and case search work."""
        self.assertContains(self.client.get(reverse("evidence_list"), {"q": "EV-0001"}), "EV-0001")
        self.assertNotContains(self.client.get(reverse("evidence_list"), {"q": "EV-9999"}), "sample.txt")
        self.assertContains(self.client.get(reverse("case_list"), {"q": "CASE-0001"}), "Test case")
