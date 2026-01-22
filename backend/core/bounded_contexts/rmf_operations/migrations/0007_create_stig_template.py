# Generated migration to create StigTemplate table

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core.bounded_contexts.rmf_operations', '0006_create_nessus_scan'),
    ]

    operations = [
        migrations.CreateModel(
            name='StigTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('name', models.CharField(help_text='Template name (e.g., \'Windows Server 2019 Member Server\')', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Template description and usage notes', null=True)),
                ('stig_type', models.CharField(db_index=True, help_text='STIG type (e.g., \'Windows Server 2019\')', max_length=255)),
                ('stig_release', models.CharField(help_text='STIG release version', max_length=100)),
                ('stig_version', models.CharField(help_text='STIG version number', max_length=50)),
                ('template_type', models.CharField(choices=[('user', 'User Template'), ('system', 'System Template'), ('benchmark', 'Benchmark Template')], default='user', help_text='Type of template (user-created, system, or benchmark)', max_length=20)),
                ('raw_ckl_content', models.TextField(help_text='Raw CKL template content for instantiation')),
                ('benchmark_title', models.CharField(blank=True, help_text='Official benchmark title', max_length=500, null=True)),
                ('benchmark_date', models.DateField(blank=True, help_text='Benchmark publication date', null=True)),
                ('usage_count', models.IntegerField(default=0, help_text='Number of checklists created from this template')),
                ('last_used_at', models.DateTimeField(blank=True, help_text='When this template was last used to create a checklist', null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this template is available for use')),
                ('is_official', models.BooleanField(default=False, help_text='Whether this is an official DISA template')),
                ('created_from_checklist_id', models.UUIDField(blank=True, help_text='ID of checklist this template was created from', null=True)),
                ('tags', models.JSONField(blank=True, default=list, help_text='Template tags for organization')),
                ('compatible_systems', models.JSONField(blank=True, default=list, help_text='List of compatible system types')),
            ],
            options={
                'ordering': ['-usage_count', '-last_used_at', 'name'],
                'db_table': 'rmf_operations_stig_templates',
            },
        ),
        migrations.AddIndex(
            model_name='stigtemplate',
            index=models.Index(fields=['stig_type', 'template_type'], name='rmf_template_stig_type_idx'),
        ),
        migrations.AddIndex(
            model_name='stigtemplate',
            index=models.Index(fields=['is_active', 'template_type'], name='rmf_template_active_type_idx'),
        ),
        migrations.AddIndex(
            model_name='stigtemplate',
            index=models.Index(fields=['created_at'], name='rmf_template_created_idx'),
        ),
        migrations.AddIndex(
            model_name='stigtemplate',
            index=models.Index(fields=['usage_count'], name='rmf_template_usage_idx'),
        ),
    ]
