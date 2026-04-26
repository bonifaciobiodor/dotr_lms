from django.urls import path
from . import views

urlpatterns = [
    path('training/<int:training_pk>/', views.assessment_list, name='assessment_list'),
    path('training/<int:training_pk>/create/', views.assessment_create, name='assessment_create'),
    path('<int:pk>/questions/', views.assessment_questions, name='assessment_questions'),
    path('<int:pk>/take/', views.take_assessment, name='take_assessment'),
    path('result/<int:pk>/', views.assessment_result, name='assessment_result'),
]
