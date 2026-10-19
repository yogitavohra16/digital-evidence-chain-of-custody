"""helpers.py - shared setup code for the automated tests.

Tests run against a temporary SQLite database that Django creates and deletes
automatically, and evidence files are written to a temporary folder, so running the
tests never touches your real db.sqlite3 or your real evidence files.
"""
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from evidence.models import Case
from evidence.services import create_case, register_evidence


class EvidenceTestCase(TestCase):
    """Base class: temporary evidence folder + a test user + a test case."""

    @classmethod
    def setUpClass(cls):
        """Point evidence storage at a temporary folder for the whole test class."""
        cls._temp_folder = tempfile.mkdtemp(prefix="evidence_tests_")
        cls._override = override_settings(EVIDENCE_STORAGE_ROOT=Path(cls._temp_folder))
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        """Remove the temporary folder afterwards."""
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._temp_folder, ignore_errors=True)

    def setUp(self):
        """Create a user, log in, and create one case for each test."""
        self.user = get_user_model().objects.create_user("tester", password="Str0ng-Test-Pass!")
        self.case = create_case(title="Test case", description="", status=Case.Status.OPEN, user=self.user)

    def make_upload(self, content=b"sample evidence bytes", name="sample.txt"):
        """Build an in-memory uploaded file."""
        return SimpleUploadedFile(name, content)

    def register(self, content=b"sample evidence bytes", name="sample.txt"):
        """Register an evidence file through the real service. Returns the Evidence."""
        return register_evidence(
            case=self.case, uploaded_file=self.make_upload(content, name),
            notes="test notes", user=self.user, handler_name="Officer Test",
        )
