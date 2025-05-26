# EVA_backend/api_service/urls.py
from django.urls import path
from . import views
urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('health_check/', views.health_check, name='health_check_alt'),
    path('modules/status', views.modules_status, name='modules_status'),
]