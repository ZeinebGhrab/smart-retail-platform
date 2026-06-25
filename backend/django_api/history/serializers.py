# ============================================================
# serializers.py — Sérializers DRF
# backend/django_api/history/serializers.py
# ============================================================

from rest_framework import serializers
from .models import Notification

from .models import NotificationsVideo, NotificationsSpace

class NotificationsSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationsSpace
        fields = ['id', 'name', 'code', 'city', 'organization_id']

class NotificationsVideoSerializer(serializers.ModelSerializer):
    space_name = serializers.CharField(source='space.name', read_only=True)
    space_code = serializers.CharField(source='space.code', read_only=True)
    msg = serializers.SerializerMethodField()

    class Meta:
        model = NotificationsVideo
        fields = [
            'id', 'path', 'code', 'status', 'probability',
            'recording_date', 'create_date', 'qualification',
            'sub_status', 'nb_alerts', 'space_id',
            'space_name', 'space_code', 'msg'
        ]

    def get_msg(self, obj):
        # Génère un message lisible selon le status
        messages = {
            'VA': 'Vol avéré',
            'VS': 'Vol suspect',
            'FA': 'Fausse alerte',
            'PE': 'En attente',
        }
        return messages.get(obj.status, obj.status)
class NotificationSerializer(serializers.ModelSerializer):
    """
    Sérializer pour les notifications de prédictions N8N
    """
    class Meta:
        model = Notification
        fields = [
            'id',
            'date',
            'generated_at',
            'message',
            'visiteurs_prevus',
            'profil_dominant',
            'niveau_affluence',
            'heure_pointe',
            'model',
            'type',
            'is_read',
        ]
        read_only_fields = ['id', 'generated_at']