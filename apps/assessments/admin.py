from django.contrib import admin
from .models import Assessment, Question, Choice, AssessmentAttempt, Answer


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'training', 'assessment_type', 'passing_score', 'is_active']
    list_filter = ['assessment_type', 'is_active']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'assessment', 'question_type', 'points']
    inlines = [ChoiceInline]


@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'assessment', 'status', 'score_percent', 'passed']
    list_filter = ['status', 'passed']
