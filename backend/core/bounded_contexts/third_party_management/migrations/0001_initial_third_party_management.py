# Generated migration for ThirdPartyManagement bounded context

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
        # ThirdParty aggregate
        migrations.CreateModel(
            name='ThirdParty',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('criticality', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], db_index=True, default='medium', max_length=20)),
                ('lifecycle_state', models.CharField(choices=[('prospect', 'Prospect'), ('active', 'Active'), ('offboarding', 'Offboarding'), ('archived', 'Archived')], db_index=True, default='prospect', max_length=20)),
                ('serviceIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of service IDs provided by this third party', size=None)),
                ('contractIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of contract IDs', size=None)),
                ('assessmentRunIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of assessment run IDs', size=None)),
                ('riskIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of risk IDs', size=None)),
                ('controlImplementationIds', ArrayField(base_field=models.UUIDField(), blank=True, default=list, help_text='Array of control implementation IDs', size=None)),
                ('tags', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'third_party_management_third_parties',
                'verbose_name': 'Third Party',
                'verbose_name_plural': 'Third Parties',
            },
        ),
        migrations.AddIndex(
            model_name='thirdparty',
            index=models.Index(fields=['lifecycle_state', 'criticality'], name='tpm_third_party_state_crit_idx'),
        ),
        
        # Read Models
        migrations.CreateModel(
            name='ThirdPartyPosture',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('third_party_id', models.UUIDField(db_index=True, unique=True)),
                ('third_party_name', models.CharField(db_index=True, max_length=255)),
                ('criticality', models.CharField(db_index=True, max_length=20)),
                ('active_contracts_count', models.IntegerField(default=0)),
                ('expired_contracts_count', models.IntegerField(default=0)),
                ('total_assessments', models.IntegerField(default=0)),
                ('latest_assessment_date', models.DateTimeField(blank=True, null=True)),
                ('open_findings_count', models.IntegerField(default=0)),
                ('open_risks_count', models.IntegerField(default=0)),
                ('critical_risks_count', models.IntegerField(default=0)),
                ('active_exceptions_count', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'third_party_management_third_party_postures',
                'verbose_name': 'Third Party Posture',
                'verbose_name_plural': 'Third Party Postures',
            },
        ),
    ]

