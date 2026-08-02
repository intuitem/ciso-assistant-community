from django.db import migrations

# TTP catalogues moved to sec_intel and the threat-modeling objects to
# threat_modeling. Django leaves the old ContentType rows behind, and
# core.permissions looks permissions up by codename alone, so the duplicates
# would raise MultipleObjectsReturned on every object permission check.
MOVED = [
    ("core", "ttpcatalog"),
    ("core", "tactic"),
    ("core", "technique"),
    ("core", "threatmodel"),
    ("core", "threatmodelnode"),
    ("core", "threatmodeledge"),
]


def purge(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    for app_label, model in MOVED:
        stale = ContentType.objects.filter(app_label=app_label, model=model)
        Permission.objects.filter(content_type__in=stale).delete()
        stale.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0186_remove_tactic_catalog_remove_tactic_folder_and_more"),
        ("sec_intel", "0002_tactic_ttpcatalog_technique_tactic_catalog"),
        ("threat_modeling", "0001_initial"),
    ]

    operations = [migrations.RunPython(purge, migrations.RunPython.noop)]
