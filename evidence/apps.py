"""App configuration for the evidence app."""
from django.apps import AppConfig


class EvidenceConfig(AppConfig):
    """Registers the 'evidence' app (cases, evidence items and custody events)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "evidence"
    verbose_name = "Evidence and Custody"
