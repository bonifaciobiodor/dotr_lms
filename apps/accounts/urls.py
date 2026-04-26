from django.urls import path
from . import views

urlpatterns = [
    # ── Authentication ────────────────────────────────────────────────────────
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Privacy ───────────────────────────────────────────────────────────────
    path('privacy-notice/', views.privacy_notice_view, name='privacy_notice'),

    # ── User management ───────────────────────────────────────────────────────
    path('profile/', views.profile_view, name='profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),

    # ── Divisions ─────────────────────────────────────────────────────────────
    path('divisions/', views.division_list, name='division_list'),
    path('divisions/create/', views.division_create, name='division_create'),
    path('divisions/<int:pk>/edit/', views.division_edit, name='division_edit'),
    path('divisions/<int:pk>/delete/', views.division_delete, name='division_delete'),

    # ── Audit log ─────────────────────────────────────────────────────────────
    path('audit-log/', views.audit_log, name='audit_log'),

    # ── Data Erasure (RA 10173) ───────────────────────────────────────────────
    path('erasure/request/', views.erasure_request_create, name='erasure_request_create'),
    path('erasure/', views.erasure_request_list, name='erasure_request_list'),
    path('erasure/<int:pk>/review/', views.erasure_request_review, name='erasure_request_review'),
    path('erasure/<int:pk>/process/', views.erasure_request_process, name='erasure_request_process'),

    # ── User Manual ───────────────────────────────────────────────────────────
    path('user-manual/', views.user_manual_view, name='user_manual'),

    # ── Organizational Structure ──────────────────────────────────────────────
    path('org-structure/', views.org_structure_view, name='org_structure_view'),
    path('org-structure/design/', views.org_structure_design, name='org_structure_design'),
    path('org-structure/design/<int:pk>/edit/', views.org_structure_design, name='org_structure_edit'),
    path('org-structure/save/', views.org_structure_save, name='org_structure_save'),
    path('org-structure/history/', views.org_structure_history, name='org_structure_history'),
    path('org-structure/<int:pk>/activate/', views.org_structure_activate, name='org_structure_activate'),
    path('org-structure/<int:pk>/download/', views.org_structure_download, name='org_structure_download'),
    path('org-structure/<int:pk>/delete/', views.org_structure_delete, name='org_structure_delete'),
]
