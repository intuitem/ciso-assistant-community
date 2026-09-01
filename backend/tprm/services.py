"""Shared entity-assessment operations, called by the API serializer and the
workflow engine so a questionnaire is built one way only."""

from django.db import transaction

from core.models import ComplianceAssessment, RequirementAssignment
from iam.models import Folder


def enclave_folder(entity_assessment):
    return Folder.objects.create(
        content_type=Folder.ContentType.ENCLAVE,
        name=f"{entity_assessment.entity.name}/{entity_assessment.name}",
        parent_folder=entity_assessment.folder,
    )


def sync_requirement_assignment(audit, representatives):
    """Create or update the RequirementAssignment so its actors match the
    representatives."""
    actors = [rep.actor for rep in representatives if hasattr(rep, "actor")]
    assignment = audit.requirement_assignments.first()
    if assignment is None:
        if not actors:
            return
        requirement_assessments = audit.requirement_assessments.all()
        if not requirement_assessments.exists():
            return
        assignment = RequirementAssignment.objects.create(
            compliance_assessment=audit,
            folder=audit.folder,
        )
        assignment.actor.set(actors)
        assignment.requirement_assessments.set(requirement_assessments)
    else:
        assignment.actor.set(actors)


def finalize_linked_audit(entity_assessment, audit):
    audit.reviewers.set(entity_assessment.reviewers.all())
    representatives = entity_assessment.representatives.all()
    audit.authors.set([rep.actor for rep in representatives if hasattr(rep, "actor")])
    sync_requirement_assignment(audit, representatives)
    entity_assessment.compliance_assessment = audit
    entity_assessment.save()


def create_enclave_audit(entity_assessment, framework, implementation_groups=None):
    """The questionnaire behind an entity assessment: an audit in its own
    enclave folder, with its requirements, reviewers and assignments. Callers
    lock the entity assessment and check it has no audit yet."""
    from core.utils import build_initial_field_visibility

    with transaction.atomic():
        # Enclave audits carry no perimeter: the enclave folder, not the entity
        # assessment's perimeter, governs their placement.
        audit = ComplianceAssessment.objects.create(
            name=entity_assessment.name,
            framework=framework,
            selected_implementation_groups=implementation_groups,
            field_visibility=build_initial_field_visibility(framework),
        )
        audit.folder = enclave_folder(entity_assessment)
        audit.save()
        audit.create_requirement_assessments()
        finalize_linked_audit(entity_assessment, audit)
    return audit
