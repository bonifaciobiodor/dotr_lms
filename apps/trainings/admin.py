from django.contrib import admin
from .models import (
    TrainingProgram, TrainingModule, TrainingRequest,
    Enrollment, ModuleProgress, AttendanceRecord
)


class TrainingModuleInline(admin.TabularInline):
    model = TrainingModule
    extra = 1
    fields = ['order', 'title', 'content_type', 'duration_minutes', 'is_required']


@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'training_type', 'delivery_mode', 'status', 'enrollment_count']
    list_filter = ['status', 'training_type', 'delivery_mode']
    search_fields = ['title', 'code']
    inlines = [TrainingModuleInline]


@admin.register(TrainingRequest)
class TrainingRequestAdmin(admin.ModelAdmin):
    list_display = ['requester', 'training', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['requester__first_name', 'requester__last_name', 'training__title']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'training', 'status', 'progress_percent', 'final_score', 'enrolled_at']
    list_filter = ['status']
    search_fields = ['user__first_name', 'user__last_name', 'training__title']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'date', 'is_present', 'time_in', 'time_out']
    list_filter = ['is_present', 'date']
