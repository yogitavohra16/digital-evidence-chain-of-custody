"""App configuration for the verification app."""
from django.apps import AppConfig


class VerificationConfig(AppConfig):
    """Registers the 'verification' app (evidence integrity checks)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "verification"
    verbose_name = "Evidence Verification"
