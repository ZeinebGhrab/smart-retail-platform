# ============================================================
# serializers.py — Sérializers DRF
# backend/django_api/history/serializers.py
# ============================================================

from rest_framework import serializers
from .models import Notification


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