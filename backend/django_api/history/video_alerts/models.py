# ============================================================
# video_alerts/models.py
# Modèles pour la détection des vols (alertes vidéo)
# ============================================================

from django.db import models


class AlertSpace(models.Model):
    """
    Représente un espace/magasin auquel est associée une caméra.
    Lié aux tables existantes 'notifications_space' de la BD MySQL.
    """
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    organization_id = models.BigIntegerField()

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
    Lié aux tables existantes 'notifications_video' de la BD MySQL.
    
    Statuts possibles :
    - PENDING : en attente de qualification
    - APPROVED : Vol/activité suspecte confirmée
    - REJECTED : Fausse alerte
    
    Qualifications possibles :
    - null : Non qualifiée
    - 'vol' : Vol confirmé
    - 'suspicious' : Comportement suspect
    - 'false_alarm' : Fausse alerte
    """
    # Choix de statut
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvé - Vol confirmé'),
        ('REJECTED', 'Rejeté - Fausse alerte'),
    ]
    
    QUALIFICATION_CHOICES = [
        ('vol', 'Vol confirmé'),
        ('suspicious', 'Comportement suspect'),
        ('false_alarm', 'Fausse alerte'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    path = models.CharField(max_length=255, help_text="Chemin de la vidéo enregistrée")
    code = models.CharField(max_length=100, help_text="Code/ID de la caméra")
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    probability = models.FloatField(
        null=True,
        blank=True,
        help_text="Probabilité de détection (0-1)"
    )
    recording_date = models.DateTimeField(help_text="Date/heure de l'enregistrement")
    create_date = models.DateTimeField(help_text="Date/heure de création de l'alerte")
    camera_id = models.BigIntegerField()
    
    space = models.ForeignKey(
        AlertSpace,
        on_delete=models.DO_NOTHING,
        db_column='space_id',
        related_name='video_alerts'
    )
    
    qualification = models.CharField(
        max_length=50,
        choices=QUALIFICATION_CHOICES,
        null=True,
        blank=True,
        help_text="Qualification manuelle de l'alerte"
    )
    sub_status = models.CharField(max_length=30, default='', blank=True)
    nb_alerts = models.IntegerField(null=True, blank=True, help_text="Nombre d'alertes dans cette vidéo")
    
    # Champs additionnels de tracking
    reviewer = models.CharField(max_length=100, null=True, blank=True, help_text="Personne ayant qualifié")
    reviewed_at = models.DateTimeField(null=True, blank=True, help_text="Date de qualification")
    notes = models.TextField(blank=True, help_text="Notes supplémentaires")

    class Meta:
        managed = False
        db_table = 'notifications_video'
        verbose_name = "Alerte vidéo"
        verbose_name_plural = "Alertes vidéo"
        ordering = ['-recording_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['space_id']),
            models.Index(fields=['recording_date']),
        ]

    def __str__(self):
        return f"Alerte {self.code} [{self.status}] - {self.recording_date}"

    def is_approved(self):
        """Vérifie si l'alerte est approuvée"""
        return self.status == 'APPROVED'

    def get_probability_percentage(self):
        """Retourne la probabilité en pourcentage"""
        return round(self.probability * 100, 2) if self.probability else None