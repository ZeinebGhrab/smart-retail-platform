# ============================================================
# models.py — Modèles FCMToken + NotificationLog + Notification
# backend/django_api/history/models.py
# ============================================================

from django.db import models


class FCMToken(models.Model):
    """
    Stocke les tokens FCM des appareils clients pour les notifications push
    """
    token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.token[:30]

    class Meta:
        verbose_name = "FCM Token"
        verbose_name_plural = "FCM Tokens"


# Modèle pour les notifications N8N (prédictions)
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
        
class NotificationsSpace(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    organization_id = models.BigIntegerField()

    class Meta:
        managed = False  # table déjà existante dans MySQL
        db_table = 'notifications_space'

class NotificationsVideo(models.Model):
    id = models.BigAutoField(primary_key=True)
    path = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    status = models.CharField(max_length=30)
    probability = models.FloatField(null=True)
    recording_date = models.DateTimeField()
    create_date = models.DateTimeField()
    camera_id = models.BigIntegerField()
    space = models.ForeignKey(
        NotificationsSpace,
        on_delete=models.DO_NOTHING,
        db_column='space_id'
    )
    qualification = models.CharField(max_length=50, null=True)
    sub_status = models.CharField(max_length=30)
    nb_alerts = models.IntegerField(null=True)

    class Meta:
        managed = False
        db_table = 'notifications_video'