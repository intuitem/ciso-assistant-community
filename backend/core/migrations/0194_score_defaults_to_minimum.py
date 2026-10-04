from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0193_compliance_assessment_outcomes_visibility"),
    ]

    operations = [
        migrations.AddField(
            model_name="complianceassessment",
            name="score_defaults_to_minimum",
            field=models.BooleanField(
                default=False, verbose_name="Scores default to the minimum"
            ),
        ),
        migrations.AddField(
            model_name="framework",
            name="score_defaults_to_minimum",
            field=models.BooleanField(
                default=False,
                help_text="New audits give applicable requirements without a score the scale minimum.",
                verbose_name="Scores default to the minimum",
            ),
        ),
    ]
