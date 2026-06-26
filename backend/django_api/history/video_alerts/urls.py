# ============================================================
# video_alerts/urls.py
# Routes pour les alertes vidéo
# ============================================================

from django.urls import path
from . import views

app_name = 'video_alerts'

urlpatterns = [
    # Espaces
    path('spaces/', views.list_alert_spaces, name='list-spaces'),
    path('spaces/<int:space_id>/', views.get_alert_space, name='space-detail'),
    
    # Alertes vidéo
    path('space/<int:space_id>/', views.videos_by_space, name='videos-by-space'),
    path('organization/<int:organization_id>/', views.videos_by_organization, name='videos-by-organization'),
    path('all/', views.list_all_video_alerts, name='all-videos'),
    path('<int:video_id>/', views.get_video_alert_detail, name='video-detail'),
    path('<int:video_id>/qualify/', views.qualify_video_alert, name='qualify-video'),
    
    # Statistiques
    path('stats/', views.video_alerts_stats, name='stats'),
]