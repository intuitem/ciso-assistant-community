from django.db import migrations, models


def populate_scheduled_date(apps, schema_editor):
    TaskNode = apps.get_model("core", "TaskNode")
    db_alias = schema_editor.connection.alias

    # Simply copy due_date into scheduled_date for all existing rows
    TaskNode.objects.using(db_alias).filter(
        scheduled_date__isnull=True,
        due_date__isnull=False,
    ).update(scheduled_date=models.F("due_date"))


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0139_tasknode_scheduled_date"),
    ]

    operations = [
        migrations.RunPython(populate_scheduled_date, migrations.RunPython.noop),
    ]
