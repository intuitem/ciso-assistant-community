"""
Re-run recompute_assessment() on every RequirementAssessment so audits
created before the compute_result aggregation fix are aligned with the new
semantic logic. Idempotent; uses the live model because recompute_assessment
references runtime enums/helpers not available on historical models.
"""

from django.db import migrations

BATCH_SIZE = 500


def backfill_results(apps, schema_editor):
    from core.models import RequirementAssessment

    fields = ["score", "result", "is_scored"]
    queryset = RequirementAssessment.objects.select_related(
        "compliance_assessment", "requirement"
    )

    batch = []
    for ra in queryset.iterator(chunk_size=BATCH_SIZE):
        ra.recompute_assessment()
        batch.append(ra)
        if len(batch) >= BATCH_SIZE:
            RequirementAssessment.objects.bulk_update(batch, fields)
            batch = []
    if batch:
        RequirementAssessment.objects.bulk_update(batch, fields)


def reverse_backfill(apps, schema_editor):
    # No reverse: there's no record of the stale pre-fix values to restore.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0169_tasktemplate_filtering_labels"),
    ]

    operations = [
        migrations.RunPython(backfill_results, reverse_backfill),
    ]
