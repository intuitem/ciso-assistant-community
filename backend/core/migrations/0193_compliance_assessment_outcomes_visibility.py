"""Outcomes get their own field visibility; they used to follow the result's.
Existing audits start from their result's visibility, so nothing changes until
someone edits it."""

from django.db import migrations


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
        ("core", "0192_framework_scoring_defaults"),
    ]

    operations = [
        migrations.RunPython(
            copy_result_visibility_to_outcomes, migrations.RunPython.noop
        ),
    ]
