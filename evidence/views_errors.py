"""views_errors.py - friendly 404 / 500 pages (used when DEBUG is False)."""
from django.shortcuts import render


def not_found(request, exception=None):
    """Show a styled 'page not found' page."""
    return render(request, "404.html", status=404)


def server_error(request):
    """Show a styled 'something went wrong' page."""
    return render(request, "500.html", status=500)
