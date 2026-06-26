# ============================================================
# n8n_predictions/apps.py
# Configuration de l'app n8n_predictions
# ============================================================

from django.apps import AppConfig


class N8nPredictionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'history.n8n_predictions'
    verbose_name = 'Prédictions N8N'