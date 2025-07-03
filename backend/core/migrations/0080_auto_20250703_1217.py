from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0079_finding_evidences_findingsassessment_evidences"),
    ]

    def update_is_published(apps, schema_editor):
        Qualification = apps.get_model("core", "Qualification")
        Qualification.objects.update(is_published=True)

    def reverse_update_is_published(apps, schema_editor):
        Qualification = apps.get_model("core", "Qualification")
        Qualification.objects.update(is_published=False)

    operations = [
        migrations.RunPython(update_is_published, reverse_update_is_published),
    ]
