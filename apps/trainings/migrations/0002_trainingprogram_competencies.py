from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trainings', '0001_initial'),
        ('competencies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingprogram',
            name='competencies',
            field=models.ManyToManyField(
                blank=True,
                help_text='Competencies whose current_level is incremented by 1 when an employee completes this training.',
                related_name='trainings',
                to='competencies.competency',
            ),
        ),
    ]
