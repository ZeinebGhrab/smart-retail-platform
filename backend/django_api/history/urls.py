from django.urls import path
from . import views
from .chat_view import chat
from .django_sse_endpoint import prediction_stream, receive_daily_report

urlpatterns = [
    # ── Analytics ────────────────────────────────────────────
    path("history/visitors/",          views.visitor_history, name="visitor-history"),
    path("history/visitors/count/",    views.visitor_count,   name="visitor-count"),
    path("history/visitors/hourly/",   views.hourly_flow,     name="visitor-hourly"),
    path("history/visitors/forecast/", views.forecast,        name="visitor-forecast"),
    path("history/summary/",           views.summary,         name="history-summary"),
    path("history/cameras/",           views.cameras,         name="history-cameras"),

    # ── Notifications N8N ────────────────────────────────────
    path("notifications/latest/",      views.latest_notification),  # lecture fichier JSON
path('notifications/history/', views.notifications_history),
    path("prediction/stream/",         prediction_stream),           # SSE → frontend écoute ici
    path("daily-report/",              receive_daily_report),        # N8N poste ici
    # ── Chat RAG ─────────────────────────────────────────────
    path("chat/",                      chat, name="chat-rag"),
]