# Generated migration for SecurityOperations bounded context

from django.db import migrations, models
import uuid
from django.contrib.postgres.fields import ArrayField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0001_initial'),
    ]

    operations = [
        # SecurityIncident aggregate
        migrations.CreateModel(
            name='SecurityIncident',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('classification_id', models.UUIDField(blank=True, db_index=True, help_text='ID of the incident classification', null=True)),
                ('lifecycle_state', models.CharField(choices=[('reported', 'Reported'), ('triaged', 'Triaged'), ('contained', 'Contained'), ('eradicated', 'Eradicated'), ('recovered', 'Recovered'), ('closed', 'Closed')], db_index=True, default='reported', max_length=20)),
                ('severity', models.CharField(choices=[('critical', 'Critical'), ('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], db_index=True, default='medium', max_length=20)),
                ('detection_source', models.CharField(choices=[('internal', 'Internal'), ('external', 'External')], db_index=True, default='internal', max_length=20)),
                ('affectedAssetIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of affected asset IDs', size=None)),
                ('affectedServiceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of affected service IDs', size=None)),
                ('relatedRiskIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of related risk IDs', size=None)),
                ('evidenceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of evidence IDs', size=None)),
                ('timeline', models.JSONField(blank=True, default=list, help_text='Array of timeline events: [{at, action, actorUserId, notes}]')),
                ('reported_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('triaged_at', models.DateTimeField(blank=True, null=True)),
                ('contained_at', models.DateTimeField(blank=True, null=True)),
                ('eradicated_at', models.DateTimeField(blank=True, null=True)),
                ('recovered_at', models.DateTimeField(blank=True, null=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'security_operations_security_incidents',
                'verbose_name': 'Security Incident',
                'verbose_name_plural': 'Security Incidents',
            },
        ),
        migrations.AddIndex(
            model_name='securityincident',
            index=models.Index(fields=['lifecycle_state', 'severity'], name='sec_ops_inc_state_sev_idx'),
        ),
        
        # AwarenessProgram aggregate
        migrations.CreateModel(
            name='AwarenessProgram',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('paused', 'Paused'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('audienceOrgUnitIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of audience organizational unit IDs', size=None)),
                ('policyIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of related policy IDs', size=None)),
                ('campaignIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of campaign IDs', size=None)),
                ('cadence_days', models.IntegerField(blank=True, help_text='Cadence in days (e.g., 30 for monthly)', null=True)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'security_operations_awareness_programs',
                'verbose_name': 'Awareness Program',
                'verbose_name_plural': 'Awareness Programs',
            },
        ),
        
        # AwarenessCampaign association
        migrations.CreateModel(
            name='AwarenessCampaign',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('programId', models.UUIDField(db_index=True, help_text='ID of the awareness program')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('planned', 'Planned'), ('running', 'Running'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], db_index=True, default='planned', max_length=20)),
                ('start_date', models.DateField(db_index=True)),
                ('end_date', models.DateField(blank=True, db_index=True, null=True)),
                ('targetUserIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of target user IDs', size=None)),
                ('completionIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of completion IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'security_operations_awareness_campaigns',
                'verbose_name': 'Awareness Campaign',
                'verbose_name_plural': 'Awareness Campaigns',
            },
        ),
        migrations.AddIndex(
            model_name='awarenesscampaign',
            index=models.Index(fields=['programId', 'lifecycle_state'], name='sec_ops_camp_prog_state_idx'),
        ),
        
        # AwarenessCompletion association
        migrations.CreateModel(
            name='AwarenessCompletion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('campaignId', models.UUIDField(db_index=True, help_text='ID of the awareness campaign')),
                ('userId', models.UUIDField(db_index=True, help_text='ID of the user')),
                ('status', models.CharField(choices=[('not_started', 'Not Started'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('failed', 'Failed')], db_index=True, default='not_started', max_length=20)),
                ('completed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('score', models.FloatField(blank=True, help_text='Completion score if applicable', null=True)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'security_operations_awareness_completions',
                'verbose_name': 'Awareness Completion',
                'verbose_name_plural': 'Awareness Completions',
            },
        ),
        migrations.AddIndex(
            model_name='awarenesscompletion',
            index=models.Index(fields=['campaignId', 'userId'], name='sec_ops_comp_camp_user_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='awarenesscompletion',
            unique_together={('campaignId', 'userId')},
        ),
    ]

