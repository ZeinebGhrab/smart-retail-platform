# ============================================================
# accounts/admin.py — Interface admin pour le modèle User personnalisé
# ============================================================

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "first_name", "last_name", "store_name", "is_staff", "is_active", "date_joined"]
    search_fields = ["email", "first_name", "last_name", "store_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name", "store_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "store_name", "first_name", "last_name", "password1", "password2"),
        }),
    )