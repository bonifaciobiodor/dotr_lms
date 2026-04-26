from django.db import models
from django.conf import settings


class TrainingProgram(models.Model):
    class TrainingType(models.TextChoices):
        MANDATORY = 'mandatory', 'Mandatory'
        OPTIONAL = 'optional', 'Optional'
        SPECIALIZED = 'specialized', 'Specialized'

    class DeliveryMode(models.TextChoices):
        ONLINE = 'online', 'Online / e-Learning'
        FACE_TO_FACE = 'f2f', 'Face-to-Face'
        BLENDED = 'blended', 'Blended Learning'
        WEBINAR = 'webinar', 'Webinar'
        OUTSOURCE = 'outsource', 'Out Source'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ONGOING = 'ongoing', 'Ongoing'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    title = models.CharField(max_length=300)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    training_type = models.CharField(max_length=20, choices=TrainingType.choices, default=TrainingType.OPTIONAL)
    delivery_mode = models.CharField(max_length=20, choices=DeliveryMode.choices, default=DeliveryMode.ONLINE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    target_participants = models.TextField(blank=True)
    max_participants = models.IntegerField(default=30)
    duration_hours = models.DecimalField(max_digits=5, decimal_places=1, default=8.0)
    venue = models.CharField(max_length=300, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    passing_score = models.IntegerField(default=75)
    cover_image = models.ImageField(upload_to='training_covers/', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_trainings'
    )
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='facilitated_trainings'
    )
    provider = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    registration_deadline = models.DateField(null=True, blank=True)
    competencies = models.ManyToManyField(
        'competencies.Competency',
        blank=True,
        related_name='trainings',
        help_text='Competencies whose current_level is incremented by 1 when an employee completes this training.',
    )
    certificate_template = models.ForeignKey(
        'certificates.CertificateTemplate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_trainings',
        help_text='Certificate template to use for this training. Falls back to the globally active template if not set or template is inactive.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.code}] {self.title}"

    @property
    def enrollment_count(self):
        return self.enrollments.filter(status__in=['enrolled', 'in_progress', 'completed']).count()

    @property
    def completion_rate(self):
        total = self.enrollments.filter(status__in=['enrolled', 'in_progress', 'completed']).count()
        if total == 0:
            return 0
        completed = self.enrollments.filter(status='completed').count()
        return round((completed / total) * 100)

    class Meta:
        app_label = 'trainings'
        ordering = ['-created_at']


class TrainingModule(models.Model):
    training = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=1)
    content_type = models.CharField(
        max_length=20,
        choices=[
            ('video', 'Video'), ('pdf', 'PDF/Document'),
            ('text', 'Text/Article'), ('quiz', 'Quiz'), ('assignment', 'Assignment')
        ],
        default='text'
    )
    content = models.TextField(blank=True)
    file_attachment = models.FileField(upload_to='module_files/', null=True, blank=True)
    duration_minutes = models.IntegerField(default=30)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.training.code} - Module {self.order}: {self.title}"

    class Meta:
        app_label = 'trainings'
        ordering = ['training', 'order']


class TrainingRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Submitted to Supervisor'
        SUPERVISOR_REVIEW = 'supervisor_review', 'Under Supervisor Review'
        PENDING_HRDD = 'pending_hrdd', 'Submitted to HRDD'
        HRDD_REVIEW = 'hrdd_review', 'Under HRDD Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='training_requests'
    )
    training = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name='requests')
    justification = models.TextField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    supervisor_remarks = models.TextField(blank=True)
    hr_remarks = models.TextField(blank=True)
    reviewed_by_supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervisor_reviews'
    )
    reviewed_by_hr = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hr_reviews'
    )
    supervisor_review_date = models.DateTimeField(null=True, blank=True)
    hr_review_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.requester} → {self.training.title} [{self.status}]"

    class Meta:
        app_label = 'trainings'
        ordering = ['-created_at']


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ENROLLED = 'enrolled', 'Enrolled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        DROPPED = 'dropped', 'Dropped'
        FAILED = 'failed', 'Failed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments'
    )
    training = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ENROLLED)
    progress_percent = models.IntegerField(default=0)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    final_score = models.IntegerField(null=True, blank=True)
    attendance_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user} → {self.training.title}"

    class Meta:
        app_label = 'trainings'
        unique_together = ['user', 'training']
        ordering = ['-enrolled_at']


class ModuleProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey(TrainingModule, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.IntegerField(default=0)

    class Meta:
        app_label = 'trainings'
        unique_together = ['enrollment', 'module']


class AttendanceRecord(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    is_present = models.BooleanField(default=True)
    remarks = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = 'trainings'
        unique_together = ['enrollment', 'date']
        ordering = ['date']