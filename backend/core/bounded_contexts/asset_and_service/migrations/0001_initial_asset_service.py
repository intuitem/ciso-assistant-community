# Generated migration for Asset and Service bounded context

from django.db import migrations, models
import uuid
from django.contrib.postgres.fields import ArrayField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0001_initial'),
    ]

    operations = [
        # Supporting Entities
        migrations.CreateModel(
            name='AssetLabel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('color', models.CharField(blank=True, help_text='Hex color code', max_length=7, null=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'asset_service_asset_labels',
                'verbose_name': 'Asset Label',
                'verbose_name_plural': 'Asset Labels',
            },
        ),
        migrations.CreateModel(
            name='AssetClassification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('confidentiality_impact', models.IntegerField(default=1, help_text='Confidentiality impact (1-5)')),
                ('integrity_impact', models.IntegerField(default=1, help_text='Integrity impact (1-5)')),
                ('availability_impact', models.IntegerField(default=1, help_text='Availability impact (1-5)')),
            ],
            options={
                'db_table': 'asset_service_asset_classifications',
                'verbose_name': 'Asset Classification',
                'verbose_name_plural': 'Asset Classifications',
            },
        ),
        migrations.CreateModel(
            name='ServiceClassification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'asset_service_service_classifications',
                'verbose_name': 'Service Classification',
                'verbose_name_plural': 'Service Classifications',
            },
        ),
        
        # Asset aggregate
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('ref_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('asset_type', models.CharField(choices=[('primary', 'Primary'), ('support', 'Support')], db_index=True, default='support', max_length=20)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('in_use', 'In Use'), ('archived', 'Archived')], db_index=True, default='draft', max_length=20)),
                ('assetClassificationId', models.UUIDField(blank=True, db_index=True, null=True)),
                ('assetLabelIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of asset label IDs', size=None)),
                ('businessOwnerOrgUnitIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of business owner organizational unit IDs', size=None)),
                ('systemOwnerUserIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of system owner user IDs', size=None)),
                ('processIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of process IDs', size=None)),
                ('dataAssetIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of data asset IDs', size=None)),
                ('serviceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of service IDs', size=None)),
                ('thirdPartyIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of third party IDs', size=None)),
                ('controlIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of control IDs', size=None)),
                ('riskIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of risk IDs', size=None)),
                ('business_value', models.CharField(blank=True, max_length=200, null=True)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'asset_service_assets',
                'verbose_name': 'Asset',
                'verbose_name_plural': 'Assets',
            },
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['lifecycle_state', 'asset_type'], name='asset_svc_asset_life_type_idx'),
        ),
        
        # Service aggregate
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('ref_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('serviceClassificationId', models.UUIDField(blank=True, db_index=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('operational', 'Operational'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('assetIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of asset IDs', size=None)),
                ('thirdPartyIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of third party IDs', size=None)),
                ('controlIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of control IDs', size=None)),
                ('riskIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of risk IDs', size=None)),
                ('contractIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of service contract IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'asset_service_services',
                'verbose_name': 'Service',
                'verbose_name_plural': 'Services',
            },
        ),
        
        # Process aggregate
        migrations.CreateModel(
            name='Process',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('ref_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('orgUnitIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of organizational unit IDs', size=None)),
                ('assetIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of asset IDs', size=None)),
                ('controlIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of control IDs', size=None)),
                ('riskIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of risk IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'asset_service_processes',
                'verbose_name': 'Process',
                'verbose_name_plural': 'Processes',
            },
        ),
        
        # ServiceContract association
        migrations.CreateModel(
            name='ServiceContract',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('serviceId', models.UUIDField(db_index=True)),
                ('thirdPartyId', models.UUIDField(db_index=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired')], db_index=True, default='draft', max_length=20)),
                ('start_date', models.DateField(db_index=True)),
                ('end_date', models.DateField(blank=True, db_index=True, null=True)),
                ('renewal_date', models.DateField(blank=True, db_index=True, null=True)),
                ('key_terms', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'asset_service_contracts',
                'verbose_name': 'Service Contract',
                'verbose_name_plural': 'Service Contracts',
            },
        ),
        migrations.AddIndex(
            model_name='servicecontract',
            index=models.Index(fields=['serviceId', 'thirdPartyId'], name='asset_svc_contract_svc_tp_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='servicecontract',
            unique_together={('serviceId', 'thirdPartyId', 'start_date')},
        ),
        
        # Read Models
        migrations.CreateModel(
            name='AssetOverview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset_id', models.UUIDField(db_index=True, unique=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('ref_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('asset_type', models.CharField(db_index=True, max_length=20)),
                ('lifecycle_state', models.CharField(db_index=True, max_length=20)),
                ('control_count', models.IntegerField(default=0)),
                ('control_implementation_status_summary', models.JSONField(blank=True, default=dict, help_text='Summary of control implementation statuses')),
                ('risk_count', models.IntegerField(default=0)),
                ('risk_residual_score_summary', models.JSONField(blank=True, default=dict, help_text='Summary of risk residual scores')),
                ('third_party_count', models.IntegerField(default=0)),
                ('third_party_contract_status_summary', models.JSONField(blank=True, default=dict, help_text='Summary of third party contract statuses')),
                ('third_party_assessment_status_summary', models.JSONField(blank=True, default=dict, help_text='Summary of third party assessment statuses')),
                ('service_count', models.IntegerField(default=0)),
                ('service_status_summary', models.JSONField(blank=True, default=dict, help_text='Summary of service statuses')),
            ],
            options={
                'db_table': 'asset_service_asset_overviews',
                'verbose_name': 'Asset Overview',
                'verbose_name_plural': 'Asset Overviews',
            },
        ),
    ]

