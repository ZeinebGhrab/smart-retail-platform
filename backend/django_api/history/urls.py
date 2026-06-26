# ============================================================
# history/urls.py — Routes principales de l'app history
# ============================================================

from django.urls import path, include

from .chat_view import chat
from .video_alerts import views as va_views
from .n8n_predictions import views as n8n_views

app_name = 'history'

urlpatterns = [

    # ── Chat IA — RAG ──────────────────────────────────────
    path('chat/', chat, name='chat'),

    # ── Visiteurs / Analytics ──────────────────────────────
    path('history/', include('history.visitors.urls', namespace='visitors')),

    # ── Alertes vidéo ──────────────────────────────────────
    path('video-alerts/', include('history.video_alerts.urls', namespace='video-alerts')),

    # Alias anciennes URLs frontend (/api/videos/...)
    path('videos/all/',                                va_views.list_all_video_alerts,  name='videos-all'),
    path('videos/spaces/',                             va_views.list_alert_spaces,      name='videos-spaces'),
    path('videos/space/<int:space_id>/',               va_views.videos_by_space,        name='videos-by-space'),
    path('videos/organisation/<int:organisation_id>/', va_views.videos_by_organization, name='videos-by-org'),
    path('videos/<int:video_id>/qualify/',             va_views.qualify_video_alert,    name='videos-qualify'),

    # ── Prédictions N8N ────────────────────────────────────
    path('predictions/', include('history.n8n_predictions.urls', namespace='predictions')),

    # Alias ancienne URL frontend (/api/prediction/stream/)
    path('prediction/stream/', n8n_views.prediction_stream, name='prediction-stream'),

]