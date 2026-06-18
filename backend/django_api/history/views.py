# ============================================================
# history/views.py — API REST : historique visiteurs / analytics + FCM
# ============================================================

import json
import time
import threading
import requests
import base64
import os
from pathlib import Path
from datetime import datetime

from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

from . import visitor_data as vd
from .models import FCMToken, NotificationLog, Notification
from .serializers import NotificationSerializer

# ── Notifications N8N : persistance fichier JSON (ancienne méthode) ────────────
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


# ── Notifications N8N — utilisation de la BD PostgreSQL ──────────────

@extend_schema(
    tags=["Notifications — N8N"],
    summary="Dernière notification reçue de N8N",
)
@api_view(["GET"])
def latest_notification(request):
    """Retourne la dernière notification créée"""
    try:
        notif = Notification.objects.latest('generated_at')
        serializer = NotificationSerializer(notif)
        return Response(serializer.data)
    except Notification.DoesNotExist:
        return Response({"message": "Aucune notification reçue pour le moment."}, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Historique des notifications reçues de N8N (du plus récent au plus ancien)",
)
@api_view(["GET"])
def notifications_history(request):
    """
    Retourne toutes les notifications, triées du plus récent au plus ancien.
    Les notifications non lues apparaissent en premier.
    """
    # Récupérer toutes les notifications, triées par date décroissante
    notifications = Notification.objects.all().order_by('-generated_at')
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Marquer une notification comme lue",
)
@api_view(["POST"])
def mark_notification_read(request, notification_id):
    """
    POST /api/notifications/{notification_id}/mark-read/
    Marque la notification avec l'ID spécifié comme lue.
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.is_read = True
        notification.save()
        serializer = NotificationSerializer(notification)
        return Response({
            "status": "ok",
            "message": "Notification marquée comme lue",
            "notification": serializer.data
        })
    except Notification.DoesNotExist:
        return Response(
            {"error": f"Notification avec l'ID {notification_id} non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Marquer toutes les notifications non lues comme lues",
)
@api_view(["POST"])
def mark_all_notifications_read(request):
    """
    POST /api/notifications/mark-all-read/
    Marque toutes les notifications non lues comme lues.
    """
    count = Notification.objects.filter(is_read=False).update(is_read=True)
    return Response({
        "status": "ok",
        "message": f"{count} notification(s) marquée(s) comme lue(s)",
        "count": count
    })


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Compter les notifications non lues",
)
@api_view(["GET"])
def unread_notifications_count(request):
    """
    GET /api/notifications/unread-count/
    Retourne le nombre de notifications non lues.
    """
    count = Notification.objects.filter(is_read=False).count()
    return Response({"unread_count": count})


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
    """
    Reçoit un rapport quotidien de N8N et le sauvegarde en BD.
    """
    payload = request.data
    if not payload:
        return Response({"error": "Payload vide."}, status=status.HTTP_400_BAD_REQUEST)

    required_fields = {"type", "date", "message", "prediction"}
    missing = required_fields - set(payload.keys())
    if missing:
        return Response(
            {"error": f"Champs manquants : {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Créer la notification en BD
        notification = Notification.objects.create(
            date=payload.get('date'),
            message=payload.get('message'),
            visiteurs_prevus=payload.get('prediction', {}).get('visiteurs_prevus', 0),
            profil_dominant=payload.get('prediction', {}).get('profil_dominant', ''),
            niveau_affluence=payload.get('prediction', {}).get('niveau_affluence', ''),
            heure_pointe=payload.get('prediction', {}).get('heure_pointe', ''),
            model=payload.get('model', 'llama3.2:3b-instruct-q4_K_M'),
            type=payload.get('type', 'prediction'),
            is_read=False,
        )

        # Broadcast via SSE
        with _sse_lock:
            active_clients = list(_sse_clients)

        delivered = 0
        for q in active_clients:
            try:
                q.put_nowait(payload)
                delivered += 1
            except Exception:
                pass

        serializer = NotificationSerializer(notification)
        return Response({
            "status": "ok",
            "clients_notified": delivered,
            "date": payload.get("date"),
            "notification": serializer.data,
        })
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ── Alias — noms attendus par history/urls.py ────────────────
prediction_stream    = sse_stream
receive_daily_report = daily_report


# ============================================================
# FCM — Firebase Cloud Messaging
# ============================================================

# Config Service Account Firebase — lue depuis les variables
# d'environnement (FCM_PROJECT_ID / FCM_CLIENT_EMAIL / FCM_PRIVATE_KEY,
# voir docker-compose.yml + .env). On ne committe jamais de vraie clé
# privée en dur dans le code source.
#
# Pour les récupérer : Firebase Console → Paramètres du projet →
# Comptes de service → Générer une nouvelle clé privée (télécharge un
# JSON contenant project_id, client_email et private_key).
#
# Le .env stocke souvent les retours à la ligne de la clé comme des
# "\n" littéraux : on les reconvertit ici en vrais retours à la ligne.
_FCM_SERVICE_ACCOUNT = {
    "project_id":   os.environ.get("FCM_PROJECT_ID", ""),
    "client_email": os.environ.get("FCM_CLIENT_EMAIL", ""),
    "private_key":  os.environ.get("FCM_PRIVATE_KEY", "").replace("\\n", "\n"),
}


class FCMConfigError(Exception):
    """Levée quand la config FCM (service account) est absente ou invalide."""


def _get_fcm_access_token() -> str:
    """Génère un token OAuth2 depuis le Service Account pour FCM v1."""
    if not all(_FCM_SERVICE_ACCOUNT.values()):
        raise FCMConfigError(
            "Configuration FCM incomplète : définissez FCM_PROJECT_ID, "
            "FCM_CLIENT_EMAIL et FCM_PRIVATE_KEY dans le .env."
        )

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

    try:
        private_key = serialization.load_pem_private_key(
            _FCM_SERVICE_ACCOUNT["private_key"].encode(),
            password=None,
            backend=default_backend(),
        )
    except ValueError as e:
        raise FCMConfigError(f"FCM_PRIVATE_KEY invalide ou mal formatée : {e}") from e

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
        timeout=10,
    )
    response.raise_for_status()
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
            return JsonResponse({"sent": 0, "errors": [], "info": "Aucun token FCM enregistré — notification ignorée."}, status=200)

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

@csrf_exempt
def notification_logs(request):
    """
    Retourne l'historique des notifications envoyées.
    GET /api/notification-logs/
    Query params optionnels :
        ?limit=20   — nombre max de résultats (défaut 20)
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'GET only'}, status=405)

    limit = int(request.GET.get('limit', 20))
    logs  = NotificationLog.objects.all()[:limit]

    return JsonResponse({
        'count': NotificationLog.objects.count(),
        'results': [
            {
                'id':          log.id,
                'title':       log.title,
                'body':        log.body,
                'data':        log.data,
                'sent_at':     log.sent_at.isoformat(),
                'sent_count':  log.sent_count,
                'error_count': log.error_count,
                'errors':      log.errors,
            }
            for log in logs
        ]
    })