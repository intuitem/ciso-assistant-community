from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0155_requirementnode_display_mode_and_attachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="framework",
            name="editing_draft",
            field=models.JSONField(
                blank=True,
                default=None,
                help_text="Work-in-progress definition. Null when no active draft.",
                null=True,
                verbose_name="Editing draft",
            ),
        ),
        migrations.AddField(
            model_name="framework",
            name="editing_version",
            field=models.IntegerField(
                default=1,
                help_text="Incremented on each publish.",
                verbose_name="Editing version",
            ),
        ),
        migrations.AddField(
            model_name="framework",
            name="editing_history",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Snapshots of previous published definitions.",
                verbose_name="Editing history",
            ),
        ),
    ]
