# Generated migration for Risk Registers bounded context

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
        # AssetRisk aggregate
        migrations.CreateModel(
            name='AssetRisk',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('threat', models.TextField(blank=True, help_text='Threat description', null=True)),
                ('vulnerability', models.TextField(blank=True, help_text='Vulnerability description', null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('assessed', 'Assessed'), ('treated', 'Treated'), ('accepted', 'Accepted'), ('closed', 'Closed')], db_index=True, default='draft', max_length=20)),
                ('assetIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of asset IDs', size=None)),
                ('controlImplementationIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of control implementation IDs', size=None)),
                ('exceptionIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of risk exception IDs', size=None)),
                ('relatedRiskIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of related risk IDs', size=None)),
                ('scoring', models.JSONField(blank=True, default=dict, help_text='Risk scoring: likelihood, impact, inherent_score, residual_score, rationale')),
                ('treatmentPlanId', models.UUIDField(blank=True, db_index=True, null=True)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'risk_registers_asset_risks',
                'verbose_name': 'Asset Risk',
                'verbose_name_plural': 'Asset Risks',
            },
        ),
        
        # ThirdPartyRisk aggregate
        migrations.CreateModel(
            name='ThirdPartyRisk',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('assessed', 'Assessed'), ('treated', 'Treated'), ('accepted', 'Accepted'), ('closed', 'Closed')], db_index=True, default='draft', max_length=20)),
                ('thirdPartyIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of third party IDs', size=None)),
                ('serviceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of service IDs', size=None)),
                ('controlImplementationIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of control implementation IDs', size=None)),
                ('assessmentRunIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of assessment run IDs', size=None)),
                ('exceptionIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of risk exception IDs', size=None)),
                ('scoring', models.JSONField(blank=True, default=dict, help_text='Risk scoring: likelihood, impact, inherent_score, residual_score, rationale')),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'risk_registers_third_party_risks',
                'verbose_name': 'Third Party Risk',
                'verbose_name_plural': 'Third Party Risks',
            },
        ),
        
        # BusinessRisk aggregate
        migrations.CreateModel(
            name='BusinessRisk',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('assessed', 'Assessed'), ('treated', 'Treated'), ('accepted', 'Accepted'), ('closed', 'Closed')], db_index=True, default='draft', max_length=20)),
                ('processIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of process IDs', size=None)),
                ('orgUnitIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of organizational unit IDs', size=None)),
                ('controlImplementationIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of control implementation IDs', size=None)),
                ('exceptionIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of risk exception IDs', size=None)),
                ('scoring', models.JSONField(blank=True, default=dict, help_text='Risk scoring: likelihood, impact, inherent_score, residual_score, rationale')),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'risk_registers_business_risks',
                'verbose_name': 'Business Risk',
                'verbose_name_plural': 'Business Risks',
            },
        ),
        
        # RiskException supporting entity
        migrations.CreateModel(
            name='RiskException',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('riskId', models.UUIDField(db_index=True, help_text='ID of the risk this exception applies to')),
                ('reason', models.TextField(help_text='Reason for the exception')),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('requested', 'Requested'), ('approved', 'Approved'), ('expired', 'Expired'), ('revoked', 'Revoked')], db_index=True, default='requested', max_length=20)),
                ('approved_by_user_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('approved_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'risk_registers_risk_exceptions',
                'verbose_name': 'Risk Exception',
                'verbose_name_plural': 'Risk Exceptions',
            },
        ),
        migrations.AddIndex(
            model_name='riskexception',
            index=models.Index(fields=['riskId', 'lifecycle_state'], name='risk_reg_exc_risk_state_idx'),
        ),
        
        # RiskTreatmentPlan supporting entity
        migrations.CreateModel(
            name='RiskTreatmentPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('riskId', models.UUIDField(db_index=True, help_text='ID of the risk this plan treats')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('strategy', models.CharField(choices=[('avoid', 'Avoid'), ('mitigate', 'Mitigate'), ('transfer', 'Transfer'), ('accept', 'Accept')], db_index=True, max_length=20)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'), ('abandoned', 'Abandoned')], db_index=True, default='draft', max_length=20)),
                ('tasks', models.JSONField(blank=True, default=list, help_text='Array of treatment tasks: {title, ownerUserId, dueDate, status, evidenceIds[]}')),
                ('started_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('tags', models.JSONField(default=list)),
            ],
            options={
                'db_table': 'risk_registers_risk_treatment_plans',
                'verbose_name': 'Risk Treatment Plan',
                'verbose_name_plural': 'Risk Treatment Plans',
            },
        ),
        migrations.AddIndex(
            model_name='risktreatmentplan',
            index=models.Index(fields=['riskId', 'lifecycle_state'], name='risk_reg_plan_risk_state_idx'),
        ),
        
        # Read Models
        migrations.CreateModel(
            name='RiskRegisterOverview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('risk_type', models.CharField(choices=[('asset', 'Asset'), ('third_party', 'Third Party'), ('business', 'Business')], db_index=True, max_length=20)),
                ('draft_count', models.IntegerField(default=0)),
                ('assessed_count', models.IntegerField(default=0)),
                ('treated_count', models.IntegerField(default=0)),
                ('accepted_count', models.IntegerField(default=0)),
                ('closed_count', models.IntegerField(default=0)),
                ('average_inherent_score', models.FloatField(blank=True, null=True)),
                ('average_residual_score', models.FloatField(blank=True, null=True)),
            ],
            options={
                'db_table': 'risk_registers_risk_register_overviews',
                'verbose_name': 'Risk Register Overview',
                'verbose_name_plural': 'Risk Register Overviews',
            },
        ),
        migrations.AlterUniqueTogether(
            name='riskregisteroverview',
            unique_together={('risk_type',)},
        ),
    ]

