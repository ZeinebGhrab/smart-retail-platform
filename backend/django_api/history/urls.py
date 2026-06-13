from django.urls import path

from . import views

urlpatterns = [
    path("history/visitors/", views.visitor_history, name="visitor-history"),
    path("history/visitors/count/", views.visitor_count, name="visitor-count"),
    path("history/visitors/hourly/", views.hourly_flow, name="visitor-hourly"),
    path("history/visitors/forecast/", views.forecast, name="visitor-forecast"),
    path("history/summary/", views.summary, name="history-summary"),
    path("history/cameras/", views.cameras, name="history-cameras"),
]
