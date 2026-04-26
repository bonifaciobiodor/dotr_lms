from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda r: redirect('dashboard'), name='home'),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.reports.urls')),
    path('competencies/', include('apps.competencies.urls')),
    path('trainings/', include('apps.trainings.urls')),
    path('assessments/', include('apps.assessments.urls')),
    path('certificates/', include('apps.certificates.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
