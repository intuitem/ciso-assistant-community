"""Scoring defaults declared by frameworks (and the audit's score default), and
an outcomes field visibility of their own.

Outcomes used to follow the result's visibility: existing audits start from
their result's visibility, so nothing changes until someone edits it. The
data step runs after the schema changes."""

from django.db import migrations, models


def copy_result_visibility_to_outcomes(apps, schema_editor):
    ComplianceAssessment = apps.get_model("core", "ComplianceAssessment")
    changed = []
    for ca in ComplianceAssessment.objects.only("id", "field_visibility").iterator(
        chunk_size=500
    ):
        visibility = ca.field_visibility
        if not isinstance(visibility, dict) or "outcomes" in visibility:
            continue
        result = visibility.get("result")
        # No result entry: visible to everyone, as outcomes are by default.
        if not isinstance(result, dict):
            continue
        visibility["outcomes"] = dict(result)
        changed.append(ca)
    ComplianceAssessment.objects.bulk_update(
        changed, ["field_visibility"], batch_size=500
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0191_roto_target_objective_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="framework",
            name="anchor_na_to_target",
            field=models.BooleanField(
                default=False,
                help_text="New audits count not applicable requirements as the target score.",
                verbose_name="Anchor N/A to target score",
            ),
        ),
        migrations.AddField(
            model_name="framework",
            name="score_calculation_method",
            field=models.CharField(
                default="average",
                help_text="Calculation method proposed for new audits.",
                max_length=30,
                verbose_name="Score calculation method",
            ),
        ),
        migrations.AddField(
            model_name="framework",
            name="score_scale_locked",
            field=models.BooleanField(
                default=False,
                help_text="The standard defines the score scale: audits cannot change it.",
                verbose_name="Score scale locked",
            ),
        ),
        migrations.AddField(
            model_name="framework",
            name="target_score",
            field=models.FloatField(
                blank=True,
                help_text="Target score proposed for new audits, on the framework scale. Implementation groups can override it.",
                null=True,
                verbose_name="Target score",
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
        migrations.AddField(
            model_name="complianceassessment",
            name="score_defaults_to_minimum",
            field=models.BooleanField(
                default=False, verbose_name="Scores default to the minimum"
            ),
        ),
        migrations.RunPython(
            copy_result_visibility_to_outcomes, migrations.RunPython.noop
        ),
    ]
