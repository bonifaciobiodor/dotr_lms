from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0004_certificatetemplate_layout_type'),
        ('trainings', '0003_trainingrequest_status_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingprogram',
            name='certificate_template',
            field=models.ForeignKey(
                blank=True,
                help_text='Certificate template to use for this training. Falls back to the globally active template if not set or template is inactive.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_trainings',
                to='certificates.certificatetemplate',
            ),
        ),
    ]
