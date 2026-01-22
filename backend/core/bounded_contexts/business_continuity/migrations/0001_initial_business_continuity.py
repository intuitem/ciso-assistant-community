# Generated migration for BusinessContinuity bounded context

from django.db import migrations, models
import uuid
from django.contrib.postgres.fields import ArrayField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0001_initial'),
        ('core.domain', '0001_initial_domain_events'),  # DDD infrastructure
    ]

    operations = [
        # BusinessContinuityPlan aggregate
        migrations.CreateModel(
            name='BusinessContinuityPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('approved', 'Approved'), ('exercised', 'Exercised'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('orgUnitIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of organizational unit IDs', size=None)),
                ('processIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of process IDs', size=None)),
                ('assetIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of asset IDs', size=None)),
                ('serviceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of service IDs', size=None)),
                ('taskIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of BCP task IDs', size=None)),
                ('auditIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of BCP audit IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'business_continuity_business_continuity_plans',
                'verbose_name': 'Business Continuity Plan',
                'verbose_name_plural': 'Business Continuity Plans',
            },
        ),
        migrations.AddIndex(
            model_name='businesscontinuityplan',
            index=models.Index(fields=['lifecycle_state'], name='bcp_lifecycle_state_idx'),
        ),
        migrations.AddIndex(
            model_name='businesscontinuityplan',
            index=models.Index(fields=['name'], name='bcp_name_idx'),
        ),
        
        # BcpTask supporting entity
        migrations.CreateModel(
            name='BcpTask',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bcpId', models.UUIDField(db_index=True, help_text='ID of the business continuity plan')),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('open', 'Open'), ('in_progress', 'In Progress'), ('done', 'Done'), ('blocked', 'Blocked')], db_index=True, default='open', max_length=20)),
                ('owner_user_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('due_date', models.DateField(blank=True, db_index=True, null=True)),
                ('evidenceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of evidence IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'business_continuity_bcp_tasks',
                'verbose_name': 'BCP Task',
                'verbose_name_plural': 'BCP Tasks',
            },
        ),
        migrations.AddIndex(
            model_name='bcptask',
            index=models.Index(fields=['bcpId', 'lifecycle_state'], name='bc_task_bcp_state_idx'),
        ),
        
        # BcpAudit supporting entity
        migrations.CreateModel(
            name='BcpAudit',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bcpId', models.UUIDField(db_index=True, help_text='ID of the business continuity plan')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('planned', 'Planned'), ('running', 'Running'), ('reported', 'Reported'), ('closed', 'Closed')], db_index=True, default='planned', max_length=20)),
                ('performed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('outcome', models.CharField(blank=True, choices=[('pass', 'Pass'), ('fail', 'Fail'), ('partial', 'Partial')], db_index=True, max_length=20, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('evidenceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of evidence IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'business_continuity_bcp_audits',
                'verbose_name': 'BCP Audit',
                'verbose_name_plural': 'BCP Audits',
            },
        ),
        migrations.AddIndex(
            model_name='bcpaudit',
            index=models.Index(fields=['bcpId', 'lifecycle_state'], name='bc_audit_bcp_state_idx'),
        ),
    ]

