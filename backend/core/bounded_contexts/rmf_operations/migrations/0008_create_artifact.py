# Generated migration to create Artifact table

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core.bounded_contexts.rmf_operations', '0007_create_stig_template'),
    ]

    operations = [
        migrations.CreateModel(
            name='Artifact',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('filename', models.CharField(help_text='Original filename', max_length=255)),
                ('file_path', models.CharField(help_text='Internal file path for storage', max_length=500, unique=True)),
                ('file_size', models.BigIntegerField(help_text='File size in bytes')),
                ('content_type', models.CharField(help_text='MIME content type', max_length=100)),
                ('file_hash', models.CharField(help_text='SHA-256 hash of file content', max_length=128)),
                ('artifact_type', models.CharField(choices=[('screenshot', 'Screenshot'), ('document', 'Document'), ('evidence', 'Evidence'), ('configuration', 'Configuration File'), ('log', 'Log File'), ('report', 'Report'), ('certificate', 'Certificate'), ('other', 'Other')], default='other', help_text='Type of artifact', max_length=20)),
                ('title', models.CharField(help_text='Artifact title', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Artifact description and context', null=True)),
                ('system_group_id', models.UUIDField(blank=True, db_index=True, help_text='Associated system group', null=True)),
                ('checklist_id', models.UUIDField(blank=True, db_index=True, help_text='Associated STIG checklist', null=True)),
                ('vulnerability_finding_id', models.UUIDField(blank=True, db_index=True, help_text='Associated vulnerability finding', null=True)),
                ('nessus_scan_id', models.UUIDField(blank=True, db_index=True, help_text='Associated Nessus scan', null=True)),
                ('control_id', models.CharField(blank=True, help_text='Associated RMF control (e.g., AC-2, IA-5)', max_length=50, null=True)),
                ('cci_ids', models.JSONField(blank=True, default=list, help_text='Associated CCI IDs')),
                ('security_level', models.CharField(choices=[('public', 'Public'), ('internal', 'Internal Use'), ('confidential', 'Confidential'), ('restricted', 'Restricted')], default='internal', help_text='Security classification level', max_length=15)),
                ('is_public', models.BooleanField(default=False, help_text='Whether artifact is publicly accessible')),
                ('access_list', models.JSONField(blank=True, default=list, help_text='List of users/groups with access (if not public)')),
                ('is_active', models.BooleanField(default=True, help_text='Whether artifact is active/available')),
                ('retention_period_days', models.IntegerField(blank=True, help_text='Retention period in days (null = indefinite)', null=True)),
                ('expires_at', models.DateTimeField(blank=True, help_text='Expiration date for automatic cleanup', null=True)),
                ('tags', models.JSONField(blank=True, default=list, help_text='Artifact tags for organization')),
                ('source', models.CharField(blank=True, help_text='Source of the artifact (e.g., \'manual_upload\', \'nessus_scan\')', max_length=100, null=True)),
                ('version', models.CharField(blank=True, help_text='Artifact version or revision', max_length=50, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'db_table': 'rmf_operations_artifacts',
            },
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['system_group_id'], name='rmf_artifact_sysgrp_idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['checklist_id'], name='rmf_artifact_checklist_idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['vulnerability_finding_id'], name='rmf_artifact_finding_idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['nessus_scan_id'], name='rmf_artifact_scan_idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['artifact_type', 'is_active'], name='rmf_artifact_type_active_idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['control_id'], name='rmf_artifact_control_idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['expires_at'], name='rmf_artifact_expires_idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['security_level'], name='rmf_artifact_security_idx'),
        ),
    ]
