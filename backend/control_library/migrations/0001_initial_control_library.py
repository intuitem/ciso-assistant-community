# Generated migration for Control Library bounded context

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        # Framework model
        migrations.CreateModel(
            name='Framework',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('name', models.CharField(help_text='Framework name (e.g., \'NIST SP 800-53\', \'ISO 27001\')', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Detailed description of the framework', null=True)),
                ('framework_id', models.CharField(help_text='Unique framework identifier (e.g., \'NIST-800-53\', \'ISO-27001\')', max_length=100, unique=True)),
                ('framework_type', models.CharField(choices=[('security', 'Security Control Framework'), ('privacy', 'Privacy Framework'), ('risk', 'Risk Management Framework'), ('compliance', 'Compliance Framework'), ('governance', 'Governance Framework'), ('audit', 'Audit Framework'), ('industry', 'Industry-Specific Framework'), ('custom', 'Custom Framework')], default='security', help_text='Type of framework', max_length=20)),
                ('provider', models.CharField(blank=True, help_text='Framework provider/organization (e.g., \'NIST\', \'ISO\', \'PCI\')', max_length=255, null=True)),
                ('version', models.CharField(help_text='Framework version (e.g., \'Rev. 5\', \'2022\')', max_length=50)),
                ('publication_date', models.DateField(blank=True, help_text='Framework publication date', null=True)),
                ('effective_date', models.DateField(blank=True, help_text='Date framework becomes effective', null=True)),
                ('review_date', models.DateField(blank=True, help_text='Next scheduled review date', null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published'), ('deprecated', 'Deprecated'), ('superseded', 'Superseded'), ('withdrawn', 'Withdrawn')], default='draft', help_text='Framework status', max_length=20)),
                ('scope', models.TextField(blank=True, help_text='Framework scope and applicability', null=True)),
                ('industry_sectors', models.JSONField(blank=True, default=list, help_text='Applicable industry sectors')),
                ('organization_sizes', models.JSONField(blank=True, default=list, help_text='Applicable organization sizes')),
                ('geographic_regions', models.JSONField(blank=True, default=list, help_text='Applicable geographic regions')),
                ('control_count', models.IntegerField(default=0, help_text='Total number of controls in the framework')),
                ('category_count', models.IntegerField(default=0, help_text='Number of control categories/families')),
                ('hierarchical_structure', models.JSONField(blank=True, default=dict, help_text='Hierarchical structure of controls and categories')),
                ('control_mappings', models.JSONField(blank=True, default=dict, help_text='Mappings to other frameworks')),
                ('documentation_url', models.URLField(blank=True, help_text='Official framework documentation URL', null=True)),
                ('reference_documents', models.JSONField(blank=True, default=list, help_text='Reference documents and resources')),
                ('implementation_guidance', models.TextField(blank=True, help_text='General implementation guidance', null=True)),
                ('assessment_methodology', models.TextField(blank=True, help_text='Framework assessment methodology', null=True)),
                ('certification_body', models.CharField(blank=True, help_text='Certifying body or authority', max_length=255, null=True)),
                ('certification_requirements', models.TextField(blank=True, help_text='Certification requirements and process', null=True)),
                ('adoption_level', models.CharField(blank=True, help_text='Framework adoption level (e.g., \'Mandatory\', \'Recommended\')', max_length=50, null=True)),
                ('mandatory_for', models.JSONField(blank=True, default=list, help_text='Organizations/industries where framework is mandatory')),
                ('related_framework_ids', models.JSONField(blank=True, default=list, help_text='IDs of related frameworks')),
                ('superseding_framework_ids', models.JSONField(blank=True, default=list, help_text='IDs of frameworks that supersede this one')),
                ('superseded_by_framework_ids', models.JSONField(blank=True, default=list, help_text='IDs of frameworks that this one supersedes')),
                ('usage_count', models.IntegerField(default=0, help_text='Number of times framework has been used')),
                ('active_assessments', models.IntegerField(default=0, help_text='Number of active assessments using this framework')),
                ('tags', models.JSONField(blank=True, default=list, help_text='Framework tags for organization')),
                ('custom_fields', models.JSONField(blank=True, default=dict, help_text='Custom fields for additional framework properties')),
                ('maturity_level', models.CharField(blank=True, help_text='Framework maturity level', max_length=50, null=True)),
                ('last_updated', models.DateField(blank=True, help_text='Last framework update date', null=True)),
                ('update_frequency', models.CharField(blank=True, help_text='Expected update frequency (e.g., \'Annual\', \'Biennial\')', max_length=50, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'db_table': 'frameworks',
            },
        ),

        # Control model
        migrations.CreateModel(
            name='Control',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('control_id', models.CharField(help_text='Control identifier (e.g., \'AC-2\', \'IA-5.1\')', max_length=100)),
                ('title', models.CharField(help_text='Control title', max_length=500)),
                ('framework_id', models.UUIDField(help_text='ID of the framework this control belongs to')),
                ('framework_control_id', models.CharField(help_text='Unique control ID within the framework', max_length=100)),
                ('control_type', models.CharField(choices=[('preventive', 'Preventive'), ('detective', 'Detective'), ('corrective', 'Corrective'), ('deterrent', 'Deterrent'), ('compensating', 'Compensating'), ('recovery', 'Recovery'), ('directive', 'Directive')], default='preventive', help_text='Type of control', max_length=20)),
                ('family', models.CharField(help_text='Control family (e.g., \'Access Control\', \'Incident Response\')', max_length=100)),
                ('subfamily', models.CharField(blank=True, help_text='Control subfamily for further categorization', max_length=100, null=True)),
                ('statement', models.TextField(help_text='Control statement/requirement')),
                ('discussion', models.TextField(blank=True, help_text='Discussion/elaboration of the control', null=True)),
                ('guidance', models.TextField(blank=True, help_text='Implementation guidance', null=True)),
                ('parameters', models.JSONField(blank=True, default=list, help_text='Control parameters and their values')),
                ('parent_control_id', models.CharField(blank=True, help_text='Parent control ID (for hierarchical controls)', max_length=100, null=True)),
                ('child_control_ids', models.JSONField(blank=True, default=list, help_text='Child control IDs')),
                ('related_control_ids', models.JSONField(blank=True, default=list, help_text='Related control IDs within same framework')),
                ('priority', models.CharField(choices=[('very_low', 'Very Low'), ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('very_high', 'Very High'), ('critical', 'Critical')], default='moderate', help_text='Control priority/importance', max_length=20)),
                ('baseline_inclusion', models.JSONField(blank=True, default=list, help_text='Baselines that include this control')),
                ('status', models.CharField(choices=[('active', 'Active'), ('deprecated', 'Deprecated'), ('withdrawn', 'Withdrawn'), ('superseded', 'Superseded')], default='active', help_text='Control status', max_length=20)),
                ('implementation_references', models.JSONField(blank=True, default=list, help_text='References to implementation guidance')),
                ('assessment_methods', models.JSONField(blank=True, default=list, help_text='Methods for assessing control implementation')),
                ('testing_procedures', models.JSONField(blank=True, default=list, help_text='Procedures for testing control effectiveness')),
                ('control_mappings', models.JSONField(blank=True, default=dict, help_text='Mappings to controls in other frameworks')),
                ('enhancements', models.JSONField(blank=True, default=list, help_text='Control enhancements and supplemental guidance')),
                ('sort_order', models.IntegerField(default=0, help_text='Sort order within family')),
                ('version', models.CharField(default='1.0', help_text='Control version', max_length=20)),
                ('last_updated', models.DateField(blank=True, help_text='Last update date', null=True)),
                ('implementation_count', models.IntegerField(default=0, help_text='Number of implementations of this control')),
                ('assessment_count', models.IntegerField(default=0, help_text='Number of assessments of this control')),
                ('average_compliance_score', models.FloatField(default=0.0, help_text='Average compliance score across assessments')),
                ('tags', models.JSONField(blank=True, default=list, help_text='Control tags for organization')),
                ('custom_fields', models.JSONField(blank=True, default=dict, help_text='Custom fields for additional control properties')),
            ],
            options={
                'ordering': ['framework_id', 'family', 'sort_order'],
                'db_table': 'controls',
            },
        ),

        # Control Implementation model
        migrations.CreateModel(
            name='ControlImplementation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('implementation_id', models.CharField(help_text='Unique implementation identifier', max_length=100, unique=True)),
                ('control_id', models.UUIDField(help_text='ID of the control being implemented')),
                ('framework_id', models.UUIDField(help_text='ID of the framework')),
                ('context_type', models.CharField(help_text='Type of context (system, process, asset, service)', max_length=50)),
                ('context_id', models.UUIDField(help_text='ID of the context entity')),
                ('context_name', models.CharField(help_text='Name of the context entity', max_length=255)),
                ('implementation_statement', models.TextField(blank=True, help_text='Specific implementation statement', null=True)),
                ('implementation_details', models.TextField(blank=True, help_text='Detailed implementation description', null=True)),
                ('responsible_party', models.CharField(blank=True, help_text='Party responsible for implementation', max_length=255, null=True)),
                ('status', models.CharField(choices=[('not_implemented', 'Not Implemented'), ('planned', 'Planned'), ('in_progress', 'In Progress'), ('implemented', 'Implemented'), ('verified', 'Verified'), ('not_applicable', 'Not Applicable'), ('compensated', 'Compensated'), ('inherited', 'Inherited')], default='not_implemented', help_text='Implementation status', max_length=20)),
                ('planned_date', models.DateField(blank=True, help_text='Planned implementation date', null=True)),
                ('implemented_date', models.DateField(blank=True, help_text='Actual implementation date', null=True)),
                ('verified_date', models.DateField(blank=True, help_text='Verification date', null=True)),
                ('compliance_status', models.CharField(blank=True, help_text='Compliance status (compliant, non-compliant, etc.)', max_length=50, null=True)),
                ('compliance_score', models.IntegerField(default=0, help_text='Compliance score (0-100)')),
                ('assessment_date', models.DateField(blank=True, help_text='Last assessment date', null=True)),
                ('assessor', models.CharField(blank=True, help_text='Person/entity who performed assessment', max_length=255, null=True)),
                ('assessment_notes', models.TextField(blank=True, help_text='Assessment notes and findings', null=True)),
                ('evidence_ids', models.JSONField(blank=True, default=list, help_text='IDs of evidence supporting this implementation')),
                ('primary_evidence_id', models.UUIDField(blank=True, help_text='ID of primary evidence', null=True)),
                ('risk_level', models.CharField(choices=[('very_low', 'Very Low'), ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('very_high', 'Very High'), ('critical', 'Critical')], default='moderate', help_text='Risk level if not implemented', max_length=20)),
                ('business_impact', models.TextField(blank=True, help_text='Business impact of non-implementation', null=True)),
                ('implementation_cost', models.DecimalField(blank=True, decimal_places=2, help_text='Estimated implementation cost', max_digits=12, null=True)),
                ('implementation_effort', models.CharField(blank=True, help_text='Implementation effort (Low, Medium, High)', max_length=50, null=True)),
                ('maintenance_cost', models.DecimalField(blank=True, decimal_places=2, help_text='Annual maintenance cost', max_digits=12, null=True)),
                ('inherited_from', models.CharField(blank=True, help_text='Source of inheritance (if applicable)', max_length=255, null=True)),
                ('compensating_controls', models.JSONField(blank=True, default=list, help_text='Compensating controls (if applicable)')),
                ('review_frequency', models.CharField(blank=True, help_text='Review frequency (e.g., \'Annual\', \'Quarterly\')', max_length=50, null=True)),
                ('next_review_date', models.DateField(blank=True, help_text='Next scheduled review date', null=True)),
                ('last_review_date', models.DateField(blank=True, help_text='Last review date', null=True)),
                ('has_exception', models.BooleanField(default=False, help_text='Whether an exception/deviation exists')),
                ('exception_justification', models.TextField(blank=True, help_text='Exception/deviation justification', null=True)),
                ('exception_approved', models.BooleanField(blank=True, help_text='Whether exception is approved', null=True)),
                ('exception_expiry', models.DateField(blank=True, help_text='Exception expiry date', null=True)),
                ('automated_monitoring', models.BooleanField(default=False, help_text='Whether implementation is automatically monitored')),
                ('monitoring_details', models.JSONField(blank=True, default=dict, help_text='Monitoring configuration and details')),
                ('alert_rules', models.JSONField(blank=True, default=list, help_text='Alert rules for this implementation')),
                ('system_integration', models.JSONField(blank=True, default=dict, help_text='Integration details with other systems')),
                ('tags', models.JSONField(blank=True, default=list, help_text='Implementation tags')),
                ('custom_fields', models.JSONField(blank=True, default=dict, help_text='Custom fields for additional properties')),
                ('access_count', models.IntegerField(default=0, help_text='Number of times accessed/reviewed')),
            ],
            options={
                'ordering': ['-created_at'],
                'db_table': 'control_implementations',
            },
        ),

        # Framework indexes
        migrations.AddIndex(
            model_name='framework',
            index=models.Index(fields=['framework_type', 'status'], name='framework_type_status_idx'),
        ),
        migrations.AddIndex(
            model_name='framework',
            index=models.Index(fields=['provider'], name='framework_provider_idx'),
        ),
        migrations.AddIndex(
            model_name='framework',
            index=models.Index(fields=['status'], name='framework_status_idx'),
        ),
        migrations.AddIndex(
            model_name='framework',
            index=models.Index(fields=['publication_date'], name='framework_publication_idx'),
        ),
        migrations.AddIndex(
            model_name='framework',
            index=models.Index(fields=['effective_date'], name='framework_effective_idx'),
        ),
        migrations.AddIndex(
            model_name='framework',
            index=models.Index(fields=['usage_count'], name='framework_usage_idx'),
        ),
        migrations.AddIndex(
            model_name='framework',
            index=models.Index(fields=['created_at'], name='framework_created_idx'),
        ),

        # Control indexes
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['framework_id', 'control_id'], name='control_framework_id_idx'),
        ),
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['framework_id', 'family'], name='control_framework_family_idx'),
        ),
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['control_type'], name='control_type_idx'),
        ),
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['family'], name='control_family_idx'),
        ),
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['priority'], name='control_priority_idx'),
        ),
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['status'], name='control_status_idx'),
        ),
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['sort_order'], name='control_sort_idx'),
        ),
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['implementation_count'], name='control_implementation_idx'),
        ),
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['created_at'], name='control_created_idx'),
        ),

        # Control Implementation indexes
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['control_id', 'context_id'], name='impl_control_context_idx'),
        ),
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['framework_id'], name='impl_framework_idx'),
        ),
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['context_type', 'context_id'], name='impl_context_type_idx'),
        ),
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['status'], name='impl_status_idx'),
        ),
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['compliance_status'], name='impl_compliance_idx'),
        ),
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['risk_level'], name='impl_risk_idx'),
        ),
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['next_review_date'], name='impl_review_idx'),
        ),
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['exception_expiry'], name='impl_exception_idx'),
        ),
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['created_at'], name='impl_created_idx'),
        ),

        # Unique constraints
        migrations.AddConstraint(
            model_name='control',
            constraint=models.UniqueConstraint(fields=['framework_id', 'framework_control_id'], name='unique_framework_control'),
        ),
        migrations.AddConstraint(
            model_name='controlimplementation',
            constraint=models.UniqueConstraint(fields=['control_id', 'context_id'], name='unique_control_context'),
        ),
    ]
