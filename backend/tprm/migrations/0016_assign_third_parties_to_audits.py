from django.db import migrations


def assign_third_parties_to_existing_audits(apps, schema_editor):
    """
    For each existing EntityAssessment that has a compliance_assessment (audit),
    create a RequirementAssignment linking all requirement assessments to the
    representatives' actors.
    """
    EntityAssessment = apps.get_model("tprm", "EntityAssessment")
    RequirementAssignment = apps.get_model("core", "RequirementAssignment")

    for ea in EntityAssessment.objects.filter(
        compliance_assessment__isnull=False
    ).select_related("compliance_assessment", "compliance_assessment__folder"):
        audit = ea.compliance_assessment
        representatives = ea.representatives.all()
        actors = []
        for rep in representatives:
            if hasattr(rep, "actor"):
                actors.append(rep.actor)
        if not actors:
            continue

        requirement_assessments = audit.requirement_assessments.all()
        if not requirement_assessments.exists():
            continue

        # Check if an assignment already exists for this audit
        if RequirementAssignment.objects.filter(compliance_assessment=audit).exists():
            continue

        assignment = RequirementAssignment.objects.create(
            compliance_assessment=audit,
            folder=audit.folder,
            status="in_progress",
        )
        assignment.actor.set(actors)
        assignment.requirement_assessments.set(requirement_assessments)


class Migration(migrations.Migration):
    dependencies = [
        ("tprm", "0015_contract_dora_exclude_and_more"),
        ("core", "0150_add_editable_mixin_to_riskmatrix"),
    ]

    operations = [
        migrations.RunPython(
            assign_third_parties_to_existing_audits,
            migrations.RunPython.noop,
        ),
    ]
