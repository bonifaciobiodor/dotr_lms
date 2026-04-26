import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from .models import TrainingProgram, TrainingModule, TrainingRequest, Enrollment, ModuleProgress, AttendanceRecord
from .utils import award_competencies
from apps.accounts.decorators import role_required
from apps.accounts.file_validators import validate_module_file
from django.contrib.auth import get_user_model
User = get_user_model()


# ─── Training Catalog ───────────────────────────────────────────────────────

@login_required
def training_calendar(request):
    """FullCalendar scheduler page."""
    return render(request, 'trainings/calendar.html', {
        'modes': TrainingProgram.DeliveryMode.choices,
        'types': TrainingProgram.TrainingType.choices,
        'statuses': TrainingProgram.Status.choices,
    })


@login_required
def calendar_events_api(request):
    """JSON API consumed by FullCalendar."""
    import json
    from django.http import JsonResponse

    # Date range filter sent by FullCalendar
    start = request.GET.get('start')
    end = request.GET.get('end')

    qs = TrainingProgram.objects.exclude(start_date__isnull=True)

    if start:
        qs = qs.filter(end_date__gte=start[:10])
    if end:
        qs = qs.filter(start_date__lte=end[:10])

    # Optional filters from UI
    mode = request.GET.get('mode')
    t_type = request.GET.get('type')
    status = request.GET.get('status')
    if mode:
        qs = qs.filter(delivery_mode=mode)
    if t_type:
        qs = qs.filter(training_type=t_type)
    if status:
        qs = qs.filter(status=status)

    # Color map by training type
    color_map = {
        'mandatory':   {'bg': '#ef4444', 'border': '#dc2626'},
        'specialized': {'bg': '#8b5cf6', 'border': '#7c3aed'},
        'optional':    {'bg': '#2563eb', 'border': '#1d4ed8'},
    }
    # Badge icon map by delivery mode
    mode_icon = {
        'online':  '💻',
        'f2f':     '🏫',
        'blended': '🔀',
        'webinar': '📡',
    }

    events = []
    for t in qs:
        colors = color_map.get(t.training_type, {'bg': '#64748b', 'border': '#475569'})
        icon = mode_icon.get(t.delivery_mode, '📚')
        events.append({
            'id': t.pk,
            'title': f"{icon} {t.title}",
            'start': t.start_date.isoformat(),
            'end': (t.end_date.isoformat() if t.end_date else t.start_date.isoformat()),
            'url': f'/trainings/{t.pk}/',
            'backgroundColor': colors['bg'],
            'borderColor': colors['border'],
            'textColor': '#ffffff',
            'extendedProps': {
                'code': t.code,
                'type': t.get_training_type_display(),
                'mode': t.get_delivery_mode_display(),
                'status': t.get_status_display(),
                'venue': t.venue or '—',
                'enrolled': t.enrollment_count,
                'max': t.max_participants,
                'duration': str(t.duration_hours),
                'description': t.description[:160] + ('…' if len(t.description) > 160 else ''),
            },
        })

    return JsonResponse(events, safe=False)


# ─── Training Catalog ────────────────────────────────────────────────────────

@login_required
def training_catalog(request):
    q = request.GET.get('q', '')
    mode = request.GET.get('mode', '')
    t_type = request.GET.get('type', '')
    trainings = TrainingProgram.objects.filter(status='published')
    if q:
        trainings = trainings.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if mode:
        trainings = trainings.filter(delivery_mode=mode)
    if t_type:
        trainings = trainings.filter(training_type=t_type)
    paginator = Paginator(trainings, 12)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'trainings/catalog.html', {
        'page_obj': page, 'q': q,
        'modes': TrainingProgram.DeliveryMode.choices,
        'types': TrainingProgram.TrainingType.choices,
    })


@login_required
def training_detail(request, pk):
    training = get_object_or_404(TrainingProgram, pk=pk)
    modules = training.modules.all()
    enrollment = None
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(user=request.user, training=training).first()
    details = [
        ('laptop', 'Mode', training.get_delivery_mode_display()),
        ('tag', 'Type', training.get_training_type_display()),
    ]
    if training.provider:
        details.append(('building', 'Provider', training.provider))
    if training.trainer:
        details.append(('user-tie', 'Trainer', training.trainer.get_full_name()))
    return render(request, 'trainings/training_detail.html', {
        'training': training, 'modules': modules, 'enrollment': enrollment, 'details': details,
        'today': timezone.now().date(),
    })


# ─── HR/Admin: Manage Trainings ──────────────────────────────────────────────

@login_required
@role_required(['admin', 'hr'])
def training_manage(request):
    trainings = TrainingProgram.objects.prefetch_related('enrollments').all()
    return render(request, 'trainings/training_manage.html', {'trainings': trainings})


@login_required
@role_required(['admin', 'hr', 'trainer'])
def training_create(request):
    from apps.competencies.models import Competency
    from apps.certificates.models import CertificateTemplate
    if request.method == 'POST':
        p = request.POST
        cert_tmpl_pk = p.get('certificate_template') or None
        cert_tmpl = CertificateTemplate.objects.filter(pk=cert_tmpl_pk).first() if cert_tmpl_pk else None
        training = TrainingProgram.objects.create(
            title=p['title'], code=p['code'], description=p['description'],
            training_type=p['training_type'], delivery_mode=p['delivery_mode'],
            max_participants=p.get('max_participants', 30),
            duration_hours=p.get('duration_hours', 8),
            passing_score=p.get('passing_score', 75),
            venue=p.get('venue', ''), provider=p.get('provider', ''),
            budget=p.get('budget') or None,
            start_date=p.get('start_date') or None,
            end_date=p.get('end_date') or None,
            registration_deadline=p.get('registration_deadline') or None,
            created_by=request.user, status='draft',
            certificate_template=cert_tmpl,
        )
        if request.FILES.get('cover_image'):
            training.cover_image = request.FILES['cover_image']
            training.save()
        training.competencies.set(request.POST.getlist('competencies'))
        messages.success(request, f'Training "{training.title}" created.')
        return redirect('training_modules', pk=training.pk)
    return render(request, 'trainings/training_form.html', {
        'title': 'Create Training Program',
        'modes': TrainingProgram.DeliveryMode.choices,
        'types': TrainingProgram.TrainingType.choices,
        'competencies': Competency.objects.filter(is_active=True).order_by('category', 'name'),
        'cert_templates': CertificateTemplate.objects.order_by('-is_active', 'name'),
    })


@login_required
@role_required(['admin', 'hr', 'trainer'])
def training_edit(request, pk):
    from apps.competencies.models import Competency
    from apps.certificates.models import CertificateTemplate
    training = get_object_or_404(TrainingProgram, pk=pk)
    if request.method == 'POST':
        p = request.POST
        cert_tmpl_pk = p.get('certificate_template') or None
        training.title = p['title']
        training.description = p['description']
        training.training_type = p['training_type']
        training.delivery_mode = p['delivery_mode']
        training.max_participants = p.get('max_participants', 30)
        training.duration_hours = p.get('duration_hours', 8)
        training.passing_score = p.get('passing_score', 75)
        training.venue = p.get('venue', '')
        training.provider = p.get('provider', '')
        training.budget = p.get('budget') or None
        training.start_date = p.get('start_date') or None
        training.end_date = p.get('end_date') or None
        training.status = p.get('status', training.status)
        training.certificate_template = CertificateTemplate.objects.filter(pk=cert_tmpl_pk).first() if cert_tmpl_pk else None
        training.save()
        training.competencies.set(request.POST.getlist('competencies'))
        messages.success(request, 'Training updated.')
        return redirect('training_detail', pk=pk)
    return render(request, 'trainings/training_form.html', {
        'title': 'Edit Training Program', 'training': training,
        'modes': TrainingProgram.DeliveryMode.choices,
        'types': TrainingProgram.TrainingType.choices,
        'statuses': TrainingProgram.Status.choices,
        'competencies': Competency.objects.filter(is_active=True).order_by('category', 'name'),
        'cert_templates': CertificateTemplate.objects.order_by('-is_active', 'name'),
    })


@login_required
@role_required(['admin', 'hr', 'trainer'])
def training_modules(request, pk):
    training = get_object_or_404(TrainingProgram, pk=pk)
    modules = training.modules.all().order_by('order')

    if request.method == 'POST':
        action = request.POST.get('action', 'add')

        if action == 'add':
            next_order = modules.count() + 1
            module = TrainingModule.objects.create(
                training=training,
                title=request.POST['title'],
                description=request.POST.get('description', ''),
                order=request.POST.get('order', next_order),
                content_type=request.POST.get('content_type', 'text'),
                content=request.POST.get('content', ''),
                duration_minutes=request.POST.get('duration_minutes', 30),
                is_required=bool(request.POST.get('is_required'))
            )
            if request.FILES.get('file_attachment'):
                try:
                    validate_module_file(request.FILES['file_attachment'])
                    module.file_attachment = request.FILES['file_attachment']
                    module.save()
                except ValueError as e:
                    module.delete()
                    messages.error(request, str(e))
                    return redirect('training_modules', pk=pk)
            messages.success(request, 'Module added successfully.')

        elif action == 'edit':
            module_id = request.POST.get('module_id')
            module = get_object_or_404(TrainingModule, pk=module_id, training=training)
            module.title = request.POST['title']
            module.description = request.POST.get('description', '')
            module.order = request.POST.get('order', module.order)
            module.content_type = request.POST.get('content_type', module.content_type)
            module.content = request.POST.get('content', '')
            module.duration_minutes = request.POST.get('duration_minutes', module.duration_minutes)
            module.is_required = bool(request.POST.get('is_required'))
            if request.FILES.get('file_attachment'):
                try:
                    validate_module_file(request.FILES['file_attachment'])
                    module.file_attachment = request.FILES['file_attachment']
                except ValueError as e:
                    messages.error(request, str(e))
                    return redirect('training_modules', pk=pk)
            module.save()
            messages.success(request, f'Module "{module.title}" updated.')

        elif action == 'delete':
            module_id = request.POST.get('module_id')
            module = get_object_or_404(TrainingModule, pk=module_id, training=training)
            title = module.title
            module.delete()
            # Re-number remaining modules
            for i, m in enumerate(training.modules.all().order_by('order'), 1):
                m.order = i
                m.save()
            messages.success(request, f'Module "{title}" deleted.')

        elif action == 'reorder':
            # Handle drag-drop reorder: receives order_<id>=<new_order>
            for key, value in request.POST.items():
                if key.startswith('order_'):
                    mod_id = key.replace('order_', '')
                    try:
                        m = TrainingModule.objects.get(pk=mod_id, training=training)
                        m.order = int(value)
                        m.save()
                    except (TrainingModule.DoesNotExist, ValueError):
                        pass
            messages.success(request, 'Module order updated.')

        return redirect('training_modules', pk=pk)

    return render(request, 'trainings/training_modules.html', {
        'training': training,
        'modules': modules,
        'content_types': TrainingModule._meta.get_field('content_type').choices,
    })


@login_required
@role_required(['admin', 'hr', 'trainer'])
def module_edit(request, training_pk, module_pk):
    """Dedicated edit page for a single module (alternative to inline)."""
    training = get_object_or_404(TrainingProgram, pk=training_pk)
    module = get_object_or_404(TrainingModule, pk=module_pk, training=training)
    if request.method == 'POST':
        module.title = request.POST['title']
        module.description = request.POST.get('description', '')
        module.order = request.POST.get('order', module.order)
        module.content_type = request.POST.get('content_type', module.content_type)
        module.content = request.POST.get('content', '')
        module.duration_minutes = request.POST.get('duration_minutes', module.duration_minutes)
        module.is_required = bool(request.POST.get('is_required'))
        module.save()
        messages.success(request, f'Module "{module.title}" updated.')
        return redirect('training_modules', pk=training_pk)
    return render(request, 'trainings/module_edit.html', {
        'training': training,
        'module': module,
        'content_types': TrainingModule._meta.get_field('content_type').choices,
    })


@login_required
@role_required(['admin', 'hr'])
def training_publish(request, pk):
    training = get_object_or_404(TrainingProgram, pk=pk)
    training.status = 'published'
    training.save()
    messages.success(request, f'"{training.title}" is now published.')
    return redirect('training_manage')


# ─── Requests & Approvals ────────────────────────────────────────────────────

@login_required
def training_request_list(request):
    TERMINAL = ('rejected', 'cancelled')
    ctx = {}

    if request.user.role in ['admin', 'hr']:
        base_qs = TrainingRequest.objects.select_related(
            'requester', 'training', 'reviewed_by_supervisor', 'reviewed_by_hr'
        )
        ctx['requests'] = base_qs.exclude(status__in=TERMINAL)
        ctx['rejected_requests'] = base_qs.filter(status='rejected')
        ctx['cancelled_requests'] = base_qs.filter(status='cancelled')
    elif request.user.role == 'supervisor':
        subordinate_ids = request.user.subordinates.values_list('id', flat=True)
        division_ids = []
        if request.user.division_id:
            from apps.accounts.models import User as UserModel
            division_ids = UserModel.objects.filter(
                division_id=request.user.division_id, is_active=True
            ).exclude(pk=request.user.pk).values_list('id', flat=True)
        reqs = TrainingRequest.objects.filter(
            Q(requester_id__in=subordinate_ids) |
            Q(requester_id__in=division_ids) |
            Q(requester=request.user)
        ).select_related('requester', 'training').distinct()
        ctx['requests'] = reqs
    else:
        ctx['requests'] = TrainingRequest.objects.filter(
            requester=request.user
        ).select_related('training')

    return render(request, 'trainings/request_list.html', ctx)


@login_required
def training_request_create(request, training_pk):
    training = get_object_or_404(TrainingProgram, pk=training_pk)
    if TrainingRequest.objects.filter(requester=request.user, training=training).exists():
        messages.warning(request, 'You have already requested this training.')
        return redirect('training_detail', pk=training_pk)
    if request.method == 'POST':
        save_as = request.POST.get('save_as', 'draft')
        status = TrainingRequest.Status.PENDING if save_as == 'submit' else TrainingRequest.Status.DRAFT
        TrainingRequest.objects.create(
            requester=request.user, training=training,
            justification=request.POST.get('justification', ''),
            status=status,
        )
        if status == TrainingRequest.Status.PENDING:
            messages.success(request, 'Training request submitted to your supervisor for review.')
        else:
            messages.success(request, 'Training request saved as draft.')
        return redirect('training_request_list')
    return render(request, 'trainings/request_form.html', {'training': training})


@login_required
def training_request_action(request, pk):
    if request.method != 'POST':
        return redirect('training_request_list')

    req = get_object_or_404(TrainingRequest, pk=pk)
    action = request.POST.get('action')
    remarks = request.POST.get('remarks', '')
    now = timezone.now()
    role = request.user.role

    # ── Employee: submit draft or cancel ──
    if action == 'submit' and req.requester == request.user and req.status == 'draft':
        req.status = TrainingRequest.Status.PENDING
        req.save()
        messages.success(request, 'Training request submitted to your supervisor for review.')

    elif action == 'cancel' and req.requester == request.user and req.status in ('draft', 'pending'):
        req.status = TrainingRequest.Status.CANCELLED
        req.save()
        messages.info(request, 'Request cancelled.')

    # ── Supervisor: stage 1 — start review (pending → supervisor_review) ──
    elif role == 'supervisor' and action == 'review' and req.status == 'pending':
        req.status = TrainingRequest.Status.SUPERVISOR_REVIEW
        req.reviewed_by_supervisor = request.user
        req.supervisor_review_date = now
        req.save()
        messages.info(request, 'Request marked as under supervisor review.')

    # ── Supervisor: stage 2 — forward to HRDD (pending or supervisor_review → pending_hrdd) ──
    elif role == 'supervisor' and action == 'forward' and req.status in ('pending', 'supervisor_review'):
        req.status = TrainingRequest.Status.PENDING_HRDD
        req.supervisor_remarks = remarks
        req.reviewed_by_supervisor = request.user
        req.supervisor_review_date = now
        req.save()
        messages.success(request, 'Request forwarded to HRDD for review and approval.')

    # ── Supervisor: reject (pending or supervisor_review) ──
    elif role == 'supervisor' and action == 'reject' and req.status in ('pending', 'supervisor_review'):
        req.status = TrainingRequest.Status.REJECTED
        req.supervisor_remarks = remarks
        req.reviewed_by_supervisor = request.user
        req.supervisor_review_date = now
        req.save()
        messages.info(request, 'Request rejected.')

    # ── HRDD: stage 3 — start review (pending_hrdd → hrdd_review) ──
    elif role == 'hr' and action == 'review' and req.status == 'pending_hrdd':
        req.status = TrainingRequest.Status.HRDD_REVIEW
        req.reviewed_by_hr = request.user
        req.hr_review_date = now
        req.save()
        messages.info(request, 'Request marked as under HRDD review.')

    # ── HRDD: approve (pending_hrdd or hrdd_review → approved + enroll) ──
    elif role == 'hr' and action == 'approve' and req.status in ('pending_hrdd', 'hrdd_review'):
        req.status = TrainingRequest.Status.APPROVED
        req.hr_remarks = remarks
        req.reviewed_by_hr = request.user
        req.hr_review_date = now
        req.save()
        Enrollment.objects.get_or_create(user=req.requester, training=req.training)
        messages.success(request, f'{req.requester.get_full_name()} approved and auto-enrolled in "{req.training.title}".')

    # ── HRDD: reject (pending_hrdd or hrdd_review) ──
    elif role == 'hr' and action == 'reject' and req.status in ('pending_hrdd', 'hrdd_review'):
        req.status = TrainingRequest.Status.REJECTED
        req.hr_remarks = remarks
        req.reviewed_by_hr = request.user
        req.hr_review_date = now
        req.save()
        messages.info(request, 'Request rejected.')

    # ── Admin: can approve/reject at ANY stage ──
    elif role == 'admin':
        if action == 'approve':
            if req.status in ('draft', 'pending', 'supervisor_review'):
                req.reviewed_by_supervisor = request.user
                req.supervisor_review_date = now
            req.status = TrainingRequest.Status.APPROVED
            req.hr_remarks = remarks or 'Approved by Admin'
            req.reviewed_by_hr = request.user
            req.hr_review_date = now
            req.save()
            Enrollment.objects.get_or_create(user=req.requester, training=req.training)
            messages.success(request, f'{req.requester.get_full_name()} approved and auto-enrolled in "{req.training.title}".')
        elif action == 'reject':
            req.status = TrainingRequest.Status.REJECTED
            req.hr_remarks = remarks
            req.reviewed_by_hr = request.user
            req.hr_review_date = now
            req.save()
            messages.info(request, 'Request rejected.')

    else:
        messages.error(request, 'You are not authorised to take this action on the current request status.')

    return redirect('training_request_list')


@login_required
def training_request_delete(request, pk):
    """Allow admin/hr to delete a rejected or cancelled request so the employee can re-request."""
    if request.user.role not in ['admin', 'hr']:
        messages.error(request, 'You are not authorised to delete training requests.')
        return redirect('training_request_list')

    req = get_object_or_404(TrainingRequest, pk=pk, status__in=['rejected', 'cancelled'])
    if request.method == 'POST':
        employee_name = req.requester.get_full_name()
        training_title = req.training.title
        req.delete()
        messages.success(request, f'Request by {employee_name} for "{training_title}" has been deleted. The employee may now re-submit.')
    return redirect('training_request_list')


# ─── Enrollment & Learning ───────────────────────────────────────────────────

@login_required
def my_learnings(request):
    enrollments = Enrollment.objects.filter(user=request.user).select_related('training')
    return render(request, 'trainings/my_learnings.html', {'enrollments': enrollments, 'today': timezone.now().date()})


@login_required
def enroll_direct(request, pk):
    """Direct enrollment for open trainings."""
    training = get_object_or_404(TrainingProgram, pk=pk, status='published')
    enrollment, created = Enrollment.objects.get_or_create(user=request.user, training=training)
    if created:
        messages.success(request, f'Enrolled in "{training.title}".')
    else:
        messages.info(request, 'You are already enrolled.')
    return redirect('learning_view', pk=pk)


@login_required
def learning_view(request, pk):
    """The learning interface for enrolled users."""
    training = get_object_or_404(TrainingProgram, pk=pk)
    enrollment = get_object_or_404(Enrollment, user=request.user, training=training)
    modules = list(training.modules.all())
    module_progress = {
        mp.module_id: mp for mp in
        ModuleProgress.objects.filter(enrollment=enrollment)
    }
    # Annotate each module with its completion status so the template needs no custom filter
    completed_ids = {mid for mid, mp in module_progress.items() if mp.is_completed}

    # Annotate modules with their quiz and the learner's quiz attempt status
    from apps.assessments.models import Assessment as AssessmentModel, AssessmentAttempt
    quiz_attempts = {
        a.assessment_id: a
        for a in AssessmentAttempt.objects.filter(
            enrollment=enrollment,
            assessment__role=AssessmentModel.Role.MODULE_QUIZ
        ).order_by('-started_at')
    }
    for module in modules:
        module.is_done = module.pk in completed_ids
        quiz = getattr(module, 'quiz', None)
        module.has_quiz   = bool(quiz and quiz.is_active)
        module.quiz_obj   = quiz if module.has_quiz else None
        if module.has_quiz and quiz.pk in quiz_attempts:
            attempt = quiz_attempts[quiz.pk]
            module.quiz_taken  = True
            module.quiz_passed = attempt.passed
            module.quiz_score  = attempt.score_percent
        else:
            module.quiz_taken  = False
            module.quiz_passed = None
            module.quiz_score  = None

    completed = len(completed_ids)
    total = len(modules)
    progress = round((completed / total) * 100) if total > 0 else 0
    if progress != enrollment.progress_percent:
        enrollment.progress_percent = progress
        if progress == 100 and enrollment.status == 'enrolled':
            enrollment.status = 'in_progress'
        enrollment.save()

    current_module_id = request.GET.get('module')
    current_module = None
    video_embed_url = None
    if current_module_id:
        current_module = get_object_or_404(TrainingModule, pk=current_module_id, training=training)
        if current_module.content_type == 'video':
            content = (current_module.content or '').strip()
            video_id = None
            if 'youtube.com/embed/' in content:
                # Covers both full URLs and pasted <iframe> embed codes
                m = re.search(r'embed/([a-zA-Z0-9_-]+)', content)
                if m:
                    video_id = m.group(1)
            elif 'youtube.com/watch' in content:
                m = re.search(r'[?&]v=([a-zA-Z0-9_-]+)', content)
                if m:
                    video_id = m.group(1)
            elif 'youtu.be/' in content:
                m = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', content)
                if m:
                    video_id = m.group(1)
            elif 'youtube.com/shorts/' in content:
                m = re.search(r'shorts/([a-zA-Z0-9_-]+)', content)
                if m:
                    video_id = m.group(1)
            else:
                # Bare video ID params e.g. "v=ABC123" or "v=ABC123&list=PL..."
                m = re.search(r'(?:^|[?&])v=([a-zA-Z0-9_-]+)', content)
                if m:
                    video_id = m.group(1)
            if video_id:
                video_embed_url = f'https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1'
            elif 'youtube.com' in content or 'youtu.be' in content:
                # Unrecognised YouTube URL — show in iframe as-is
                video_embed_url = content

    from apps.assessments.models import Assessment as AssessmentModel
    final_exam = training.assessments.filter(
        is_active=True, role=AssessmentModel.Role.FINAL_EXAM
    ).first()
    return render(request, 'trainings/learning_view.html', {
        'training': training, 'enrollment': enrollment,
        'modules': modules, 'completed_ids': completed_ids,
        'current_module': current_module, 'progress': progress,
        'video_embed_url': video_embed_url,
        'final_exam': final_exam,
        'today': timezone.now().date(),
    })


@login_required
def mark_module_complete(request, enrollment_pk, module_pk):
    if request.method != 'POST':
        return redirect('learning_view', pk=module_pk)

    enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, user=request.user)
    module = get_object_or_404(TrainingModule, pk=module_pk, training=enrollment.training)
    mp, created = ModuleProgress.objects.get_or_create(enrollment=enrollment, module=module)
    if not mp.is_completed:
        mp.is_completed = True
        mp.completed_at = timezone.now()
        mp.save()

    # Recalculate progress
    total = enrollment.training.modules.count()
    completed_count = ModuleProgress.objects.filter(enrollment=enrollment, is_completed=True).count()
    enrollment.progress_percent = round((completed_count / total) * 100) if total > 0 else 0
    all_done = (completed_count >= total)

    if all_done:
        enrollment.status = Enrollment.Status.IN_PROGRESS
        enrollment.save()
        # Check for Final Exam (fires only when ALL modules are done)
        from apps.assessments.models import Assessment as AssessmentModel
        final_exam = enrollment.training.assessments.filter(
            is_active=True, role=AssessmentModel.Role.FINAL_EXAM
        ).first()
        if final_exam:
            messages.success(request, '🎓 All modules complete! Take the Final Exam to earn your certificate.')
            return redirect('take_assessment', pk=final_exam.pk)
        else:
            enrollment.status = Enrollment.Status.COMPLETED
            enrollment.final_score = 100
            enrollment.completed_at = timezone.now()
            enrollment.save()
            _auto_issue_certificate(enrollment, request=request)
            award_competencies(enrollment)
            messages.success(request, '🎉 Training completed! Your certificate has been issued.')
            return redirect('learning_view', pk=enrollment.training_id)
    else:
        enrollment.save()
        # Check if this module has a quiz attached — redirect to it
        from apps.assessments.models import Assessment as AssessmentModel
        module_quiz = getattr(module, 'quiz', None)
        if module_quiz and module_quiz.is_active:
            messages.info(request, f'Module complete! Take the short quiz to reinforce your learning.')
            return redirect('take_assessment', pk=module_quiz.pk)
        messages.success(request, f'Module "{module.title}" marked as complete. Keep going!')

    return redirect('learning_view', pk=enrollment.training_id)


def _auto_issue_certificate(enrollment, request=None):
    """Auto-issue certificate when enrollment is completed."""
    from apps.certificates.models import Certificate, CertificateTemplate
    if enrollment.status == Enrollment.Status.COMPLETED:
        template = CertificateTemplate.get_active()
        cert, created = Certificate.objects.get_or_create(
            enrollment=enrollment,
            defaults={
                'certificate_number': Certificate.generate_certificate_number(),
                'template': template,
            }
        )
        if created:
            cert.generate_qr(request=request)
        return cert
    return None


@login_required
@role_required(['admin', 'hr', 'trainer'])
def enrollment_manage(request, training_pk):
    training = get_object_or_404(TrainingProgram, pk=training_pk)
    enrollments = Enrollment.objects.filter(training=training).select_related('user')
    users = User.objects.filter(is_active=True).exclude(
        id__in=enrollments.values_list('user_id', flat=True)
    )
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            user = get_object_or_404(User, pk=user_id)
            Enrollment.objects.get_or_create(user=user, training=training)
            messages.success(request, f'{user.get_full_name()} enrolled.')
        return redirect('enrollment_manage', training_pk=training_pk)
    return render(request, 'trainings/enrollment_manage.html', {
        'training': training, 'enrollments': enrollments, 'available_users': users
    })


@login_required
@role_required(['admin', 'hr', 'trainer'])
def attendance_manage(request, training_pk):
    training = get_object_or_404(TrainingProgram, pk=training_pk)
    enrollments = Enrollment.objects.filter(training=training).select_related('user')
    import datetime
    today = datetime.date.today()
    if request.method == 'POST':
        date_str = request.POST.get('date', str(today))
        date = datetime.date.fromisoformat(date_str)
        for enrollment in enrollments:
            is_present = bool(request.POST.get(f'present_{enrollment.id}'))
            time_in_str = request.POST.get(f'time_in_{enrollment.id}')
            time_out_str = request.POST.get(f'time_out_{enrollment.id}')
            AttendanceRecord.objects.update_or_create(
                enrollment=enrollment, date=date,
                defaults={
                    'is_present': is_present,
                    'time_in': time_in_str or None,
                    'time_out': time_out_str or None,
                    'recorded_by': request.user
                }
            )
        messages.success(request, 'Attendance recorded.')
    attendance_dates = AttendanceRecord.objects.filter(
        enrollment__training=training
    ).values_list('date', flat=True).distinct()
    return render(request, 'trainings/attendance.html', {
        'training': training, 'enrollments': enrollments,
        'today': today, 'attendance_dates': attendance_dates
    })


# ─── Nomination Form ─────────────────────────────────────────────────────────

@login_required
def nomination_form(request):
    import json as _json
    gedsi_questions = [
        'Do you have mobility problems? Like difficulty in walking and/or climbing stairs?',
        'Are you having an emotional/behavioural problem?',
        'Do you have difficulty in reading and identifying speech sounds?',
        'Do you have difficulty communicating?',
        'Do you have difficulty remembering or concentrating?',
        'Do you have difficulty in doing simple arithmetic calculations?',
        'Do you have difficulty in reading even with corrective lenses?',
        'Do you have any difficulty in hearing?',
    ]
    outsource_trainings = (
        TrainingProgram.objects
        .filter(delivery_mode='outsource')
        .exclude(status__in=['draft', 'cancelled'])
        .prefetch_related('competencies')
        .order_by('title')
    )
    trainings_data = {}
    for t in outsource_trainings:
        competencies_list = list(
            t.competencies.values('name', 'category')
        )
        categories = list({c['category'] for c in competencies_list})
        trainings_data[t.pk] = {
            'title': t.title,
            'start_date': str(t.start_date) if t.start_date else '',
            'end_date': str(t.end_date) if t.end_date else '',
            'venue': t.venue,
            'categories': categories,
            'competencies': competencies_list,
        }
    u = request.user
    years_in_service = ''
    if u.date_hired:
        today = timezone.now().date()
        delta_months = (today.year - u.date_hired.year) * 12 + (today.month - u.date_hired.month)
        yrs, mos = divmod(delta_months, 12)
        parts = []
        if yrs:
            parts.append(f"{yrs} yr{'s' if yrs > 1 else ''}")
        if mos:
            parts.append(f"{mos} mo{'s' if mos > 1 else ''}")
        years_in_service = ', '.join(parts) if parts else 'Less than 1 month'

    return render(request, 'trainings/nomination_form.html', {
        'gedsi_questions': gedsi_questions,
        'today': timezone.now().date(),
        'outsource_trainings': outsource_trainings,
        'trainings_json': _json.dumps(trainings_data),
        'years_in_service': years_in_service,
    })