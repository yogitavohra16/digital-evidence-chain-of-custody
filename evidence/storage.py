"""storage.py - where uploaded evidence files are kept on disk.

SECURITY: evidence is stored in a PRIVATE folder (settings.EVIDENCE_STORAGE_ROOT).
The storage has NO public URL and the project has NO URL route that serves the
folder, so evidence files can never be fetched by typing an address in a browser.

This is a simple local folder - fine for a demonstration, but NOT a secure forensic
evidence vault (no encryption, no write-once media, no off-site copy).
"""
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateEvidenceStorage(FileSystemStorage):
    """A FileSystemStorage that always uses settings.EVIDENCE_STORAGE_ROOT.

    Why a small class: reading the setting on every use (instead of once at start-up)
    lets the automated tests point the storage at a temporary folder, so tests never
    write into the real evidence folder.
    """

    @property
    def base_location(self):
        """The folder where files are stored."""
        return str(settings.EVIDENCE_STORAGE_ROOT)

    @property
    def location(self):
        """Absolute version of the storage folder."""
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        """None means 'this storage has no public web address' (by design)."""
        return None
