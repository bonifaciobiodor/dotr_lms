"""
Management command: apply_retention

Enforces the DATA_RETENTION schedule defined in settings.py.
Run via cron or scheduler — recommended: daily at midnight.

    python manage.py apply_retention [--dry-run]

Retention rules (per COA/CSC/RA 10173):
  - AuditLog records older than AUDIT_LOG_DAYS are deleted.
  - AssessmentAttempts (non-passing, no certificate) older than
    ASSESSMENT_ATTEMPT_DAYS are deleted.
  - Completed DataErasureRequests older than ERASURE_REQUEST_DAYS are deleted.
  - Training Enrollment/ModuleProgress records are NEVER auto-deleted;
    they must be retained for CSC PRIME-HRM compliance (5 years).
    The command logs a WARNING if any records exceed the soft threshold
    so an officer can decide manually.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta


class Command(BaseCommand):
    help = 'Apply data retention policy per DATA_RETENTION settings (RA 10173 / COA).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be deleted without actually deleting.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        retention = getattr(settings, 'DATA_RETENTION', {})
        now = timezone.now()

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no data will be deleted.\n'))

        # ── 1. Audit Logs ─────────────────────────────────────────────────────
        audit_days = retention.get('AUDIT_LOG_DAYS', 3 * 365)
        self._purge(
            label='AuditLog',
            model_path='apps.accounts.models.AuditLog',
            cutoff=now - timedelta(days=audit_days),
            date_field='timestamp',
            dry_run=dry_run,
        )

        # ── 2. Assessment Attempts (non-certified) ────────────────────────────
        attempt_days = retention.get('ASSESSMENT_ATTEMPT_DAYS', 365)
        self._purge(
            label='AssessmentAttempt (non-passing)',
            model_path='apps.assessments.models.AssessmentAttempt',
            cutoff=now - timedelta(days=attempt_days),
            date_field='submitted_at',
            extra_filters={'passed': False},
            dry_run=dry_run,
        )

        # ── 3. Completed DataErasureRequests ──────────────────────────────────
        erasure_days = retention.get('ERASURE_REQUEST_DAYS', 365)
        self._purge(
            label='DataErasureRequest (completed)',
            model_path='apps.accounts.models.DataErasureRequest',
            cutoff=now - timedelta(days=erasure_days),
            date_field='processed_at',
            extra_filters={'status': 'completed'},
            dry_run=dry_run,
        )

        # ── 4. Soft-warning for overdue training records ───────────────────────
        training_days = retention.get('TRAINING_RECORD_DAYS', 5 * 365)
        self._warn_overdue(
            label='Enrollment (completed)',
            model_path='apps.trainings.models.Enrollment',
            cutoff=now - timedelta(days=training_days),
            date_field='completed_at',
            extra_filters={'status': 'completed'},
        )

        self.stdout.write(self.style.SUCCESS('Retention policy applied.'))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _purge(self, label, model_path, cutoff, date_field,
               extra_filters=None, dry_run=False):
        model = self._import_model(model_path)
        if model is None:
            return
        filters = {f'{date_field}__lt': cutoff, **(extra_filters or {})}
        qs = model.objects.filter(**filters)
        count = qs.count()
        if count == 0:
            self.stdout.write(f'  {label}: nothing to purge.')
            return
        self.stdout.write(
            f'  {label}: {count} record(s) older than {cutoff.date()} '
            f'{"would be" if dry_run else "will be"} deleted.'
        )
        if not dry_run:
            deleted, _ = qs.delete()
            self.stdout.write(self.style.SUCCESS(f'    Deleted {deleted} {label} record(s).'))

    def _warn_overdue(self, label, model_path, cutoff, date_field, extra_filters=None):
        model = self._import_model(model_path)
        if model is None:
            return
        filters = {f'{date_field}__lt': cutoff, **(extra_filters or {})}
        count = model.objects.filter(**filters).count()
        if count:
            self.stdout.write(
                self.style.WARNING(
                    f'  WARNING: {count} {label} record(s) have exceeded the '
                    f'{(cutoff - timezone.now()).days * -1}-day soft-retention threshold. '
                    'Review manually — these are NOT auto-deleted.'
                )
            )

    @staticmethod
    def _import_model(model_path):
        """Dynamically import a model by dotted path to avoid circular imports."""
        from django.apps import apps
        # model_path = 'apps.accounts.models.AuditLog'  →  app_label='accounts', model='AuditLog'
        try:
            parts = model_path.split('.')
            model_name = parts[-1]
            # Walk installed apps to find the model by name
            return apps.get_model(
                app_label=parts[-3] if len(parts) >= 3 else parts[0],
                model_name=model_name,
            )
        except (LookupError, Exception):
            return None
