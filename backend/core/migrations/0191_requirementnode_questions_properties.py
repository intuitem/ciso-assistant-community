from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0190_framework_result_aggregation"),
    ]

    operations = [
        migrations.AddField(
            model_name="requirementnode",
            name="questions_properties",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Presentation metadata for the requirement questions.",
                verbose_name="Questions properties",
            ),
        ),
    ]
