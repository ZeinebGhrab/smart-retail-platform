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
            'language',
            'send_telegram_message',
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
            'sub_status',
            'probability',
            'probability_percentage',
            'recording_date',
            'create_date',
            'space_id',
            'space_name',
            'qualification',
            'nb_alerts',
            'assigned_to',
            'approval_result',
        ]
        read_only_fields = ['id', 'create_date']

    def get_probability_percentage(self, obj):
        return obj.get_probability_percentage()


class VideoTheftAlertDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur détaillé des alertes vidéo (tous les champs réels)"""

    space = AlertSpaceSerializer(read_only=True)
    space_id = serializers.IntegerField(write_only=True)
    probability_percentage = serializers.SerializerMethodField()

    class Meta:
        model = VideoTheftAlert
        fields = [
            'id',
            'path',
            'original_path',
            'code',
            'status',
            'sub_status',
            'probability',
            'probability_percentage',
            'recording_date',
            'send_date',
            'create_date',
            'update_date',
            'camera_id',
            'space_id',
            'space',
            'send_notified',
            'metadata',
            'detected_by_model',
            'nb_alerts',
            'assigned_to',
            'approval_result',
            'comment',
            'qualification',
            'qualification_update_date',
            'modified_by_id',
            'modified_by_qualification_id',
        ]
        read_only_fields = [
            'id',
            'path',
            'original_path',
            'code',
            'camera_id',
            'recording_date',
            'create_date',
            'update_date',
            'send_date',
            'send_notified',
            'metadata',
            'detected_by_model',
        ]

    def get_probability_percentage(self, obj):
        return obj.get_probability_percentage()


class VideoQualificationSerializer(serializers.Serializer):
    """Sérialiseur pour la qualification manuelle d'une alerte vidéo"""

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
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Commentaire / notes"
    )
    assigned_to = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text="Email du relecteur assigné"
    )
    approval_result = serializers.ChoiceField(
        choices=['TP', 'TN', 'FP', 'FN'],
        required=False,
        allow_null=True,
        help_text="Résultat d'approbation (TP/TN/FP/FN)"
    )

    def validate(self, data):
        if not data:
            raise serializers.ValidationError(
                "Au moins un champ doit être fourni."
            )
        return data