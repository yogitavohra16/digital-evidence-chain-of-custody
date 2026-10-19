"""urls.py - the project's main address table.

Django starts here, matches the beginning of the address, and hands the rest to the
matching app's own urls.py with include().

NOTE: there is intentionally NO route serving the evidence storage folder, so
evidence files are not publicly reachable.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Django's built-in authentication views (we only supply the HTML template).
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html",
                                                redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),   # POST only (Django 5)
    path("blockchain/", include("blockchain.urls")),
    path("verification/", include("verification.urls")),
    path("reports/", include("reports.urls")),
    path("", include("evidence.urls")),
]

handler404 = "evidence.views_errors.not_found"
handler500 = "evidence.views_errors.server_error"
