# Generated migration to add asset classification fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core.bounded_contexts.rmf_operations', '0003_create_audit_log'),
    ]

    operations = [
        migrations.AddField(
            model_name='stigchecklist',
            name='asset_type',
            field=models.CharField(
                choices=[
                    ('computing', 'Computing'),
                    ('network', 'Network'),
                    ('storage', 'Storage'),
                    ('application', 'Application'),
                    ('database', 'Database'),
                    ('web_server', 'Web Server'),
                    ('other', 'Other')
                ],
                default='computing',
                help_text='Type of asset this checklist applies to',
                max_length=20
            ),
        ),
    ]
