from django.db import migrations, models


EVERYONE_EDIT = {"auditor": "edit", "respondent": "edit"}
AUDITOR_ONLY = {"auditor": "edit", "respondent": "hidden"}
HIDDEN = {"auditor": "hidden", "respondent": "hidden"}


def booleans_to_field_visibility(apps, schema_editor):
    """Translate legacy boolean toggles into per-role field_visibility entries.

    Storage shape: {field_name: {role: 'edit' | 'read' | 'hidden'}}.
    Existing entries on field_visibility are preserved; only missing keys are filled.
    """
    CA = apps.get_model("core", "ComplianceAssessment")
    RA = apps.get_model("core", "RequirementAssessment")
    batch = []
    fields = ["field_visibility"]
    for ca in CA.objects.all().iterator():
        fv = dict(ca.field_visibility or {})
        before = dict(fv)

        if not ca.scoring_enabled:
            fv.setdefault("score", dict(HIDDEN))
            fv.setdefault("is_scored", dict(HIDDEN))
        if not ca.show_documentation_score:
            fv.setdefault("documentation_score", dict(HIDDEN))

        # status and extended_result historically rendered for auditors only;
        # preserve that by defaulting to AUDITOR_ONLY when enabled, HIDDEN when not.
        fv.setdefault(
            "extended_result",
            dict(AUDITOR_ONLY) if ca.extended_result_enabled else dict(HIDDEN),
        )
        fv.setdefault(
            "status",
            dict(AUDITOR_ONLY) if ca.progress_status_enabled else dict(HIDDEN),
        )

        # respondent_alignment: keep visible only on CAs that already use it.
        # New default is AUDITOR_ONLY (opt-in); CAs with any non-null alignment
        # value on a child RequirementAssessment are considered active users.
        alignment_in_use = RA.objects.filter(
            compliance_assessment_id=ca.id,
            respondent_alignment__isnull=False,
        ).exists()
        fv.setdefault(
            "respondent_alignment",
            dict(EVERYONE_EDIT) if alignment_in_use else dict(AUDITOR_ONLY),
        )

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
    # losslessly from the per-role field_visibility map.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0167_backfill_respondent_alignment"),
    ]

    operations = [
        # Update help_text on field_visibility to reflect the new per-role model.
        migrations.AlterField(
            model_name="complianceassessment",
            name="field_visibility",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Per-field visibility map: "
                    "{field_name: {role: 'edit' | 'read' | 'hidden'}}. "
                    "Missing keys resolve to 'edit' for every role."
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
