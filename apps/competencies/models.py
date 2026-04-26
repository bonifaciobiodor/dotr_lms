from django.db import models
from django.conf import settings


class CompetencyCategory(models.TextChoices):
    CORE = 'core', 'Core Competency'
    LEADERSHIP = 'leadership', 'Leadership Competency'
    TECHNICAL = 'technical', 'Technical Competency'
    FUNCTIONAL = 'functional', 'Functional Competency'


class ProficiencyLevel(models.IntegerChoices):
    BASIC = 1, 'Basic'
    INTERMEDIATE = 2, 'Intermediate'
    ADVANCED = 3, 'Advanced'
    EXPERT = 4, 'Expert'


class Competency(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=20, choices=CompetencyCategory.choices)
    description = models.TextField()
    behavioral_indicators = models.TextField(blank=True, help_text="Describe observable behaviors per level")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"

    class Meta:
        app_label = 'competencies'
        ordering = ['category', 'name']
        verbose_name_plural = 'Competencies'


class PositionCompetency(models.Model):
    position = models.CharField(max_length=200)
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE)
    required_level = models.IntegerField(choices=ProficiencyLevel.choices, default=ProficiencyLevel.BASIC)

    def __str__(self):
        return f"{self.position} - {self.competency.name} (Level {self.required_level})"

    class Meta:
        app_label = 'competencies'
        unique_together = ['position', 'competency']


class EmployeeCompetency(models.Model):
    class Source(models.TextChoices):
        MANUAL    = 'manual', 'Manually Assessed'
        JAF       = 'jaf',    'From Job Analysis Form'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='competencies')
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE)
    current_level = models.IntegerField(choices=ProficiencyLevel.choices, default=ProficiencyLevel.BASIC)
    target_level = models.IntegerField(choices=ProficiencyLevel.choices, default=ProficiencyLevel.INTERMEDIATE)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assessed_competencies'
    )
    assessment_date = models.DateField(null=True, blank=True)
    source = models.CharField(
        max_length=10, choices=Source.choices, default=Source.MANUAL,
        help_text='How this competency entry was created'
    )
    jaf_entry = models.ForeignKey(
        'JobAnalysisEntry', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='synced_competencies',
        help_text='The approved JAF that created/updated this entry'
    )
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_gap(self):
        return max(0, self.target_level - self.current_level)

    def __str__(self):
        return f"{self.user} - {self.competency.name}"

    class Meta:
        app_label = 'competencies'
        unique_together = ['user', 'competency']


class IndividualDevelopmentPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'
        APPROVED = 'approved', 'Approved'
        COMPLETED = 'completed', 'Completed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='idps')
    year = models.IntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    career_objective = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_idps'
    )
    approval_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"IDP - {self.user} ({self.year})"

    class Meta:
        app_label = 'competencies'
        unique_together = ['user', 'year']
        ordering = ['-year']


class IDPActivity(models.Model):
    idp = models.ForeignKey(IndividualDevelopmentPlan, on_delete=models.CASCADE, related_name='activities')
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE)
    learning_intervention = models.CharField(max_length=300)
    timeline = models.CharField(max_length=100)
    success_indicator = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.learning_intervention

    class Meta:
        app_label = 'competencies'


# ── Job Analysis ──────────────────────────────────────────────────────────────

class JobDescription(models.Model):
    """Formal job description for a position used as the basis for job analysis."""

    position_title = models.CharField(max_length=200)
    division = models.ForeignKey(
        'accounts.Division', on_delete=models.SET_NULL, null=True, blank=True
    )
    salary_grade = models.IntegerField(null=True, blank=True)
    employment_status = models.CharField(max_length=50, blank=True)
    office_unit = models.CharField(max_length=200, blank=True, help_text="Office / organizational unit")
    immediate_supervisor = models.CharField(max_length=200, blank=True)

    # Core job content
    duties_and_responsibilities = models.TextField(help_text="List of duties and responsibilities")
    performance_standards = models.TextField(blank=True, help_text="Key performance standards / targets")

    # Qualification standards (CSC format)
    education = models.TextField(blank=True)
    training = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    eligibility = models.TextField(blank=True, help_text="Civil Service Eligibility")
    knowledge_skills_abilities = models.TextField(
        blank=True, help_text="Knowledge, Skills, and Abilities (KSAs) required"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_job_descriptions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.position_title

    class Meta:
        app_label = 'competencies'
        ordering = ['position_title']
        verbose_name = 'Job Description'
        verbose_name_plural = 'Job Descriptions'


class JobAnalysis(models.Model):
    """Analysis of a job description to identify required competencies."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        FINALIZED = 'finalized', 'Finalized'
        APPLIED = 'applied', 'Applied to Position'

    job_description = models.ForeignKey(
        JobDescription, on_delete=models.CASCADE, related_name='analyses'
    )
    analyzed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='conducted_job_analyses'
    )
    analysis_date = models.DateField(null=True, blank=True)
    summary = models.TextField(blank=True, help_text="Summary of job analysis findings and methodology")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='applied_job_analyses'
    )
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Job Analysis — {self.job_description.position_title} ({self.get_status_display()})"

    class Meta:
        app_label = 'competencies'
        ordering = ['-created_at']
        verbose_name = 'Job Analysis'
        verbose_name_plural = 'Job Analyses'


class JobAnalysisCompetency(models.Model):
    """Maps a required competency (with proficiency level) to a job analysis."""

    job_analysis = models.ForeignKey(
        JobAnalysis, on_delete=models.CASCADE, related_name='competency_mappings'
    )
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE)
    required_level = models.IntegerField(
        choices=ProficiencyLevel.choices, default=ProficiencyLevel.BASIC
    )
    justification = models.TextField(
        blank=True,
        help_text="Basis for requiring this competency at the specified level"
    )

    def __str__(self):
        return f"{self.competency.name} (Level {self.required_level}) — {self.job_analysis}"

    class Meta:
        app_label = 'competencies'
        unique_together = ['job_analysis', 'competency']
        ordering = ['competency__category', 'competency__name']


# ── DOTr Job Analysis Form (Employee Self-Report) ─────────────────────────────

class JobAnalysisEntry(models.Model):
    """Employee-filled DOTr Job Analysis Form."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted to Supervisor'
        SUPERVISOR_REVIEW = 'supervisor_review', 'Under Supervisor Review'
        PENDING_HRDD = 'pending_hrdd', 'Submitted to HRDD'
        HRDD_REVIEW = 'hrdd_review', 'Under HRDD Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Returned for Revision'

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='job_analysis_form_entries'
    )
    # Header
    full_name = models.CharField(max_length=200)
    position_title = models.CharField(max_length=200)
    office_service_division = models.CharField(max_length=200, blank=True)
    section_project_unit = models.CharField(max_length=200, blank=True)
    alternate_position = models.CharField(max_length=200, blank=True)

    # Sections
    job_purpose = models.TextField(blank=True)
    main_duties = models.TextField(blank=True)
    challenges_critical_issues = models.TextField(blank=True)
    additional_comments = models.TextField(blank=True)

    # Employee certification
    certified_date = models.DateField(null=True, blank=True)

    # Supervisor / Division Head review
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='jaf_reviewed'
    )
    reviewed_date = models.DateField(null=True, blank=True)

    # Director approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='jaf_approved'
    )
    approved_date = models.DateField(null=True, blank=True)
    rejection_comment = models.TextField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    # True when a supervisor/division head created the form on behalf of the employee
    supervisor_created = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Job Analysis Form — {self.full_name} ({self.position_title})"

    class Meta:
        app_label = 'competencies'
        ordering = ['-created_at']
        verbose_name = 'Job Analysis Form Entry'
        verbose_name_plural = 'Job Analysis Form Entries'


class JAFRevisionComment(models.Model):
    """Audit trail of every revision comment left on a Job Analysis Form entry."""

    entry = models.ForeignKey(
        JobAnalysisEntry, on_delete=models.CASCADE, related_name='revision_comments'
    )
    comment = models.TextField()
    commented_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='jaf_revision_comments'
    )
    commented_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revision comment on {self.entry} by {self.commented_by} at {self.commented_at}"

    class Meta:
        app_label = 'competencies'
        ordering = ['commented_at']


class SecondaryDuty(models.Model):
    """A row in the Secondary Duties & Responsibilities table."""

    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        PERIODICALLY = 'periodically', 'Periodically / As Instructed'

    entry = models.ForeignKey(
        JobAnalysisEntry, on_delete=models.CASCADE, related_name='secondary_duties'
    )
    order = models.PositiveSmallIntegerField(default=1)
    task = models.TextField()
    frequency = models.CharField(max_length=20, choices=Frequency.choices)

    def __str__(self):
        return f"{self.task[:60]} ({self.get_frequency_display()})"

    class Meta:
        app_label = 'competencies'
        ordering = ['order']


class RequiredSkill(models.Model):
    """A row in the Required Competencies table."""

    class Proficiency(models.TextChoices):
        BASIC = 'basic', 'Basic'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'
        SUPERIOR = 'superior', 'Superior'

    entry = models.ForeignKey(
        JobAnalysisEntry, on_delete=models.CASCADE, related_name='required_skills'
    )
    order = models.PositiveSmallIntegerField(default=1)
    competency = models.ForeignKey(
        Competency, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='jaf_required_skills'
    )
    skill_name = models.CharField(max_length=300, blank=True)
    proficiency_level = models.CharField(max_length=20, choices=Proficiency.choices)

    def __str__(self):
        return f"{self.skill_name} ({self.get_proficiency_level_display()})"

    class Meta:
        app_label = 'competencies'
        ordering = ['order']


class ToolEquipment(models.Model):
    """A row in the Tools and Equipment section."""

    entry = models.ForeignKey(
        JobAnalysisEntry, on_delete=models.CASCADE, related_name='tools_equipment'
    )
    order = models.PositiveSmallIntegerField(default=1)
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'competencies'
        ordering = ['order']


# ── DOTr Competency Framework ─────────────────────────────────────────────────

class DOTrOfficeMandate(models.Model):
    """A numbered mandate/function of a DOTr Division."""

    division = models.ForeignKey(
        'accounts.Division', on_delete=models.CASCADE, related_name='mandates',
        null=True, blank=True,
    )
    order = models.PositiveSmallIntegerField(default=1)
    description = models.TextField()

    def __str__(self):
        return f"{self.division.name} — Mandate {self.order}"

    class Meta:
        app_label = 'competencies'
        ordering = ['order']
        verbose_name = 'DOTr Office Mandate'
        verbose_name_plural = 'DOTr Office Mandates'


class DOTrCompetencyType(models.TextChoices):
    CORE = 'core', 'Core Competency'
    LEADERSHIP = 'leadership', 'Leadership Competency'
    FUNCTIONAL = 'functional', 'Functional Competency'


class DOTrCompetency(models.Model):
    """A named competency in the DOTr Competency Framework (Core, Leadership, or Functional)."""

    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=DOTrCompetencyType.choices)
    description = models.TextField(blank=True, help_text="One-line definition / tagline shown below the name")
    division = models.ForeignKey(
        'accounts.Division', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dotr_competencies',
        help_text="For functional competencies — the Division/Office this applies to"
    )
    office = models.CharField(
        max_length=200, blank=True,
        help_text="Synced from division.name for easy querying"
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dotr_competencies_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_type_display()}] {self.name}"

    class Meta:
        app_label = 'competencies'
        ordering = ['type', 'order', 'name']
        verbose_name = 'DOTr Competency'
        verbose_name_plural = 'DOTr Competencies'


class DOTrCompetencyIndicator(models.Model):
    """A single behavioral indicator for a DOTr competency at a given proficiency level."""

    class Level(models.IntegerChoices):
        BASIC = 1, 'Basic'
        INTERMEDIATE = 2, 'Intermediate'
        ADVANCED = 3, 'Advanced'
        SUPERIOR = 4, 'Superior'

    competency = models.ForeignKey(
        DOTrCompetency, on_delete=models.CASCADE, related_name='indicators'
    )
    level = models.IntegerField(choices=Level.choices)
    indicator_number = models.CharField(max_length=10, blank=True, help_text="e.g. 1.1, 2.3")
    description = models.TextField()
    order = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"{self.competency.name} — L{self.level} {self.indicator_number}"

    class Meta:
        app_label = 'competencies'
        ordering = ['level', 'order']
        verbose_name = 'DOTr Competency Indicator'
        verbose_name_plural = 'DOTr Competency Indicators'
