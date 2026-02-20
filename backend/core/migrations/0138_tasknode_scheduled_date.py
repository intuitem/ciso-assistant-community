from datetime import timedelta
from django.db import migrations, models
from core.utils import _generate_occurrences


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
        ("core", "0137_add_threats_to_finding"),
    ]

    operations = [
        migrations.AddField(
            model_name="tasknode",
            name="scheduled_date",
            field=models.DateField(
                blank=True,
                help_text="Original date from the recurrence rule. Not user-editable.",
                null=True,
                verbose_name="Scheduled date",
            ),
        ),
        migrations.RunPython(populate_scheduled_date, migrations.RunPython.noop),
    ]
