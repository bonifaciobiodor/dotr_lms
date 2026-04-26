from django.urls import path
from . import views

urlpatterns = [
    path('', views.training_catalog, name='training_catalog'),
    path('calendar/', views.training_calendar, name='training_calendar'),
    path('calendar/events/', views.calendar_events_api, name='calendar_events_api'),
    path('manage/', views.training_manage, name='training_manage'),
    path('create/', views.training_create, name='training_create'),
    path('my-learnings/', views.my_learnings, name='my_learnings'),
    path('requests/', views.training_request_list, name='training_request_list'),
    path('requests/<int:training_pk>/new/', views.training_request_create, name='training_request_create'),
    path('requests/<int:pk>/action/', views.training_request_action, name='training_request_action'),
    path('requests/<int:pk>/delete/', views.training_request_delete, name='training_request_delete'),
    path('enrollment/<int:enrollment_pk>/module/<int:module_pk>/complete/', views.mark_module_complete, name='mark_module_complete'),
    path('<int:pk>/', views.training_detail, name='training_detail'),
    path('<int:pk>/edit/', views.training_edit, name='training_edit'),
    path('<int:pk>/modules/', views.training_modules, name='training_modules'),
    path('<int:training_pk>/modules/<int:module_pk>/edit/', views.module_edit, name='module_edit'),
    path('<int:pk>/publish/', views.training_publish, name='training_publish'),
    path('<int:pk>/enroll/', views.enroll_direct, name='enroll_direct'),
    path('<int:pk>/learn/', views.learning_view, name='learning_view'),
    path('<int:training_pk>/enrollments/', views.enrollment_manage, name='enrollment_manage'),
    path('<int:training_pk>/attendance/', views.attendance_manage, name='attendance_manage'),
    path('nomination-form/', views.nomination_form, name='nomination_form'),
]