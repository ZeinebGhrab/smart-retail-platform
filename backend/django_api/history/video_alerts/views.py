# ============================================================
# video_alerts/views.py
# Vues API pour les alertes vidéo
# ============================================================

from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import VideoTheftAlert, AlertSpace
from .serializers import (
    VideoTheftAlertListSerializer,
    VideoTheftAlertDetailSerializer,
    VideoQualificationSerializer,
    AlertSpaceSerializer,
)
from ..utils import get_pagination_params


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

STATUS_PARAM = OpenApiParameter(
    "status",
    str,
    description="Filtrer par statut: PENDING, APPROVED, REJECTED",
    required=False,
)

QUALIFICATION_PARAM = OpenApiParameter(
    "qualification",
    str,
    description="Filtrer par qualification: vol, suspicious, false_alarm, ou 'null' pour non qualifiées",
    required=False,
)


# ──────────────────────────────────────────────────────────
# API : Espaces de surveillance
# ──────────────────────────────────────────────────────────

@extend_schema(
    tags=["Alertes Vidéo - Espaces"],
    summary="Liste tous les espaces de surveillance",
)
@api_view(['GET'])
def list_alert_spaces(request):
    """
    GET /api/video-alerts/spaces/
    Retourne la liste de tous les espaces de surveillance disponibles.
    """
    spaces = AlertSpace.objects.all().order_by('name')
    serializer = AlertSpaceSerializer(spaces, many=True)
    return Response({
        'count': spaces.count(),
        'results': serializer.data,
    })


@extend_schema(
    tags=["Alertes Vidéo - Espaces"],
    summary="Détails d'un espace de surveillance",
)
@api_view(['GET'])
def get_alert_space(request, space_id):
    """
    GET /api/video-alerts/spaces/<space_id>/
    Retourne les détails d'un espace spécifique.
    """
    try:
        space = AlertSpace.objects.get(id=space_id)
        serializer = AlertSpaceSerializer(space)
        return Response(serializer.data)
    except AlertSpace.DoesNotExist:
        return Response(
            {'error': f'Espace {space_id} non trouvé'},
            status=status.HTTP_404_NOT_FOUND
        )


# ──────────────────────────────────────────────────────────
# API : Alertes vidéo
# ──────────────────────────────────────────────────────────

@extend_schema(
    tags=["Alertes Vidéo"],
    summary="Alertes vidéo d'un espace spécifique",
    parameters=[STATUS_PARAM, QUALIFICATION_PARAM, PAGINATION_PARAM, OFFSET_PARAM],
)
@api_view(['GET'])
def videos_by_space(request, space_id):
    """
    GET /api/video-alerts/space/<space_id>/
    Retourne les alertes vidéo approuvées pour un espace donné.
    
    Paramètres optionnels :
    - status : Filtrer par statut
    - qualification : Filtrer par qualification (vol, suspicious, false_alarm, ou 'null' pour non qualifiées)
    - limit : Nombre max de résultats
    - offset : Décalage pour pagination
    """
    # Récupérer les alertes du space
    alerts = VideoTheftAlert.objects.filter(
        space_id=space_id,
        status='APPROVED'
    ).order_by('-recording_date')
    
    # Appliquer filtres
    status_filter = request.query_params.get('status')
    if status_filter:
        alerts = alerts.filter(status=status_filter)
    
    # FIX: Logique de filtrage améliorée et clarifiée
    qualification = request.query_params.get('qualification')
    if qualification is not None:
        if qualification == 'null':
            # Afficher les alertes non qualifiées
            alerts = alerts.filter(qualification__isnull=True)
        else:
            # Afficher les alertes avec la qualification spécifiée (vol, suspicious, false_alarm)
            alerts = alerts.filter(qualification=qualification)
    # Si qualification est None, pas de filtre appliqué (affiche tous les enregistrements)
    
    # Pagination
    limit, offset = get_pagination_params(request.query_params)
    total_count = alerts.count()
    alerts = alerts[offset:offset + limit]
    
    serializer = VideoTheftAlertListSerializer(alerts, many=True)
    return Response({
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'results': serializer.data,
    })


@extend_schema(
    tags=["Alertes Vidéo"],
    summary="Alertes vidéo d'une organisation",
    parameters=[STATUS_PARAM, QUALIFICATION_PARAM, PAGINATION_PARAM, OFFSET_PARAM],
)
@api_view(['GET'])
def videos_by_organization(request, organization_id):
    """
    GET /api/video-alerts/organization/<organization_id>/
    Retourne les alertes vidéo approuvées pour tous les espaces d'une organisation.
    
    Paramètres optionnels :
    - status : Filtrer par statut
    - qualification : Filtrer par qualification (vol, suspicious, false_alarm, ou 'null' pour non qualifiées)
    - limit : Nombre max de résultats
    - offset : Décalage pour pagination
    """
    alerts = VideoTheftAlert.objects.filter(
        space__organization_id=organization_id,
        status='APPROVED'
    ).order_by('-recording_date')
    
    # Appliquer filtres
    status_filter = request.query_params.get('status')
    if status_filter:
        alerts = alerts.filter(status=status_filter)
    
    # FIX: Logique de filtrage améliorée et clarifiée
    qualification = request.query_params.get('qualification')
    if qualification is not None:
        if qualification == 'null':
            # Afficher les alertes non qualifiées
            alerts = alerts.filter(qualification__isnull=True)
        else:
            # Afficher les alertes avec la qualification spécifiée
            alerts = alerts.filter(qualification=qualification)
    # Si qualification est None, pas de filtre appliqué
    
    # Pagination
    limit, offset = get_pagination_params(request.query_params)
    total_count = alerts.count()
    alerts = alerts[offset:offset + limit]
    
    serializer = VideoTheftAlertListSerializer(alerts, many=True)
    return Response({
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'results': serializer.data,
    })


@extend_schema(
    tags=["Alertes Vidéo"],
    summary="Toutes les alertes vidéo (approuvées)",
    parameters=[QUALIFICATION_PARAM, PAGINATION_PARAM, OFFSET_PARAM],
)
@api_view(['GET'])
def list_all_video_alerts(request):
    """
    GET /api/video-alerts/all/
    Retourne toutes les alertes vidéo approuvées de tous les espaces.
    
    Paramètres optionnels :
    - qualification : Filtrer par qualification (vol, suspicious, false_alarm, ou 'null' pour non qualifiées)
    - limit : Nombre max de résultats
    - offset : Décalage pour pagination
    """
    alerts = VideoTheftAlert.objects.filter(
        status='APPROVED'
    ).order_by('-recording_date')
    
    # FIX: Logique de filtrage améliorée et clarifiée
    qualification = request.query_params.get('qualification')
    if qualification is not None:
        if qualification == 'null':
            # Afficher les alertes non qualifiées
            alerts = alerts.filter(qualification__isnull=True)
        else:
            # Afficher les alertes avec la qualification spécifiée
            alerts = alerts.filter(qualification=qualification)
    # Si qualification est None, pas de filtre appliqué
    
    # Pagination
    limit, offset = get_pagination_params(request.query_params)
    total_count = alerts.count()
    alerts = alerts[offset:offset + limit]
    
    serializer = VideoTheftAlertListSerializer(alerts, many=True)
    return Response({
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'results': serializer.data,
    })


@extend_schema(
    tags=["Alertes Vidéo"],
    summary="Détail d'une alerte vidéo",
)
@api_view(['GET'])
def get_video_alert_detail(request, video_id):
    """
    GET /api/video-alerts/<video_id>/
    Retourne le détail complet d'une alerte vidéo.
    """
    try:
        video = VideoTheftAlert.objects.get(id=video_id)
        serializer = VideoTheftAlertDetailSerializer(video)
        return Response(serializer.data)
    except VideoTheftAlert.DoesNotExist:
        return Response(
            {'error': f'Alerte vidéo {video_id} non trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=["Alertes Vidéo"],
    summary="Qualifier une alerte vidéo",
    request=VideoQualificationSerializer,
)
@api_view(['PATCH', 'POST'])
def qualify_video_alert(request, video_id):
    """
    PATCH /api/video-alerts/<video_id>/qualify/
    POST /api/video-alerts/<video_id>/qualify/
    
    Qualifie manuellement une alerte vidéo en mettant à jour son statut.
    
    Corps de la requête :
    {
        \"status\": \"APPROVED\" | \"REJECTED\" | \"PENDING\",
        \"qualification\": \"vol\" | \"suspicious\" | \"false_alarm\",
        \"comment\": \"Commentaires supplémentaires\",
        \"assigned_to\": \"email@relecteur.com\",
        \"approval_result\": \"TP\" | \"TN\" | \"FP\" | \"FN\"
    }
    """
    try:
        video = VideoTheftAlert.objects.get(id=video_id)
    except VideoTheftAlert.DoesNotExist:
        return Response(
            {'error': f'Alerte vidéo {video_id} non trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = VideoQualificationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data

    # Mettre à jour uniquement les champs modifiés
    fields_to_update = []

    if 'status' in validated_data:
        video.status = validated_data['status']
        fields_to_update.append('status')

    if 'qualification' in validated_data:
        video.qualification = validated_data['qualification']
        video.qualification_update_date = timezone.now()
        fields_to_update.append('qualification')
        fields_to_update.append('qualification_update_date')

    if 'comment' in validated_data:
        video.comment = validated_data['comment']
        fields_to_update.append('comment')

    if 'assigned_to' in validated_data:
        video.assigned_to = validated_data['assigned_to']
        fields_to_update.append('assigned_to')

    if 'approval_result' in validated_data:
        video.approval_result = validated_data['approval_result']
        fields_to_update.append('approval_result')

    if not fields_to_update:
        return Response(
            {'error': 'Aucun champ à mettre à jour.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # update_date est NOT NULL en BD — toujours mis à jour
    video.update_date = timezone.now()
    fields_to_update.append('update_date')

    video.save(update_fields=fields_to_update)
    
    response_serializer = VideoTheftAlertDetailSerializer(video)
    return Response({
        'status': 'ok',
        'message': 'Alerte vidéo mise à jour avec succès',
        'alert': response_serializer.data,
    })


# ──────────────────────────────────────────────────────────
# API : Statistiques et rapports
# ──────────────────────────────────────────────────────────

@extend_schema(
    tags=["Alertes Vidéo - Rapports"],
    summary="Statistiques des alertes vidéo",
)
@api_view(['GET'])
def video_alerts_stats(request):
    """
    GET /api/video-alerts/stats/
    Retourne les statistiques globales sur les alertes vidéo.
    """
    total_alerts = VideoTheftAlert.objects.count()
    approved_alerts = VideoTheftAlert.objects.filter(status='APPROVED').count()
    pending_alerts = VideoTheftAlert.objects.filter(status='PENDING').count()
    rejected_alerts = VideoTheftAlert.objects.filter(status='REJECTED').count()
    
    qualified_alerts = VideoTheftAlert.objects.filter(qualification__isnull=False).count()
    
    # Alertes par qualification
    by_qualification = {
        'vol': VideoTheftAlert.objects.filter(qualification='vol').count(),
        'suspicious': VideoTheftAlert.objects.filter(qualification='suspicious').count(),
        'false_alarm': VideoTheftAlert.objects.filter(qualification='false_alarm').count(),
    }
    
    return Response({
        'total': total_alerts,
        'by_status': {
            'approved': approved_alerts,
            'pending': pending_alerts,
            'rejected': rejected_alerts,
        },
        'qualified': qualified_alerts,
        'by_qualification': by_qualification,
    })