from django.db import models
from django.conf import settings


class Assessment(models.Model):
    class AssessmentType(models.TextChoices):
        PRE_TEST = 'pre_test', 'Pre-Test'
        POST_TEST = 'post_test', 'Post-Test'
        QUIZ = 'quiz', 'Quiz'
        FINAL_EXAM = 'final_exam', 'Final Exam'

    class Role(models.TextChoices):
        MODULE_QUIZ = 'module_quiz', 'Module Quiz'
        FINAL_EXAM  = 'final_exam',  'Final Exam'

    training = models.ForeignKey(
        'trainings.TrainingProgram', on_delete=models.CASCADE, related_name='assessments'
    )
    # Role distinguishes per-module quizzes from the training-level final exam
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.FINAL_EXAM,
        help_text='Module Quiz fires after the linked module; Final Exam fires after all modules.'
    )
    # Only set when role=module_quiz; one quiz per module (OneToOne enforced in clean/unique)
    module = models.OneToOneField(
        'trainings.TrainingModule', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='quiz',
        help_text='The module this quiz is attached to (Module Quiz only).'
    )
    title = models.CharField(max_length=300)
    assessment_type = models.CharField(max_length=20, choices=AssessmentType.choices, default=AssessmentType.POST_TEST)
    description = models.TextField(blank=True)
    time_limit_minutes = models.IntegerField(default=60)
    passing_score = models.IntegerField(default=75)
    max_attempts = models.IntegerField(default=3)
    shuffle_questions = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.training.code} - {self.title}"

    @property
    def question_count(self):
        return self.questions.count()

    class Meta:
        app_label = 'assessments'
        ordering = ['training', 'assessment_type']


class Question(models.Model):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = 'mc', 'Multiple Choice'
        TRUE_FALSE = 'tf', 'True or False'
        IDENTIFICATION = 'id', 'Identification'

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=5, choices=QuestionType.choices, default=QuestionType.MULTIPLE_CHOICE)
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=1)
    explanation = models.TextField(blank=True)

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:60]}"

    class Meta:
        app_label = 'assessments'
        ordering = ['assessment', 'order']


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=1)

    def __str__(self):
        return f"{'✓' if self.is_correct else '✗'} {self.choice_text}"

    class Meta:
        app_label = 'assessments'
        ordering = ['question', 'order']


class AssessmentAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In Progress'
        SUBMITTED = 'submitted', 'Submitted'
        GRADED = 'graded', 'Graded'

    enrollment = models.ForeignKey(
        'trainings.Enrollment', on_delete=models.CASCADE, related_name='attempts'
    )
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    score = models.IntegerField(null=True, blank=True)
    score_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    attempt_number = models.IntegerField(default=1)

    def calculate_score(self):
        answers = self.answers.all()
        total_points = sum(a.question.points for a in answers)
        earned_points = sum(a.question.points for a in answers if a.is_correct)
        if total_points > 0:
            self.score = earned_points
            self.score_percent = round((earned_points / total_points) * 100, 2)
            self.passed = self.score_percent >= self.assessment.passing_score
        self.status = 'graded'
        self.save()
        # Only Final Exam completion marks the enrollment as done and awards competencies
        if self.passed and self.assessment.role == Assessment.Role.FINAL_EXAM:
            self.enrollment.final_score = self.score_percent
            self.enrollment.status = 'completed'
            from django.utils import timezone
            self.enrollment.completed_at = timezone.now()
            self.enrollment.save()
            from apps.trainings.utils import award_competencies
            award_competencies(self.enrollment)
        return self.score_percent

    def __str__(self):
        return f"{self.enrollment.user} - {self.assessment.title} (Attempt {self.attempt_number})"

    class Meta:
        app_label = 'assessments'
        ordering = ['-started_at']


class Answer(models.Model):
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        app_label = 'assessments'
        unique_together = ['attempt', 'question']
