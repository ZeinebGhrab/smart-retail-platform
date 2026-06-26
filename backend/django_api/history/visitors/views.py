# ============================================================
# history/visitors/views.py — Vues API visiteurs / analytics
# ============================================================

from rest_framework.decorators import api_view
from rest_framework.response import Response
from . import data as vd


@api_view(['GET'])
def visitor_history(request):
    """
    GET /api/history/visitors/
    Paramètres optionnels :
    - start_date, end_date : bornes de date (YYYY-MM-DD)
    - camera               : Porte_nord | Porte_sud
    - limit                : taille de page (défaut 14)
    - offset               : décalage (défaut 0)
    """
    full = vd.get_visitor_history(
        start_date=request.query_params.get('start_date'),
        end_date=request.query_params.get('end_date'),
        camera=request.query_params.get('camera'),
    )

    # ── Pagination ──────────────────────────────────────────
    try:
        limit = int(request.query_params.get('limit', 14))
    except (ValueError, TypeError):
        limit = 14
    try:
        offset = int(request.query_params.get('offset', 0))
    except (ValueError, TypeError):
        offset = 0

    all_results = full['results']
    total_count = len(all_results)
    page_results = all_results[offset: offset + limit]

    return Response({
        'start_date':  full['start_date'],
        'end_date':    full['end_date'],
        'camera':      full['camera'],
        'count':       total_count,          # total tous résultats
        'limit':       limit,
        'offset':      offset,
        'results':     page_results,         # page courante seulement
    })


@api_view(['GET'])
def visitor_count(request):
    """GET /api/history/visitors/count/"""
    return Response(vd.get_visitor_count(
        date=request.query_params.get('date'),
        camera=request.query_params.get('camera'),
    ))


@api_view(['GET'])
def hourly_flow(request):
    """GET /api/history/visitors/hourly/"""
    return Response(vd.get_hourly_visitor_flow(
        date=request.query_params.get('date'),
        camera=request.query_params.get('camera'),
    ))


@api_view(['GET'])
def forecast(request):
    """GET /api/history/visitors/forecast/"""
    return Response(vd.forecast_visitors(
        target_date=request.query_params.get('date'),
        camera=request.query_params.get('camera'),
    ))


@api_view(['GET'])
def summary(request):
    """GET /api/history/summary/"""
    return Response(vd.get_summary())


@api_view(['GET'])
def cameras(request):
    """GET /api/history/cameras/"""
    return Response({'cameras': vd.list_cameras()})