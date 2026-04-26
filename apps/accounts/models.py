from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Division(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='headed_divisions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'accounts'
        ordering = ['name']


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'System Admin'
        HR = 'hr', 'HR / L&D Officer'
        SUPERVISOR = 'supervisor', 'Supervisor / Division Chief'
        EMPLOYEE = 'employee', 'Employee'
        TRAINER = 'trainer', 'Trainer / Facilitator'
        EXECUTIVE = 'executive', 'Executive Viewer'

    class EmploymentStatus(models.TextChoices):
        PERMANENT = 'permanent', 'Permanent'
        CASUAL = 'casual', 'Casual'
        CONTRACTUAL = 'contractual', 'Contractual'
        COS = 'cos', 'Contract of Service'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    division = models.ForeignKey(
        'accounts.Division', on_delete=models.SET_NULL, null=True, blank=True
    )
    position = models.CharField(max_length=200, blank=True)
    salary_grade = models.IntegerField(null=True, blank=True)
    employment_status = models.CharField(
        max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.PERMANENT
    )
    contact_number = models.CharField(max_length=20, blank=True)
    date_hired = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    supervisor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subordinates'
    )
    # ── RA 10173 Data Privacy Act ─────────────────────────────────────────────
    privacy_consent = models.BooleanField(
        default=False,
        help_text='User has acknowledged and accepted the Data Privacy Notice.'
    )
    privacy_consent_date = models.DateTimeField(
        null=True, blank=True,
        help_text='Timestamp when the user gave privacy consent.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        name = self.get_full_name()
        return f"{name} ({self.employee_id})" if self.employee_id else name or self.username

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    def is_hr_user(self):
        return self.role == self.Role.HR

    def is_supervisor_user(self):
        return self.role == self.Role.SUPERVISOR

    def can_approve(self):
        return self.role in [self.Role.ADMIN, self.Role.HR, self.Role.SUPERVISOR]

    class Meta:
        app_label = 'accounts'
        ordering = ['last_name', 'first_name']


class AuditLog(models.Model):
    user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=200)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"

    class Meta:
        app_label = 'accounts'
        ordering = ['-timestamp']


class OrganizationalStructure(models.Model):
    """A saved version of the DOTr organizational chart."""
    filename = models.CharField(max_length=300)
    html_file = models.FileField(upload_to='org_structures/', null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='created_org_structures'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename

    def activate(self):
        OrganizationalStructure.objects.exclude(pk=self.pk).update(is_active=False)
        self.is_active = True
        self.save(update_fields=['is_active'])

    class Meta:
        app_label = 'accounts'
        ordering = ['-created_at']


class OrgUnit(models.Model):
    """A single node in an OrganizationalStructure tree."""
    UNIT_TYPE_CHOICES = [
        ('office', 'Office'),
        ('bureau', 'Bureau'),
        ('service', 'Service'),
        ('division', 'Division'),
        ('section', 'Section'),
        ('unit', 'Unit'),
        ('other', 'Other'),
    ]

    org_structure = models.ForeignKey(
        OrganizationalStructure, on_delete=models.CASCADE, related_name='units'
    )
    name = models.CharField(max_length=200)
    abbreviation = models.CharField(max_length=50, blank=True)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPE_CHOICES, default='division')
    head_position = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    order = models.IntegerField(default=0)
    division_ref = models.ForeignKey(
        Division, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='org_units'
    )
    head_user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='org_unit_heads',
        help_text='Employee assigned as head of this unit'
    )

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'accounts'
        ordering = ['order', 'name']


class DataErasureRequest(models.Model):
    """
    RA 10173 (Data Privacy Act) — Data Subject Right to Erasure.
    Employees may request removal of their personal data.
    Admins review and execute an anonymisation (not hard-delete) so
    audit trails and training statistics are preserved.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved — Awaiting Processing'
        REJECTED = 'rejected', 'Rejected'
        COMPLETED = 'completed', 'Completed'

    requester = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='erasure_requests'
    )
    reason = models.TextField(
        help_text='Reason provided by the data subject for requesting erasure.'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    reviewed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_erasure_requests'
    )
    review_date = models.DateTimeField(null=True, blank=True)
    review_remarks = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Erasure Request #{self.pk} — {self.get_status_display()}"

    class Meta:
        app_label = 'accounts'
        ordering = ['-created_at']
