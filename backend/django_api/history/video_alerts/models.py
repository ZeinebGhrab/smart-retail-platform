# ============================================================
# video_alerts/models.py
# Modèles pour la détection des vols (alertes vidéo)
# ============================================================

from django.db import models


class AlertSpace(models.Model):
    """
    Représente un espace/magasin.
    Table réelle : notifications_space
    """
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    create_date = models.DateTimeField()
    update_date = models.DateTimeField()
    address = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    organization_id = models.BigIntegerField()
    telegram_chat_id = models.CharField(max_length=100)
    language = models.CharField(max_length=2)
    token_web_connector = models.CharField(max_length=255, null=True, blank=True)
    url_web_connector = models.CharField(max_length=255, null=True, blank=True)
    send_telegram_message = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'notifications_space'
        verbose_name = "Espace de surveillance"
        verbose_name_plural = "Espaces de surveillance"

    def __str__(self):
        return f"{self.name} ({self.code})"


class VideoTheftAlert(models.Model):
    """
    Alerte vidéo pour détection de vol/comportement suspect.
    Table réelle : notifications_video

    Statuts possibles :
    - PENDING : en attente de qualification
    - APPROVED : Vol/activité suspecte confirmée
    - REJECTED : Fausse alerte

    Qualifications possibles (champ qualification) :
    - null : Non qualifiée
    - 'vol' : Vol confirmé
    - 'suspicious' : Comportement suspect
    - 'false_alarm' : Fausse alerte
    """
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvé - Vol confirmé'),
        ('REJECTED', 'Rejeté'),
    ]

    QUALIFICATION_CHOICES = [
        ('vol', 'Vol confirmé'),
        ('suspicious', 'Comportement suspect'),
        ('false_alarm', 'Fausse alerte'),
    ]

    id = models.BigAutoField(primary_key=True)
    path = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    recording_date = models.DateTimeField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    send_date = models.DateField(null=True, blank=True)
    create_date = models.DateTimeField()
    update_date = models.DateTimeField()
    camera_id = models.BigIntegerField()
    modified_by_id = models.CharField(max_length=32, null=True, blank=True)
    send_notified = models.BooleanField(default=False)
    sub_status = models.CharField(max_length=30, default='', blank=True)
    original_path = models.CharField(max_length=255, null=True, blank=True)
    probability = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    detected_by_model = models.BooleanField(null=True, blank=True)
    nb_alerts = models.IntegerField(null=True, blank=True)
    assigned_to = models.CharField(max_length=254, null=True, blank=True)
    approval_result = models.CharField(max_length=2, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    modified_by_qualification_id = models.CharField(max_length=32, null=True, blank=True)
    qualification = models.CharField(
        max_length=50,
        choices=QUALIFICATION_CHOICES,
        null=True,
        blank=True,
    )
    qualification_update_date = models.DateTimeField(null=True, blank=True)
    space = models.ForeignKey(
        AlertSpace,
        on_delete=models.DO_NOTHING,
        db_column='space_id',
        related_name='video_alerts'
    )

    class Meta:
        managed = False
        db_table = 'notifications_video'
        verbose_name = "Alerte vidéo"
        verbose_name_plural = "Alertes vidéo"
        ordering = ['-recording_date']

    def __str__(self):
        return f"Alerte {self.code} [{self.status}] - {self.recording_date}"

    def is_approved(self):
        return self.status == 'APPROVED'

    def get_probability_percentage(self):
        return round(self.probability * 100, 2) if self.probability else None