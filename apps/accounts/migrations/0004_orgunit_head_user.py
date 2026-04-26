import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_org_structure'),
    ]

    operations = [
        migrations.AddField(
            model_name='orgunit',
            name='head_user',
            field=models.ForeignKey(
                blank=True,
                help_text='Employee assigned as head of this unit',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='org_unit_heads',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
