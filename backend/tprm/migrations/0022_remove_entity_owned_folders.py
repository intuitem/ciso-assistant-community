# The main entity is now marked by is_main (stamped in 0021, which reads the
# legacy owned_folders convention) — the field has no remaining consumer.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tprm", "0021_entity_scope_and_campaign_entities_backfill"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="entity",
            name="owned_folders",
        ),
    ]
