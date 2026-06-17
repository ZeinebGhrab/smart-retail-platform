# ============================================================
# models.py — Modèle FCMToken (Firebase Cloud Messaging)
# backend/django_api/history/models.py
# ============================================================

from django.db import models


class FCMToken(models.Model):
    """
    Stocke les tokens FCM des appareils clients pour les notifications push
    """
    token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.token[:30]

    class Meta:
        verbose_name = "FCM Token"
        verbose_name_plural = "FCM Tokens"