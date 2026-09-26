from django.db import migrations


def _levels(definition):
    if isinstance(definition, dict):
        return definition.get("scale") or []
    return definition or []


def copy_framework_labels(apps, schema_editor):
    """Audits no longer fall back to their framework's labels at display time.

    Copy them onto the audits that relied on that fallback (no labels of their
    own, no preset, still on the framework's range) so nothing changes for them.
    """
    ComplianceAssessment = apps.get_model("core", "ComplianceAssessment")
    to_update = []
    for audit in ComplianceAssessment.objects.filter(
        score_scale_preset__isnull=True
    ).select_related("framework"):
        framework = audit.framework
        if _levels(audit.scores_definition) or not _levels(framework.scores_definition):
            continue
        if (audit.min_score, audit.max_score) != (
            framework.min_score,
            framework.max_score,
        ):
            continue
        audit.scores_definition = framework.scores_definition
        to_update.append(audit)
    ComplianceAssessment.objects.bulk_update(
        to_update, ["scores_definition"], batch_size=500
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0190_compliance_assessment_score_scale_preset"),
    ]

    operations = [
        migrations.RunPython(copy_framework_labels, migrations.RunPython.noop),
    ]
