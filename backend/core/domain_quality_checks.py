from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    Finding,
    OrganisationIssue,
    OrganisationObjective,
    RiskAssessment,
    Severity,
    TaskNode,
    TaskTemplate,
)
from iam.models import RoleAssignment

GOVERNANCE = "governance"
OPERATIONS = "operations"
BLOCKS = (GOVERNANCE, OPERATIONS)

OPEN_FINDING_STATUSES = (
    Finding.Status.IDENTIFIED,
    Finding.Status.CONFIRMED,
    Finding.Status.ASSIGNED,
    Finding.Status.IN_PROGRESS,
)
LIVE_OBJECTIVE_STATUSES = (
    OrganisationObjective.Status.DRAFT,
    OrganisationObjective.Status.IN_PROGRESS,
)
PLANNED_CONTROL_STATUSES = (
    AppliedControl.Status.TO_DO,
    AppliedControl.Status.IN_PROGRESS,
    AppliedControl.Status.ON_HOLD,
)


@dataclass(frozen=True)
class Rule:
    block: str
    severity: str
    msgid: str
    msg: str
    model: type
    obj_type: str
    link: str
    filter: Callable
    columns: tuple = field(default_factory=tuple)
    name: F | None = None


def _rules(today: date) -> list[Rule]:
    return [
        Rule(
            GOVERNANCE,
            "warnings",
            "objectiveNoAppliedControlOrTask",
            _("Objective has no applied control nor task"),
            OrganisationObjective,
            "organisationobjective",
            "organisation-objectives",
            lambda qs: qs.filter(
                is_active=True,
                status__in=LIVE_OBJECTIVE_STATUSES,
                applied_controls__isnull=True,
                tasks__isnull=True,
            ),
            ("status", "health", "due_date"),
        ),
        Rule(
            GOVERNANCE,
            "warnings",
            "objectiveOverdue",
            _("Objective is past its due date and not achieved"),
            OrganisationObjective,
            "organisationobjective",
            "organisation-objectives",
            lambda qs: qs.filter(is_active=True, due_date__lt=today).exclude(
                status__in=(
                    OrganisationObjective.Status.ACHIEVED,
                    OrganisationObjective.Status.DEPRECATED,
                )
            ),
            ("status", "health", "due_date"),
        ),
        Rule(
            GOVERNANCE,
            "warnings",
            "objectiveAchievedNotOnTrack",
            _("Objective is achieved but its health is at risk or off track"),
            OrganisationObjective,
            "organisationobjective",
            "organisation-objectives",
            lambda qs: qs.filter(
                status=OrganisationObjective.Status.ACHIEVED,
                health__in=(
                    OrganisationObjective.Health.AT_RISK,
                    OrganisationObjective.Health.OFF_TRACK,
                ),
            ),
            ("status", "health", "due_date"),
        ),
        Rule(
            GOVERNANCE,
            "info",
            "objectiveNoMetric",
            _("Objective has no tracking metric"),
            OrganisationObjective,
            "organisationobjective",
            "organisation-objectives",
            lambda qs: qs.filter(
                is_active=True,
                status__in=LIVE_OBJECTIVE_STATUSES,
                metrics__isnull=True,
            ),
            ("status", "health", "due_date"),
        ),
        Rule(
            GOVERNANCE,
            "info",
            "organisationIssueNoObjective",
            _("Issue is not addressed by any objective"),
            OrganisationIssue,
            "organisationissue",
            "organisation-issues",
            lambda qs: qs.filter(
                status=OrganisationIssue.Status.ACTIVE, objectives__isnull=True
            ),
            ("status",),
        ),
        Rule(
            GOVERNANCE,
            "warnings",
            "evidenceMissing",
            _("Evidence is missing"),
            Evidence,
            "evidence",
            "evidences",
            lambda qs: qs.filter(status=Evidence.Status.MISSING),
            ("status", "expiry_date"),
        ),
        Rule(
            GOVERNANCE,
            "warnings",
            "evidenceExpired",
            _("Evidence is expired"),
            Evidence,
            "evidence",
            "evidences",
            lambda qs: qs.filter(status=Evidence.Status.EXPIRED),
            ("status", "expiry_date"),
        ),
        Rule(
            GOVERNANCE,
            "warnings",
            "evidenceExpiryDatePassed",
            _("Evidence expiry date has passed but its status is not expired"),
            Evidence,
            "evidence",
            "evidences",
            lambda qs: qs.filter(expiry_date__lt=today).exclude(
                status=Evidence.Status.EXPIRED
            ),
            ("status", "expiry_date"),
        ),
        Rule(
            GOVERNANCE,
            "warnings",
            "findingNoStatus",
            _("Finding has no status"),
            Finding,
            "finding",
            "findings",
            lambda qs: qs.filter(status=Finding.Status.UNDEFINED),
            ("status", "due_date"),
        ),
        Rule(
            GOVERNANCE,
            "warnings",
            "findingNoSeverity",
            _("Finding has no severity"),
            Finding,
            "finding",
            "findings",
            lambda qs: qs.filter(severity=Severity.UNDEFINED),
            ("status", "due_date"),
        ),
        Rule(
            GOVERNANCE,
            "warnings",
            "findingNoAppliedControl",
            _("Open finding has no applied control"),
            Finding,
            "finding",
            "findings",
            lambda qs: qs.filter(
                status__in=OPEN_FINDING_STATUSES, applied_controls__isnull=True
            ),
            ("status", "due_date"),
        ),
        Rule(
            OPERATIONS,
            "warnings",
            "appliedControlNoOwner",
            _("Applied control has no owner"),
            AppliedControl,
            "appliedcontrol",
            "applied-controls",
            lambda qs: qs.filter(owner__isnull=True).exclude(
                status=AppliedControl.Status.DEPRECATED
            ),
            ("status", "eta", "priority"),
        ),
        Rule(
            OPERATIONS,
            "warnings",
            "appliedControlNoEta",
            _("Planned applied control has no ETA"),
            AppliedControl,
            "appliedcontrol",
            "applied-controls",
            lambda qs: qs.filter(status__in=PLANNED_CONTROL_STATUSES, eta__isnull=True),
            ("status", "eta", "priority"),
        ),
        Rule(
            OPERATIONS,
            "warnings",
            "appliedControlNoStatus",
            _("Applied control has no status"),
            AppliedControl,
            "appliedcontrol",
            "applied-controls",
            lambda qs: qs.filter(status=AppliedControl.Status.UNDEFINED),
            ("status", "eta", "priority"),
        ),
        Rule(
            OPERATIONS,
            "warnings",
            "taskTemplateNoAssignee",
            _("Task has no assignee"),
            TaskTemplate,
            "tasktemplate",
            "task-templates",
            lambda qs: qs.filter(enabled=True, assigned_to__isnull=True),
        ),
        Rule(
            OPERATIONS,
            "warnings",
            "taskNodeOverdue",
            _("Task occurrence is past its due date"),
            TaskNode,
            "tasknode",
            "task-nodes",
            lambda qs: qs.filter(
                status__in=("pending", "in_progress"),
                due_date__lt=today,
                to_delete=False,
                task_template__enabled=True,
            ),
            ("status", "due_date"),
            F("task_template__name"),
        ),
    ]


def empty_block() -> dict:
    return {"errors": [], "warnings": [], "info": [], "count": 0}


def _run_rules(user, today, scopes, bucket_for):
    viewable = {}
    for rule in _rules(today):
        scope = scopes.get(rule.model)
        if scope is None:
            continue
        if rule.model not in viewable:
            viewable[rule.model] = RoleAssignment.get_viewable_object_ids(
                user, rule.model
            )
        qs = rule.filter(
            rule.model.objects.filter(
                id__in=rule.model.objects.filter(scope).values("id")
            ).filter(id__in=viewable[rule.model])
        )
        if rule.name is not None:
            qs = qs.annotate(issue_name=rule.name)
            name_field = "issue_name"
        else:
            name_field = "name"
        for row in (
            qs.order_by()
            .values("id", "folder_id", name_field, *rule.columns)
            .distinct()
        ):
            block = bucket_for(row)[rule.block]
            block[rule.severity].append(
                {
                    "msg": str(rule.msg),
                    "msgid": rule.msgid,
                    "obj_type": rule.obj_type,
                    "link": f"{rule.link}/{row['id']}",
                    "object": {
                        "id": row["id"],
                        "name": row[name_field],
                        **{c: row[c] for c in rule.columns},
                    },
                }
            )
            block["count"] += 1


def domain_quality_checks(folders, user, today: date | None = None) -> dict:
    today = today or date.today()
    folder_ids = [f.id for f in folders]
    res = {str(fid): {block: empty_block() for block in BLOCKS} for fid in folder_ids}
    scopes = {rule.model: Q(folder_id__in=folder_ids) for rule in _rules(today)}
    _run_rules(user, today, scopes, lambda row: res[str(row["folder_id"])])
    return res


def _compliance_assessment_scopes(audit) -> dict:
    return {
        AppliedControl: Q(requirement_assessments__compliance_assessment=audit),
        Evidence: Q(requirement_assessments__compliance_assessment=audit)
        | Q(applied_controls__requirement_assessments__compliance_assessment=audit),
        Finding: Q(findings_assessment__compliance_assessment=audit),
        TaskTemplate: Q(compliance_assessments=audit),
        TaskNode: Q(task_template__compliance_assessments=audit),
    }


def _risk_assessment_scopes(risk_assessment) -> dict:
    controls = Q(risk_scenarios__risk_assessment=risk_assessment) | Q(
        risk_scenarios_e__risk_assessment=risk_assessment
    )
    return {
        AppliedControl: controls,
        Evidence: Q(applied_controls__risk_scenarios__risk_assessment=risk_assessment)
        | Q(applied_controls__risk_scenarios_e__risk_assessment=risk_assessment),
        TaskTemplate: Q(risk_assessments=risk_assessment),
        TaskNode: Q(task_template__risk_assessments=risk_assessment),
    }


OBJECT_SCOPES = {
    ComplianceAssessment: _compliance_assessment_scopes,
    RiskAssessment: _risk_assessment_scopes,
}


def object_quality_checks(obj, user, today: date | None = None) -> dict:
    res = {block: empty_block() for block in BLOCKS}
    _run_rules(
        user,
        today or date.today(),
        OBJECT_SCOPES[type(obj)](obj),
        lambda row: res,
    )
    return res


def object_xrays(obj, user, today: date | None = None) -> dict:
    return {
        "object": {
            "id": obj.id,
            "name": obj.name,
            "type": obj._meta.model_name,
        },
        "assessment": obj.quality_check(),
        **object_quality_checks(obj, user, today),
    }
