from django.db import migrations, models


def booleans_to_field_visibility(apps, schema_editor):
    """Translate legacy boolean toggles into field_visibility entries.

    Existing entries on field_visibility are preserved; only missing keys are filled.
    """
    CA = apps.get_model("core", "ComplianceAssessment")
    batch = []
    fields = ["field_visibility"]
    for ca in CA.objects.all().iterator():
        fv = dict(ca.field_visibility or {})
        before = dict(fv)

        if not ca.scoring_enabled:
            fv.setdefault("score", "hidden")
            fv.setdefault("is_scored", "hidden")
        if not ca.show_documentation_score:
            fv.setdefault("documentation_score", "hidden")
        # status and extended_result historically rendered for auditors only;
        # preserve that behaviour by defaulting to "auditor" when enabled, "hidden" when not.
        fv.setdefault(
            "extended_result", "auditor" if ca.extended_result_enabled else "hidden"
        )
        fv.setdefault("status", "auditor" if ca.progress_status_enabled else "hidden")

        if fv != before:
            ca.field_visibility = fv
            batch.append(ca)
        if len(batch) >= 1000:
            CA.objects.bulk_update(batch, fields)
            batch = []
    if batch:
        CA.objects.bulk_update(batch, fields)


def reverse_noop(apps, schema_editor):
    # Reverse migration is intentionally a no-op: the boolean columns are
    # re-added by the schema reverse, but their values cannot be recovered
    # losslessly from the merged field_visibility map.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0167_backfill_respondent_alignment"),
    ]

    operations = [
        # Update help_text on field_visibility to reflect the new single-tier model.
        migrations.AlterField(
            model_name="complianceassessment",
            name="field_visibility",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Per-field visibility map: {field_name: 'everyone' | 'auditor' | 'hidden'}. "
                    "Missing keys resolve to 'everyone'."
                ),
                verbose_name="Field visibility",
            ),
        ),
        migrations.RunPython(booleans_to_field_visibility, reverse_noop),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="scoring_enabled",
        ),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="show_documentation_score",
        ),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="extended_result_enabled",
        ),
        migrations.RemoveField(
            model_name="complianceassessment",
            name="progress_status_enabled",
        ),
    ]
