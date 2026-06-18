# ============================================================
# models.py — Modèles FCMToken + NotificationLog + Notification
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


# ← NOUVEAU: Modèle pour les notifications N8N (prédictions)
class Notification(models.Model):
    """
    Historique des notifications de prédictions reçues de N8N.
    Stocke les prédictions d'affluence et autres rapports IA.
    """
    date               = models.DateField()
    generated_at       = models.DateTimeField(auto_now_add=True)
    message            = models.TextField()  # Le message texte de la prédiction
    visiteurs_prevus   = models.IntegerField(default=0)
    profil_dominant    = models.CharField(max_length=255, default='')
    niveau_affluence   = models.CharField(max_length=100, default='')
    heure_pointe       = models.CharField(max_length=50, default='')
    model              = models.CharField(max_length=255, default='llama3.2:3b-instruct-q4_K_M')
    type               = models.CharField(max_length=50, default='prediction')
    # champ pour marquer comme lue
    is_read            = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.date}] Prédiction - {self.niveau_affluence}"

    class Meta:
        ordering = ['-generated_at']  # Plus récent en premier
        verbose_name = "Notification de prédiction"
        verbose_name_plural = "Notifications de prédictions"