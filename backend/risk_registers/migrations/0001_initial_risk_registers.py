# Generated migration for Risk Registers bounded context

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core_domain', '0001_initial'),  # Depends on DDD infrastructure
    ]

    operations = [
        migrations.CreateModel(
            name='AssetRisk',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('version', models.IntegerField(default=1)),
                ('asset_id', models.UUIDField(db_index=True, help_text='ID of the asset this risk assessment applies to')),
                ('asset_name', models.CharField(help_text='Cached name of the asset for performance', max_length=255)),
                ('risk_title', models.CharField(help_text='Title/description of the risk', max_length=500)),
                ('risk_description', models.TextField(help_text='Detailed description of the risk scenario')),
                ('risk_id', models.CharField(help_text='Unique risk identifier (e.g., RISK-AST-001)', max_length=100, unique=True)),
                ('risk_category', models.CharField(choices=[('confidentiality', 'Confidentiality'), ('integrity', 'Integrity'), ('availability', 'Availability'), ('financial', 'Financial'), ('reputational', 'Reputational'), ('operational', 'Operational'), ('compliance', 'Compliance'), ('strategic', 'Strategic')], default='operational', help_text='Primary category of the risk', max_length=20)),
                ('risk_subcategory', models.CharField(blank=True, help_text='More specific risk subcategory', max_length=100, null=True)),
                ('threat_source', models.CharField(blank=True, help_text='Source of the threat (e.g., hacker, natural disaster, insider)', max_length=255, null=True)),
                ('threat_vector', models.CharField(blank=True, help_text='How the threat is executed (e.g., phishing, physical access, SQL injection)', max_length=255, null=True)),
                ('vulnerability_description', models.TextField(blank=True, help_text='Description of the vulnerability being exploited', null=True)),
                ('cve_ids', models.JSONField(blank=True, default=list, help_text='Associated CVE identifiers')),
                ('cwe_ids', models.JSONField(blank=True, default=list, help_text='Associated CWE identifiers')),
                ('cvss_base_score', models.FloatField(default=0.0, help_text='CVSS base score (0.0-10.0)')),
                ('cvss_temporal_score', models.FloatField(default=0.0, help_text='CVSS temporal score')),
                ('cvss_environmental_score', models.FloatField(default=0.0, help_text='CVSS environmental score')),
                ('inherent_likelihood', models.IntegerField(default=1, help_text='Inherent likelihood score (1-5)')),
                ('inherent_impact', models.IntegerField(default=1, help_text='Inherent impact score (1-5)')),
                ('inherent_risk_score', models.IntegerField(default=1, help_text='Inherent risk score (calculated)')),
                ('residual_likelihood', models.IntegerField(default=1, help_text='Residual likelihood after controls')),
                ('residual_impact', models.IntegerField(default=1, help_text='Residual impact after controls')),
                ('residual_risk_score', models.IntegerField(default=1, help_text='Residual risk score (calculated)')),
                ('inherent_risk_level', models.CharField(choices=[('very_low', 'Very Low'), ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('very_high', 'Very High'), ('critical', 'Critical')], default='moderate', help_text='Inherent risk level', max_length=20)),
                ('residual_risk_level', models.CharField(choices=[('very_low', 'Very Low'), ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('very_high', 'Very High'), ('critical', 'Critical')], default='moderate', help_text='Residual risk level after controls', max_length=20)),
                ('risk_appetite', models.CharField(choices=[('very_low', 'Very Low'), ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('very_high', 'Very High'), ('critical', 'Critical')], default='moderate', help_text="Organization's risk appetite for this risk", max_length=20)),
                ('risk_threshold', models.IntegerField(default=3, help_text='Risk score threshold for treatment (1-5)')),
                ('requires_treatment', models.BooleanField(default=False, help_text='Whether this risk requires treatment')),
                ('treatment_strategy', models.CharField(blank=True, choices=[('accept', 'Accept'), ('avoid', 'Avoid'), ('mitigate', 'Mitigate'), ('transfer', 'Transfer'), ('monitor', 'Monitor Only')], help_text='Risk treatment strategy', max_length=50, null=True)),
                ('treatment_plan', models.TextField(blank=True, help_text='Detailed treatment plan', null=True)),
                ('treatment_owner_user_id', models.UUIDField(blank=True, db_index=True, help_text='User ID responsible for treatment implementation', null=True)),
                ('treatment_owner_username', models.CharField(blank=True, help_text='Username of treatment owner', max_length=150, null=True)),
                ('treatment_status', models.CharField(choices=[('planned', 'Planned'), ('in_progress', 'In Progress'), ('implemented', 'Implemented'), ('effective', 'Effective'), ('ineffective', 'Ineffective')], default='planned', help_text='Status of treatment implementation', max_length=20)),
                ('treatment_implemented_date', models.DateField(blank=True, help_text='Date treatment was implemented', null=True)),
                ('treatment_effective_date', models.DateField(blank=True, help_text='Date treatment became effective', null=True)),
                ('treatment_milestones', models.JSONField(blank=True, default=list, help_text='Treatment implementation milestones')),
                ('monitoring_frequency', models.CharField(choices=[('continuous', 'Continuous'), ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annually', 'Annually')], default='monthly', help_text='How often this risk should be monitored', max_length=50)),
                ('last_review_date', models.DateField(blank=True, help_text='Date of last risk review', null=True)),
                ('next_review_date', models.DateField(blank=True, help_text='Date of next scheduled review', null=True)),
                ('review_notes', models.TextField(blank=True, help_text='Notes from risk reviews', null=True)),
                ('risk_owner_user_id', models.UUIDField(blank=True, db_index=True, help_text='User ID of the risk owner', null=True)),
                ('risk_owner_username', models.CharField(blank=True, help_text='Username of the risk owner', max_length=150, null=True)),
                ('risk_manager_user_id', models.UUIDField(blank=True, db_index=True, help_text='User ID of the risk manager', null=True)),
                ('risk_manager_username', models.CharField(blank=True, help_text='Username of the risk manager', max_length=150, null=True)),
                ('supporting_evidence', models.JSONField(blank=True, default=list, help_text='Evidence supporting the risk assessment')),
                ('related_findings', models.JSONField(blank=True, default=list, help_text='IDs of related findings or vulnerabilities')),
                ('related_controls', models.JSONField(blank=True, default=list, help_text='IDs of related controls that address this risk')),
                ('tags', models.JSONField(blank=True, default=list, help_text='Risk tags for organization and filtering')),
                ('custom_fields', models.JSONField(blank=True, default=dict, help_text='Custom fields for additional risk properties')),
                ('assessed_by_user_id', models.UUIDField(blank=True, help_text='User ID of person who performed assessment', null=True)),
                ('assessed_by_username', models.CharField(blank=True, help_text='Username of assessor', max_length=150, null=True)),
                ('assessment_methodology', models.CharField(blank=True, help_text='Risk assessment methodology used', max_length=100, null=True)),
                ('confidence_level', models.CharField(choices=[('very_low', 'Very Low'), ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('very_high', 'Very High')], default='moderate', help_text='Confidence level in the assessment', max_length=20)),
            ],
            options={
                'db_table': 'asset_risks',
                'ordering': ['-residual_risk_score', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RiskRegister',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('version', models.IntegerField(default=1)),
                ('name', models.CharField(help_text="Name of the risk register", max_length=255)),
                ('description', models.TextField(blank=True, help_text='Description of the risk register scope and purpose', null=True)),
                ('register_id', models.CharField(help_text="Unique register identifier (e.g., RR-2024, RR-IT)", max_length=100, unique=True)),
                ('scope', models.CharField(help_text="Scope of the register (e.g., 'Enterprise', 'IT', 'Finance')", max_length=100)),
                ('owning_organization', models.CharField(blank=True, help_text='Organization or department owning this register', max_length=255, null=True)),
                ('owner_user_id', models.UUIDField(blank=True, db_index=True, help_text='User ID of the register owner', null=True)),
                ('owner_username', models.CharField(blank=True, help_text='Username of the register owner', max_length=150, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived'), ('superseded', 'Superseded')], default='draft', help_text='Status of the risk register', max_length=20)),
                ('asset_risk_ids', models.JSONField(blank=True, default=list, help_text='IDs of asset risks included in this register')),
                ('third_party_risk_ids', models.JSONField(blank=True, default=list, help_text='IDs of third party risks included in this register')),
                ('business_risk_ids', models.JSONField(blank=True, default=list, help_text='IDs of business risks included in this register')),
                ('risk_scenario_ids', models.JSONField(blank=True, default=list, help_text='IDs of risk scenarios included in this register')),
                ('total_risks', models.IntegerField(default=0, help_text='Total number of risks in the register')),
                ('critical_risks', models.IntegerField(default=0, help_text='Number of critical risks')),
                ('high_risks', models.IntegerField(default=0, help_text='Number of high risks')),
                ('moderate_risks', models.IntegerField(default=0, help_text='Number of moderate risks')),
                ('low_risks', models.IntegerField(default=0, help_text='Number of low risks')),
                ('risks_requiring_treatment', models.IntegerField(default=0, help_text='Number of risks requiring treatment')),
                ('risks_under_treatment', models.IntegerField(default=0, help_text='Number of risks currently under treatment')),
                ('risks_effectively_treated', models.IntegerField(default=0, help_text='Number of risks with effective treatment')),
                ('risk_appetite_statement', models.TextField(blank=True, help_text="Organization's risk appetite statement", null=True)),
                ('risk_appetite_critical_threshold', models.IntegerField(default=20, help_text='Risk score threshold for critical risks')),
                ('risk_appetite_high_threshold', models.IntegerField(default=15, help_text='Risk score threshold for high risks')),
                ('risk_appetite_moderate_threshold', models.IntegerField(default=10, help_text='Risk score threshold for moderate risks')),
                ('reporting_frequency', models.CharField(choices=[('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annually', 'Annually')], default='monthly', help_text='Frequency of risk register reporting', max_length=50)),
                ('last_report_date', models.DateField(blank=True, help_text='Date of last risk report', null=True)),
                ('next_report_date', models.DateField(blank=True, help_text='Date of next scheduled report', null=True)),
                ('last_review_date', models.DateField(blank=True, help_text='Date of last register review', null=True)),
                ('next_review_date', models.DateField(blank=True, help_text='Date of next scheduled review', null=True)),
                ('risk_heat_map', models.JSONField(blank=True, default=dict, help_text='Risk heat map data for visualization')),
                ('included_risk_categories', models.JSONField(blank=True, default=list, help_text='Risk categories included in this register')),
                ('excluded_risk_categories', models.JSONField(blank=True, default=list, help_text='Risk categories excluded from this register')),
                ('risk_scoring_methodology', models.CharField(default='Likelihood x Impact', help_text='Risk scoring methodology used', max_length=100)),
                ('regulatory_requirements', models.JSONField(blank=True, default=list, help_text='Regulatory requirements this register addresses')),
                ('compliance_frameworks', models.JSONField(blank=True, default=list, help_text='Compliance frameworks this register supports')),
                ('tags', models.JSONField(blank=True, default=list, help_text='Register tags for organization')),
                ('custom_fields', models.JSONField(blank=True, default=dict, help_text='Custom fields for additional register properties')),
            ],
            options={
                'db_table': 'risk_registers',
                'ordering': ['-created_at'],
            },
        ),
        # Add database indexes for performance
        migrations.AddIndex(
            model_name='assetrisk',
            index=models.Index(fields=['asset_id', 'residual_risk_level'], name='asset_risk_level_idx'),
        ),
        migrations.AddIndex(
            model_name='assetrisk',
            index=models.Index(fields=['risk_category'], name='asset_risk_category_idx'),
        ),
        migrations.AddIndex(
            model_name='assetrisk',
            index=models.Index(fields=['treatment_status'], name='asset_risk_treatment_idx'),
        ),
        migrations.AddIndex(
            model_name='assetrisk',
            index=models.Index(fields=['next_review_date'], name='asset_risk_review_idx'),
        ),
        migrations.AddIndex(
            model_name='assetrisk',
            index=models.Index(fields=['requires_treatment'], name='asset_risk_treatment_needed_idx'),
        ),
        migrations.AddIndex(
            model_name='assetrisk',
            index=models.Index(fields=['residual_risk_score'], name='asset_risk_score_idx'),
        ),
        migrations.AddIndex(
            model_name='assetrisk',
            index=models.Index(fields=['created_at'], name='asset_risk_created_idx'),
        ),
        migrations.AddIndex(
            model_name='riskregister',
            index=models.Index(fields=['status'], name='risk_register_status_idx'),
        ),
        migrations.AddIndex(
            model_name='riskregister',
            index=models.Index(fields=['scope'], name='risk_register_scope_idx'),
        ),
        migrations.AddIndex(
            model_name='riskregister',
            index=models.Index(fields=['owner_user_id'], name='risk_register_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='riskregister',
            index=models.Index(fields=['next_report_date'], name='risk_register_report_idx'),
        ),
        migrations.AddIndex(
            model_name='riskregister',
            index=models.Index(fields=['next_review_date'], name='risk_register_review_idx'),
        ),
        migrations.AddIndex(
            model_name='riskregister',
            index=models.Index(fields=['total_risks'], name='risk_register_total_risks_idx'),
        ),
        migrations.AddIndex(
            model_name='riskregister',
            index=models.Index(fields=['critical_risks'], name='risk_register_critical_idx'),
        ),
        migrations.AddIndex(
            model_name='riskregister',
            index=models.Index(fields=['created_at'], name='risk_register_created_idx'),
        ),
    ]
