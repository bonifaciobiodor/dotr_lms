import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competencies', '0006_jaf_status_hrdd_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='requiredskill',
            name='competency',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='jaf_required_skills',
                to='competencies.competency',
            ),
        ),
        migrations.AlterField(
            model_name='requiredskill',
            name='skill_name',
            field=models.CharField(blank=True, max_length=300),
        ),
    ]
