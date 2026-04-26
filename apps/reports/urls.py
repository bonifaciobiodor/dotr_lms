from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('reports/', views.reports_view, name='reports'),
    path('reports/compliance/', views.compliance_report, name='compliance_report'),
]
