# ============================================================
# history/views.py — API REST : historique visiteurs / analytics
# Source de données : data/shoppingclub_2025_2026.csv
# ============================================================

import json
import threading
from pathlib import Path

from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import StreamingHttpResponse

from . import visitor_data as vd

# ── Notifications N8N : persistance fichier JSON ────────────
# N8N écrit le dernier rapport ici (depuis le nœud "Push SSE → Django",
# en plus du broadcast SSE), ce qui permet au front de récupérer le
# dernier rapport même après un rechargement de page / reconnexion.
_NOTIF_DIR = Path(getattr(settings, "BACKEND_DIR", Path(__file__).resolve().parent.parent.parent)) / "data"
_NOTIF_FILE = _NOTIF_DIR / "notifications.json"

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


# ── Notifications N8N — lecture / écriture fichier JSON ─────

def _read_notifications() -> list:
    if not _NOTIF_FILE.exists():
        return []
    try:
        with open(_NOTIF_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _append_notification(payload: dict) -> None:
    _NOTIF_DIR.mkdir(parents=True, exist_ok=True)
    history = _read_notifications()
    history.append(payload)
    # Garde les 100 derniers rapports maximum
    history = history[-100:]
    with open(_NOTIF_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Dernière notification reçue de N8N",
    description="Retourne le dernier rapport quotidien reçu via /api/daily-report/ (persisté en fichier JSON).",
)
@api_view(["GET"])
def latest_notification(request):
    history = _read_notifications()
    if not history:
        return Response({"message": "Aucune notification reçue pour le moment."}, status=200)
    return Response(history[-1])


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Historique des notifications reçues de N8N",
    description="Retourne la liste des rapports quotidiens reçus via /api/daily-report/ (les plus récents en dernier).",
)
@api_view(["GET"])
def notifications_history(request):
    return Response({"count": len(_read_notifications()), "results": _read_notifications()})


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

    # Persistance fichier JSON (pour /api/notifications/latest/ et /history/)
    _append_notification(payload)

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


# ── Alias — noms attendus par history/urls.py ────────────────
# (le endpoint SSE est consommé par le Dashboard React via
#  useSSEPrediction.ts ; le endpoint POST est appelé par le
#  workflow N8N "Push SSE → Django")
prediction_stream = sse_stream
receive_daily_report = daily_report