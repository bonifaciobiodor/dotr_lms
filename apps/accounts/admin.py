from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Division, AuditLog


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'head']
    search_fields = ['name', 'code']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'get_full_name', 'employee_id', 'role', 'division', 'is_active']
    list_filter = ['role', 'division', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'employee_id']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('DOTR Info', {'fields': ('role', 'employee_id', 'division', 'position',
                                   'salary_grade', 'employment_status', 'contact_number',
                                   'date_hired', 'supervisor', 'avatar')}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'timestamp']
    list_filter = ['action', 'model_name']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'details', 'ip_address', 'timestamp']
