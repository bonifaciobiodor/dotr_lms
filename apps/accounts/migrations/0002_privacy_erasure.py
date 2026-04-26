"""
Migration: Add RA 10173 Data Privacy Act compliance fields.

- User.privacy_consent         — boolean, tracks consent acceptance
- User.privacy_consent_date    — timestamp of consent
- DataErasureRequest           — NPC-compliant data subject erasure workflow
"""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # ── 1. Privacy consent fields on User ─────────────────────────────────
        migrations.AddField(
            model_name='user',
            name='privacy_consent',
            field=models.BooleanField(
                default=False,
                help_text='User has acknowledged and accepted the Data Privacy Notice.',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='privacy_consent_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Timestamp when the user gave privacy consent.',
            ),
        ),

        # ── 2. DataErasureRequest model ────────────────────────────────────────
        migrations.CreateModel(
            name='DataErasureRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(
                    help_text='Reason provided by the data subject for requesting erasure.',
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending Review'),
                        ('approved', 'Approved — Awaiting Processing'),
                        ('rejected', 'Rejected'),
                        ('completed', 'Completed'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('review_date', models.DateTimeField(blank=True, null=True)),
                ('review_remarks', models.TextField(blank=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('requester', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='erasure_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_erasure_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
