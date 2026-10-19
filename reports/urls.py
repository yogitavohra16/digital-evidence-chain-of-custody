"""urls.py - URL routes for the reports app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.report_home, name="report_home"),
    path("generate/", views.generate_report, name="generate_report"),
]
