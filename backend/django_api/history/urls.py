# ============================================================
# history/urls.py — Routes principales de l'app history
# ============================================================

from django.urls import path, include

from .video_alerts import views as va_views
from .n8n_predictions import views as n8n_views

app_name = 'history'

urlpatterns = [

    # ── Chat IA — RAG ──────────────────────────────────────
    path('', include('history.chatbot.urls', namespace='chatbot')),

    # ── Visiteurs / Analytics ──────────────────────────────
    path('history/', include('history.visitors.urls', namespace='visitors')),

    # ── Alertes vidéo ──────────────────────────────────────
    path('video-alerts/', include('history.video_alerts.urls', namespace='video-alerts')),

    # Alias anciennes URLs frontend (/api/videos/...)
    path('videos/all/',                                va_views.list_all_video_alerts,  name='videos-all'),
    path('videos/spaces/',                             va_views.list_alert_spaces,      name='videos-spaces'),
    path('videos/space/<int:space_id>/',               va_views.videos_by_space,        name='videos-by-space'),

    path('videos/organisation/<int:organization_id>/', va_views.videos_by_organization, name='videos-by-org'),
    path('videos/<int:video_id>/qualify/',             va_views.qualify_video_alert,    name='videos-qualify'),
    path('videos/<int:video_id>/',                     va_views.get_video_alert_detail, name='videos-detail'),

    # Alias notifications (frontend appelle /api/notifications/...)
    path('notifications/latest/',                          n8n_views.latest_notification,         name='notif-latest'),
    path('notifications/history/',                         n8n_views.notifications_history,       name='notif-history'),
    path('notifications/unread-count/',                    n8n_views.unread_notifications_count,  name='notif-unread-count'),
    path('notifications/mark-all-read/',                   n8n_views.mark_all_notifications_read, name='notif-mark-all'),
    path('notifications/<int:notification_id>/mark-read/', n8n_views.mark_notification_read,      name='notif-mark-read'),
    path('notifications/<int:notification_id>/',           n8n_views.get_notification_detail,     name='notif-detail'),

    # ── Prédictions N8N ────────────────────────────────────
    path('predictions/', include('history.n8n_predictions.urls', namespace='predictions')),

    # Alias ancienne URL frontend (/api/prediction/stream/)
    path('prediction/stream/', n8n_views.prediction_stream, name='prediction-stream'),

    # Alias FCM (frontend appelle /api/fcm-token/ et /api/send-fcm/)
    path('fcm-token/', n8n_views.register_fcm_token, name='fcm-token'),
    path('send-fcm/',  n8n_views.send_fcm_notification, name='send-fcm'),

]