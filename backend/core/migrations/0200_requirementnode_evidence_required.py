from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0199_framework_result_aggregation"),
    ]

    operations = [
        migrations.AddField(
            model_name="requirementnode",
            name="evidence_required",
            field=models.BooleanField(
                default=False,
                help_text="When set, the requirement cannot be submitted without at least one evidence attached.",
                verbose_name="Evidence required",
            ),
        ),
    ]
