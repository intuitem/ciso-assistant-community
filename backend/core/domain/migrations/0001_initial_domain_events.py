# Generated migration for domain events

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),  # Adjust based on your core app migrations
    ]

    operations = [
        migrations.CreateModel(
            name='EventStore',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_id', models.UUIDField(db_index=True, unique=True)),
                ('aggregate_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('aggregate_version', models.IntegerField(default=0)),
                ('occurred_at', models.DateTimeField(db_index=True)),
                ('event_type', models.CharField(db_index=True, max_length=255)),
                ('payload', models.JSONField()),
            ],
            options={
                'db_table': 'domain_events',
                'ordering': ['occurred_at'],
            },
        ),
        migrations.AddIndex(
            model_name='eventstore',
            index=models.Index(fields=['aggregate_id', 'aggregate_version'], name='domain_even_aggreg_idx'),
        ),
        migrations.AddIndex(
            model_name='eventstore',
            index=models.Index(fields=['event_type', 'occurred_at'], name='domain_even_event_t_idx'),
        ),
    ]

