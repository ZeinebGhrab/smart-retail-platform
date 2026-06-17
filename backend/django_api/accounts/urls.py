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
]