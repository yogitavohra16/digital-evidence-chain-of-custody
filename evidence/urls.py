"""urls.py - connects web addresses to view functions.

Each path() says: "when the browser asks for this address, call this view".
`name=` gives the route a short name so templates can write {% url 'name' %}
instead of hard-coding addresses.
"""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("cases/", views.case_list, name="case_list"),
    path("cases/new/", views.case_create, name="case_create"),
    path("cases/<str:case_id>/", views.case_detail, name="case_detail"),
    path("evidence/", views.evidence_list, name="evidence_list"),
    path("evidence/register/", views.evidence_register, name="evidence_register"),
    path("evidence/<str:evidence_id>/", views.evidence_detail, name="evidence_detail"),
    path("evidence/<str:evidence_id>/custody/", views.custody_history, name="custody_history"),
    path("custody/add/", views.custody_add, name="custody_add"),
]
