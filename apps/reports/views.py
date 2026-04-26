from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from django.utils import timezone
import datetime
from django.contrib.auth import get_user_model
from apps.accounts.models import Division
User = get_user_model()
from apps.trainings.models import TrainingProgram, Enrollment, TrainingRequest
from apps.competencies.models import EmployeeCompetency, Competency
from apps.certificates.models import Certificate
from apps.accounts.decorators import role_required


@login_required
def dashboard(request):
    user = request.user
    now = timezone.now()
    today = now.date()

    if user.role in ['admin', 'hr', 'executive']:
        # Executive / HR Dashboard
        total_employees = User.objects.filter(is_active=True).count()
        total_trainings = TrainingProgram.objects.exclude(status='draft').count()
        total_enrollments = Enrollment.objects.count()
        completed_enrollments = Enrollment.objects.filter(status='completed').count()
        completion_rate = round((completed_enrollments / total_enrollments * 100) if total_enrollments else 0)
        pending_requests = TrainingRequest.objects.filter(
            status__in=['pending', 'supervisor_review', 'pending_hrdd', 'hrdd_review']
        ).count()
        ongoing_trainings = TrainingProgram.objects.filter(status='published').count()
        recent_enrollments = Enrollment.objects.select_related('user', 'training').order_by('-enrolled_at')[:8]
        upcoming_trainings = TrainingProgram.objects.filter(
            start_date__gte=today, status='published'
        ).order_by('start_date')[:5]
        # Division stats
        division_stats = Division.objects.annotate(
            emp_count=Count('user', filter=Q(user__is_active=True))
        ).values('name', 'emp_count')[:8]
        # Training type breakdown
        type_stats = TrainingProgram.objects.values('training_type').annotate(count=Count('id'))
        # Monthly completions (last 6 months)
        monthly_completions = []
        for i in range(5, -1, -1):
            month_start = (today.replace(day=1) - datetime.timedelta(days=i*28)).replace(day=1)
            month_end = (month_start + datetime.timedelta(days=32)).replace(day=1)
            count = Enrollment.objects.filter(
                status='completed',
                completed_at__gte=month_start,
                completed_at__lt=month_end
            ).count()
            monthly_completions.append({'month': month_start.strftime('%b %Y'), 'count': count})

        certs_issued = Certificate.objects.count()
        context = {
            'is_admin_view': True,
            'total_employees': total_employees,
            'total_trainings': total_trainings,
            'total_enrollments': total_enrollments,
            'completion_rate': completion_rate,
            'pending_requests': pending_requests,
            'ongoing_trainings': ongoing_trainings,
            'recent_enrollments': recent_enrollments,
            'upcoming_trainings': upcoming_trainings,
            'division_stats': list(division_stats),
            'type_stats': list(type_stats),
            'monthly_completions': monthly_completions,
            'certs_issued': certs_issued,
        }

    elif user.role == 'supervisor':
        subordinates = user.subordinates.filter(is_active=True)
        sub_ids = subordinates.values_list('id', flat=True)
        sub_enrollments = Enrollment.objects.filter(user_id__in=sub_ids)
        pending_requests = TrainingRequest.objects.filter(
            requester_id__in=sub_ids, status__in=['pending', 'supervisor_review']
        ).count()
        completion_rate = round(
            sub_enrollments.filter(status='completed').count() /
            sub_enrollments.count() * 100
            if sub_enrollments.count() > 0 else 0
        )
        context = {
            'is_supervisor_view': True,
            'subordinates': subordinates,
            'sub_enrollments': sub_enrollments.select_related('user', 'training')[:8],
            'pending_requests': pending_requests,
            'completion_rate': completion_rate,
        }

    else:
        # Employee Dashboard
        enrollments = Enrollment.objects.filter(user=user).select_related('training')
        in_progress = enrollments.filter(status__in=['enrolled', 'in_progress'])
        completed = enrollments.filter(status='completed')
        my_requests = TrainingRequest.objects.filter(user=user).select_related('training')[:5] \
            if hasattr(TrainingRequest, 'user') else \
            TrainingRequest.objects.filter(requester=user).select_related('training')[:5]
        competency_gaps = EmployeeCompetency.objects.filter(
            user=user
        ).select_related('competency')
        gaps = [ec for ec in competency_gaps if ec.get_gap() > 0]
        upcoming = TrainingProgram.objects.filter(
            status='published', start_date__gte=today
        ).order_by('start_date')[:4]
        context = {
            'is_employee_view': True,
            'enrollments': enrollments,
            'in_progress': in_progress,
            'completed': completed,
            'my_requests': my_requests,
            'competency_gaps': gaps[:5],
            'upcoming': upcoming,
        }

    return render(request, 'dashboard/dashboard.html', context)


@login_required
@role_required(['admin', 'hr'])
def reports_view(request):
    """Comprehensive reports page."""
    # Training completion report
    trainings = TrainingProgram.objects.annotate(
        total_enrolled=Count('enrollments'),
        total_completed=Count('enrollments', filter=Q(enrollments__status='completed'))
    ).exclude(status='draft')

    # Division completion stats
    divisions = Division.objects.annotate(
        emp_count=Count('user', filter=Q(user__is_active=True)),
        completed_count=Count('user__enrollments', filter=Q(user__enrollments__status='completed'))
    )

    # Competency gap summary
    from django.db.models import F, ExpressionWrapper, IntegerField
    gaps = EmployeeCompetency.objects.select_related('competency', 'user').filter(
        current_level__lt=F('target_level')
    ).annotate(gap=ExpressionWrapper(F('target_level') - F('current_level'), output_field=IntegerField()))

    return render(request, 'reports/reports.html', {
        'trainings': trainings,
        'divisions': divisions,
        'gaps': gaps,
    })


@login_required
@role_required(['admin', 'hr'])
def compliance_report(request):
    """CSC PRIME-HRM Compliance Report."""
    mandatory_trainings = TrainingProgram.objects.filter(training_type='mandatory')
    employees = User.objects.filter(is_active=True).prefetch_related('enrollments')
    compliance_data = []
    for emp in employees:
        completed_mandatory = Enrollment.objects.filter(
            user=emp,
            training__training_type='mandatory',
            status='completed'
        ).count()
        total_mandatory = mandatory_trainings.count()
        rate = round((completed_mandatory / total_mandatory * 100) if total_mandatory > 0 else 0)
        compliance_data.append({
            'employee': emp,
            'completed': completed_mandatory,
            'total': total_mandatory,
            'rate': rate,
            'compliant': completed_mandatory == total_mandatory
        })
    return render(request, 'reports/compliance.html', {
        'compliance_data': compliance_data,
        'mandatory_trainings': mandatory_trainings,
    })
