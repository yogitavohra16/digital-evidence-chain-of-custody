"""admin.py - read-only view of the blockchain table in the admin site."""
from django.contrib import admin

from .models import BlockRecord


@admin.register(BlockRecord)
class BlockRecordAdmin(admin.ModelAdmin):
    """Blocks can be viewed but never added, edited or deleted from the admin."""

    list_display = ("block_index", "current_hash", "previous_hash", "custody_event")

    def has_add_permission(self, request):
        """Blocks are created only by the application."""
        return False

    def has_change_permission(self, request, obj=None):
        """Blocks must not be edited."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Blocks must not be deleted."""
        return False
