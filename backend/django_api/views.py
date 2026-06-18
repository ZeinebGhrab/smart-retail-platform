# ============================================================
# views.py — FCM (Firebase Cloud Messaging) endpoints
# backend/django_api/views.py
# ============================================================

from .history.models import FCMToken, NotificationLog
import json
import os
import time
import requests
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64

# ============================================================
# Chargement du Service Account Firebase depuis le fichier JSON
# Le fichier est exclu du git via .gitignore
# ============================================================
_CREDS_PATH = Path(__file__).resolve().parent / "firebase-credentials.json"

def _load_service_account() -> dict:
    """Charge firebase-credentials.json une seule fois au démarrage."""
    if not _CREDS_PATH.exists():
        raise FileNotFoundError(
            f"firebase-credentials.json introuvable : {_CREDS_PATH}\n"
            "Téléchargez-le depuis Firebase Console → Paramètres → Comptes de service."
        )
    with open(_CREDS_PATH, "r") as f:
        return json.load(f)

SERVICE_ACCOUNT = _load_service_account()


def get_fcm_access_token():
    """
    Génère un token OAuth2 depuis le Service Account pour FCM v1
    """
    now = int(time.time())

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
    ).rstrip(b'=').decode()

    payload = base64.urlsafe_b64encode(json.dumps({
        "iss": SERVICE_ACCOUNT["client_email"],
        "scope": "https://www.googleapis.com/auth/firebase.messaging",
        "aud": "https://oauth2.googleapis.com/token",
        "exp": now + 3600,
        "iat": now
    }).encode()).rstrip(b'=').decode()

    private_key = serialization.load_pem_private_key(
        SERVICE_ACCOUNT["private_key"].encode(),
        password=None,
        backend=default_backend()
    )
    signature = base64.urlsafe_b64encode(
        private_key.sign(
            f"{header}.{payload}".encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    ).rstrip(b'=').decode()

    jwt = f"{header}.{payload}.{signature}"

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt
        }
    )
    return response.json()["access_token"]


@csrf_exempt
def save_fcm_token(request):
    """
    Sauvegarde un token FCM dans la base de données
    POST /api/fcm-token/
    Payload: {"token": "device_token_from_firebase"}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try:
        data = json.loads(request.body)
        token = data.get('token')
        if not token:
            return JsonResponse({'error': 'token manquant'}, status=400)
        FCMToken.objects.get_or_create(token=token)
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def send_fcm(request):
    """
    Envoie une notification push via Firebase Cloud Messaging v1
    et sauvegarde le résultat dans NotificationLog.
    POST /api/send-fcm/
    Payload: {
        "title": "Titre",
        "body": "Corps du message",
        "data": {"key": "value"}
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        data  = json.loads(request.body)
        title = data.get('title', 'ShopAnalytics')
        body  = data.get('body', '')
        extra = {k: str(v) for k, v in data.get('data', {}).items()}

        tokens = list(FCMToken.objects.values_list('token', flat=True))
        if not tokens:
            return JsonResponse({'error': 'Aucun token enregistré'}, status=404)

        access_token = get_fcm_access_token()
        url = f"https://fcm.googleapis.com/v1/projects/{SERVICE_ACCOUNT['project_id']}/messages:send"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        sent   = 0
        errors = []
        for token in tokens:
            response = requests.post(url, headers=headers, json={
                "message": {
                    "token": token,
                    "notification": {
                        "title": title,
                        "body":  body
                    },
                    "data": extra,
                    "android": {
                        "priority": "high",
                        "notification": {"sound": "default"}
                    }
                }
            })
            if response.status_code == 200:
                sent += 1
            else:
                errors.append(response.json())

        # ── Sauvegarder dans NotificationLog ────────────────
        NotificationLog.objects.create(
            title       = title,
            body        = body,
            data        = extra,
            sent_count  = sent,
            error_count = len(errors),
            errors      = errors,
        )

        return JsonResponse({'sent': sent, 'errors': errors})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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