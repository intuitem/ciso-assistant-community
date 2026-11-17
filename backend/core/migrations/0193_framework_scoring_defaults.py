from django.db import migrations, models


def count_switched_off_scores(apps, schema_editor):
    """The per-requirement scoring switch is gone: requirements it switched off
    count again where their audit scores, as when scoring is turned on.
    Questionnaire requirements keep is_scored (it means "questionnaire complete")."""
    ComplianceAssessment = apps.get_model("core", "ComplianceAssessment")
    RequirementAssessment = apps.get_model("core", "RequirementAssessment")
    # scoring_enabled: score visible to auditors (a missing key is hidden by
    # default). A malformed map only skips its audit, never the deployment.
    scoring = [
        ca.pk
        for ca in ComplianceAssessment.objects.only("pk", "field_visibility")
        if isinstance(ca.field_visibility, dict)
        and isinstance(pair := ca.field_visibility.get("score"), dict)
        and pair.get("auditor", "edit") != "hidden"
    ]
    for start in range(0, len(scoring), 500):
        RequirementAssessment.objects.filter(
            compliance_assessment_id__in=scoring[start : start + 500],
            is_scored=False,
            score__isnull=False,
            requirement__assessable=True,
            requirement__questions__isnull=True,
        ).exclude(result="not_applicable").update(is_scored=True)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0192_backfill_evidencerevision_attachment_hash"),
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
        # Last: no schema change follows the data update (PostgreSQL).
        migrations.RunPython(count_switched_off_scores, migrations.RunPython.noop),
    ]
