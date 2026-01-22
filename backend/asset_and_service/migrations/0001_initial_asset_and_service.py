# Generated migration for Asset and Service bounded context

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        # Asset model
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('name', models.CharField(help_text='Asset name or identifier', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Detailed description of the asset', null=True)),
                ('asset_id', models.CharField(help_text='Unique asset identifier (e.g., AST-001, HW-001)', max_length=100, unique=True)),
                ('asset_type', models.CharField(choices=[('hardware', 'Hardware'), ('software', 'Software'), ('data', 'Data'), ('network', 'Network Infrastructure'), ('cloud_service', 'Cloud Service'), ('physical', 'Physical Asset'), ('intangible', 'Intangible Asset'), ('service', 'Service'), ('other', 'Other')], default='hardware', help_text='Type of asset', max_length=20)),
                ('category', models.CharField(blank=True, help_text='Asset category (e.g., \'Server\', \'Database\', \'Network Device\')', max_length=100, null=True)),
                ('subcategory', models.CharField(blank=True, help_text='Asset subcategory for further classification', max_length=100, null=True)),
                ('sensitivity_level', models.CharField(choices=[('public', 'Public'), ('internal', 'Internal'), ('confidential', 'Confidential'), ('restricted', 'Restricted'), ('highly_sensitive', 'Highly Sensitive')], default='internal', help_text='Data sensitivity or classification level', max_length=20)),
                ('criticality_level', models.CharField(choices=[('very_low', 'Very Low'), ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('very_high', 'Very High'), ('critical', 'Critical')], default='moderate', help_text='Business criticality of the asset', max_length=20)),
                ('acquisition_cost', models.DecimalField(blank=True, decimal_places=2, help_text='Original acquisition cost', max_digits=12, null=True)),
                ('current_value', models.DecimalField(blank=True, decimal_places=2, help_text='Current assessed value', max_digits=12, null=True)),
                ('depreciation_method', models.CharField(blank=True, help_text='Depreciation method used', max_length=50, null=True)),
                ('useful_life_years', models.IntegerField(blank=True, help_text='Expected useful life in years', null=True)),
                ('location', models.CharField(blank=True, help_text='Physical or logical location', max_length=255, null=True)),
                ('room', models.CharField(blank=True, help_text='Room or specific location identifier', max_length=100, null=True)),
                ('rack_position', models.CharField(blank=True, help_text='Rack position for data center assets', max_length=50, null=True)),
                ('manufacturer', models.CharField(blank=True, help_text='Asset manufacturer or vendor', max_length=100, null=True)),
                ('model', models.CharField(blank=True, help_text='Asset model or version', max_length=100, null=True)),
                ('serial_number', models.CharField(blank=True, help_text='Serial number or unique identifier', max_length=100, null=True)),
                ('firmware_version', models.CharField(blank=True, help_text='Firmware or software version', max_length=50, null=True)),
                ('status', models.CharField(choices=[('planned', 'Planned'), ('procured', 'Procured'), ('deployed', 'Deployed'), ('active', 'Active'), ('maintenance', 'Under Maintenance'), ('decommissioned', 'Decommissioned'), ('disposed', 'Disposed'), ('lost_stolen', 'Lost/Stolen')], default='planned', help_text='Current lifecycle status', max_length=20)),
                ('acquisition_date', models.DateField(blank=True, help_text='Date asset was acquired', null=True)),
                ('deployment_date', models.DateField(blank=True, help_text='Date asset was deployed', null=True)),
                ('last_maintenance_date', models.DateField(blank=True, help_text='Date of last maintenance', null=True)),
                ('next_maintenance_date', models.DateField(blank=True, help_text='Date of next scheduled maintenance', null=True)),
                ('warranty_expiry_date', models.DateField(blank=True, help_text='Warranty expiry date', null=True)),
                ('end_of_life_date', models.DateField(blank=True, help_text='Expected end of life date', null=True)),
                ('disposal_date', models.DateField(blank=True, help_text='Date asset was disposed', null=True)),
                ('owner_user_id', models.UUIDField(blank=True, db_index=True, help_text='User ID of the asset owner', null=True)),
                ('owner_username', models.CharField(blank=True, help_text='Username of the asset owner', max_length=150, null=True)),
                ('custodian_user_id', models.UUIDField(blank=True, db_index=True, help_text='User ID of the asset custodian', null=True)),
                ('custodian_username', models.CharField(blank=True, help_text='Username of the asset custodian', max_length=150, null=True)),
                ('owning_organization', models.CharField(blank=True, help_text='Organization or department owning the asset', max_length=255, null=True)),
                ('parent_asset_ids', models.JSONField(blank=True, default=list, help_text='IDs of parent assets (what this asset belongs to)')),
                ('child_asset_ids', models.JSONField(blank=True, default=list, help_text='IDs of child assets (what belongs to this asset)')),
                ('related_asset_ids', models.JSONField(blank=True, default=list, help_text='IDs of related assets')),
                ('supporting_service_ids', models.JSONField(blank=True, default=list, help_text='IDs of services that support this asset')),
                ('dependent_service_ids', models.JSONField(blank=True, default=list, help_text='IDs of services that depend on this asset')),
                ('risk_score', models.IntegerField(default=0, help_text='Calculated risk score (0-100)')),
                ('compliance_status', models.CharField(blank=True, help_text='Compliance status (compliant, non-compliant, etc.)', max_length=50, null=True)),
                ('last_assessment_date', models.DateField(blank=True, help_text='Date of last risk/compliance assessment', null=True)),
                ('configuration_baseline', models.TextField(blank=True, help_text='Baseline configuration', null=True)),
                ('last_configuration_change', models.DateTimeField(blank=True, help_text='Last configuration change timestamp', null=True)),
                ('change_history', models.JSONField(blank=True, default=list, help_text='History of configuration changes')),
                ('monitoring_enabled', models.BooleanField(default=False, help_text='Whether asset is monitored')),
                ('monitoring_details', models.JSONField(blank=True, default=dict, help_text='Monitoring configuration and thresholds')),
                ('alert_rules', models.JSONField(blank=True, default=list, help_text='Alert rules for this asset')),
                ('tags', models.JSONField(blank=True, default=list, help_text='Asset tags for organization and filtering')),
                ('custom_fields', models.JSONField(blank=True, default=dict, help_text='Custom fields for additional asset properties')),
                ('usage_metrics', models.JSONField(blank=True, default=dict, help_text='Usage statistics and metrics')),
                ('access_logs', models.JSONField(blank=True, default=list, help_text='Recent access and usage logs')),
            ],
            options={
                'ordering': ['-created_at'],
                'db_table': 'assets',
            },
        ),

        # Service model
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('name', models.CharField(help_text='Service name', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Detailed description of the service', null=True)),
                ('service_id', models.CharField(help_text='Unique service identifier (e.g., SVC-001, APP-001)', max_length=100, unique=True)),
                ('service_type', models.CharField(choices=[('business', 'Business Service'), ('technical', 'Technical Service'), ('application', 'Application Service'), ('infrastructure', 'Infrastructure Service'), ('network', 'Network Service'), ('security', 'Security Service'), ('cloud', 'Cloud Service'), ('other', 'Other')], default='technical', help_text='Type of service', max_length=20)),
                ('category', models.CharField(blank=True, help_text='Service category (e.g., \'Authentication\', \'Database\', \'Web Service\')', max_length=100, null=True)),
                ('criticality_level', models.CharField(choices=[('very_low', 'Very Low'), ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('very_high', 'Very High'), ('critical', 'Critical')], default='moderate', help_text='Business criticality of the service', max_length=20)),
                ('status', models.CharField(choices=[('planned', 'Planned'), ('design', 'Design'), ('development', 'Development'), ('testing', 'Testing'), ('deployment', 'Deployment'), ('active', 'Active'), ('maintenance', 'Maintenance'), ('deprecated', 'Deprecated'), ('retired', 'Retired')], default='planned', help_text='Current lifecycle status', max_length=20)),
                ('owner_user_id', models.UUIDField(blank=True, db_index=True, help_text='User ID of the service owner', null=True)),
                ('owner_username', models.CharField(blank=True, help_text='Username of the service owner', max_length=150, null=True)),
                ('manager_user_id', models.UUIDField(blank=True, db_index=True, help_text='User ID of the service manager', null=True)),
                ('manager_username', models.CharField(blank=True, help_text='Username of the service manager', max_length=150, null=True)),
                ('owning_organization', models.CharField(blank=True, help_text='Organization or department owning the service', max_length=255, null=True)),
                ('portfolio', models.CharField(blank=True, help_text='Service portfolio (e.g., \'Core\', \'Support\', \'Development\')', max_length=100, null=True)),
                ('version', models.CharField(blank=True, help_text='Service version', max_length=50, null=True)),
                ('sla_availability_target', models.FloatField(blank=True, help_text='SLA availability target as percentage (e.g., 99.9)', null=True)),
                ('sla_response_time_target', models.IntegerField(blank=True, help_text='SLA response time target in seconds', null=True)),
                ('sla_resolution_time_target', models.IntegerField(blank=True, help_text='SLA resolution time target in seconds', null=True)),
                ('dependent_service_ids', models.JSONField(blank=True, default=list, help_text='IDs of services this service depends on')),
                ('supporting_service_ids', models.JSONField(blank=True, default=list, help_text='IDs of services that support this service')),
                ('dependent_asset_ids', models.JSONField(blank=True, default=list, help_text='IDs of assets this service depends on')),
                ('supporting_asset_ids', models.JSONField(blank=True, default=list, help_text='IDs of assets that support this service')),
                ('consumer_groups', models.JSONField(blank=True, default=list, help_text='Groups or roles that consume this service')),
                ('stakeholder_contacts', models.JSONField(blank=True, default=list, help_text='Key stakeholders and their contact information')),
                ('documentation_url', models.URLField(blank=True, help_text='URL to service documentation', null=True)),
                ('api_documentation_url', models.URLField(blank=True, help_text='URL to API documentation', null=True)),
                ('runbook_url', models.URLField(blank=True, help_text='URL to operational runbook', null=True)),
                ('monitoring_enabled', models.BooleanField(default=False, help_text='Whether service is monitored')),
                ('monitoring_details', models.JSONField(blank=True, default=dict, help_text='Monitoring configuration and endpoints')),
                ('health_check_url', models.URLField(blank=True, help_text='Health check endpoint URL', null=True)),
                ('availability_percentage', models.FloatField(default=0.0, help_text='Current availability percentage')),
                ('average_response_time', models.IntegerField(default=0, help_text='Average response time in milliseconds')),
                ('error_rate_percentage', models.FloatField(default=0.0, help_text='Error rate percentage')),
                ('throughput_requests_per_minute', models.IntegerField(default=0, help_text='Throughput in requests per minute')),
                ('incident_count', models.IntegerField(default=0, help_text='Number of incidents in the last 30 days')),
                ('open_incident_count', models.IntegerField(default=0, help_text='Number of currently open incidents')),
                ('problem_count', models.IntegerField(default=0, help_text='Number of known problems')),
                ('planned_changes', models.JSONField(blank=True, default=list, help_text='Upcoming planned changes')),
                ('emergency_changes', models.IntegerField(default=0, help_text='Number of emergency changes in last 30 days')),
                ('annual_cost', models.DecimalField(blank=True, decimal_places=2, help_text='Annual cost of the service', max_digits=12, null=True)),
                ('cost_center', models.CharField(blank=True, help_text='Cost center code', max_length=50, null=True)),
                ('budget_category', models.CharField(blank=True, help_text='Budget category', max_length=100, null=True)),
                ('recovery_time_objective', models.IntegerField(blank=True, help_text='Recovery Time Objective in minutes', null=True)),
                ('recovery_point_objective', models.IntegerField(blank=True, help_text='Recovery Point Objective in minutes', null=True)),
                ('backup_frequency', models.CharField(blank=True, help_text='Backup frequency (e.g., \'daily\', \'hourly\')', max_length=50, null=True)),
                ('planned_go_live_date', models.DateField(blank=True, help_text='Planned go-live date', null=True)),
                ('actual_go_live_date', models.DateField(blank=True, help_text='Actual go-live date', null=True)),
                ('last_review_date', models.DateField(blank=True, help_text='Date of last service review', null=True)),
                ('next_review_date', models.DateField(blank=True, help_text='Date of next scheduled review', null=True)),
                ('end_of_life_date', models.DateField(blank=True, help_text='Planned end of life date', null=True)),
                ('customer_satisfaction_score', models.FloatField(blank=True, help_text='Customer satisfaction score (1-5)', null=True)),
                ('service_quality_score', models.FloatField(blank=True, help_text='Overall service quality score (1-5)', null=True)),
                ('configuration_items', models.JSONField(blank=True, default=list, help_text='Configuration items related to this service')),
                ('technical_details', models.JSONField(blank=True, default=dict, help_text='Technical specifications and details')),
                ('tags', models.JSONField(blank=True, default=list, help_text='Service tags for organization and filtering')),
                ('custom_fields', models.JSONField(blank=True, default=dict, help_text='Custom fields for additional service properties')),
            ],
            options={
                'ordering': ['-created_at'],
                'db_table': 'services',
            },
        ),

        # Asset indexes
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['asset_type', 'status'], name='asset_type_status_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['category', 'subcategory'], name='asset_category_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['owner_user_id'], name='asset_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['criticality_level'], name='asset_criticality_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['sensitivity_level'], name='asset_sensitivity_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['status'], name='asset_status_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['location'], name='asset_location_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['next_maintenance_date'], name='asset_maintenance_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['end_of_life_date'], name='asset_eol_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['created_at'], name='asset_created_idx'),
        ),

        # Service indexes
        migrations.AddIndex(
            model_name='service',
            index=models.Index(fields=['service_type', 'status'], name='service_type_status_idx'),
        ),
        migrations.AddIndex(
            model_name='service',
            index=models.Index(fields=['category'], name='service_category_idx'),
        ),
        migrations.AddIndex(
            model_name='service',
            index=models.Index(fields=['owner_user_id'], name='service_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='service',
            index=models.Index(fields=['criticality_level'], name='service_criticality_idx'),
        ),
        migrations.AddIndex(
            model_name='service',
            index=models.Index(fields=['status'], name='service_status_idx'),
        ),
        migrations.AddIndex(
            model_name='service',
            index=models.Index(fields=['portfolio'], name='service_portfolio_idx'),
        ),
        migrations.AddIndex(
            model_name='service',
            index=models.Index(fields=['next_review_date'], name='service_review_idx'),
        ),
        migrations.AddIndex(
            model_name='service',
            index=models.Index(fields=['end_of_life_date'], name='service_eol_idx'),
        ),
        migrations.AddIndex(
            model_name='service',
            index=models.Index(fields=['created_at'], name='service_created_idx'),
        ),
    ]
