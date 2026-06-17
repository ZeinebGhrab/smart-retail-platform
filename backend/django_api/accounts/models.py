# ============================================================
# accounts/models.py — Modèle utilisateur personnalisé
#
# Authentification par e-mail 
# + nom du commerce, saisi à l'inscription.
#
# Champs alignés sur le formulaire Register.tsx (frontend) :
#   firstName, lastName, storeName, email, password
# ============================================================

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """Utilisateur ShopAnalytics / Anavid Store 360 (un compte = un commerce)."""

    username = None  # désactivé : on utilise l'e-mail comme identifiant
    email = models.EmailField("adresse e-mail", unique=True)
    store_name = models.CharField("nom du commerce", max_length=150, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # le formulaire d'inscription gère firstName/lastName/storeName

    objects = UserManager()

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.email} — {self.store_name}" if self.store_name else self.email