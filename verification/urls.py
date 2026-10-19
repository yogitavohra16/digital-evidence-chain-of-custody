"""urls.py - URL routes for the verification app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.verify_view, name="verify"),
]
