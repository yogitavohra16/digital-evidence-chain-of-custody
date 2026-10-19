"""models.py - the verification history table.

Every time someone verifies an evidence file we append one row here. Rows are never
edited: the history shows what was checked, when, by whom, and the outcome. The
ORIGINAL hash on the Evidence row is never changed by verification.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from evidence.models import Evidence


class VerificationRecord(models.Model):
    """One integrity-verification attempt for one evidence item."""

    class Result(models.TextChoices):
        MATCH = "MATCH", "Integrity verified"
        MISMATCH = "MISMATCH", "Integrity mismatch"
        FILE_MISSING = "FILE_MISSING", "File missing"
        ERROR = "ERROR", "Verification error"

    evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="verification_records")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="verifications_run"
    )
    verified_at = models.DateTimeField(default=timezone.now)
    # A copy of the original hash at the time of verification (for the history).
    original_hash = models.CharField(max_length=64)
    # Empty when the hash could not be calculated (missing file / read error).
    current_hash = models.CharField(max_length=64, blank=True)
    result = models.CharField(max_length=20, choices=Result.choices)
    error_details = models.TextField(blank=True)

    class Meta:
        ordering = ["-verified_at", "-id"]

    def __str__(self):
        return f"{self.evidence.evidence_id}: {self.get_result_display()}"
