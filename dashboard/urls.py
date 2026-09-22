from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/metrics/', views.dashboard_metrics_api, name='metrics_api'),
]
