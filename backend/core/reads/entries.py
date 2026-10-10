"""The readable models: which models a read may touch, and how each one's
rows filter and serialize.

Shared by the workflow engine's ``read_objects`` action and by anything else
in the product that reads objects through a declared, whitelisted surface.
Adding a model here makes it readable everywhere at once; keep the rules in
``ReadEntry``'s docstring when doing so.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field

from django.db.models import (
    BooleanField,
    Count,
    ForeignKey,
    Model,
    OuterRef,
    Q,
    Subquery,
)
from django.db.models.functions import Coalesce

from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Finding,
    FindingsAssessment,
    Incident,
    QuickFormResponse,
    RequirementAssessment,
    RiskAcceptance,
    RiskAssessment,
    RiskScenario,
    SecurityException,
    TaskNode,
    ValidationFlow,
    Vulnerability,
)
from doc_management.models import DocumentContainer, DocumentRevision, ManagedDocument
from tprm.models import Entity, EntityAssessment

from .filters import get_model_field

# Columns every readable model exposes, when it has them.
BASE_READ_FIELDS = ["id", "name", "created_at", "updated_at"]


@dataclass(frozen=True)
class Annotation:
    """A database-side value a read may filter, order and aggregate on as if
    it were a column. ``expression`` must be a correlated subquery or a
    scalar expression, never an aggregate over a join: an outer aggregate
    would drag every row into a GROUP BY and poison aggregate mode. ``kind``
    is one of filters.KINDS and decides the operators and functions offered.
    """

    expression: object
    kind: str


@dataclass(frozen=True)
class ReadEntry:
    """One READABLE_MODELS entry: a model workflows may read, and how its
    rows filter and serialize.

    BASE_READ_FIELDS plus ``fields`` is both the serialized output and the
    filter/order whitelist: concrete columns only, no "__" paths, so filters
    cannot tunnel into other objects. FK fields are listed under their API
    name and filter on the id value — still no join.

    A ``computed`` key may shadow a listed column to reshape its output to
    the API read serializer's shape (display labels, matrix cells, nested FK
    dicts) so workflow rows read like API responses; the column name stays
    the filter/order surface, comparing on the raw stored value.
    """

    model: type[Model]
    #: Readable columns on top of BASE_READ_FIELDS.
    fields: list[str]
    #: Output-only values, key -> callable(row); never filterable/orderable.
    computed: dict[str, Callable] = dataclass_field(default_factory=dict)
    #: Same, but resolved only when the node config names them in `include`.
    #: For values too expensive to pay for on every read of the model.
    optional_computed: dict[str, Callable] = dataclass_field(default_factory=dict)
    #: {relation path: model}. Prefetched like `prefetch_related`, but each
    #: queryset carries the same folder and visibility filters as the read
    #: itself — a row the run may see must not arrive with children it may not.
    prefetch_scoped: dict = dataclass_field(default_factory=dict)
    #: Restriction every read of this model must satisfy.
    base_filter: Q | None = None
    #: Integer columns where -1 means "not rated"; range filters skip it.
    skip_unrated: frozenset[str] = frozenset()
    #: Relations the computed callables dereference per row.
    select_related: list[str] = dataclass_field(default_factory=list)
    #: The same, for the to-many relations a computed walks — without it a
    #: read pays one query per row per relation.
    prefetch_related: list[str] = dataclass_field(default_factory=list)
    #: Database-side values, name -> Annotation: readable, filterable,
    #: orderable and aggregatable like a column, computed by the database.
    annotations: dict[str, Annotation] = dataclass_field(default_factory=dict)

    def readable_fields(self) -> list[str]:
        """Return the field names a read node may output, filter and order
        by: BASE_READ_FIELDS trimmed to columns the model actually has (e.g.
        RequirementAssessment has no name column), plus ``fields``, plus the
        annotations."""
        columns = {field.name for field in self.model._meta.concrete_fields}
        return (
            [field for field in BASE_READ_FIELDS if field in columns]
            + self.fields
            + list(self.annotations)
        )

    def categorical_fields(self) -> list[str]:
        """Readable columns holding one of a fixed set of values: a choice, a
        boolean, a related object. Grouping by one names categories (a status,
        a framework id), never row content such as a name or a description."""
        categorical = []
        for name in self.readable_fields():
            column = get_model_field(self.model, name)
            if column is None or name in self.annotations:
                continue
            if column.choices or isinstance(column, (BooleanField, ForeignKey)):
                categorical.append(name)
        return categorical


def related_count(model, relation):
    """How many rows of ``model`` point at the outer row through
    ``relation`` (a field of ``model``), as a correlated subquery: zero when
    none do, and never a GROUP BY on the outer query."""
    return Annotation(
        expression=Coalesce(
            Subquery(
                model.objects.filter(**{relation: OuterRef("pk")})
                .order_by()
                .values(relation)
                .annotate(n=Count("pk"))
                .values("n")[:1]
            ),
            0,
        ),
        kind="numeric",
    )


def _quick_form_answers(response):
    """Answers of a quick form response keyed by question node_id, in the
    legacy {urn: value} vocabulary (choice URNs for choice questions)."""
    from core.utils import build_answers_dict, extract_node_id

    by_urn = build_answers_dict(
        response.answers.select_related("question").prefetch_related("selected_choices")
    )
    return {extract_node_id(urn) or urn: value for urn, value in by_urn.items()}


def _evidence_summary(evidence):
    """What a reader needs to judge whether a piece of evidence backs anything:
    what it is, whether a file or link is actually attached, and whether it has
    lapsed. Never `get_size`/`attachment_hash` — those stat and hash the file.
    `last_revision` sorts the prefetched revisions in Python, so it costs no
    query once `…__revisions` is prefetched."""
    revision = evidence.last_revision
    return {
        "id": str(evidence.id),
        "name": evidence.name,
        "status": evidence.get_status_display(),
        "expiry_date": (
            evidence.expiry_date.isoformat() if evidence.expiry_date else None
        ),
        # The distinction that matters when a claim is being checked: an
        # evidence row can exist with nothing behind it.
        "attached": bool(revision and (revision.attachment or revision.link)),
    }


def _requirement_backing(assessment):
    """The controls a requirement leans on, each carrying its own evidence.

    Evidence reaches a requirement two ways — attached to the requirement
    assessment, or attached to one of its controls — and anything weighing a
    result against what supports it needs both. Nesting the indirect evidence
    under its control keeps that distinction visible instead of merging the two
    into one undifferentiated pile."""
    return [
        {
            "id": str(control.id),
            "ref_id": control.ref_id,
            "name": control.name,
            "status": control.get_status_display(),
            "eta": control.eta.isoformat() if control.eta else None,
            "evidences": [
                _evidence_summary(evidence) for evidence in control.evidences.all()
            ],
        }
        for control in assessment.applied_controls.all()
    ]


def _quality_check_with_text(obj):
    """The quality-check envelope plus its findings as lines a document can use:
    the template grammar cannot pluck `msg` out of a list of dicts or join them.

    Each `msg` is prefixed with the object it names. Asked about one requirement
    that prefix is on every line and says nothing; asked about the audit it is
    the only thing telling the lines apart. Scope decides, not how many
    requirements happen to have findings. `text` nests under a heading the
    caller writes.
    """
    findings = obj.quality_check()
    entries = findings["errors"] + findings["warnings"]
    shared = str(obj) if isinstance(obj, RequirementAssessment) else None

    messages = []
    for entry in entries:
        message = entry["msg"]
        prefix = f"{shared}: "
        if shared and message.startswith(prefix):
            message = message[len(prefix) :]
        messages.append(message)

    return {
        **findings,
        # The one question a workflow branches on: did any rule speak?
        "flagged": bool(entries),
        "messages": messages,
        "text": "\n".join(f"  - {message}" for message in messages),
    }


def _requirements_breakdown(assessment):
    """Total assessable requirement assessments and their count per result —
    stable shape: every result key present, zeroes included."""
    by_result = {result: 0 for result in RequirementAssessment.Result.values}
    total = 0
    for count, result in assessment.get_requirements_result_count():
        by_result[result] = count
        total += count
    return {"total": total, **by_result}


READABLE_MODELS: dict[str, ReadEntry] = {
    "applied_control": ReadEntry(
        model=AppliedControl,
        fields=[
            "description",
            "ref_id",
            "status",
            "eta",
            "expiry_date",
            "priority",
            "link",
        ],
        computed={"priority": lambda o: o.get_priority_display()},
        annotations={"evidences_count": related_count(Evidence, "applied_controls")},
    ),
    "evidence": ReadEntry(
        model=Evidence,
        fields=["description", "status"],
        computed={"status": lambda o: o.get_status_display()},
    ),
    "incident": ReadEntry(
        model=Incident,
        fields=["description", "ref_id", "status", "severity", "link"],
        computed={
            "status": lambda o: o.get_status_display(),
            "severity": lambda o: o.get_severity_display(),
        },
    ),
    "asset": ReadEntry(
        model=Asset,
        fields=["description", "ref_id", "type", "reference_link"],
        computed={"type": lambda o: o.get_type_display()},
    ),
    "vulnerability": ReadEntry(
        model=Vulnerability,
        fields=["description", "ref_id", "status", "severity", "eta", "due_date"],
        computed={"severity": lambda o: o.get_severity_display()},
    ),
    "security_exception": ReadEntry(
        model=SecurityException,
        fields=["description", "ref_id", "status", "severity", "expiration_date"],
        computed={"severity": lambda o: o.get_severity_display()},
    ),
    "entity": ReadEntry(
        model=Entity,
        fields=[
            "description",
            "ref_id",
            "mission",
            "reference_link",
            "is_active",
            "default_dependency",
            "default_penetration",
            "default_maturity",
            "default_trust",
        ],
    ),
    "findings_assessment": ReadEntry(
        model=FindingsAssessment,
        fields=["description", "ref_id", "status", "eta", "due_date"],
    ),
    "finding": ReadEntry(
        model=Finding,
        fields=[
            "description",
            "ref_id",
            "status",
            "severity",
            "eta",
            "due_date",
            "priority",
            "findings_assessment",
        ],
        computed={
            "severity": lambda o: o.get_severity_display(),
            "priority": lambda o: o.get_priority_display(),
            "findings_assessment": lambda f: (
                {
                    "str": str(f.findings_assessment),
                    "id": str(f.findings_assessment_id),
                    "name": f.findings_assessment.name,
                }
                if f.findings_assessment_id
                else None
            ),
        },
        select_related=["findings_assessment"],
    ),
    "compliance_assessment": ReadEntry(
        model=ComplianceAssessment,
        fields=[
            "description",
            "ref_id",
            "status",
            "eta",
            "due_date",
            "framework",
            "perimeter",
        ],
        # Output-only values (never filterable/orderable — they don't exist as
        # queryable columns). Each callable may run its own queries per row,
        # which the list cap bounds.
        computed={
            "computed_outcome": lambda ca: ca.computed_outcome,
            # The audit's own progress rule: per-audit modes (status-driven,
            # result-visible, questions, implementation groups) make it a
            # Python value, so an aggregate over it runs in the worker.
            "progress": lambda ca: ca.progress,
            "scores": lambda ca: ca.get_global_score(),
            "requirements": _requirements_breakdown,
            # Actor ids, the shape task_template's assignees take.
            "reviewers": lambda ca: [str(a.id) for a in ca.reviewers.all()],
            "authors": lambda ca: [str(a.id) for a in ca.authors.all()],
        },
        prefetch_related=["reviewers", "authors"],
        # Opt-in: one call walks every requirement of the audit with its
        # controls and evidences, so no unrelated read pays for it.
        optional_computed={"quality_check": _quality_check_with_text},
    ),
    "risk_assessment": ReadEntry(
        model=RiskAssessment,
        fields=["description", "ref_id", "status", "eta", "due_date"],
    ),
    "quick_form_response": ReadEntry(
        model=QuickFormResponse,
        # `outcome_refs` is the filterable mirror of `computed_outcome`: `computed`
        # entries below are output-only, and reads filter concrete columns only.
        fields=[
            "description",
            "status",
            "eta",
            "due_date",
            "quick_form",
            "outcome_refs",
        ],
        computed={
            "computed_outcome": lambda r: r.computed_outcome,
            "computed_values": lambda r: r.computed_values,
            "score": lambda r: r.score,
            "answers": _quick_form_answers,
        },
    ),
    "document_container": ReadEntry(
        model=DocumentContainer,
        fields=["description", "ref_id", "document_type"],
        computed={"document_type": lambda c: c.get_document_type_display()},
    ),
    "managed_document": ReadEntry(
        model=ManagedDocument,
        fields=["description", "locale", "default_locale", "container"],
        computed={
            # The variant's own title is optional; the container names it then.
            "name": lambda d: d.display_name,
            "container": lambda d: (
                {
                    "str": str(d.container),
                    "id": str(d.container_id),
                    "name": d.container.name,
                }
                if d.container_id
                else None
            ),
            "document_type": lambda d: (
                d.container.document_type if d.container_id else None
            ),
            # The served revision, so a read can branch on what is published
            # without a second read.
            "current_revision": lambda d: (
                {
                    "id": str(d.current_revision_id),
                    "version_number": d.current_revision.version_number,
                    "status": d.current_revision.status,
                }
                if d.current_revision_id
                else None
            ),
        },
        select_related=["container", "current_revision"],
    ),
    "document_revision": ReadEntry(
        model=DocumentRevision,
        # `content` is the markdown itself: node outputs cap a string leaf at
        # MAX_LEAF_CHARS, so a whole document reaches an AI step through
        # output_mapping (variables are not capped), never through
        # {{nodes.<ref>...}}.
        fields=[
            "version_number",
            "status",
            "source",
            "change_summary",
            "content",
            "published_at",
            "document",
        ],
        computed={
            "name": str,
            "status": lambda r: r.get_status_display(),
            "document": lambda r: {
                "str": str(r.document),
                "id": str(r.document_id),
                "name": r.document.display_name,
            },
        },
        select_related=["document", "document__container"],
    ),
    "entity_assessment": ReadEntry(
        model=EntityAssessment,
        fields=["description", "status", "eta", "due_date"],
    ),
    "task_node": ReadEntry(
        model=TaskNode,
        # One occurrence of a recurring task, so a collected file can answer
        # for it.
        fields=["status", "due_date", "scheduled_date", "observation", "task_template"],
        computed={
            "name": str,
            "task_template": lambda tn: {
                "str": str(tn.task_template),
                "id": str(tn.task_template_id),
                "name": tn.task_template.name,
            },
        },
        select_related=["task_template"],
    ),
    "requirement_assessment": ReadEntry(
        model=RequirementAssessment,
        # Assessments of non-assessable requirements (section headings)
        # exist in the database; never read them.
        base_filter=Q(requirement__assessable=True),
        fields=[
            "status",
            "result",
            "extended_result",
            "score",
            "is_scored",
            "documentation_score",
            "eta",
            "due_date",
            # The assessor's own note. It was writable before it was readable,
            # which left a run able to overwrite a note it could not see.
            "observation",
            "compliance_assessment",
        ],
        # Identify the requirement and the audit on every row, under the
        # same keys and shapes as RequirementAssessmentReadSerializer.
        computed={
            "name": str,
            "requirement": lambda ra: {
                "id": str(ra.requirement_id),
                "ref_id": ra.requirement.ref_id,
                "name": ra.requirement.name,
                # The expectation itself. Without it a reader is working from
                # a title.
                "description": ra.requirement.description,
            },
            # Subset of the API's FieldsRelatedField dict.
            "compliance_assessment": lambda ra: {
                "str": str(ra.compliance_assessment),
                "id": str(ra.compliance_assessment_id),
                "name": ra.compliance_assessment.name,
            },
        },
        # Opt-in: each costs per row, and a page carrying all three is how a
        # read outgrows one node output.
        optional_computed={
            "quality_check": _quality_check_with_text,
            # What is claimed to satisfy the requirement, and what backs it.
            "applied_controls": _requirement_backing,
            "evidences": lambda ra: [
                _evidence_summary(evidence) for evidence in ra.evidences.all()
            ],
        },
        select_related=["requirement", "compliance_assessment"],
        annotations={
            "applied_controls_count": related_count(
                AppliedControl, "requirement_assessments"
            ),
            "evidences_count": related_count(Evidence, "requirement_assessments"),
        },
        # Keyed by the computed value that needs it: unasked, unqueried.
        prefetch_scoped={
            "applied_controls": {
                "applied_controls": AppliedControl,
                "applied_controls__evidences": Evidence,
                "applied_controls__evidences__revisions": EvidenceRevision,
            },
            "evidences": {
                "evidences": Evidence,
                "evidences__revisions": EvidenceRevision,
            },
        },
    ),
    "risk_scenario": ReadEntry(
        model=RiskScenario,
        fields=[
            "description",
            "ref_id",
            "treatment",
            "inherent_level",
            "current_level",
            "residual_level",
            "risk_assessment",
        ],
        # The level columns hold -1 until the scenario is rated; range and
        # negated filters must not match those rows (eq -1 still selects them).
        skip_unrated=frozenset({"inherent_level", "current_level", "residual_level"}),
        # Levels serialize as their matrix cell dict, like the API
        # serializer; filters keep comparing the raw integer column.
        computed={
            "inherent_level": lambda s: s.get_inherent_risk(),
            "current_level": lambda s: s.get_current_risk(),
            "residual_level": lambda s: s.get_residual_risk(),
            # Subset of the API's FieldsRelatedField dict.
            "risk_assessment": lambda s: {
                "str": str(s.risk_assessment),
                "id": str(s.risk_assessment_id),
                "name": s.risk_assessment.name,
            },
        },
        select_related=["risk_assessment__risk_matrix"],
        annotations={
            "applied_controls_count": related_count(AppliedControl, "risk_scenarios")
        },
    ),
    "risk_acceptance": ReadEntry(
        model=RiskAcceptance,
        fields=["description", "state", "expiry_date", "justification"],
        computed={"state": lambda o: o.get_state_display()},
    ),
    "validation_flow": ReadEntry(
        model=ValidationFlow,
        fields=["ref_id", "status", "validation_deadline"],
        # The API's display key for this nameless model.
        computed={"str": str},
    ),
}
