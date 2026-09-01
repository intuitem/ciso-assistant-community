"""Shared entity-assessment operations, called by the API serializer and the
workflow engine so a questionnaire is built one way only."""

from django.db import transaction

from core.models import ComplianceAssessment, RequirementAssignment
from iam.models import Folder, User


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


def default_representatives_from_entity(entity_assessment):
    """Fall back to the entity's own representatives when none were picked.

    The picker already offers exactly these users; leaving it empty produced an
    assessment nobody could answer — no audit authors, no requirement assignment,
    and nobody in the enclave's respondent group. Runs only where an audit is
    created or linked, so clearing the field on an assessment that already has one
    stays a deliberate clear.
    """
    if entity_assessment.representatives.exists():
        return
    users = User.objects.filter(
        representative__entity=entity_assessment.entity, is_third_party=True
    ).distinct()
    if users:
        entity_assessment.representatives.set(users)


def finalize_linked_audit(entity_assessment, audit):
    audit.reviewers.set(entity_assessment.reviewers.all())
    default_representatives_from_entity(entity_assessment)
    representatives = entity_assessment.representatives.all()
    audit.authors.set([rep.actor for rep in representatives if hasattr(rep, "actor")])
    sync_requirement_assignment(audit, representatives)
    entity_assessment.compliance_assessment = audit
    entity_assessment.save()


def create_enclave_audit(
    entity_assessment, framework, implementation_groups=None, field_visibility=None
):
    """The questionnaire behind an entity assessment: an audit in its own
    enclave folder, with its requirements, reviewers and assignments. Callers
    lock the entity assessment and check it has no audit yet.

    `field_visibility` carries the pills the caller set explicitly; they are merged
    onto the third-party profile rather than replacing it, since an editor only sends
    what was touched.
    """
    from core.utils import EVERYONE_EDIT, build_third_party_field_visibility

    # This questionnaire is addressed to a third party, so it starts from that
    # profile: the internal-audit defaults would expose the auditor's side.
    visibility = build_third_party_field_visibility(framework)
    for key, pair in (field_visibility or {}).items():
        if not isinstance(pair, dict):
            continue
        visibility.setdefault(key, dict(EVERYONE_EDIT))
        visibility[key].update(pair)

    with transaction.atomic():
        # Enclave audits carry no perimeter: the enclave folder, not the entity
        # assessment's perimeter, governs their placement.
        audit = ComplianceAssessment.objects.create(
            name=entity_assessment.name,
            framework=framework,
            selected_implementation_groups=implementation_groups,
            field_visibility=visibility,
        )
        audit.folder = enclave_folder(entity_assessment)
        audit.save()
        audit.create_requirement_assessments()
        finalize_linked_audit(entity_assessment, audit)
    return audit
