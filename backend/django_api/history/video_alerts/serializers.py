# ============================================================
# video_alerts/serializers.py
# Sérialiseurs pour les alertes vidéo
# ============================================================

from rest_framework import serializers
from .models import VideoTheftAlert, AlertSpace


class AlertSpaceSerializer(serializers.ModelSerializer):
    """Sérialiseur pour un espace de surveillance"""
    
    class Meta:
        model = AlertSpace
        fields = [
            'id',
            'name',
            'code',
            'city',
            'address',
            'country',
            'organization_id',
        ]
        read_only_fields = ['id']


class VideoTheftAlertListSerializer(serializers.ModelSerializer):
    """Sérialiseur liste (aperçu) des alertes vidéo"""
    
    space_name = serializers.CharField(source='space.name', read_only=True)
    probability_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoTheftAlert
        fields = [
            'id',
            'code',
            'status',
            'probability',
            'probability_percentage',
            'recording_date',
            'create_date',
            'space_id',
            'space_name',
            'qualification',
            'nb_alerts',
        ]
        read_only_fields = [
            'id',
            'create_date',
        ]
    
    def get_probability_percentage(self, obj):
        return obj.get_probability_percentage()


class VideoTheftAlertDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur détaillé des alertes vidéo (avec tous les champs)"""
    
    space = AlertSpaceSerializer(read_only=True)
    space_id = serializers.IntegerField(write_only=True)
    probability_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoTheftAlert
        fields = [
            'id',
            'path',
            'code',
            'status',
            'probability',
            'probability_percentage',
            'recording_date',
            'create_date',
            'camera_id',
            'space_id',
            'space',
            'qualification',
            'sub_status',
            'nb_alerts',
            'reviewer',
            'reviewed_at',
            'notes',
        ]
        read_only_fields = [
            'id',
            'path',
            'code',
            'camera_id',
            'recording_date',
            'create_date',
        ]
    
    def get_probability_percentage(self, obj):
        return obj.get_probability_percentage()


class VideoQualificationSerializer(serializers.Serializer):
    """Sérialiseur pour la qualification d'une alerte vidéo"""
    
    status = serializers.ChoiceField(
        choices=['PENDING', 'APPROVED', 'REJECTED'],
        required=False,
        help_text="Nouveau statut de l'alerte"
    )
    qualification = serializers.ChoiceField(
        choices=['vol', 'suspicious', 'false_alarm'],
        required=False,
        help_text="Qualification manuelle"
    )
    reviewer = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Nom du relecteur"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Notes supplémentaires"
    )
    
    def validate(self, data):
        """Validation personnalisée"""
        if not data:
            raise serializers.ValidationError(
                "Au moins un champ doit être fourni (status, qualification, notes, reviewer)"
            )
        return data