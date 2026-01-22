# Generated migration to add asset hierarchy and compliance tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core.bounded_contexts.rmf_operations', '0004_add_asset_classification'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemgroup',
            name='asset_hierarchy',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Asset hierarchy and relationships within this system group'
            ),
        ),
        migrations.AddField(
            model_name='systemgroup',
            name='last_compliance_check',
            field=models.DateTimeField(
                blank=True,
                help_text='Timestamp of last compliance verification',
                null=True
            ),
        ),
    ]
