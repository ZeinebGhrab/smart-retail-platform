# ============================================================
# history/views.py — API REST : historique visiteurs / analytics
# Source de données : data/shoppingclub_2025_2026.csv
# ============================================================

import json
import threading

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import StreamingHttpResponse

from . import visitor_data as vd

_DATE_PARAM = OpenApiParameter(
    "date", str, description="Date au format YYYY-MM-DD (par défaut : dernière date disponible)."
)
_START_DATE_PARAM = OpenApiParameter(
    "start_date", str, description="Date de début (YYYY-MM-DD), incluse."
)
_END_DATE_PARAM = OpenApiParameter(
    "end_date", str, description="Date de fin (YYYY-MM-DD), incluse."
)
_CAMERA_PARAM = OpenApiParameter(
    "camera", str, description="Filtrer par caméra : 'Porte_nord' ou 'Porte_sud' (par défaut : toutes, agrégées)."
)

# ── SSE : liste des clients connectés (thread-safe) ─────────
_sse_clients: list = []
_sse_lock = threading.Lock()


@extend_schema(
    tags=["Historique visiteurs"],
    summary="Historique journalier des visiteurs",
    description="Retourne l'historique journalier des visiteurs (analytics) avec ventilation par genre et âge.",
    parameters=[_START_DATE_PARAM, _END_DATE_PARAM, _CAMERA_PARAM],
)
@api_view(["GET"])
def visitor_history(request):
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    camera = request.query_params.get("camera")

    result = vd.get_visitor_history(start_date=start_date, end_date=end_date, camera=camera)
    return Response(result)


@extend_schema(
    tags=["Historique visiteurs"],
    summary="Nombre de visiteurs pour une date donnée",
    description="Retourne le nombre de visiteurs (et le détail genre/âge) pour une date donnée (par défaut : la dernière date disponible).",
    parameters=[_DATE_PARAM, _CAMERA_PARAM],
)
@api_view(["GET"])
def visitor_count(request):
    date = request.query_params.get("date")
    camera = request.query_params.get("camera")

    result = vd.get_visitor_count(date=date, camera=camera)
    return Response(result)


@extend_schema(
    tags=["Historique visiteurs"],
    summary="Flux horaire de visiteurs",
    description="Retourne le nombre de visiteurs par heure pour une date donnée, ainsi que l'heure de pointe.",
    parameters=[_DATE_PARAM, _CAMERA_PARAM],
)
@api_view(["GET"])
def hourly_flow(request):
    date = request.query_params.get("date")
    camera = request.query_params.get("camera")

    result = vd.get_hourly_visitor_flow(date=date, camera=camera)
    return Response(result)


@extend_schema(
    tags=["Prévisions"],
    summary="Prévision du nombre de visiteurs",
    description=(
        "Prévoit le nombre de visiteurs pour une date donnée (par défaut : demain) via "
        "régression linéaire sur l'historique + ajustement par jour de la semaine."
    ),
    parameters=[_DATE_PARAM, _CAMERA_PARAM],
)
@api_view(["GET"])
def forecast(request):
    date = request.query_params.get("date")
    camera = request.query_params.get("camera")

    result = vd.forecast_visitors(target_date=date, camera=camera)
    return Response(result)


@extend_schema(
    tags=["Résumé"],
    summary="KPIs globaux",
    description="Retourne un résumé global : période couverte, total visiteurs, répartition par caméra / genre / tranche d'âge.",
)
@api_view(["GET"])
def summary(request):
    return Response(vd.get_summary())


@extend_schema(
    tags=["Résumé"],
    summary="Liste des caméras disponibles",
)
@api_view(["GET"])
def cameras(request):
    return Response({"cameras": vd.list_cameras()})


# ── SSE stream ───────────────────────────────────────────────

def sse_stream(request):
    """
    GET /api/daily-report/stream/
    Connexion SSE longue durée — le Dashboard React s'y abonne
    pour recevoir les rapports quotidiens en temps réel.
    """
    import queue

    q: queue.Queue = queue.Queue()
    with _sse_lock:
        _sse_clients.append(q)

    def event_stream():
        try:
            # Heartbeat initial pour confirmer la connexion
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    payload = q.get(timeout=30)
                    yield f"event: llm_report\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    # Keepalive toutes les 30 s
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                try:
                    _sse_clients.remove(q)
                except ValueError:
                    pass

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


# ── Endpoint POST appelé par N8N ─────────────────────────────

@extend_schema(
    tags=["Rapport quotidien — N8N"],
    summary="Réception du rapport quotidien depuis N8N",
    description=(
        "Reçoit le payload structuré généré par N8N (Formater Payload SSE) "
        "et le diffuse immédiatement à tous les clients SSE connectés "
        "(Dashboard React + ChatIA Ionic).\n\n"
        "Payload attendu (PredictionData) :\n"
        "```json\n"
        "{\n"
        '  "type": "llm_report",\n'
        '  "date": "2026-06-16",\n'
        '  "generated_at": "2026-06-16T06:00:00Z",\n'
        '  "message": "...",\n'
        '  "prediction": {\n'
        '    "visiteurs_prevus": 412,\n'
        '    "profil_dominant": "Familles",\n'
        '    "niveau_affluence": "Élevé",\n'
        '    "heure_pointe": "14:00 - 18:00"\n'
        "  }\n"
        "}\n"
        "```"
    ),
)
@api_view(["POST"])
def daily_report(request):
    """
    POST /api/daily-report/
    Appelé par le nœud N8N « Push SSE → Django ».
    Diffuse le payload à tous les clients SSE abonnés.
    """
    payload = request.data
    if not payload:
        return Response({"error": "Payload vide."}, status=400)

    required_fields = {"type", "date", "message", "prediction"}
    missing = required_fields - set(payload.keys())
    if missing:
        return Response({"error": f"Champs manquants : {', '.join(missing)}"}, status=400)

    # Broadcast à tous les clients SSE connectés
    with _sse_lock:
        active_clients = list(_sse_clients)

    delivered = 0
    for q in active_clients:
        try:
            q.put_nowait(payload)
            delivered += 1
        except Exception:
            pass

    return Response({
        "status": "broadcasted",
        "clients_notified": delivered,
        "date": payload.get("date"),
    })