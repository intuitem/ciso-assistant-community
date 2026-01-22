# Generated migration for Privacy bounded context

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
        # DataAsset aggregate
        migrations.CreateModel(
            name='DataAsset',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('data_categories', models.JSONField(blank=True, default=list, help_text='Array of data category strings')),
                ('contains_personal_data', models.BooleanField(db_index=True, default=False, help_text='Whether this asset contains personal data')),
                ('retention_policy', models.TextField(blank=True, help_text='Retention policy description', null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('assetIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of asset IDs that store this data', size=None)),
                ('ownerOrgUnitIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of owner organizational unit IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'privacy_data_assets',
                'verbose_name': 'Data Asset',
                'verbose_name_plural': 'Data Assets',
            },
        ),
        migrations.AddIndex(
            model_name='dataasset',
            index=models.Index(fields=['contains_personal_data'], name='privacy_da_personal_idx'),
        ),
        
        # DataFlow aggregate
        migrations.CreateModel(
            name='DataFlow',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('purpose', models.TextField(blank=True, help_text='Purpose of the data flow', null=True)),
                ('source_system_asset_id', models.UUIDField(db_index=True, help_text='ID of the source system asset')),
                ('destination_system_asset_id', models.UUIDField(db_index=True, help_text='ID of the destination system asset')),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('dataAssetIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of data asset IDs flowing through this flow', size=None)),
                ('thirdPartyIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of third party IDs involved in this flow', size=None)),
                ('controlImplementationIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of control implementation IDs', size=None)),
                ('privacyRiskIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of privacy risk IDs', size=None)),
                ('transfer_mechanisms', models.JSONField(blank=True, default=list, help_text='Array of transfer mechanism strings (e.g., API, SFTP, Email)')),
                ('encryption_in_transit', models.BooleanField(blank=True, db_index=True, help_text='Whether data is encrypted in transit', null=True)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'privacy_data_flows',
                'verbose_name': 'Data Flow',
                'verbose_name_plural': 'Data Flows',
            },
        ),
        migrations.AddIndex(
            model_name='dataflow',
            index=models.Index(fields=['source_system_asset_id', 'destination_system_asset_id'], name='privacy_df_source_dest_idx'),
        ),
        
        # Read Models
        migrations.CreateModel(
            name='PrivacyOverview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('total_data_assets', models.IntegerField(default=0)),
                ('active_data_assets', models.IntegerField(default=0)),
                ('data_assets_with_personal_data', models.IntegerField(default=0)),
                ('total_data_flows', models.IntegerField(default=0)),
                ('active_data_flows', models.IntegerField(default=0)),
                ('flows_without_encryption', models.IntegerField(default=0)),
                ('total_privacy_risks', models.IntegerField(default=0)),
                ('open_privacy_risks', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'privacy_privacy_overviews',
                'verbose_name': 'Privacy Overview',
                'verbose_name_plural': 'Privacy Overviews',
            },
        ),
    ]

