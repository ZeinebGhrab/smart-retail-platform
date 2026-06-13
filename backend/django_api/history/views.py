# ============================================================
# history/views.py — API REST : historique visiteurs / analytics
# Source de données : data/shoppingclub_2025_2026.csv
# ============================================================

from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import visitor_data as vd


@api_view(["GET"])
def visitor_history(request):
    """
    GET /api/history/visitors/

    Historique journalier des visiteurs (analytics).

    Query params (optionnels) :
      - start_date : "YYYY-MM-DD"
      - end_date   : "YYYY-MM-DD"
      - camera     : "Porte_nord" | "Porte_sud" (sinon: total des deux)
    """
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    camera = request.query_params.get("camera")

    result = vd.get_visitor_history(start_date=start_date, end_date=end_date, camera=camera)
    return Response(result)


@api_view(["GET"])
def visitor_count(request):
    """
    GET /api/history/visitors/count/

    Nombre de visiteurs pour une date donnée (par défaut la dernière
    date disponible dans le CSV).

    Query params (optionnels) :
      - date   : "YYYY-MM-DD"
      - camera : "Porte_nord" | "Porte_sud"
    """
    date = request.query_params.get("date")
    camera = request.query_params.get("camera")

    result = vd.get_visitor_count(date=date, camera=camera)
    return Response(result)


@api_view(["GET"])
def hourly_flow(request):
    """
    GET /api/history/visitors/hourly/

    Flux horaire de visiteurs pour une date donnée.

    Query params (optionnels) :
      - date   : "YYYY-MM-DD"
      - camera : "Porte_nord" | "Porte_sud"
    """
    date = request.query_params.get("date")
    camera = request.query_params.get("camera")

    result = vd.get_hourly_visitor_flow(date=date, camera=camera)
    return Response(result)


@api_view(["GET"])
def forecast(request):
    """
    GET /api/history/visitors/forecast/

    Prévision du nombre de visiteurs (régression linéaire + ajustement
    par jour de semaine).

    Query params (optionnels) :
      - date   : "YYYY-MM-DD" (par défaut : demain)
      - camera : "Porte_nord" | "Porte_sud"
    """
    date = request.query_params.get("date")
    camera = request.query_params.get("camera")

    result = vd.forecast_visitors(target_date=date, camera=camera)
    return Response(result)


@api_view(["GET"])
def summary(request):
    """
    GET /api/history/summary/

    KPIs globaux : période couverte, total visiteurs, répartition
    par caméra / genre / tranche d'âge.
    """
    return Response(vd.get_summary())


@api_view(["GET"])
def cameras(request):
    """GET /api/history/cameras/ — liste des caméras disponibles."""
    return Response({"cameras": vd.list_cameras()})
