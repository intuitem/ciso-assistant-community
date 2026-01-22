# Generated migration to create NessusScan table

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core.bounded_contexts.rmf_operations', '0005_add_system_hierarchy'),
    ]

    operations = [
        migrations.CreateModel(
            name='NessusScan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('systemGroupId', models.UUIDField(help_text='Associated system group for this scan')),
                ('filename', models.CharField(help_text='Original Nessus scan filename', max_length=255)),
                ('raw_xml_content', models.TextField(help_text='Complete raw Nessus XML scan data')),
                ('scan_date', models.DateTimeField(blank=True, help_text='When the Nessus scan was performed', null=True)),
                ('scanner_version', models.CharField(blank=True, help_text='Nessus scanner version', max_length=100, null=True)),
                ('policy_name', models.CharField(blank=True, help_text='Nessus scan policy name', max_length=255, null=True)),
                ('total_hosts', models.IntegerField(default=0, help_text='Total number of hosts scanned')),
                ('total_vulnerabilities', models.IntegerField(default=0, help_text='Total number of vulnerabilities found')),
                ('scan_duration_seconds', models.IntegerField(blank=True, help_text='Duration of the scan in seconds', null=True)),
                ('critical_count', models.IntegerField(default=0, help_text='Critical severity vulnerabilities')),
                ('high_count', models.IntegerField(default=0, help_text='High severity vulnerabilities')),
                ('medium_count', models.IntegerField(default=0, help_text='Medium severity vulnerabilities')),
                ('low_count', models.IntegerField(default=0, help_text='Low severity vulnerabilities')),
                ('info_count', models.IntegerField(default=0, help_text='Informational findings')),
                ('correlated_checklist_ids', models.JSONField(blank=True, default=list, help_text='CKL checklists correlated with this scan')),
                ('tags', models.JSONField(blank=True, default=list, help_text='Custom tags for organization')),
                ('processing_status', models.CharField(choices=[('uploaded', 'Uploaded'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='uploaded', help_text='Current processing status of the scan', max_length=20)),
                ('processing_error', models.TextField(blank=True, help_text='Error message if processing failed', null=True)),
            ],
            options={
                'db_table': 'rmf_operations_nessus_scans',
                'ordering': ['-scan_date', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='nessusscan',
            index=models.Index(fields=['systemGroupId'], name='rmf_nessus_sysgrp_idx'),
        ),
        migrations.AddIndex(
            model_name='nessusscan',
            index=models.Index(fields=['scan_date'], name='rmf_nessus_scan_date_idx'),
        ),
        migrations.AddIndex(
            model_name='nessusscan',
            index=models.Index(fields=['processing_status'], name='rmf_nessus_status_idx'),
        ),
        migrations.AddIndex(
            model_name='nessusscan',
            index=models.Index(fields=['created_at'], name='rmf_nessus_created_idx'),
        ),
    ]
