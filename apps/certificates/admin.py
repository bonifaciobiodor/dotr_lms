from django.contrib import admin
from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'get_employee', 'get_training', 'issued_date', 'is_valid']
    list_filter = ['is_valid', 'issued_date']
    search_fields = ['certificate_number', 'enrollment__user__first_name', 'enrollment__user__last_name']

    def get_employee(self, obj):
        return obj.enrollment.user.get_full_name()
    get_employee.short_description = 'Employee'

    def get_training(self, obj):
        return obj.enrollment.training.title
    get_training.short_description = 'Training'
