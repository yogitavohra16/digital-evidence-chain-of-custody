"""admin.py - read-only view of verification history."""
from django.contrib import admin

from .models import VerificationRecord


@admin.register(VerificationRecord)
class VerificationRecordAdmin(admin.ModelAdmin):
    """Verification history is view-only."""

    list_display = ("evidence", "result", "verified_by", "verified_at")

    def has_add_permission(self, request):
        """Records are created by running a verification."""
        return False

    def has_change_permission(self, request, obj=None):
        """History must not be edited."""
        return False

    def has_delete_permission(self, request, obj=None):
        """History must not be deleted."""
        return False
