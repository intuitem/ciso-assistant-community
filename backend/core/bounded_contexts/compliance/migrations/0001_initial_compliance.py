# Generated migration for Compliance bounded context

from django.db import migrations, models
import uuid
from django.contrib.postgres.fields import ArrayField
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0001_initial'),
    ]

    operations = [
        # ComplianceFramework aggregate
        migrations.CreateModel(
            name='ComplianceFramework',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('version', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('requirementIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of requirement IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'compliance_compliance_frameworks',
                'verbose_name': 'Compliance Framework',
                'verbose_name_plural': 'Compliance Frameworks',
            },
        ),
        migrations.AddIndex(
            model_name='complianceframework',
            index=models.Index(fields=['name', 'version'], name='compl_framework_name_ver_idx'),
        ),
        
        # Requirement aggregate
        migrations.CreateModel(
            name='Requirement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('frameworkId', models.UUIDField(db_index=True, help_text='ID of the compliance framework')),
                ('code', models.CharField(db_index=True, help_text='Requirement code (e.g., AC-1)', max_length=100)),
                ('statement', models.TextField(help_text='Requirement statement')),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('active', 'Active'), ('retired', 'Retired')], db_index=True, default='active', max_length=20)),
                ('mappedControlIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of mapped control IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'compliance_requirements',
                'verbose_name': 'Requirement',
                'verbose_name_plural': 'Requirements',
            },
        ),
        migrations.AddIndex(
            model_name='requirement',
            index=models.Index(fields=['frameworkId', 'code'], name='compl_req_framework_code_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='requirement',
            unique_together={('frameworkId', 'code')},
        ),
        
        # OnlineAssessment aggregate
        migrations.CreateModel(
            name='OnlineAssessment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('questionnaireId', models.UUIDField(db_index=True, help_text='ID of the questionnaire')),
                ('target_type', models.CharField(choices=[('third_party', 'Third Party'), ('org_unit', 'Organizational Unit'), ('service', 'Service'), ('asset', 'Asset'), ('process', 'Process')], db_index=True, help_text='Type of entity this assessment targets', max_length=50)),
                ('scoring_model', models.CharField(blank=True, help_text='Scoring model for the assessment', max_length=255, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'compliance_online_assessments',
                'verbose_name': 'Online Assessment',
                'verbose_name_plural': 'Online Assessments',
            },
        ),
        
        # AssessmentRun association
        migrations.CreateModel(
            name='AssessmentRun',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assessmentId', models.UUIDField(db_index=True, help_text='ID of the assessment')),
                ('target_type', models.CharField(choices=[('third_party', 'Third Party'), ('org_unit', 'Organizational Unit'), ('service', 'Service'), ('asset', 'Asset'), ('process', 'Process')], db_index=True, max_length=50)),
                ('target_id', models.UUIDField(db_index=True)),
                ('lifecycle_state', models.CharField(choices=[('invited', 'Invited'), ('in_progress', 'In Progress'), ('submitted', 'Submitted'), ('reviewed', 'Reviewed'), ('closed', 'Closed')], db_index=True, default='invited', max_length=20)),
                ('invitedUserIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of invited user IDs', size=None)),
                ('respondentUserIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of respondent user IDs', size=None)),
                ('findingIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of finding IDs', size=None)),
                ('evidenceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of evidence IDs', size=None)),
                ('started_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('submitted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('score', models.FloatField(blank=True, help_text='Assessment score', null=True)),
                ('answers', models.JSONField(blank=True, default=list, help_text='Array of answers: [{questionId, value, notes}]')),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'compliance_assessment_runs',
                'verbose_name': 'Assessment Run',
                'verbose_name_plural': 'Assessment Runs',
            },
        ),
        migrations.AddIndex(
            model_name='assessmentrun',
            index=models.Index(fields=['assessmentId', 'target_type', 'target_id'], name='compl_run_assess_tgt_idx'),
        ),
        
        # ComplianceAudit association
        migrations.CreateModel(
            name='ComplianceAudit',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('planned', 'Planned'), ('running', 'Running'), ('reported', 'Reported'), ('closed', 'Closed')], db_index=True, default='planned', max_length=20)),
                ('scopeFrameworkIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of framework IDs in scope', size=None)),
                ('scopeRequirementIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of requirement IDs in scope', size=None)),
                ('auditor_org', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('start_date', models.DateField(db_index=True)),
                ('end_date', models.DateField(blank=True, db_index=True, null=True)),
                ('findingIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of finding IDs', size=None)),
                ('tags', models.JSONField(default=list)),
            ],
            options={
                'db_table': 'compliance_compliance_audits',
                'verbose_name': 'Compliance Audit',
                'verbose_name_plural': 'Compliance Audits',
            },
        ),
        
        # ComplianceFinding association
        migrations.CreateModel(
            name='ComplianceFinding',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('source_type', models.CharField(choices=[('audit', 'Audit'), ('assessment', 'Assessment'), ('internal_review', 'Internal Review')], db_index=True, max_length=20)),
                ('source_id', models.UUIDField(db_index=True, help_text='ID of the source (audit, assessment, etc.)')),
                ('lifecycle_state', models.CharField(choices=[('open', 'Open'), ('triaged', 'Triaged'), ('remediating', 'Remediing'), ('verified', 'Verified'), ('closed', 'Closed')], db_index=True, default='open', max_length=20)),
                ('severity', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], db_index=True, default='medium', max_length=20)),
                ('requirementIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of requirement IDs', size=None)),
                ('controlImplementationIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of control implementation IDs', size=None)),
                ('remediationTaskIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of remediation task IDs', size=None)),
                ('evidenceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of evidence IDs', size=None)),
                ('tags', models.JSONField(default=list)),
            ],
            options={
                'db_table': 'compliance_compliance_findings',
                'verbose_name': 'Compliance Finding',
                'verbose_name_plural': 'Compliance Findings',
            },
        ),
        migrations.AddIndex(
            model_name='compliancefinding',
            index=models.Index(fields=['source_type', 'source_id'], name='compl_find_source_idx'),
        ),
        migrations.AddIndex(
            model_name='compliancefinding',
            index=models.Index(fields=['lifecycle_state', 'severity'], name='compl_find_state_sev_idx'),
        ),
        
        # ComplianceException association
        migrations.CreateModel(
            name='ComplianceException',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('requirementId', models.UUIDField(db_index=True, help_text='ID of the requirement this exception applies to')),
                ('reason', models.TextField(help_text='Reason for the exception')),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('requested', 'Requested'), ('approved', 'Approved'), ('expired', 'Expired'), ('revoked', 'Revoked')], db_index=True, default='requested', max_length=20)),
                ('approved_by_user_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('tags', models.JSONField(default=list)),
            ],
            options={
                'db_table': 'compliance_compliance_exceptions',
                'verbose_name': 'Compliance Exception',
                'verbose_name_plural': 'Compliance Exceptions',
            },
        ),
        migrations.AddIndex(
            model_name='complianceexception',
            index=models.Index(fields=['requirementId', 'lifecycle_state'], name='compl_exc_req_state_idx'),
        ),
        
        # Read Models
        migrations.CreateModel(
            name='CompliancePostureByFramework',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('framework_id', models.UUIDField(db_index=True, unique=True)),
                ('framework_name', models.CharField(db_index=True, max_length=255)),
                ('framework_version', models.CharField(blank=True, max_length=100, null=True)),
                ('total_requirements', models.IntegerField(default=0)),
                ('active_requirements', models.IntegerField(default=0)),
                ('requirements_with_controls', models.IntegerField(default=0)),
                ('coverage_percentage', models.FloatField(default=0.0, help_text='Percentage of requirements with controls')),
                ('open_findings_count', models.IntegerField(default=0)),
                ('triaged_findings_count', models.IntegerField(default=0)),
                ('remediating_findings_count', models.IntegerField(default=0)),
                ('verified_findings_count', models.IntegerField(default=0)),
                ('closed_findings_count', models.IntegerField(default=0)),
                ('active_exceptions_count', models.IntegerField(default=0)),
                ('expired_exceptions_count', models.IntegerField(default=0)),
                ('total_audits', models.IntegerField(default=0)),
                ('recent_audit_date', models.DateField(blank=True, null=True)),
            ],
            options={
                'db_table': 'compliance_compliance_posture_by_framework',
                'verbose_name': 'Compliance Posture By Framework',
                'verbose_name_plural': 'Compliance Posture By Framework',
            },
        ),
    ]

