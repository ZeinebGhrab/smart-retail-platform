# ============================================================
# accounts/urls.py — Routes /api/auth/...
# ============================================================

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("auth/register/", views.register, name="auth-register"),
    path("auth/login/",     views.login,    name="auth-login"),
    path("auth/refresh/",   TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me/",        views.me,       name="auth-me"),
    path("auth/logout/",    views.logout,   name="auth-logout"),

    # ── Mot de passe oublié (3 étapes) ──────────────────────
    path("auth/password-reset/request/", views.password_reset_request, name="auth-pw-reset-request"),
    path("auth/password-reset/verify/",  views.password_reset_verify,  name="auth-pw-reset-verify"),
    path("auth/password-reset/confirm/", views.password_reset_confirm, name="auth-pw-reset-confirm"),
]