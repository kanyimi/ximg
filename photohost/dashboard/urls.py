from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("login/", views.login_view, name="login"),

    path("2fa/", views.twofa_page, name="twofa_page"),
    path("partials/2fa/", views.twofa_partial, name="twofa_partial"),
    path("2fa/disable/", views.twofa_disable, name="twofa_disable"),
    path("2fa/verify/", views.twofa_verify, name="twofa_verify"),


    path("", views.shell, name="shell"),

    # full "pages" (still work if you open directly)
    path("stats/", views.stats_page, name="stats"),
    path("sections/", views.sections_page, name="sections"),
    path("files/", views.files_page, name="files"),
    path("secret-notes/", views.secret_notes_page, name="secret_notes"),  # ✅ add
    path("api/secret-notes/", views.api_secret_notes, name="api_secret_notes"),
    # partials (AJAX loaded into shell)
    path("partials/stats/", views.stats_partial, name="stats_partial"),
    path("partials/sections/", views.sections_partial, name="sections_partial"),
    path("partials/files/", views.files_partial, name="files_partial"),
    path("partials/secret-notes/", views.secret_notes_partial, name="secret_notes_partial"),  # ✅ add

    path("logout/", views.logout_view, name="logout"),
]
