# ============================================================
# n8n_predictions/serializers.py
# Sérialiseurs pour les prédictions N8N
# ============================================================

from rest_framework import serializers
from .models import PredictionNotification, FCMToken, PushNotificationLog


class FCMTokenSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les tokens FCM"""
    
    device_type = serializers.CharField(source='get_device_type', read_only=True)
    
    class Meta:
        model = FCMToken
        fields = [
            'id',
            'token',
            'device_info',
            'device_type',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FCMTokenCreateSerializer(serializers.Serializer):
    """Sérialiseur pour la création d'un token FCM"""
    
    token = serializers.CharField(help_text="Token FCM de l'appareil")
    device_info = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Infos sur l'appareil (optionnel)"
    )


class PredictionNotificationListSerializer(serializers.ModelSerializer):
    """Sérialiseur liste des prédictions (aperçu)"""
    
    confidence_percentage = serializers.SerializerMethodField()
    tags_list = serializers.SerializerMethodField()
    
    class Meta:
        model = PredictionNotification
        fields = [
            'id',
            'notification_uuid',
            'type',
            'title',
            'date',
            'visiteurs_prevus',
            'niveau_affluence',
            'is_read',
            'generated_at',
            'confidence_percentage',
            'tags_list',
        ]
        read_only_fields = ['id', 'notification_uuid', 'generated_at']
    
    def get_confidence_percentage(self, obj):
        return obj.get_confidence_percentage()
    
    def get_tags_list(self, obj):
        return obj.get_tags_list()


class PredictionNotificationDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur détaillé des prédictions"""
    
    confidence_percentage = serializers.SerializerMethodField()
    tags_list = serializers.SerializerMethodField()
    
    class Meta:
        model = PredictionNotification
        fields = [
            'id',
            'notification_uuid',
            'type',
            'title',
            'message',
            'date',
            'visiteurs_prevus',
            'profil_dominant',
            'niveau_affluence',
            'heure_pointe',
            'model',
            'confidence_score',
            'confidence_percentage',
            'is_read',
            'generated_at',
            'sent_at',
            'read_at',
            'tags',
            'tags_list',
            'metadata',
        ]
        read_only_fields = [
            'id',
            'notification_uuid',
            'generated_at',
            'sent_at',
            'read_at',
        ]
    
    def get_confidence_percentage(self, obj):
        return obj.get_confidence_percentage()
    
    def get_tags_list(self, obj):
        return obj.get_tags_list()


class PredictionNotificationCreateSerializer(serializers.Serializer):
    """Sérialiseur pour la création d'une notification N8N"""
    
    type = serializers.ChoiceField(
        choices=['prediction', 'report', 'alert', 'custom'],
        default='prediction'
    )
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    date = serializers.DateField()
    
    visiteurs_prevus = serializers.IntegerField(required=False, default=0)
    profil_dominant = serializers.CharField(required=False, allow_blank=True, default='')
    niveau_affluence = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'very_high'],
        required=False,
        default='medium'
    )
    heure_pointe = serializers.CharField(required=False, allow_blank=True, default='')
    
    model = serializers.CharField(required=False, default='llama3.2:3b-instruct-q4_K_M')
    confidence_score = serializers.FloatField(required=False, allow_null=True)
    
    tags = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)
    
    notification_uuid = serializers.CharField(required=False, help_text="UUID unique de N8N (optionnel)")


class PredictionNotificationUpdateSerializer(serializers.Serializer):
    """Sérialiseur pour la mise à jour d'une notification"""
    
    is_read = serializers.BooleanField(required=False)
    tags = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class PushNotificationLogSerializer(serializers.ModelSerializer):
    """Sérialiseur pour l'historique d'envoi FCM"""
    
    success_rate = serializers.FloatField(read_only=True)
    notification_title = serializers.CharField(
        source='notification.title',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = PushNotificationLog
        fields = [
            'id',
            'notification',
            'notification_title',
            'title',
            'body',
            'status',
            'sent_at',
            'sent_count',
            'error_count',
            'success_rate',
            'errors',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'sent_at',
            'created_at',
            'updated_at',
        ]


class NotificationStatsSerializer(serializers.Serializer):
    """Sérialiseur pour les statistiques de notifications"""
    
    total = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    by_type = serializers.DictField()
    by_affluence = serializers.DictField()
    recent_avg_confidence = serializers.FloatField()