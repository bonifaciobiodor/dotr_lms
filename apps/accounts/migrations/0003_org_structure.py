import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_privacy_erasure'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganizationalStructure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=300)),
                ('html_file', models.FileField(blank=True, null=True, upload_to='org_structures/')),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_org_structures',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrgUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('abbreviation', models.CharField(blank=True, max_length=50)),
                ('unit_type', models.CharField(
                    choices=[
                        ('office', 'Office'),
                        ('bureau', 'Bureau'),
                        ('service', 'Service'),
                        ('division', 'Division'),
                        ('section', 'Section'),
                        ('unit', 'Unit'),
                        ('other', 'Other'),
                    ],
                    default='division',
                    max_length=20,
                )),
                ('head_position', models.CharField(blank=True, max_length=200)),
                ('order', models.IntegerField(default=0)),
                ('division_ref', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='org_units',
                    to='accounts.division',
                )),
                ('org_structure', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='units',
                    to='accounts.organizationalstructure',
                )),
                ('parent', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='children',
                    to='accounts.orgunit',
                )),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
    ]
