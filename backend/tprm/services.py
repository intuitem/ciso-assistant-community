"""Fan-out helpers for entity-based campaigns."""

from django.db import transaction

from core.models import Campaign, ComplianceAssessment
from core.utils import build_initial_field_visibility
from iam.models import Folder
from tprm.models import EntityAssessment


def _implementation_groups_for(campaign, framework):
    if not campaign.selected_implementation_groups:
        return None
    groups = [
        group["value"]
        for group in campaign.selected_implementation_groups
        if group["framework"] == str(framework.id)
    ]
    return groups or None


def fan_out_campaign(campaign):
    """Create the campaign's assessments, one per entity × framework.

    Internal campaigns create ComplianceAssessments in each entity's own
    folder ("an entity's audits live where the entity lives"), assigned to
    the entity's default_assignee actors — auto-assignment is the point of a
    campaign: the audits must land in each assignee's "my assignments".
    External campaigns create EntityAssessments with their enclave audit.
    """
    frameworks = campaign.frameworks.all()

    if campaign.target_scope == Campaign.TargetScope.EXTERNAL:
        for entity in campaign.entities.all():
            for framework in frameworks:
                create_campaign_entity_assessment(
                    campaign=campaign,
                    entity=entity,
                    framework=framework,
                    implementation_groups=_implementation_groups_for(
                        campaign, framework
                    ),
                )
        return

    for entity in campaign.entities.all():
        default_assignee = list(entity.default_assignee.all())
        for framework in frameworks:
            compliance_assessment = ComplianceAssessment.objects.create(
                name=f"{campaign.name} - {entity.name} - {framework.name}",
                campaign=campaign,
                framework=framework,
                folder=entity.folder,
                selected_implementation_groups=_implementation_groups_for(
                    campaign, framework
                ),
                field_visibility=build_initial_field_visibility(framework),
            )
            compliance_assessment.create_requirement_assessments()
            compliance_assessment.authors.set(default_assignee)


def create_campaign_entity_assessment(
    campaign, entity, framework, implementation_groups=None
):
    """Create an EntityAssessment plus its enclave audit for an external campaign.

    Mirrors EntityAssessmentWriteSerializer._create_audit: an enclave folder
    under the assessment's folder hosts the audit, and the audit links back to
    the campaign so campaign metrics aggregate it. Respondent enrollment stays
    a per-assessment step — representatives are assigned on the entity
    assessment afterwards, exactly as in the manual flow.
    """
    with transaction.atomic():
        entity_assessment = EntityAssessment.objects.create(
            name=f"{campaign.name} - {entity.name} - {framework.name}",
            entity=entity,
            folder=campaign.folder,
            due_date=campaign.due_date,
        )
        enclave = Folder.objects.create(
            content_type=Folder.ContentType.ENCLAVE,
            name=f"{entity.name}/{entity_assessment.name}",
            parent_folder=entity_assessment.folder,
        )
        audit = ComplianceAssessment.objects.create(
            name=entity_assessment.name,
            framework=framework,
            selected_implementation_groups=implementation_groups,
            field_visibility=build_initial_field_visibility(framework),
            folder=enclave,
            campaign=campaign,
        )
        audit.create_requirement_assessments()
        entity_assessment.compliance_assessment = audit
        entity_assessment.save()
    return entity_assessment
