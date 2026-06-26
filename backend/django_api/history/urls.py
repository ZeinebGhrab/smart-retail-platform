# ============================================================
# history/urls.py
# Routes principales de l'app history
# Inclut les sous-modules video_alerts et n8n_predictions
# ============================================================

from django.urls import path, include
from history.chat_view import chat

app_name = 'history'

urlpatterns = [
    # Chat IA — RAG (Llama 3.2 + ChromaDB)
    path('chat/', chat, name='chat'),

    # Routes pour les alertes vidéo
    path('video-alerts/', include('history.video_alerts.urls', namespace='video-alerts')),
    
    # Routes pour les prédictions N8N
    path('predictions/', include('history.n8n_predictions.urls', namespace='predictions')),
]