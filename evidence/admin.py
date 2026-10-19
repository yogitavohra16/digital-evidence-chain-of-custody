"""admin.py - the Django admin site (for the project owner only).

Evidence, custody events and verification records are shown READ-ONLY so the admin
site is not an easy way to rewrite the history. (A person with direct database or
file-system access could still change data; the blockchain validation exists to make
that visible.)
"""
from django.contrib import admin

from .models import Case, CustodyEvent, Evidence


class ReadOnlyAdmin(admin.ModelAdmin):
    """Base admin class: view only, no add / change / delete."""

    def has_add_permission(self, request):
        """Adding must go through the application so a block is created."""
        return False

    def has_change_permission(self, request, obj=None):
        """History must not be edited."""
        return False

    def has_delete_permission(self, request, obj=None):
        """History must not be deleted."""
        return False


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    """Cases may be browsed and edited (title, status)."""

    list_display = ("case_id", "title", "status", "created_by", "created_at")
    search_fields = ("case_id", "title")
    readonly_fields = ("case_id", "created_by", "created_at")

    def has_delete_permission(self, request, obj=None):
        """Cases are never deleted from the admin."""
        return False


@admin.register(Evidence)
class EvidenceAdmin(ReadOnlyAdmin):
    """Evidence is read-only: the original hash must not be edited."""

    list_display = ("evidence_id", "case", "original_filename", "status", "registered_at")
    search_fields = ("evidence_id", "original_filename")


@admin.register(CustodyEvent)
class CustodyEventAdmin(ReadOnlyAdmin):
    """Custody events are read-only (append-oriented history)."""

    list_display = ("evidence", "action_type", "handler_name", "timestamp")
    search_fields = ("evidence__evidence_id", "handler_name")
