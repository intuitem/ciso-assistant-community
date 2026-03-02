from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0138_validationflow_accreditations_and_more"),
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
        migrations.AddConstraint(
            model_name="tasknode",
            constraint=models.UniqueConstraint(
                fields=("task_template", "due_date"),
                condition=models.Q(due_date__isnull=False),
                name="unique_tasknode_template_due_date",
            ),
        ),
    ]
