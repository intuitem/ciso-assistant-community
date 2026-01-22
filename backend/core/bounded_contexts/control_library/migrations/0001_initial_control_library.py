# Generated migration for Control Library bounded context

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
        # Control aggregate
        migrations.CreateModel(
            name='Control',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('objective', models.TextField(blank=True, null=True)),
                ('ref_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('control_type', models.CharField(blank=True, choices=[('policy', 'Policy'), ('process', 'Process'), ('technical', 'Technical'), ('physical', 'Physical'), ('procedure', 'Procedure')], db_index=True, max_length=20, null=True)),
                ('domain', models.CharField(blank=True, max_length=255, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('approved', 'Approved'), ('deprecated', 'Deprecated')], db_index=True, default='draft', max_length=20)),
                ('legalRequirementIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of legal requirement IDs', size=None)),
                ('relatedControlIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of related control IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'control_library_controls',
                'verbose_name': 'Control',
                'verbose_name_plural': 'Controls',
            },
        ),
        migrations.AddIndex(
            model_name='control',
            index=models.Index(fields=['lifecycle_state', 'control_type'], name='ctrl_lib_ctrl_life_type_idx'),
        ),
        
        # Policy aggregate
        migrations.CreateModel(
            name='Policy',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('version', models.CharField(db_index=True, default='1.0', max_length=50)),
                ('description', models.TextField(blank=True, null=True)),
                ('lifecycle_state', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published'), ('retired', 'Retired')], db_index=True, default='draft', max_length=20)),
                ('ownerUserIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of owner user IDs', size=None)),
                ('relatedControlIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of related control IDs', size=None)),
                ('applicableOrgUnitIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of applicable organizational unit IDs', size=None)),
                ('publication_date', models.DateField(blank=True, db_index=True, null=True)),
                ('review_cadence_days', models.IntegerField(blank=True, help_text='Days between reviews', null=True)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'control_library_policies',
                'verbose_name': 'Policy',
                'verbose_name_plural': 'Policies',
            },
        ),
        migrations.AddIndex(
            model_name='policy',
            index=models.Index(fields=['title', 'version'], name='ctrl_lib_policy_title_ver_idx'),
        ),
        
        # EvidenceItem aggregate
        migrations.CreateModel(
            name='EvidenceItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('source_type', models.CharField(choices=[('upload', 'Upload'), ('link', 'Link'), ('system_record', 'System Record')], db_index=True, default='upload', max_length=20)),
                ('lifecycle_state', models.CharField(choices=[('collected', 'Collected'), ('verified', 'Verified'), ('expired', 'Expired')], db_index=True, default='collected', max_length=20)),
                ('uri', models.URLField(blank=True, max_length=2048, null=True)),
                ('collected_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'control_library_evidence_items',
                'verbose_name': 'Evidence Item',
                'verbose_name_plural': 'Evidence Items',
            },
        ),
        migrations.AddIndex(
            model_name='evidenceitem',
            index=models.Index(fields=['lifecycle_state', 'source_type'], name='ctrl_lib_evid_life_src_idx'),
        ),
        
        # ControlImplementation association
        migrations.CreateModel(
            name='ControlImplementation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('controlId', models.UUIDField(db_index=True)),
                ('target_type', models.CharField(choices=[('asset', 'Asset'), ('service', 'Service'), ('process', 'Process'), ('third_party', 'Third Party'), ('org_unit', 'Organizational Unit'), ('data_flow', 'Data Flow'), ('data_asset', 'Data Asset')], db_index=True, max_length=50)),
                ('target_id', models.UUIDField(db_index=True)),
                ('lifecycle_state', models.CharField(choices=[('planned', 'Planned'), ('implemented', 'Implemented'), ('operating', 'Operating'), ('ineffective', 'Ineffective'), ('retired', 'Retired')], db_index=True, default='planned', max_length=20)),
                ('ownerUserIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of owner user IDs', size=None)),
                ('evidenceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of evidence IDs', size=None)),
                ('frequency', models.CharField(choices=[('ad_hoc', 'Ad Hoc'), ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annually', 'Annually')], db_index=True, default='ad_hoc', max_length=20)),
                ('last_tested_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('effectiveness_rating', models.IntegerField(blank=True, help_text='Effectiveness rating (1-5)', null=True)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'control_library_control_implementations',
                'verbose_name': 'Control Implementation',
                'verbose_name_plural': 'Control Implementations',
            },
        ),
        migrations.AddIndex(
            model_name='controlimplementation',
            index=models.Index(fields=['controlId', 'target_type', 'target_id'], name='ctrl_lib_impl_ctrl_tgt_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='controlimplementation',
            unique_together={('controlId', 'target_type', 'target_id')},
        ),
        
        # PolicyAcknowledgement association
        migrations.CreateModel(
            name='PolicyAcknowledgement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('policyId', models.UUIDField(db_index=True)),
                ('policy_version', models.CharField(db_index=True, max_length=50)),
                ('userId', models.UUIDField(db_index=True)),
                ('acknowledged_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('method', models.CharField(choices=[('clickwrap', 'Clickwrap'), ('training', 'Training'), ('doc_sign', 'Document Signing')], db_index=True, default='clickwrap', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'control_library_policy_acknowledgements',
                'verbose_name': 'Policy Acknowledgement',
                'verbose_name_plural': 'Policy Acknowledgements',
            },
        ),
        migrations.AddIndex(
            model_name='policyacknowledgement',
            index=models.Index(fields=['policyId', 'userId'], name='ctrl_lib_ack_policy_user_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='policyacknowledgement',
            unique_together={('policyId', 'policy_version', 'userId')},
        ),
        
        # Read Models
        migrations.CreateModel(
            name='ControlOverview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('control_id', models.UUIDField(db_index=True, unique=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('ref_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('control_type', models.CharField(blank=True, max_length=20, null=True)),
                ('lifecycle_state', models.CharField(db_index=True, max_length=20)),
                ('implementation_count', models.IntegerField(default=0)),
                ('implementation_status_summary', models.JSONField(blank=True, default=dict, help_text='Summary of implementation statuses by lifecycle state')),
                ('evidence_count', models.IntegerField(default=0)),
                ('related_control_count', models.IntegerField(default=0)),
                ('legal_requirement_count', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'control_library_control_overviews',
                'verbose_name': 'Control Overview',
                'verbose_name_plural': 'Control Overviews',
            },
        ),
    ]

