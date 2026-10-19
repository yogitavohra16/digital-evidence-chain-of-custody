"""App configuration for the reports app."""
from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Registers the 'reports' app (PDF report generation)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "reports"
    verbose_name = "Reports"
