# ============================================================
# video_alerts/apps.py
# Configuration de l'app video_alerts
# ============================================================

from django.apps import AppConfig


class VideoAlertsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'history.video_alerts'
    verbose_name = 'Alertes Vidéo'