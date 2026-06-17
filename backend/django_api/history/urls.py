# ============================================================
# urls.py — Routes API avec endpoints FCM 
# backend/django_api/history/urls.py
# ============================================================

from django.urls import path
from . import views
from .chat_view import chat
from ..views import save_fcm_token, send_fcm  # Import des fonctions FCM

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
    path("prediction/stream/",         views.prediction_stream),    # SSE → frontend écoute ici
    path("daily-report/",              views.receive_daily_report), # N8N poste ici
    
    # ── FCM (Firebase Cloud Messaging) ───────────────────────
    path('fcm-token/',                 save_fcm_token, name='save-fcm-token'),
    path('send-fcm/',                  send_fcm, name='send-fcm'),
    
    # ── Chat RAG ─────────────────────────────────────────────
    path("chat/",                      chat, name="chat-rag"),
]