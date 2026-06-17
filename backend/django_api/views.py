# ============================================================
# views.py — FCM (Firebase Cloud Messaging) endpoints
# backend/django_api/views.py
# ============================================================

from .history.models import FCMToken
import json
import time
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64

# ============================================================
# Config Service Account Firebase
# ============================================================
SERVICE_ACCOUNT = {
    "project_id": "anavid-91d01",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDCGXJ3wJE8EBph\nmHlW1QWbChDr4rPWP7Xddm3RDEcbPo6Yjt8/WclE3+7tB5SqhvHli2hlsFm6/TR3\ncHxZc1oHSE34b4jBpRA9py3OElaPE+fGlhXRvaG1bnvQgkAqFVtKJhQ3H8kxBV7L\nrdNZExSTXrNtozSkSxtKM7jZw/8CzAJVOHxt4D0eOV3uVX0ZZYogbUHyv1wvLgK8\n8pN2b5eygaA4M+KoL7t5NpSE9ExIFdzLACbhGTPjrbFpG4UI/pDd4RWaom/zoxca\n0ljH2pTDSJiV+ahDNUE4OHRr0dmHqy/KH1eVKhSp5CpZdvupAgKqaseO8I5yvQzD\nDoXvLwj7AgMBAAECggEAExU9mYPcVsUXuuZ3o4kmpHAQatVrX4VjA+a1Wq5No8jH\nBaO77Wmn7dAWy8U8VHZ9yNb0b1Vi9Q0Y5ldJh0fduMXFXxQKirNUtFY/6bjVO5SC\n68jTIb+QBJtb3yU3Jr9AlIeUfDjxTSydSpwiVJyy7Kw/95sD1wh7vEdduKpzsEDW\nB6cqLOThezgMKtQIT8eUPWPeiKeObZlbKB8W9Ivd8pW/Sd9QBkdXJ3CFqtvO9sgz\nkQsldI7REirDOcNSaI0MWmmVBk18p4aGlAAywYXkl+NOZBj2Co1ExHbUKFAlepKJ\nvEXOpgMtoSkenMofLgw38HYDeb7yQSbhOBDhDPtDDQKBgQDlkQ5iozQQiOo+ON4/\nNtN3yat2pqamdlxjevGwMFY5eFC/TuIKLR/Y1o5pzQ1lZAMnWc6x38qp7uVkJv93\nUUsg2xmnZ9lVZtUNUMbYoWdBmjcpJBsstxPtPsapjSQki2gteE098sCYSLsmdrj6\nD7dMRtKk/MbGAFqQjuwwVuJUBQKBgQDYcuwdb8oIesFtVShKUQMCwOoXr/44xOTO\nWyfLIrzJZGbMfyp10Qu0SzCLPfnQJSqDhaiA8LA3hcWq+60b/Xd2kGhL709DAwON\nUoCtc2t3IkEU8eedglP/F2PamQaP6FHrfFTVtIlPEo/gV4HBTpbdoeH7YbfVe5G2\n/PScbN94/wKBgQDemI/FTxC987SGjufZjdTw8wiibSdsg5pED8NonwYMhcBuMBP3\n4BdgT3MZ3e1eYeK49lj4mtJNgkrFmRbfYGEjw6+VZpoTODnfxnJ5Pc/8iYdxCgSb\nkA3vXo6Ne0EPemmSpXLoXYkoYGWv/zCPsEuA16+KsVwgQ9mNEDivCqA87QKBgQCr\nxEdr9NK3d/MX+IRItZFWFhGvSpLMKjQJLn2dzqtShsKtdh0T8hj/ssuLNFuSumvK\ng7781ASDiz0aOy9dDwBGrsKVwAt+el3PQLGs8/NMT3qmTHIppMtTnBQ53UY/3XVl\nEv2fue1dOrXCqq7l4KAIsfbLrvhcCfvQ41ya5itRsQKBgQDCCYvtWMvsqL0gTMUh\n+gteckLYxfeDqzhwG5FaTGhhSeFBAKKyDyP4tvSPTthPFLQhl3JHvl4MXfDGGgE+\nUHk4fz01gpTWyxjKlVU5LnEOrts8iRLIBSsV9uhgYhHB3XHUnbkk7FnAct8bJJgW\neZXFz+Hz0PdYloAqSky8mZ4jdQ==\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-fbsvc@anavid-91d01.iam.gserviceaccount.com"
}


def get_fcm_access_token():
    """
    Génère un token OAuth2 depuis le Service Account pour FCM v1
    """
    now = int(time.time())

    # Construire le JWT
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

    # Signer avec la clé privée RSA
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

    # Échanger le JWT contre un access token
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
        data = json.loads(request.body)
        tokens = list(FCMToken.objects.values_list('token', flat=True))

        if not tokens:
            return JsonResponse({'error': 'Aucun token enregistré'}, status=404)

        # Obtenir le token OAuth2
        access_token = get_fcm_access_token()
        url = f"https://fcm.googleapis.com/v1/projects/{SERVICE_ACCOUNT['project_id']}/messages:send"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        sent = 0
        errors = []
        for token in tokens:
            response = requests.post(url, headers=headers, json={
                "message": {
                    "token": token,
                    "notification": {
                        "title": data.get('title', 'ShopAnalytics'),
                        "body": data.get('body', '')
                    },
                    "data": {k: str(v) for k, v in data.get('data', {}).items()},
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

        return JsonResponse({'sent': sent, 'errors': errors})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)