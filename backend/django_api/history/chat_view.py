# ============================================================
# history/chat_view.py — Endpoint Django pour le Chat IA
# POST /api/chat/
# Body  : { "question": "Nombre de visiteurs le 2026-05-30 ?" }
# Return: { "answer": "...", "model": "...", "sources": {...} }
#
# Délègue entièrement à rag_pipeline.run_rag_pipeline()
# ============================================================

from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample

from .rag_pipeline import run_rag_pipeline


@extend_schema(
    tags=["Chat IA — RAG"],
    summary="Question en langage naturel (RAG + Llama 3.2)",
    description=(
        "Reçoit une question en français et retourne une réponse générée par "
        "Llama 3.2 3B (via Ollama), enrichie par retrieval ChromaDB + CSV visiteurs. "
        "Modèle sélectionné automatiquement depuis results/eligible_models.json.\n\n"
        "Le champ optionnel 'history' permet de fournir les derniers échanges de la "
        "conversation (format [{role: 'user'|'assistant', content: '...'}]) afin que "
        "le modèle réponde correctement aux questions de suivi (ex: 'Et hier ?')."
    ),
    examples=[
        OpenApiExample(
            "Visiteurs par date",
            value={"question": "Nombre de visiteurs le 2026-05-30 ?"},
            request_only=True,
        ),
        OpenApiExample(
            "Historique semaine",
            value={"question": "Historique des 7 derniers jours Porte_nord"},
            request_only=True,
        ),
        OpenApiExample(
            "Question de suivi avec historique",
            value={
                "question": "Et hier ?",
                "history": [
                    {"role": "user", "content": "Combien de visiteurs aujourd'hui ?"},
                    {"role": "assistant", "content": "📊 Aujourd'hui : 1234 visiteurs."},
                ],
            },
            request_only=True,
        ),
    ],
)
@api_view(["POST"])
def chat(request):
    question = (request.data.get("question") or "").strip()
    if not question:
        return Response({"error": "Champ 'question' manquant ou vide."}, status=400)

    history = request.data.get("history") or []
    if not isinstance(history, list):
        history = []

    result = run_rag_pipeline(question, history=history)
    return Response(result)