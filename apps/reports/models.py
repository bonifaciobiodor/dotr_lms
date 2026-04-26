# Reports app computes analytics from other models in views.
# No dedicated models — app_label declared for completeness.

from django.db import models


class ReportPlaceholder(models.Model):
    """Placeholder to satisfy Django app registry. Not used."""
    class Meta:
        app_label = 'reports'
        managed = False  # No table created
