from django.contrib import admin
from .models import (
    Competency, PositionCompetency, EmployeeCompetency,
    IndividualDevelopmentPlan, IDPActivity,
    JobAnalysisEntry, SecondaryDuty, RequiredSkill, ToolEquipment,
    JAFRevisionComment,
    DOTrCompetency, DOTrCompetencyIndicator, DOTrOfficeMandate,
)


@admin.register(Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'code']


@admin.register(PositionCompetency)
class PositionCompetencyAdmin(admin.ModelAdmin):
    list_display = ['position', 'competency', 'required_level']
    list_filter = ['required_level']


@admin.register(EmployeeCompetency)
class EmployeeCompetencyAdmin(admin.ModelAdmin):
    list_display = ['user', 'competency', 'current_level', 'target_level']
    list_filter = ['current_level', 'target_level']


class IDPActivityInline(admin.TabularInline):
    model = IDPActivity
    extra = 1


@admin.register(IndividualDevelopmentPlan)
class IDPAdmin(admin.ModelAdmin):
    list_display = ['user', 'year', 'status', 'approved_by']
    list_filter = ['status', 'year']
    inlines = [IDPActivityInline]


# ── Job Analysis Form ──────────────────────────────────────────────────────────

class SecondaryDutyInline(admin.TabularInline):
    model = SecondaryDuty
    extra = 0
    fields = ['order', 'task', 'frequency']
    ordering = ['order']


class RequiredSkillInline(admin.TabularInline):
    model = RequiredSkill
    extra = 0
    fields = ['order', 'competency', 'skill_name', 'proficiency_level']
    ordering = ['order']
    autocomplete_fields = ['competency']


class ToolEquipmentInline(admin.TabularInline):
    model = ToolEquipment
    extra = 0
    fields = ['order', 'name']
    ordering = ['order']


class JAFRevisionCommentInline(admin.TabularInline):
    model = JAFRevisionComment
    extra = 0
    fields = ['commented_by', 'comment', 'commented_at']
    readonly_fields = ['commented_at']
    ordering = ['commented_at']


@admin.register(JobAnalysisEntry)
class JobAnalysisEntryAdmin(admin.ModelAdmin):
    list_display  = [
        'full_name', 'position_title', 'employee_division',
        'status', 'supervisor_created', 'reviewed_by', 'approved_by',
        'created_at',
    ]
    list_filter   = ['status', 'supervisor_created']
    search_fields = ['full_name', 'position_title', 'office_service_division']
    readonly_fields = [
        'created_at', 'updated_at',
        'certified_date', 'reviewed_date', 'approved_date',
    ]
    fieldsets = [
        ('Header', {
            'fields': [
                'employee',
                ('full_name', 'position_title'),
                ('office_service_division', 'section_project_unit'),
                'alternate_position',
            ]
        }),
        ('Job Content', {
            'fields': ['job_purpose', 'main_duties', 'challenges_critical_issues', 'additional_comments']
        }),
        ('Workflow', {
            'fields': [
                'status', 'supervisor_created',
                ('reviewed_by', 'reviewed_date'),
                ('approved_by', 'approved_date'),
                'rejection_comment',
                ('created_at', 'updated_at'),
            ]
        }),
    ]
    inlines = [
        SecondaryDutyInline,
        RequiredSkillInline,
        ToolEquipmentInline,
        JAFRevisionCommentInline,
    ]

    @admin.display(description='Division')
    def employee_division(self, obj):
        div = getattr(obj.employee, 'division', None)
        return str(div) if div else '—'


# ── DOTr Competency Framework ─────────────────────────────────────────────────

class DOTrOfficeMandateInline(admin.TabularInline):
    model = DOTrOfficeMandate
    extra = 1
    fields = ['order', 'description']
    ordering = ['order']


@admin.register(DOTrOfficeMandate)
class DOTrOfficeMandateAdmin(admin.ModelAdmin):
    list_display = ['division', 'order', 'description']
    list_filter = ['division']
    search_fields = ['description', 'division__name']


class DOTrIndicatorInline(admin.TabularInline):
    model = DOTrCompetencyIndicator
    extra = 2
    fields = ['level', 'indicator_number', 'description', 'order']
    ordering = ['level', 'order']


@admin.register(DOTrCompetency)
class DOTrCompetencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'office', 'order', 'is_active', 'created_at']
    list_filter = ['type', 'is_active']
    search_fields = ['name', 'office']
    inlines = [DOTrIndicatorInline]


@admin.register(DOTrCompetencyIndicator)
class DOTrCompetencyIndicatorAdmin(admin.ModelAdmin):
    list_display = ['competency', 'level', 'indicator_number', 'order']
    list_filter = ['level', 'competency__type']
    search_fields = ['description', 'competency__name']
