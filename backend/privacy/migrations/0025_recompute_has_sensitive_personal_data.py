from django.db import migrations
from django.db.models import Exists, OuterRef


def recompute_sensitive_flag(apps, schema_editor):
    """The flag was never cleared when sensitive personal data was deleted,
    unmarked or moved to another processing."""
    Processing = apps.get_model("privacy", "Processing")
    PersonalData = apps.get_model("privacy", "PersonalData")

    has_sensitive = Exists(
        PersonalData.objects.filter(processing=OuterRef("pk"), is_sensitive=True)
    )
    Processing.objects.filter(has_sensitive_personal_data=True).exclude(
        has_sensitive
    ).update(has_sensitive_personal_data=False)
    Processing.objects.filter(has_sensitive, has_sensitive_personal_data=False).update(
        has_sensitive_personal_data=True
    )


class Migration(migrations.Migration):
    dependencies = [
        ("privacy", "0024_processing_role_and_controllers"),
    ]

    operations = [
        migrations.RunPython(recompute_sensitive_flag, migrations.RunPython.noop),
    ]
