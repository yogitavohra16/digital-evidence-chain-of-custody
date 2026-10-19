"""forensic_tags.py - small helpers used inside templates.

Template filters let a template change how a value is displayed, for example
{{ evidence.sha256_hash|short_hash }}.
"""
from django import template

register = template.Library()


@register.filter
def short_hash(value, length=12):
    """Shorten a long hash for tables: first N characters followed by an ellipsis.

    The full hash is always available in a tooltip / details page; this is only for
    saving horizontal space.
    """
    value = str(value or "")
    length = int(length)
    return value if len(value) <= length else f"{value[:length]}\u2026"


@register.filter
def status_class(value):
    """Map a status / result code to a CSS class for a coloured badge.

    Green, amber and red are used ONLY for meaningful states.
    """
    mapping = {
        # evidence status
        "REGISTERED": "info", "TRANSFERRED": "info", "IN_ANALYSIS": "warning",
        "ANALYSIS_COMPLETED": "success", "RETURNED": "neutral", "ARCHIVED": "neutral",
        # case status
        "OPEN": "info", "UNDER_REVIEW": "warning", "CLOSED": "neutral",
        # verification result
        "MATCH": "success", "MISMATCH": "danger", "FILE_MISSING": "danger", "ERROR": "warning",
    }
    return mapping.get(str(value), "neutral")


@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    """Build a '?page=N' link that keeps the current search / filter parameters."""
    params = context["request"].GET.copy()
    params["page"] = page_number
    return "?" + params.urlencode()
