"""urls.py - URL routes for the blockchain app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.ledger, name="ledger"),
    path("tamper-demo/", views.tamper_demo, name="tamper_demo"),
]
