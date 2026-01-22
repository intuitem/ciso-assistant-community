# Generated migration to add audit fields to RMF aggregates

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core.bounded_contexts.rmf_operations', '0001_initial_rmf_operations'),
    ]

    operations = [
        # Add audit fields to SystemGroup
        migrations.AddField(
            model_name='systemgroup',
            name='created_by',
            field=models.UUIDField(blank=True, help_text='User who created this record', null=True),
        ),
        migrations.AddField(
            model_name='systemgroup',
            name='updated_by',
            field=models.UUIDField(blank=True, help_text='User who last updated this record', null=True),
        ),

        # Add audit fields to StigChecklist
        migrations.AddField(
            model_name='stigchecklist',
            name='created_by',
            field=models.UUIDField(blank=True, help_text='User who created this record', null=True),
        ),
        migrations.AddField(
            model_name='stigchecklist',
            name='updated_by',
            field=models.UUIDField(blank=True, help_text='User who last updated this record', null=True),
        ),

        # Add audit fields to VulnerabilityFinding
        migrations.AddField(
            model_name='vulnerabilityfinding',
            name='created_by',
            field=models.UUIDField(blank=True, help_text='User who created this record', null=True),
        ),
        migrations.AddField(
            model_name='vulnerabilityfinding',
            name='updated_by',
            field=models.UUIDField(blank=True, help_text='User who last updated this record', null=True),
        ),

        # Add audit fields to ChecklistScore
        migrations.AddField(
            model_name='checklistscore',
            name='created_by',
            field=models.UUIDField(blank=True, help_text='User who created this record', null=True),
        ),
        migrations.AddField(
            model_name='checklistscore',
            name='updated_by',
            field=models.UUIDField(blank=True, help_text='User who last updated this record', null=True),
        ),
    ]
