"""Shared entity-assessment operations, called by the API serializer and the
workflow engine so a questionnaire is built one way only."""

from django.db import transaction

from core.models import ComplianceAssessment, RequirementAssignment
from iam.models import Folder, User


def enclave_folder(entity_assessment):
    """The vendor's workspace: one enclave per entity per domain, reused by every round.

    Matched on where the entity's existing audits live, not on the folder name, so
    workspaces created under the old per-assessment naming are adopted as-is.
    """
    from tprm.models import EntityAssessment

    existing = set(
        EntityAssessment.objects.filter(
            entity=entity_assessment.entity,
            folder=entity_assessment.folder,
            compliance_assessment__folder__content_type=Folder.ContentType.ENCLAVE,
        )
        .exclude(pk=entity_assessment.pk)
        .values_list("compliance_assessment__folder_id", flat=True)
    )
    # Only when unambiguous: several workspaces means the entity predates this model,
    # so leave it to `consolidate_entity_workspaces` rather than widening access.
    if len(existing) == 1:
        return Folder.objects.get(pk=existing.pop())

    # Sibling folder names have to be unique; fall back to the old form on a clash.
    name = entity_assessment.entity.name
    if Folder.objects.filter(
        parent_folder=entity_assessment.folder, name__iexact=name
    ).exists():
        name = f"{name}/{entity_assessment.name}"
    return Folder.objects.create(
        content_type=Folder.ContentType.ENCLAVE,
        name=name,
        parent_folder=entity_assessment.folder,
    )


def sync_requirement_assignment(audit, representatives):
    """Create or update the RequirementAssignment so its actors match the
    representatives."""
    from core.utils import assign_audit_to

    assign_audit_to(
        audit, [rep.actor for rep in representatives if hasattr(rep, "actor")]
    )


def default_representatives_from_entity(entity_assessment):
    """Fall back to the entity's own representatives when none were picked, so the
    assessment reaches somebody. Only on audit create/link."""
    if entity_assessment.representatives.exists():
        return
    users = User.objects.filter(
        representative__entity=entity_assessment.entity, is_third_party=True
    ).distinct()
    if users:
        entity_assessment.representatives.set(users)


def sync_audit_schedule(entity_assessment, audit):
    """Keep the questionnaire's clock on the assessment's, in both directions of edit."""
    if (audit.due_date, audit.eta) == (
        entity_assessment.due_date,
        entity_assessment.eta,
    ):
        return
    audit.due_date = entity_assessment.due_date
    audit.eta = entity_assessment.eta
    audit.save(update_fields=["due_date", "eta"])


def finalize_linked_audit(entity_assessment, audit):
    sync_audit_schedule(entity_assessment, audit)
    audit.reviewers.set(entity_assessment.reviewers.all())
    default_representatives_from_entity(entity_assessment)
    representatives = entity_assessment.representatives.all()
    audit.authors.set([rep.actor for rep in representatives if hasattr(rep, "actor")])
    sync_requirement_assignment(audit, representatives)
    entity_assessment.compliance_assessment = audit
    entity_assessment.save()


def create_enclave_audit(
    entity_assessment,
    framework,
    implementation_groups=None,
    field_visibility=None,
    baseline=None,
    enclave=None,
):
    """The questionnaire behind an entity assessment: an audit in its own
    enclave folder, with its requirements, reviewers and assignments. Callers
    lock the entity assessment and check it has no audit yet.

    `field_visibility` is merged onto the third-party profile, not a replacement:
    an editor only sends the pills that were touched. `baseline` carries a previous
    audit's answers, results and evidences into this one; `enclave` reuses an existing
    workspace instead of minting one, so a revision keeps the vendor's folder.
    """
    from core.utils import EVERYONE_EDIT, build_third_party_field_visibility

    # Addressed to a third party: the internal-audit defaults would expose the auditor.
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
            # Revisions share the workspace, and name+version identify an audit within
            # a folder: without this every revision would be v1.0 and collide.
            version=entity_assessment.version,
            framework=framework,
            selected_implementation_groups=implementation_groups,
            field_visibility=visibility,
            # The questionnaire is what the third party opens and what the reminders
            # and the overdue lock read: without the dates the deadline is invisible.
            due_date=entity_assessment.due_date,
            eta=entity_assessment.eta,
        )
        audit.folder = enclave or enclave_folder(entity_assessment)
        audit.save()
        audit.create_requirement_assessments(baseline)
        finalize_linked_audit(entity_assessment, audit)
    return audit


def workspaces_by_entity():
    """(entity, domain) -> {workspace folder: [audit names]}."""
    from collections import defaultdict

    from tprm.models import EntityAssessment

    grouped = defaultdict(lambda: defaultdict(list))
    for ea in EntityAssessment.objects.filter(
        compliance_assessment__isnull=False,
        compliance_assessment__folder__content_type=Folder.ContentType.ENCLAVE,
    ).select_related("entity", "folder", "compliance_assessment__folder"):
        grouped[(ea.entity, ea.folder)][ea.compliance_assessment.folder].append(ea.name)
    return grouped


def _folder_models():
    """Models that can hold rows in a workspace, discovered so a later one is not missed.

    A model whose table is absent is skipped here rather than by swallowing query errors.
    """
    from django.apps import apps
    from django.db import connection

    from iam.models import RoleAssignment, UserGroup

    tables = set(connection.introspection.table_names())
    for model in apps.get_models():
        if model in (Folder, UserGroup, RoleAssignment):
            continue
        if model._meta.db_table not in tables:
            continue
        if any(
            getattr(field, "attname", None) == "folder_id"
            for field in model._meta.get_fields()
        ):
            yield model


def workspace_contents(folders):
    counts = {}
    for model in _folder_models():
        try:
            n = model.objects.filter(folder__in=folders).count()
        except Exception as exc:
            # This is the gate that decides a workspace is safe to delete, so a
            # silenced failure here would report it as empty.
            raise RuntimeError(
                f"could not count {model._meta.label} in the workspace: {exc}"
            ) from exc
        if n:
            counts[model] = n
    return counts


def workspace_members(folders):
    from iam.models import UserGroup

    return {
        user
        for group in UserGroup.objects.filter(folder__in=folders)
        for user in group.user_set.all()
    }


def generated_workspace_name(entity, audit_names):
    """The names this code used to mint. A workspace an admin renamed by hand is not
    ours to relabel."""
    return {f"{entity.name}/{audit}" for audit in audit_names}


def rename_workspace(entity, domain, folder, audit_names):
    """Give a single workspace the entity's name. Returns the new name, or None when
    it should be left alone."""
    if folder.name == entity.name:
        return None
    if folder.name not in generated_workspace_name(entity, audit_names):
        return None
    if (
        Folder.objects.filter(parent_folder=domain, name__iexact=entity.name)
        .exclude(pk=folder.pk)
        .exists()
    ):
        return None
    folder.name = entity.name
    folder.save()
    return entity.name


def consolidate_workspaces(entity, domain, sources):
    """Move every workspace of an entity into one, merging their respondent groups."""
    from auditlog.registry import auditlog

    from core.utils import RoleCodename, UserGroupCodename, bulk_update_with_log
    from iam.models import Role, RoleAssignment, UserGroup

    name = entity.name
    if Folder.objects.filter(parent_folder=domain, name__iexact=name).exists():
        name = f"{name} (workspace)"
    target = Folder.objects.create(
        content_type=Folder.ContentType.ENCLAVE, name=name, parent_folder=domain
    )

    for model in _folder_models():
        try:
            rows = list(model.objects.filter(folder__in=sources))
        except Exception as exc:
            # Skipping a model would leave rows pointing at a folder deleted below,
            # unseen by the guard: abort this entity instead.
            raise RuntimeError(
                f"could not read {model._meta.label} while consolidating "
                f"{entity.name}: {exc}"
            ) from exc
        if not rows:
            continue
        if auditlog.contains(model):
            for row in rows:
                row.folder = target
            bulk_update_with_log(model, rows, ["folder"])
        else:
            model.objects.filter(pk__in=[row.pk for row in rows]).update(folder=target)

    # One save() per child, not a queryset update: `Folder.descendants` is maintained
    # by save() alone, and a column write would break recursive role resolution.
    for child in Folder.objects.filter(parent_folder__in=sources):
        child.parent_folder = target
        child.save()

    respondents, _ = UserGroup.objects.get_or_create(
        name=UserGroupCodename.THIRD_PARTY_RESPONDENT, folder=target, builtin=True
    )
    assignment, _ = RoleAssignment.objects.get_or_create(
        user_group=respondents,
        role=Role.objects.get(name=RoleCodename.THIRD_PARTY_RESPONDENT),
        builtin=True,
        folder=target,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(target)
    for group in UserGroup.objects.filter(folder__in=sources):
        for user in group.user_set.all():
            user.user_groups.add(respondents)
    RoleAssignment.objects.filter(folder__in=sources).delete()
    UserGroup.objects.filter(folder__in=sources).delete()

    leftover = workspace_contents(sources)
    if leftover:
        raise RuntimeError(f"refusing to delete non-empty workspaces: {leftover}")
    for folder in sources:
        folder.delete()

    if (
        target.name != entity.name
        and not Folder.objects.filter(parent_folder=domain, name__iexact=entity.name)
        .exclude(pk=target.pk)
        .exists()
    ):
        target.name = entity.name
        target.save()
    return target


def normalize_entity_workspaces(apply=False, entity_name=None):
    """One workspace per entity per domain. Each entity is independent: one that fails is skipped."""
    from django.db import transaction

    plan = []
    groups = workspaces_by_entity()
    for (entity, domain), workspaces in groups.items():
        if entity_name and entity.name != entity_name:
            continue
        sources = list(workspaces)
        row = {
            "entity": entity,
            "domain": domain,
            "workspaces": workspaces,
            "action": "consolidate" if len(sources) > 1 else "rename",
            "members": sorted(u.email for u in workspace_members(sources)),
            "contents": workspace_contents(sources),
            "error": None,
            "result": None,
        }
        if len(sources) == 1:
            folder = sources[0]
            audits = workspaces[folder]
            if (
                folder.name == entity.name
                or folder.name not in generated_workspace_name(entity, audits)
            ):
                continue
            row["from"] = folder.name
            row["to"] = entity.name
        if not apply:
            plan.append(row)
            continue
        try:
            with transaction.atomic():
                if len(sources) > 1:
                    row["result"] = consolidate_workspaces(entity, domain, sources)
                else:
                    row["result"] = rename_workspace(
                        entity, domain, sources[0], workspaces[sources[0]]
                    )
        except Exception as exc:
            row["error"] = str(exc)
        plan.append(row)
    return plan
