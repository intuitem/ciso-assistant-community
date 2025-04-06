from django.db import migrations


def replace_slash_in_folder_names(apps, schema_editor):
    Folder = apps.get_model("iam", "Folder")
    for folder in Folder.objects.all():
        if "/" in folder.name:
            folder.name = folder.name.replace("/", "_")
            folder.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0010_user_preferences"),
    ]

    operations = [
        migrations.RunPython(replace_slash_in_folder_names),
    ]
