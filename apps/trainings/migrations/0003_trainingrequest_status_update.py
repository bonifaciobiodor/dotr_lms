from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trainings', '0002_trainingprogram_competencies'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('pending', 'Submitted to Supervisor'),
                    ('supervisor_review', 'Under Supervisor Review'),
                    ('pending_hrdd', 'Submitted to HRDD'),
                    ('hrdd_review', 'Under HRDD Review'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                    ('cancelled', 'Cancelled'),
                ],
                default='draft',
                max_length=30,
            ),
        ),
    ]
