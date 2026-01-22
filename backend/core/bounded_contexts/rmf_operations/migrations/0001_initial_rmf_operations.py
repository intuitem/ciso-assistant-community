# Generated migration for RMF Operations bounded context

from django.db import migrations, models
import uuid
from django.contrib.postgres.fields import ArrayField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core.domain', '0001_initial_domain_events'),  # Domain events dependency
    ]

    operations = [
        # SystemGroup aggregate
        migrations.CreateModel(
            name='SystemGroup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')], db_index=True, default='draft', max_length=20)),
                ('checklistIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of STIG checklist IDs', size=None)),
                ('assetIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of asset IDs', size=None)),
                ('nessusScanIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of Nessus scan IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('totalChecklists', models.IntegerField(default=0)),
                ('totalOpenVulnerabilities', models.IntegerField(default=0)),
                ('totalCat1Open', models.IntegerField(default=0)),
                ('totalCat2Open', models.IntegerField(default=0)),
                ('totalCat3Open', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'rmf_system_groups',
                'verbose_name': 'System Group',
                'verbose_name_plural': 'System Groups',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='systemgroup',
            index=models.Index(fields=['lifecycle_state', 'name'], name='rmf_system_group_state_name_idx'),
        ),
        migrations.AddIndex(
            model_name='systemgroup',
            index=models.Index(fields=['created_at'], name='rmf_system_group_created_idx'),
        ),
        migrations.AddIndex(
            model_name='systemgroup',
            index=models.Index(fields=['updated_at'], name='rmf_system_group_updated_idx'),
        ),

        # StigChecklist aggregate
        migrations.CreateModel(
            name='StigChecklist',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('systemGroupId', models.UUIDField(blank=True, db_index=True, null=True)),
                ('hostName', models.CharField(db_index=True, max_length=255)),
                ('stigType', models.CharField(db_index=True, max_length=255)),
                ('stigRelease', models.CharField(max_length=255)),
                ('version', models.CharField(max_length=50)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')], db_index=True, default='draft', max_length=20)),
                ('assetInfo', models.JSONField(blank=True, default=dict)),
                ('rawCklData', models.JSONField(blank=True, default=dict)),
                ('isWebDatabase', models.BooleanField(default=False)),
                ('webDatabaseSite', models.CharField(blank=True, max_length=255)),
                ('webDatabaseInstance', models.CharField(blank=True, max_length=255)),
                ('vulnerabilityFindingIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of vulnerability finding IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'rmf_stig_checklists',
                'verbose_name': 'STIG Checklist',
                'verbose_name_plural': 'STIG Checklists',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='stigchecklist',
            index=models.Index(fields=['systemGroupId', 'lifecycle_state'], name='rmf_checklist_system_state_idx'),
        ),
        migrations.AddIndex(
            model_name='stigchecklist',
            index=models.Index(fields=['stigType', 'version'], name='rmf_checklist_stig_version_idx'),
        ),
        migrations.AddIndex(
            model_name='stigchecklist',
            index=models.Index(fields=['hostName'], name='rmf_checklist_hostname_idx'),
        ),
        migrations.AddIndex(
            model_name='stigchecklist',
            index=models.Index(fields=['created_at'], name='rmf_checklist_created_idx'),
        ),
        migrations.AddIndex(
            model_name='stigchecklist',
            index=models.Index(fields=['updated_at'], name='rmf_checklist_updated_idx'),
        ),

        # VulnerabilityFinding aggregate
        migrations.CreateModel(
            name='VulnerabilityFinding',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('checklistId', models.UUIDField(db_index=True)),
                ('vulnId', models.CharField(db_index=True, max_length=50)),
                ('stigId', models.CharField(db_index=True, max_length=50)),
                ('ruleId', models.CharField(max_length=50)),
                ('ruleTitle', models.CharField(max_length=500)),
                ('ruleDiscussion', models.TextField(blank=True, null=True)),
                ('checkContent', models.TextField(blank=True, null=True)),
                ('fixText', models.TextField(blank=True, null=True)),
                ('status_data', models.JSONField(default=dict)),
                ('severity_category', models.CharField(db_index=True, max_length=10)),
                ('ruleVersion', models.CharField(blank=True, max_length=50)),
                ('cciIds', models.JSONField(default=list)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'rmf_vulnerability_findings',
                'verbose_name': 'Vulnerability Finding',
                'verbose_name_plural': 'Vulnerability Findings',
                'ordering': ['-updated_at'],
                'unique_together': [['checklistId', 'vulnId']],
            },
        ),
        migrations.AddIndex(
            model_name='vulnerabilityfinding',
            index=models.Index(fields=['checklistId', 'status_data'], name='rmf_finding_checklist_status_idx'),
        ),
        migrations.AddIndex(
            model_name='vulnerabilityfinding',
            index=models.Index(fields=['severity_category', 'status_data'], name='rmf_finding_severity_status_idx'),
        ),
        migrations.AddIndex(
            model_name='vulnerabilityfinding',
            index=models.Index(fields=['stigId'], name='rmf_finding_stig_idx'),
        ),
        migrations.AddIndex(
            model_name='vulnerabilityfinding',
            index=models.Index(fields=['vulnId'], name='rmf_finding_vuln_idx'),
        ),
        migrations.AddIndex(
            model_name='vulnerabilityfinding',
            index=models.Index(fields=['created_at'], name='rmf_finding_created_idx'),
        ),
        migrations.AddIndex(
            model_name='vulnerabilityfinding',
            index=models.Index(fields=['updated_at'], name='rmf_finding_updated_idx'),
        ),

        # ChecklistScore aggregate
        migrations.CreateModel(
            name='ChecklistScore',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('checklistId', models.UUIDField(db_index=True, unique=True)),
                ('systemGroupId', models.UUIDField(blank=True, db_index=True, null=True)),
                ('hostName', models.CharField(db_index=True, max_length=255)),
                ('stigType', models.CharField(db_index=True, max_length=255)),
                ('totalCat1Open', models.IntegerField(default=0)),
                ('totalCat1NotAFinding', models.IntegerField(default=0)),
                ('totalCat1NotApplicable', models.IntegerField(default=0)),
                ('totalCat1NotReviewed', models.IntegerField(default=0)),
                ('totalCat2Open', models.IntegerField(default=0)),
                ('totalCat2NotAFinding', models.IntegerField(default=0)),
                ('totalCat2NotApplicable', models.IntegerField(default=0)),
                ('totalCat2NotReviewed', models.IntegerField(default=0)),
                ('totalCat3Open', models.IntegerField(default=0)),
                ('totalCat3NotAFinding', models.IntegerField(default=0)),
                ('totalCat3NotApplicable', models.IntegerField(default=0)),
                ('totalCat3NotReviewed', models.IntegerField(default=0)),
                ('lastCalculatedAt', models.DateTimeField(db_index=True)),
            ],
            options={
                'db_table': 'rmf_checklist_scores',
                'verbose_name': 'Checklist Score',
                'verbose_name_plural': 'Checklist Scores',
                'ordering': ['-lastCalculatedAt'],
            },
        ),
        migrations.AddIndex(
            model_name='checklistscore',
            index=models.Index(fields=['checklistId'], name='rmf_score_checklist_idx'),
        ),
        migrations.AddIndex(
            model_name='checklistscore',
            index=models.Index(fields=['systemGroupId'], name='rmf_score_system_idx'),
        ),
        migrations.AddIndex(
            model_name='checklistscore',
            index=models.Index(fields=['stigType'], name='rmf_score_stig_type_idx'),
        ),
        migrations.AddIndex(
            model_name='checklistscore',
            index=models.Index(fields=['lastCalculatedAt'], name='rmf_score_calculated_idx'),
        ),
    ]
