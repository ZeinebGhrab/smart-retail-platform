# ============================================================
# n8n_predictions/urls.py
# Routes pour les prédictions N8N
# ============================================================

from django.urls import path
from . import views

app_name = 'n8n_predictions'

urlpatterns = [
    # Notifications
    path('notifications/latest/', views.latest_notification, name='latest-notification'),
    path('notifications/history/', views.notifications_history, name='notifications-history'),
    path('notifications/<int:notification_id>/', views.get_notification_detail, name='notification-detail'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark-read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark-all-read'),
    path('notifications/unread-count/', views.unread_notifications_count, name='unread-count'),
    
    # Streaming SSE
    path('stream/', views.prediction_stream, name='stream'),
    
    # Rapports (N8N → Backend)
    path('daily-report/', views.receive_daily_report, name='daily-report'),
    
    # FCM
    path('fcm/register/', views.register_fcm_token, name='register-fcm-token'),
    path('fcm/send/', views.send_fcm_notification, name='send-fcm-notification'),
    
    # Statistiques
    path('stats/', views.notification_stats, name='stats'),
]