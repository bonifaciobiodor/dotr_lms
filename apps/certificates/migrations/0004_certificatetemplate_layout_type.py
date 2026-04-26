from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0003_alter_certificatetemplate_accent_color_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='certificatetemplate',
            name='layout_type',
            field=models.CharField(
                choices=[('classic', 'Classic (Centered)'), ('modern', 'Modern (Blue Sidebar)')],
                default='classic',
                help_text='Classic: traditional centered layout. Modern: DOTR blue sidebar with competency panel.',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='certificatetemplate',
            name='competency_level_label',
            field=models.CharField(
                default='Basic Level',
                help_text='Proficiency level label shown in the modern layout sidebar (e.g. Basic Level, Intermediate Level)',
                max_length=100,
            ),
        ),
    ]
