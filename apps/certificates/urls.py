from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_certificates, name='my_certificates'),
    path('all/', views.certificate_list, name='certificate_list'),
    path('<int:pk>/', views.certificate_detail, name='certificate_detail'),
    path('<int:pk>/revoke/', views.certificate_revoke, name='certificate_revoke'),
    path('issue/<int:enrollment_pk>/', views.issue_certificate, name='issue_certificate'),
    path('verify/<str:cert_number>/', views.verify_certificate, name='verify_certificate'),
    # Template management
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:pk>/activate/', views.template_activate, name='template_activate'),
    path('templates/<int:pk>/preview/', views.template_preview, name='template_preview'),
]