# ============================================================
# history/visitors/urls.py — Routes visiteurs / analytics
# ============================================================

from django.urls import path
from . import views

app_name = 'visitors'

urlpatterns = [
    path('visitors/',          views.visitor_history, name='history'),
    path('visitors/count/',    views.visitor_count,   name='count'),
    path('visitors/hourly/',   views.hourly_flow,     name='hourly'),
    path('visitors/forecast/', views.forecast,        name='forecast'),
    path('summary/',           views.summary,         name='summary'),
    path('cameras/',           views.cameras,         name='cameras'),
]