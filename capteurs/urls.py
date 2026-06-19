from django.urls import path
from . import views

urlpatterns = [
    path("", views.liste, name="liste"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("capteur/<str:capteur_id>/", views.detail, name="detail"),
]