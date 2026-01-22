# Generated migration to create AuditLog table

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core.bounded_contexts.rmf_operations', '0002_add_audit_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('user_id', models.UUIDField(help_text='User who performed the action')),
                ('username', models.CharField(help_text='Username for display purposes', max_length=150)),
                ('action_type', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete'), ('import_ckl', 'Import CKL'), ('export_ckl', 'Export CKL'), ('bulk_update', 'Bulk Update'), ('compliance_check', 'Compliance Check'), ('activate', 'Activate'), ('archive', 'Archive'), ('assign_system', 'Assign to System'), ('remove_from_system', 'Remove from System')], help_text='Type of action performed', max_length=20)),
                ('entity_type', models.CharField(choices=[('system_group', 'System Group'), ('stig_checklist', 'STIG Checklist'), ('vulnerability_finding', 'Vulnerability Finding'), ('checklist_score', 'Checklist Score'), ('nessus_scan', 'Nessus Scan')], help_text='Type of entity affected', max_length=20)),
                ('entity_id', models.UUIDField(help_text='ID of the affected entity')),
                ('entity_name', models.CharField(help_text='Human-readable entity name/title', max_length=255)),
                ('old_values', models.JSONField(blank=True, help_text='Previous values before the change', null=True)),
                ('new_values', models.JSONField(blank=True, help_text='New values after the change', null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, help_text='IP address of the user', null=True)),
                ('user_agent', models.TextField(blank=True, help_text='User agent string from the request', null=True)),
                ('session_id', models.CharField(blank=True, help_text='Session identifier', max_length=100, null=True)),
                ('correlation_id', models.CharField(blank=True, help_text='Request correlation ID', max_length=100, null=True)),
                ('success', models.BooleanField(default=True, help_text='Whether the operation was successful')),
                ('error_message', models.TextField(blank=True, help_text='Error message if operation failed', null=True)),
            ],
            options={
                'db_table': 'rmf_operations_audit_logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user_id'], name='rmf_audit_user_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['entity_type', 'entity_id'], name='rmf_audit_entity_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action_type'], name='rmf_audit_action_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['created_at'], name='rmf_audit_created_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['success'], name='rmf_audit_success_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['correlation_id'], name='rmf_audit_correlation_idx'),
        ),
    ]
