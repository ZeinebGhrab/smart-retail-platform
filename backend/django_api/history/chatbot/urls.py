# ============================================================
# history/chatbot/urls.py — Routes du Chat IA (RAG)
# ============================================================

from django.urls import path
from .views import chat

app_name = 'chatbot'

urlpatterns = [
    path('chat/', chat, name='chat'),
]