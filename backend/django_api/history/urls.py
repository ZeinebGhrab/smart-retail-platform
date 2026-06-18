# ============================================================
# history/urls.py — Routes API
# ============================================================

from django.urls import path
from . import views
from .chat_view import chat

urlpatterns = [
    # ── Analytics ────────────────────────────────────────────
    path("history/visitors/",          views.visitor_history,     name="visitor-history"),
    path("history/visitors/count/",    views.visitor_count,       name="visitor-count"),
    path("history/visitors/hourly/",   views.hourly_flow,         name="visitor-hourly"),
    path("history/visitors/forecast/", views.forecast,            name="visitor-forecast"),
    path("history/summary/",           views.summary,             name="history-summary"),
    path("history/cameras/",           views.cameras,             name="history-cameras"),

    # ── Notifications N8N (PostgreSQL BD) ────────────────────
    path("notifications/latest/",           views.latest_notification,        name="notifications-latest"),
    path("notifications/history/",          views.notifications_history,      name="notifications-history"),
    path("notifications/unread-count/",     views.unread_notifications_count, name="notifications-unread-count"),
    path("notifications/<int:notification_id>/mark-read/", views.mark_notification_read, name="mark-notification-read"),
    path("notifications/mark-all-read/",    views.mark_all_notifications_read, name="mark-all-notifications-read"),
    path("prediction/stream/",              views.prediction_stream,          name="prediction-stream"),
    path("daily-report/",                   views.receive_daily_report,       name="receive-daily-report"),

    # ── FCM (Firebase Cloud Messaging) ───────────────────────
    path("fcm-token/",                 views.save_fcm_token,      name="save-fcm-token"),
    path("send-fcm/",                  views.send_fcm,            name="send-fcm"),

    # ── Historique des notifications FCM ─────────────────────
    path("notification-logs/",         views.notification_logs,   name="notification-logs"),

    # ── Chat RAG ─────────────────────────────────────────────
    path("chat/",                      chat,                      name="chat-rag"),
]