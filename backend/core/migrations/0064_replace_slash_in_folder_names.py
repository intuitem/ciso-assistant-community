from django.db import migrations


def replace_slash_in_perimeter_names(apps, schema_editor):
    Perimeter = apps.get_model("core", "Perimeter")
    for perimeter in Perimeter.objects.all():
        if "/" in perimeter.name:
            perimeter.name = perimeter.name.replace("/", "_")
            perimeter.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0064_incident_timelineentry"),
    ]

    operations = [
        migrations.RunPython(replace_slash_in_perimeter_names),
    ]
