# ============================================================
# accounts/models.py — Modèle utilisateur personnalisé
#
# Authentification par e-mail 
# + nom du commerce, saisi à l'inscription.
#
# Champs alignés sur le formulaire Register.tsx (frontend) :
#   firstName, lastName, storeName, email, password
# ============================================================

import random
import string
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

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

def _otp_code():
    """Génère un code OTP à 6 chiffres."""
    return ''.join(random.choices(string.digits, k=6))


class PasswordResetToken(models.Model):
    """
    Token OTP à usage unique pour la réinitialisation de mot de passe.
    Expire après 15 minutes. Invalidé après utilisation.
    Pas d'e-mail requis : le code est affiché dans la réponse API
    (mode dev/demo). En prod, remplacer par un envoi SMTP dans request_password_reset.
    """

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reset_tokens")
    code       = models.CharField(max_length=6, default=_otp_code)
    created_at = models.DateTimeField(auto_now_add=True)
    used       = models.BooleanField(default=False)

    OTP_LIFETIME = timedelta(minutes=15)

    class Meta:
        verbose_name = "Token de réinitialisation"
        ordering = ["-created_at"]

    def is_valid(self) -> bool:
        """Vrai si le token n'a pas été utilisé et n'est pas expiré."""
        return not self.used and (timezone.now() - self.created_at) < self.OTP_LIFETIME

    def consume(self):
        """Marque le token comme utilisé."""
        self.used = True
        self.save(update_fields=["used"])

    def __str__(self):
        return f"OTP {self.code} — {self.user.email} ({'utilisé' if self.used else 'valide'})"