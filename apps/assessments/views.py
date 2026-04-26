from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Assessment, Question, Choice, AssessmentAttempt, Answer
from apps.trainings.models import TrainingProgram, Enrollment
from apps.accounts.decorators import role_required


@login_required
@role_required(['admin', 'hr', 'trainer'])
def assessment_list(request, training_pk):
    training = get_object_or_404(TrainingProgram, pk=training_pk)
    assessments = training.assessments.select_related('module').all()
    return render(request, 'assessments/assessment_list.html', {
        'training': training,
        'assessments': assessments,
        'final_exams':   assessments.filter(role=Assessment.Role.FINAL_EXAM).count(),
        'module_quizzes': assessments.filter(role=Assessment.Role.MODULE_QUIZ).count(),
    })


@login_required
@role_required(['admin', 'hr', 'trainer'])
def assessment_create(request, training_pk):
    from apps.trainings.models import TrainingModule
    training = get_object_or_404(TrainingProgram, pk=training_pk)
    modules = training.modules.order_by('order')
    # Modules that already have a quiz (exclude from dropdown for new ones)
    taken_module_ids = set(
        Assessment.objects.filter(training=training, module__isnull=False)
        .values_list('module_id', flat=True)
    )
    available_modules = [m for m in modules if m.pk not in taken_module_ids]

    if request.method == 'POST':
        p = request.POST
        role = p.get('role', Assessment.Role.FINAL_EXAM)
        module = None
        if role == Assessment.Role.MODULE_QUIZ:
            module_pk = p.get('module_id')
            if module_pk:
                module = get_object_or_404(TrainingModule, pk=module_pk, training=training)
        assessment = Assessment.objects.create(
            training=training,
            role=role,
            module=module,
            title=p['title'],
            assessment_type=p['assessment_type'],
            description=p.get('description', ''),
            time_limit_minutes=p.get('time_limit_minutes', 30 if role == Assessment.Role.MODULE_QUIZ else 60),
            passing_score=p.get('passing_score', 75),
            max_attempts=p.get('max_attempts', 3),
            shuffle_questions=bool(p.get('shuffle_questions')),
            created_by=request.user
        )
        messages.success(request, f'{"Module Quiz" if role == Assessment.Role.MODULE_QUIZ else "Final Exam"} created. Add questions below.')
        return redirect('assessment_questions', pk=assessment.pk)
    return render(request, 'assessments/assessment_form.html', {
        'training': training,
        'types': Assessment.AssessmentType.choices,
        'roles': Assessment.Role.choices,
        'available_modules': available_modules,
        'title': 'Create Assessment',
    })


@login_required
@role_required(['admin', 'hr', 'trainer'])
def assessment_questions(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)
    questions = assessment.questions.prefetch_related('choices').all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_question':
            q = Question.objects.create(
                assessment=assessment,
                question_text=request.POST['question_text'],
                question_type=request.POST['question_type'],
                points=request.POST.get('points', 1),
                order=questions.count() + 1
            )
            # Add choices
            for i in range(1, 6):
                ct = request.POST.get(f'choice_{i}')
                if ct:
                    is_correct = (request.POST.get('correct_choice') == str(i))
                    Choice.objects.create(question=q, choice_text=ct, is_correct=is_correct, order=i)
            messages.success(request, 'Question added.')
        elif action == 'delete_question':
            qid = request.POST.get('question_id')
            Question.objects.filter(pk=qid, assessment=assessment).delete()
            messages.success(request, 'Question deleted.')
        return redirect('assessment_questions', pk=pk)
    return render(request, 'assessments/assessment_questions.html', {
        'assessment': assessment, 'questions': questions,
        'question_types': Question.QuestionType.choices
    })


@login_required
def take_assessment(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk, is_active=True)
    enrollment = get_object_or_404(Enrollment, user=request.user, training=assessment.training)
    # Check attempts
    attempt_count = AssessmentAttempt.objects.filter(
        enrollment=enrollment, assessment=assessment
    ).count()
    if attempt_count >= assessment.max_attempts:
        messages.error(request, f'Maximum attempts ({assessment.max_attempts}) reached.')
        return redirect('learning_view', pk=assessment.training_id)
    # Check for in-progress attempt
    attempt = AssessmentAttempt.objects.filter(
        enrollment=enrollment, assessment=assessment, status='in_progress'
    ).first()
    if not attempt:
        attempt = AssessmentAttempt.objects.create(
            enrollment=enrollment, assessment=assessment,
            attempt_number=attempt_count + 1
        )
    questions = assessment.questions.prefetch_related('choices').all()
    if assessment.shuffle_questions:
        questions = questions.order_by('?')
    if request.method == 'POST':
        for question in assessment.questions.all():
            selected_choice_id = request.POST.get(f'q_{question.id}')
            text_answer = request.POST.get(f'text_{question.id}', '')
            is_correct = False
            selected_choice = None
            if selected_choice_id:
                try:
                    selected_choice = Choice.objects.get(pk=selected_choice_id, question=question)
                    is_correct = selected_choice.is_correct
                except (Choice.DoesNotExist, ValueError):
                    pass
            Answer.objects.update_or_create(
                attempt=attempt, question=question,
                defaults={
                    'selected_choice': selected_choice,
                    'text_answer': text_answer,
                    'is_correct': is_correct
                }
            )
        attempt.submitted_at = timezone.now()
        score_percent = attempt.calculate_score()
        is_module_quiz = (assessment.role == Assessment.Role.MODULE_QUIZ)

        if is_module_quiz:
            # Module quiz: no certificate, just show feedback and go back to learning
            if attempt.passed:
                messages.success(request, f'✅ Quiz passed! Score: {score_percent}%. Keep going!')
            else:
                remaining = assessment.max_attempts - AssessmentAttempt.objects.filter(
                    enrollment=attempt.enrollment, assessment=assessment
                ).count()
                if remaining > 0:
                    messages.warning(request, f'Score: {score_percent}% — below passing ({assessment.passing_score}%). {remaining} attempt(s) left.')
                else:
                    messages.error(request, f'Score: {score_percent}%. No more attempts. Review the module and continue.')
            return redirect('assessment_result', pk=attempt.pk)

        # Final Exam: auto-issue certificate if passed
        if attempt.passed:
            from apps.certificates.models import Certificate, CertificateTemplate
            template = CertificateTemplate.get_active()
            cert, created = Certificate.objects.get_or_create(
                enrollment=attempt.enrollment,
                defaults={
                    'certificate_number': Certificate.generate_certificate_number(),
                    'template': template,
                }
            )
            if created:
                cert.generate_qr(request=request)
            if created:
                messages.success(request, f'🎉 Congratulations! You passed with {score_percent}%! Your certificate has been issued.')
            else:
                messages.success(request, f'Assessment submitted! Score: {score_percent}%')
        else:
            remaining = attempt.assessment.max_attempts - AssessmentAttempt.objects.filter(
                enrollment=attempt.enrollment, assessment=attempt.assessment
            ).count()
            if remaining > 0:
                messages.warning(request, f'Score: {score_percent}%. Passing score is {attempt.assessment.passing_score}%. You have {remaining} attempt(s) remaining.')
            else:
                messages.error(request, f'Score: {score_percent}%. No more attempts remaining.')
        return redirect('assessment_result', pk=attempt.pk)
    return render(request, 'assessments/take_assessment.html', {
        'assessment': assessment, 'attempt': attempt, 'questions': questions
    })


@login_required
def assessment_result(request, pk):
    attempt = get_object_or_404(AssessmentAttempt, pk=pk, enrollment__user=request.user)
    answers = attempt.answers.select_related('question', 'selected_choice').all()
    is_module_quiz = (attempt.assessment.role == Assessment.Role.MODULE_QUIZ)
    attempts_used = AssessmentAttempt.objects.filter(
        enrollment=attempt.enrollment, assessment=attempt.assessment
    ).count()
    return render(request, 'assessments/assessment_result.html', {
        'attempt': attempt,
        'answers': answers,
        'is_module_quiz': is_module_quiz,
        'attempts_used': attempts_used,
    })