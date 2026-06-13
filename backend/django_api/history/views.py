# ============================================================
# history/views.py — API REST : historique visiteurs / analytics
# Source de données : data/shoppingclub_2025_2026.csv
# ============================================================

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import api_view
from rest_framework.response import Response

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