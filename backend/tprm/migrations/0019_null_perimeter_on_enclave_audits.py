from django.db import migrations


def null_perimeter_on_enclave_audits(apps, schema_editor):
    """
    Audits living in an enclave folder (created by or linked to an entity
    assessment) must not reference a domain-level perimeter. The enclave
    folder, not the perimeter, governs their placement.
    """
    ComplianceAssessment = apps.get_model("core", "ComplianceAssessment")

    ComplianceAssessment.objects.filter(
        perimeter__isnull=False,
        folder__content_type="EN",
    ).update(perimeter=None)


class Migration(migrations.Migration):
    dependencies = [
        ("tprm", "0018_assign_third_parties_to_audits"),
        ("core", "0181_customizable_asset_classes"),
    ]

    operations = [
        migrations.RunPython(
            null_perimeter_on_enclave_audits,
            migrations.RunPython.noop,
        ),
    ]
