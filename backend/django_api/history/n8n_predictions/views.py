# ============================================================
# n8n_predictions/views.py
# Vues API pour les prédictions et notifications N8N
# ============================================================

import json
import queue
import threading
import uuid
from datetime import datetime

from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    PredictionNotification,
    FCMToken,
    PushNotificationLog,
)
from .serializers import (
    PredictionNotificationListSerializer,
    PredictionNotificationDetailSerializer,
    PredictionNotificationCreateSerializer,
    PredictionNotificationUpdateSerializer,
    FCMTokenCreateSerializer,
    PushNotificationLogSerializer,
    NotificationStatsSerializer,
)
from .fcm_service import FCMService
from ..utils import get_pagination_params

# ──────────────────────────────────────────────────────────
# SSE (Server-Sent Events) — Broadcast temps réel
# ──────────────────────────────────────────────────────────

_sse_clients: list = []  # Queue pour chaque client connecté
_sse_lock = threading.Lock()  # Thread-safe access


# ──────────────────────────────────────────────────────────
# Paramètres OpenAPI récurrents
# ──────────────────────────────────────────────────────────

PAGINATION_PARAM = OpenApiParameter(
    "limit",
    int,
    description="Nombre maximum de résultats (défaut: 50)",
    required=False,
)

OFFSET_PARAM = OpenApiParameter(
    "offset",
    int,
    description="Décalage pour la pagination (défaut: 0)",
    required=False,
)

TYPE_PARAM = OpenApiParameter(
    "type",
    str,
    description="Filtrer par type: prediction, report, alert, custom",
    required=False,
)

READ_PARAM = OpenApiParameter(
    "is_read",
    str,
    description="Filtrer par statut de lecture: true, false",
    required=False,
)


# ──────────────────────────────────────────────────────────
# Notifications — Récupération et gestion
# ──────────────────────────────────────────────────────────

@extend_schema(
    tags=["Notifications — N8N"],
    summary="Dernière notification reçue",
)
@api_view(['GET'])
def latest_notification(request):
    """
    GET /api/predictions/notifications/latest/
    Retourne la dernière notification reçue de N8N.
    """
    try:
        notif = PredictionNotification.objects.latest('generated_at')
        serializer = PredictionNotificationDetailSerializer(notif)
        return Response(serializer.data)
    except PredictionNotification.DoesNotExist:
        return Response(
            {"message": "Aucune notification reçue pour le moment."},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Historique des notifications",
    parameters=[TYPE_PARAM, READ_PARAM, PAGINATION_PARAM, OFFSET_PARAM],
)
@api_view(['GET'])
def notifications_history(request):
    """
    GET /api/predictions/notifications/history/
    Retourne l'historique des notifications (du plus récent au plus ancien).
    
    Paramètres optionnels :
    - type : Filtrer par type de notification
    - is_read : Filtrer par statut de lecture (true/false)
    - limit : Nombre max de résultats
    - offset : Décalage pour pagination
    """
    notifications = PredictionNotification.objects.all().order_by('-generated_at')
    
    # Filtres
    notif_type = request.query_params.get('type')
    if notif_type:
        notifications = notifications.filter(type=notif_type)
    
    is_read = request.query_params.get('is_read')
    if is_read and is_read.lower() == 'true':
        notifications = notifications.filter(is_read=True)
    elif is_read and is_read.lower() == 'false':
        notifications = notifications.filter(is_read=False)
    
    # Pagination
    limit, offset = get_pagination_params(request.query_params)
    total_count = notifications.count()
    notifications = notifications[offset:offset + limit]
    
    serializer = PredictionNotificationListSerializer(notifications, many=True)
    return Response({
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'results': serializer.data,
    })


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Détail d'une notification",
)
@api_view(['GET'])
def get_notification_detail(request, notification_id):
    """
    GET /api/predictions/notifications/<notification_id>/
    Retourne le détail complet d'une notification.
    """
    try:
        notification = PredictionNotification.objects.get(id=notification_id)
        serializer = PredictionNotificationDetailSerializer(notification)
        return Response(serializer.data)
    except PredictionNotification.DoesNotExist:
        return Response(
            {'error': f'Notification {notification_id} non trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Marquer une notification comme lue",
)
@api_view(['POST'])
def mark_notification_read(request, notification_id):
    """
    POST /api/predictions/notifications/<notification_id>/mark-read/
    Marque une notification comme lue.
    """
    try:
        notification = PredictionNotification.objects.get(id=notification_id)
        notification.mark_as_read()
        serializer = PredictionNotificationDetailSerializer(notification)
        return Response({
            'status': 'ok',
            'message': 'Notification marquée comme lue',
            'notification': serializer.data,
        })
    except PredictionNotification.DoesNotExist:
        return Response(
            {'error': f'Notification {notification_id} non trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Marquer toutes les notifications comme lues",
)
@api_view(['POST'])
def mark_all_notifications_read(request):
    """
    POST /api/predictions/notifications/mark-all-read/
    Marque toutes les notifications non lues comme lues.
    """
    count = PredictionNotification.objects.filter(is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    return Response({
        'status': 'ok',
        'message': f'{count} notification(s) marquée(s) comme lue(s)',
        'count': count,
    })


@extend_schema(
    tags=["Notifications — N8N"],
    summary="Compter les notifications non lues",
)
@api_view(['GET'])
def unread_notifications_count(request):
    """
    GET /api/predictions/notifications/unread-count/
    Retourne le nombre de notifications non lues.
    """
    count = PredictionNotification.objects.filter(is_read=False).count()
    return Response({'unread_count': count})


# ──────────────────────────────────────────────────────────
# SSE Stream — Broadcast temps réel des prédictions
# ──────────────────────────────────────────────────────────

def prediction_stream(request):
    """
    GET /api/predictions/stream/
    Flux Server-Sent Events pour recevoir les prédictions en temps réel.
    
    Chaque client reçoit les nouvelles prédictions au fur et à mesure.
    """
    q: queue.Queue = queue.Queue()
    
    with _sse_lock:
        _sse_clients.append(q)
    
    def event_stream():
        try:
            # Envoyer un événement de connexion
            # IMPORTANT : ce sont de vrais retours à la ligne (\n), pas la
            # séquence littérale "\\n". Le protocole SSE exige des retours
            # à la ligne réels pour séparer "event:" / "data:" et terminer
            # le message ; avec des "\\n" échappés, EventSource côté
            # frontend ne reçoit jamais d'événement valide (ni onmessage,
            # ni les listeners "llm_report"/"prediction").
            yield "event: connected\ndata: {}\n\n"
            
            # Attendre les événements
            while True:
                try:
                    payload = q.get(timeout=30)
                    # On émet sous les deux noms pour rester compatible avec
                    # tous les listeners déjà enregistrés côté frontend
                    # (useSSEPrediction écoute "llm_report" ET "prediction").
                    event_name = 'llm_report' if payload.get('type') == 'llm_report' else 'prediction'
                    yield f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    # Keep-alive toutes les 30 secondes
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


# ──────────────────────────────────────────────────────────
# Réception de rapports quotidiens depuis N8N
# ──────────────────────────────────────────────────────────

# Mapping niveau_affluence : valeurs françaises n8n → codes Django
_AFFLUENCE_MAP = {
    'faible':      'low',
    'modéré':      'medium',
    'modere':      'medium',
    'élevé':       'high',
    'eleve':       'high',
    'très élevé':  'very_high',
    'tres eleve':  'very_high',
    # codes déjà corrects
    'low':         'low',
    'medium':      'medium',
    'high':        'high',
    'very_high':   'very_high',
}

# Mapping type : valeurs n8n → codes Django
_TYPE_MAP = {
    'llm_report':  'report',
    'prediction':  'prediction',
    'report':      'report',
    'alert':       'alert',
    'custom':      'custom',
}


def _normalize_payload(payload: dict) -> dict:
    """
    Normalise le payload n8n avant sauvegarde :
    - Génère 'title' si absent
    - Normalise 'type' (llm_report → report)
    - Normalise 'niveau_affluence' (Élevé → high)
    - Remonte 'generated_at' depuis le payload si présent
    """
    payload = dict(payload)  # copie mutable
    prediction = payload.get('prediction', {})

    # -- type
    raw_type = payload.get('type', 'prediction')
    payload['type'] = _TYPE_MAP.get(raw_type.lower(), 'report')

    # -- title : généré automatiquement si absent
    if not payload.get('title'):
        date_str = payload.get('date', '')
        payload['title'] = f"Rapport IA – {date_str}" if date_str else "Rapport IA"

    # -- niveau_affluence dans prediction{}
    raw_niveau = str(prediction.get('niveau_affluence', 'medium')).lower()
    # Essai exact puis sans accents
    import unicodedata
    def strip_accents(s):
        return ''.join(
            c for c in unicodedata.normalize('NFD', s)
            if unicodedata.category(c) != 'Mn'
        )
    normalized_niveau = (
        _AFFLUENCE_MAP.get(raw_niveau)
        or _AFFLUENCE_MAP.get(strip_accents(raw_niveau))
        or 'medium'
    )
    prediction['niveau_affluence'] = normalized_niveau
    payload['prediction'] = prediction

    return payload


@extend_schema(
    tags=["Rapport quotidien — N8N"],
    summary="Réception d'une prédiction depuis N8N",
)
@api_view(['POST'])
@csrf_exempt
def receive_daily_report(request):
    """
    POST /api/predictions/daily-report/
    Reçoit un rapport quotidien de N8N, le sauvegarde en BD, et le broadcast via SSE.

    Payload minimal accepté (format n8n) :
    {
        "type": "llm_report",          ← ou "prediction", "report", etc.
        "date": "2026-06-26",
        "generated_at": "2026-06-26T06:00:00Z",
        "message": "Texte du rapport LLM...",
        "prediction": {
            "visiteurs_prevus": 150,
            "profil_dominant": "Femmes 25-35",
            "niveau_affluence": "Élevé",  ← valeurs FR ou EN acceptées
            "heure_pointe": "14h30"
        }
    }
    Le champ "title" est optionnel : généré automatiquement si absent.
    """
    payload = request.data

    if not payload:
        return Response(
            {'error': 'Payload vide.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    required_fields = {'message', 'date', 'prediction'}
    missing = required_fields - set(payload.keys())
    if missing:
        return Response(
            {'error': f"Champs manquants : {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        payload = _normalize_payload(payload)

        # Générer UUID unique si absent
        notification_uuid = payload.get('notification_uuid') or str(uuid.uuid4())

        # Créer la notification en BD
        prediction_data = payload.get('prediction', {})
        notification = PredictionNotification.objects.create(
            notification_uuid=notification_uuid,
            type=payload.get('type', 'report'),
            title=payload.get('title', ''),
            message=payload.get('message', ''),
            date=payload.get('date'),
            visiteurs_prevus=prediction_data.get('visiteurs_prevus', 0),
            profil_dominant=prediction_data.get('profil_dominant', ''),
            niveau_affluence=prediction_data.get('niveau_affluence', 'medium'),
            heure_pointe=prediction_data.get('heure_pointe', ''),
            model=payload.get('model', 'llama3.2:3b-instruct-q4_K_M'),
            confidence_score=payload.get('confidence_score'),
            is_read=False,
            tags=payload.get('tags', ''),
            metadata=payload.get('metadata', {}),
        )
        
        # Broadcast via SSE — on diffuse le payload normalisé (même
        # contenu que celui qui vient d'être sauvegardé en BD), pas le
        # payload brut n8n, pour que le frontend reçoive une structure
        # cohérente quel que soit le format exact envoyé par n8n.
        broadcast_payload = dict(payload)
        broadcast_payload['notification_id'] = notification.id
        broadcast_payload['generated_at'] = notification.generated_at.isoformat()

        with _sse_lock:
            active_clients = list(_sse_clients)
        
        delivered = 0
        for q in active_clients:
            try:
                q.put_nowait(broadcast_payload)
                delivered += 1
            except Exception:
                pass
        
        serializer = PredictionNotificationDetailSerializer(notification)
        return Response({
            'status': 'ok',
            'clients_notified': delivered,
            'date': payload.get('date'),
            'notification_id': notification.id,
            'notification_uuid': notification.notification_uuid,
            'notification': serializer.data,
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ──────────────────────────────────────────────────────────
# FCM — Firebase Cloud Messaging
# ──────────────────────────────────────────────────────────

@extend_schema(
    tags=["FCM — Notifications Push"],
    summary="Enregistrer un token FCM",
)
@api_view(['POST'])
@csrf_exempt
def register_fcm_token(request):
    """
    POST /api/predictions/fcm/register/
    Enregistre un token FCM pour un appareil client.
    
    Payload :
    {
        \"token\": \"token_fcm_unique_...\",
        \"device_info\": \"iOS-14.5\" (optionnel)
    }
    """
    serializer = FCMTokenCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    token = serializer.validated_data.get('token')
    device_info = serializer.validated_data.get('device_info', '')
    
    fcm_token, created = FCMToken.objects.get_or_create(
        token=token,
        defaults={'device_info': device_info, 'is_active': True}
    )
    
    if not created and not fcm_token.is_active:
        fcm_token.is_active = True
        fcm_token.device_info = device_info
        fcm_token.save()
    
    return Response({
        'status': 'ok',
        'message': 'Token FCM enregistré avec succès',
        'token_id': fcm_token.id,
        'created': created,
    })


@extend_schema(
    tags=["FCM — Notifications Push"],
    summary="Envoyer une notification push",
)
@api_view(['POST'])
def send_fcm_notification(request):
    """
    POST /api/predictions/fcm/send/
    Envoie une notification push à tous les appareils enregistrés.
    
    Payload :
    {
        \"title\": \"Titre de la notification\",
        \"body\": \"Corps du message\",
        \"data\": {
            \"key1\": \"value1\",
            \"key2\": \"value2\"
        }
    }
    """
    data = request.data
    
    if not data.get('title') or not data.get('body'):
        return Response(
            {'error': 'title et body requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Créer un log d'envoi
    log = PushNotificationLog.objects.create(
        title=data.get('title'),
        body=data.get('body'),
        data=data.get('data', {}),
        status='queued',
    )
    
    # Envoyer via FCM
    result = FCMService.send_notification(
        title=data.get('title'),
        body=data.get('body'),
        data=data.get('data', {}),
        log_record=log,
    )
    
    return Response({
    'status': 'ok',
    'log_id': log.id,
    'sent': result.get('sent', 0),
    'failed': result.get('failed', 0),
    'total': result.get('total', result.get('sent', 0) + result.get('failed', 0)),
    'errors': result.get('errors', [])[:10],
    })


# ──────────────────────────────────────────────────────────
# Statistiques et rapports
# ──────────────────────────────────────────────────────────

@extend_schema(
    tags=["Prédictions — Rapports"],
    summary="Statistiques des notifications",
)
@api_view(['GET'])
def notification_stats(request):
    """
    GET /api/predictions/stats/
    Retourne les statistiques globales sur les notifications et prédictions.
    """
    total = PredictionNotification.objects.count()
    unread_count = PredictionNotification.objects.filter(is_read=False).count()
    
    # Par type
    by_type = {}
    for type_choice in ['prediction', 'report', 'alert', 'custom']:
        by_type[type_choice] = PredictionNotification.objects.filter(type=type_choice).count()
    
    # Par niveau d'affluence
    by_affluence = {}
    for level in ['low', 'medium', 'high', 'very_high']:
        by_affluence[level] = PredictionNotification.objects.filter(niveau_affluence=level).count()
    
    # Score de confiance moyen des 10 dernières prédictions
    recent = PredictionNotification.objects.filter(
        confidence_score__isnull=False
    ).order_by('-generated_at')[:10]
    
    avg_confidence = 0
    if recent:
        avg_confidence = sum(n.confidence_score for n in recent) / len(recent)
    
    return Response({
        'total': total,
        'unread_count': unread_count,
        'by_type': by_type,
        'by_affluence': by_affluence,
        'recent_avg_confidence': round(avg_confidence, 3),
    })