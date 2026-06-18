# ============================================================
# models.py — Modèles FCMToken + NotificationLog
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


class NotificationLog(models.Model):
    """
    Historique de toutes les notifications push envoyées via FCM.
    Chaque entrée correspond à un appel POST /api/send-fcm/.
    """
    title        = models.CharField(max_length=255)
    body         = models.TextField()
    data         = models.JSONField(default=dict, blank=True)
    sent_at      = models.DateTimeField(auto_now_add=True)
    sent_count   = models.IntegerField(default=0)   # nombre d'appareils atteints
    error_count  = models.IntegerField(default=0)   # nombre d'erreurs FCM
    errors       = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"[{self.sent_at:%Y-%m-%d %H:%M}] {self.title} — {self.sent_count} envoyé(s)"

    class Meta:
        ordering = ['-sent_at']
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"