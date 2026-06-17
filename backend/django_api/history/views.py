# ============================================================
# history/views.py — API REST : historique visiteurs / analytics + FCM
# ============================================================

import json
import time
import threading
import requests
import base64
from pathlib import Path

from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

from . import visitor_data as vd
from .models import FCMToken

# ── Notifications N8N : persistance fichier JSON ────────────
_NOTIF_DIR  = Path(getattr(settings, "BACKEND_DIR", Path(__file__).resolve().parent.parent.parent)) / "data"
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
    parameters=[_START_DATE_PARAM, _END_DATE_PARAM, _CAMERA_PARAM],
)
@api_view(["GET"])
def visitor_history(request):
    start_date = request.query_params.get("start_date")
    end_date   = request.query_params.get("end_date")
    camera     = request.query_params.get("camera")
    result = vd.get_visitor_history(start_date=start_date, end_date=end_date, camera=camera)
    return Response(result)


@extend_schema(
    tags=["Historique visiteurs"],
    summary="Nombre de visiteurs pour une date donnée",
    parameters=[_DATE_PARAM, _CAMERA_PARAM],
)
@api_view(["GET"])
def visitor_count(request):
    date   = request.query_params.get("date")
    camera = request.query_params.get("camera")
    result = vd.get_visitor_count(date=date, camera=camera)
    return Response(result)


@extend_schema(
    tags=["Historique visiteurs"],
    summary="Flux horaire de visiteurs",
    parameters=[_DATE_PARAM, _CAMERA_PARAM],
)
@api_view(["GET"])
def hourly_flow(request):
    date   = request.query_params.get("date")
    camera = request.query_params.get("camera")
    result = vd.get_hourly_visitor_flow(date=date, camera=camera)
    return Response(result)


@extend_schema(
    tags=["Prévisions"],
    summary="Prévision du nombre de visiteurs",
    parameters=[_DATE_PARAM, _CAMERA_PARAM],
)
@api_view(["GET"])
def forecast(request):
    date   = request.query_params.get("date")
    camera = request.query_params.get("camera")
    result = vd.forecast_visitors(target_date=date, camera=camera)
    return Response(result)


@extend_schema(tags=["Résumé"], summary="KPIs globaux")
@api_view(["GET"])
def summary(request):
    return Response(vd.get_summary())


@extend_schema(tags=["Résumé"], summary="Liste des caméras disponibles")
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
    history = history[-100:]
    with open(_NOTIF_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Dernière notification reçue de N8N",
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
)
@api_view(["GET"])
def notifications_history(request):
    return Response(_read_notifications())


# ── SSE stream ───────────────────────────────────────────────

def sse_stream(request):
    import queue
    q: queue.Queue = queue.Queue()
    with _sse_lock:
        _sse_clients.append(q)

    def event_stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    payload = q.get(timeout=30)
                    yield f"event: llm_report\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except queue.Empty:
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
    response["Cache-Control"]     = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@extend_schema(
    tags=["Rapport quotidien — N8N"],
    summary="Réception du rapport quotidien depuis N8N",
)
@api_view(["POST"])
def daily_report(request):
    payload = request.data
    if not payload:
        return Response({"error": "Payload vide."}, status=400)

    required_fields = {"type", "date", "message", "prediction"}
    missing = required_fields - set(payload.keys())
    if missing:
        return Response({"error": f"Champs manquants : {', '.join(missing)}"}, status=400)

    _append_notification(payload)

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
prediction_stream    = sse_stream
receive_daily_report = daily_report


# ============================================================
# FCM — Firebase Cloud Messaging
# ============================================================

# Config Service Account Firebase — projet shop-analytics-anavid
_FCM_SERVICE_ACCOUNT = {
    "project_id":   "shop-analytics-anavid",
    "client_email": "firebase-adminsdk-fbsvc@shop-analytics-anavid.iam.gserviceaccount.com",
    # ⚠️  Remplacer par la vraie clé privée du projet shop-analytics-anavid
    # Firebase Console → Project Settings → Service accounts → Generate new private key
    "private_key":  "REPLACE_WITH_PRIVATE_KEY_FROM_FIREBASE_CONSOLE",
}


def _get_fcm_access_token() -> str:
    """Génère un token OAuth2 depuis le Service Account pour FCM v1."""
    now = int(time.time())

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    payload = base64.urlsafe_b64encode(json.dumps({
        "iss":   _FCM_SERVICE_ACCOUNT["client_email"],
        "scope": "https://www.googleapis.com/auth/firebase.messaging",
        "aud":   "https://oauth2.googleapis.com/token",
        "exp":   now + 3600,
        "iat":   now,
    }).encode()).rstrip(b"=").decode()

    private_key = serialization.load_pem_private_key(
        _FCM_SERVICE_ACCOUNT["private_key"].encode(),
        password=None,
        backend=default_backend(),
    )
    signature = base64.urlsafe_b64encode(
        private_key.sign(
            f"{header}.{payload}".encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    ).rstrip(b"=").decode()

    jwt = f"{header}.{payload}.{signature}"

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt},
    )
    return response.json()["access_token"]


@csrf_exempt
def save_fcm_token(request):
    """POST /api/fcm-token/ — Sauvegarde un token FCM."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        data  = json.loads(request.body)
        token = data.get("token")
        if not token:
            return JsonResponse({"error": "token manquant"}, status=400)
        FCMToken.objects.get_or_create(token=token)
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def send_fcm(request):
    """POST /api/send-fcm/ — Envoie une notification push via FCM v1."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        data   = json.loads(request.body)
        tokens = list(FCMToken.objects.values_list("token", flat=True))
        if not tokens:
            return JsonResponse({"error": "Aucun token enregistré"}, status=404)

        access_token = _get_fcm_access_token()
        url = f"https://fcm.googleapis.com/v1/projects/{_FCM_SERVICE_ACCOUNT['project_id']}/messages:send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        }

        sent, errors = 0, []
        for token in tokens:
            resp = requests.post(url, headers=headers, json={
                "message": {
                    "token": token,
                    "notification": {
                        "title": data.get("title", "ShopAnalytics"),
                        "body":  data.get("body", ""),
                    },
                    "data":    {k: str(v) for k, v in data.get("data", {}).items()},
                    "android": {"priority": "high", "notification": {"sound": "default"}},
                }
            })
            if resp.status_code == 200:
                sent += 1
            else:
                errors.append(resp.json())

        return JsonResponse({"sent": sent, "errors": errors})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)