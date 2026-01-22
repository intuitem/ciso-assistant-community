# Generated migration for Organization bounded context

from django.db import migrations, models
import uuid
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0001_initial'),  # Core app migrations
        # Note: EventStore is in core.domain, but migrations are handled separately
        # If EventStore migration exists, add: ('core_domain', '0001_initial_domain_events')
    ]

    operations = [
        # OrgUnit aggregate
        migrations.CreateModel(
            name='OrgUnit',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('ref_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('parentOrgUnitId', models.UUIDField(blank=True, db_index=True, null=True)),
                ('childOrgUnitIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of child organizational unit IDs', size=None)),
                ('ownerUserIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of owner user IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'organization_org_units',
                'verbose_name': 'Organizational Unit',
                'verbose_name_plural': 'Organizational Units',
            },
        ),
        migrations.AddIndex(
            model_name='orgunit',
            index=models.Index(fields=['parentOrgUnitId', 'lifecycle_state'], name='org_orgunit_parent_life_idx'),
        ),
        
        # User aggregate
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('email', models.EmailField(db_index=True, max_length=254, unique=True)),
                ('display_name', models.CharField(blank=True, max_length=255, null=True)),
                ('first_name', models.CharField(blank=True, max_length=150, null=True)),
                ('last_name', models.CharField(blank=True, max_length=150, null=True)),
                ('password', models.CharField(blank=True, max_length=128, null=True)),
                ('is_superuser', models.BooleanField(default=False)),
                ('lifecycle_state', models.CharField(choices=[('invited', 'Invited'), ('active', 'Active'), ('disabled', 'Disabled')], db_index=True, default='invited', max_length=20)),
                ('groupIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of group IDs the user belongs to', size=None)),
                ('orgUnitIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of organizational unit IDs the user belongs to', size=None)),
                ('preferences', models.JSONField(blank=True, default=dict)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('observation', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'organization_users',
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
            },
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='org_user_email_idx'),
        ),
        
        # Group aggregate
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('active', 'Active'), ('retired', 'Retired')], db_index=True, default='active', max_length=20)),
                ('permissionIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of permission IDs', size=None)),
                ('userIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of user IDs in this group', size=None)),
                ('builtin', models.BooleanField(default=False, help_text='Built-in groups cannot be deleted')),
            ],
            options={
                'db_table': 'organization_groups',
                'verbose_name': 'Group',
                'verbose_name_plural': 'Groups',
            },
        ),
        
        # ResponsibilityAssignment association
        migrations.CreateModel(
            name='ResponsibilityAssignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('subject_type', models.CharField(choices=[('asset', 'Asset'), ('process', 'Process'), ('service', 'Service'), ('risk', 'Risk'), ('control', 'Control'), ('policy', 'Policy'), ('project', 'Project'), ('data_asset', 'Data Asset'), ('data_flow', 'Data Flow'), ('third_party', 'Third Party'), ('org_unit', 'Organizational Unit')], db_index=True, max_length=50)),
                ('subject_id', models.UUIDField(db_index=True)),
                ('userId', models.UUIDField(db_index=True)),
                ('role', models.CharField(db_index=True, max_length=255)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'organization_responsibility_assignments',
                'verbose_name': 'Responsibility Assignment',
                'verbose_name_plural': 'Responsibility Assignments',
            },
        ),
        migrations.AddIndex(
            model_name='responsibilityassignment',
            index=models.Index(fields=['subject_type', 'subject_id'], name='org_resp_subject_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='responsibilityassignment',
            unique_together={('subject_type', 'subject_id', 'userId', 'role')},
        ),
        
        # Read Models
        migrations.CreateModel(
            name='OrgUnitOverview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('org_unit_id', models.UUIDField(db_index=True, unique=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('ref_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('lifecycle_state', models.CharField(db_index=True, max_length=20)),
                ('child_count', models.IntegerField(default=0)),
                ('owner_count', models.IntegerField(default=0)),
                ('user_count', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'organization_org_unit_overviews',
                'verbose_name': 'Org Unit Overview',
                'verbose_name_plural': 'Org Unit Overviews',
            },
        ),
        migrations.CreateModel(
            name='UserOverview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.UUIDField(db_index=True, unique=True)),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('display_name', models.CharField(blank=True, max_length=255, null=True)),
                ('lifecycle_state', models.CharField(db_index=True, max_length=20)),
                ('group_count', models.IntegerField(default=0)),
                ('org_unit_count', models.IntegerField(default=0)),
                ('responsibility_count', models.IntegerField(default=0)),
                ('group_names', models.JSONField(blank=True, default=list)),
                ('org_unit_names', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'organization_user_overviews',
                'verbose_name': 'User Overview',
                'verbose_name_plural': 'User Overviews',
            },
        ),
    ]

