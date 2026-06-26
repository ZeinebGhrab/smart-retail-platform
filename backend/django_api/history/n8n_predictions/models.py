# ============================================================
# n8n_predictions/models.py
# Modèles pour les notifications et prédictions reçues de N8N
# ============================================================

from django.db import models
from django.utils import timezone


class FCMToken(models.Model):
    """
    Firebase Cloud Messaging Token.
    Stocke les tokens FCM des appareils clients pour les notifications push.
    """
    token = models.CharField(max_length=255, unique=True, help_text="Token FCM unique de l'appareil")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    device_info = models.CharField(max_length=255, blank=True, help_text="Infos sur l'appareil (OS, version)")
    is_active = models.BooleanField(default=True, help_text="Token actif ou révoqué")

    class Meta:
        verbose_name = "Token FCM"
        verbose_name_plural = "Tokens FCM"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.token[:30]}... ({self.get_device_type()})"

    def get_device_type(self):
        """Extrait le type d'appareil des infos"""
        if not self.device_info:
            return "Unknown"
        return self.device_info.split('-')[0] if '-' in self.device_info else self.device_info


class PredictionNotification(models.Model):
    """
    Notification de prédiction reçue de N8N.
    Stocke les prédictions d'affluence, profils de visiteurs et autres rapports IA.
    
    Types de notifications :
    - 'prediction' : Prédiction d'affluence
    - 'report' : Rapport analytique
    - 'alert' : Alerte système
    - 'custom' : Notification personnalisée
    """
    
    TYPE_CHOICES = [
        ('prediction', "Prédiction d'affluence"),
        ('report', 'Rapport analytique'),
        ('alert', 'Alerte système'),
        ('custom', 'Notification personnalisée'),
    ]
    
    AFFLUENCE_LEVEL_CHOICES = [
        ('low', 'Faible'),
        ('medium', 'Moyen'),
        ('high', 'Élevé'),
        ('very_high', 'Très élevé'),
    ]
    
    # Identifiants
    notification_uuid = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="UUID unique de la notification N8N"
    )
    
    # Contenu principal
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        default='prediction',
        help_text="Type de notification"
    )
    title = models.CharField(max_length=255, help_text="Titre de la notification")
    message = models.TextField(help_text="Corps du message/texte principal")
    
    # Données de prédiction
    date = models.DateField(help_text="Date concernée par la prédiction")
    visiteurs_prevus = models.IntegerField(
        default=0,
        help_text="Nombre de visiteurs prévus"
    )
    profil_dominant = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Profil dominant de visiteurs (ex: 'Femmes 25-35')"
    )
    niveau_affluence = models.CharField(
        max_length=50,
        choices=AFFLUENCE_LEVEL_CHOICES,
        default='medium',
        help_text="Niveau d'affluence prévu"
    )
    heure_pointe = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Heure de pointe estimée (ex: '14h30')"
    )
    
    # Metadata du modèle
    model = models.CharField(
        max_length=255,
        default='llama3.2:3b-instruct-q4_K_M',
        help_text="Modèle LLM utilisé pour générer la prédiction"
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Score de confiance de la prédiction (0-1)"
    )
    
    # Statut et traçabilité
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Marqué comme lue"
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp de création de la notification"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp d'envoi push (si envoyé)"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp de première lecture"
    )
    
    # Métadonnées additionnelles
    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text="Tags séparés par virgule (ex: 'urgent,affluence')"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Données JSON supplémentaires"
    )

    class Meta:
        verbose_name = "Notification de prédiction"
        verbose_name_plural = "Notifications de prédictions"
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['date', '-generated_at']),
            models.Index(fields=['is_read', '-generated_at']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"[{self.date}] {self.title} - {self.get_type_display()}"

    def mark_as_read(self):
        """Marque la notification comme lue"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    def get_tags_list(self):
        """Retourne la liste des tags"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',')]

    def get_confidence_percentage(self):
        """Retourne le score de confiance en pourcentage"""
        return round(self.confidence_score * 100, 2) if self.confidence_score else None


class PushNotificationLog(models.Model):
    """
    Historique des notifications push envoyées via FCM.
    Permet de suivre l'envoi, les erreurs et les confirmations.
    """
    
    STATUS_CHOICES = [
        ('queued', "En file d'attente"),
        ('sent', 'Envoyée'),
        ('failed', 'Échouée'),
        ('bounced', 'Rejetée'),
    ]
    
    notification = models.ForeignKey(
        PredictionNotification,
        on_delete=models.CASCADE,
        related_name='push_logs',
        null=True,
        blank=True
    )
    
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True, help_text="Données custom pour la notification")
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='queued'
    )
    
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_count = models.IntegerField(default=0, help_text="Nombre d'appareils ayant reçu l'alerte")
    error_count = models.IntegerField(default=0, help_text="Nombre d'erreurs lors de l'envoi")
    errors = models.JSONField(default=list, blank=True, help_text="Liste des erreurs d'envoi")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Journal d'envoi FCM"
        verbose_name_plural = "Journaux d'envoi FCM"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.get_status_display()} ({self.sent_count} sent, {self.error_count} failed)"

    @property
    def success_rate(self):
        """Calcule le taux de succès d'envoi"""
        total = self.sent_count + self.error_count
        if total == 0:
            return 0
        return round((self.sent_count / total) * 100, 2)