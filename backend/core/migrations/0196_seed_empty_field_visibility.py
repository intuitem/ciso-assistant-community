from django.db import migrations

from core.utils import build_initial_field_visibility


def seed_empty_field_visibility(apps, schema_editor):
    """Give every audit stored without a `field_visibility` map the one a new audit gets.

    For such an audit the backend hid fields by the code defaults while pages and progress
    read the framework's template; storing the template makes them agree. A map that is
    present, even malformed, is left alone."""
    ComplianceAssessment = apps.get_model("core", "ComplianceAssessment")
    Framework = apps.get_model("core", "Framework")
    empty = [
        audit
        for audit in ComplianceAssessment.objects.only(
            "pk", "field_visibility", "framework_id"
        )
        if not audit.field_visibility
    ]
    frameworks = Framework.objects.in_bulk({audit.framework_id for audit in empty})
    for audit in empty:
        audit.field_visibility = build_initial_field_visibility(
            frameworks.get(audit.framework_id)
        )
    ComplianceAssessment.objects.bulk_update(
        empty, ["field_visibility"], batch_size=500
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0195_compliance_assessment_computed_values"),
    ]

    operations = [
        migrations.RunPython(seed_empty_field_visibility, migrations.RunPython.noop),
    ]
