# ============================================================
# n8n_predictions/fcm_service.py
# Service Firebase Cloud Messaging pour l'envoi de notifications
# ============================================================

import json
import time
import base64
import os
import requests
import logging
from django.utils import timezone
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

from .models import FCMToken, PushNotificationLog

logger = logging.getLogger(__name__)


class FCMConfigError(Exception):
    """Exception levée quand la configuration FCM est invalide."""
    pass


class FCMService:
    """
    Service pour gérer l'envoi de notifications push via Firebase Cloud Messaging.
    
    Configuration requise (variables d'environnement) :
    - FCM_PROJECT_ID : Google Cloud Project ID
    - FCM_CLIENT_EMAIL : Email du compte de service
    - FCM_PRIVATE_KEY : Clé privée du compte de service (au format PEM)
    """
    
    # Configuration
    FCM_SERVICE_ACCOUNT = {
        "project_id":   os.environ.get("FCM_PROJECT_ID", ""),
        "client_email": os.environ.get("FCM_CLIENT_EMAIL", ""),
        "private_key":  os.environ.get("FCM_PRIVATE_KEY", "").replace("\\\\n", "\\n"),
    }
    
    FCM_AUTH_URL = "https://oauth2.googleapis.com/token"
    FCM_SEND_URL_TEMPLATE = "https://fcm.googleapis.com/v1/projects/{}/messages:send"
    
    _access_token = None
    _token_expiry = 0
    
    @classmethod
    def validate_config(cls):
        """Valide la configuration FCM"""
        if not all(cls.FCM_SERVICE_ACCOUNT.values()):
            raise FCMConfigError(
                "Configuration FCM incomplète. Définissez FCM_PROJECT_ID, "
                "FCM_CLIENT_EMAIL et FCM_PRIVATE_KEY dans le .env."
            )
    
    @classmethod
    def get_access_token(cls) -> str:
        """
        Génère un token OAuth2 depuis le Service Account pour FCM v1.
        Utilise un cache avec expiration.
        """
        cls.validate_config()
        
        # Retourner le token en cache s'il est encore valide
        now = int(time.time())
        if cls._access_token and now < cls._token_expiry - 300:  # Renouveler 5 min avant expiration
            return cls._access_token
        
        # Créer un JWT signé
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        
        payload = base64.urlsafe_b64encode(json.dumps({
            "iss":   cls.FCM_SERVICE_ACCOUNT["client_email"],
            "scope": "https://www.googleapis.com/auth/firebase.messaging",
            "aud":   "https://oauth2.googleapis.com/token",
            "exp":   now + 3600,
            "iat":   now,
        }).encode()).rstrip(b"=").decode()
        
        try:
            private_key = serialization.load_pem_private_key(
                cls.FCM_SERVICE_ACCOUNT["private_key"].encode(),
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
        
        # Échanger le JWT pour un access token
        try:
            response = requests.post(
                cls.FCM_AUTH_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": jwt
                },
                timeout=10,
            )
            response.raise_for_status()
            token_data = response.json()
            cls._access_token = token_data["access_token"]
            cls._token_expiry = now + token_data.get("expires_in", 3600)
            return cls._access_token
        except requests.RequestException as e:
            logger.error(f"Erreur lors de la récupération du token FCM : {e}")
            raise FCMConfigError(f"Impossible de récupérer le token FCM : {e}") from e
    
    @classmethod
    def send_notification(
        cls,
        title: str,
        body: str,
        data: dict = None,
        tokens: list = None,
        log_record: PushNotificationLog = None,
    ) -> dict:
        """
        Envoie une notification push à une liste de tokens FCM.
        
        Args:
            title : Titre de la notification
            body : Corps du message
            data : Dictionnaire de données custom (optionnel)
            tokens : Liste des tokens FCM (si None, récupère tous les tokens actifs)
            log_record : Enregistrement PushNotificationLog pour tracer l'envoi
        
        Returns:
            Dict avec {\"sent\": int, \"failed\": int, \"errors\": list}
        """
        data = data or {}
        
        if not tokens:
            tokens = list(FCMToken.objects.filter(is_active=True).values_list("token", flat=True))
        
        if not tokens:
            logger.warning("Aucun token FCM actif trouvé pour l'envoi")
            return {"sent": 0, "failed": 0, "errors": ["Aucun token FCM disponible"]}
        
        try:
            access_token = cls.get_access_token()
        except FCMConfigError as e:
            logger.error(f"Erreur de configuration FCM : {e}")
            return {"sent": 0, "failed": len(tokens), "errors": [str(e)]}
        
        url = cls.FCM_SEND_URL_TEMPLATE.format(cls.FCM_SERVICE_ACCOUNT["project_id"])
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        sent_count = 0
        error_list = []
        
        for token in tokens:
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json={
                        "message": {
                            "token": token,
                            "notification": {
                                "title": title,
                                "body": body,
                            },
                            "data": {k: str(v) for k, v in data.items()},
                            "android": {
                                "priority": "high",
                                "notification": {"sound": "default"}
                            },
                        }
                    },
                    timeout=5,
                )
                
                if response.status_code == 200:
                    sent_count += 1
                    logger.debug(f"Notification envoyée au token {token[:20]}...")
                else:
                    error = response.json()
                    error_list.append({
                        "token": token[:20] + "...",
                        "status": response.status_code,
                        "error": error.get("error", {}).get("message", "Unknown error")
                    })
                    logger.warning(f"Erreur d'envoi pour {token[:20]}... : {error}")
            except requests.RequestException as e:
                error_list.append({
                    "token": token[:20] + "...",
                    "error": str(e)
                })
                logger.error(f"Exception lors de l'envoi à {token[:20]}... : {e}")        
        # Mettre à jour le log si fourni
        if log_record:
            log_record.sent_count = sent_count
            log_record.error_count = len(tokens) - sent_count
            log_record.errors = error_list
            log_record.status = 'sent' if sent_count > 0 else 'failed'
            log_record.sent_at = timezone.now()
            log_record.save()
        
        return {
            "sent": sent_count,
            "failed": len(tokens) - sent_count,
            "total": len(tokens),
            "errors": error_list,
        }


# Alias pour faciliter l'utilisation
def send_fcm_notification(title: str, body: str, data: dict = None) -> dict:
    """
    Fonction convenience pour envoyer une notification FCM.
    """
    return FCMService.send_notification(title, body, data)