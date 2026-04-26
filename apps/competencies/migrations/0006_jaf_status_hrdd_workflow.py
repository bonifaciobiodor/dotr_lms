from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competencies', '0005_jaf_supervisor_created_flag'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobanalysisentry',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('submitted', 'Submitted to Supervisor'),
                    ('supervisor_review', 'Under Supervisor Review'),
                    ('pending_hrdd', 'Submitted to HRDD'),
                    ('hrdd_review', 'Under HRDD Review'),
                    ('approved', 'Approved'),
                    ('rejected', 'Returned for Revision'),
                ],
                default='draft',
                max_length=20,
            ),
        ),
    ]
