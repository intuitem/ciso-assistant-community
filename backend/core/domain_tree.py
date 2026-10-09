"""Domain tree feed: one framework's audits summed up per domain.

The contract is mirrored by the frontend type `DomainTreeFeed`
(frontend/src/routes/(app)/(internal)/experimental/domain-tree/feed.ts).
Results are pre-summed per (audit, section, implementation-group signature) so
the payload grows with the number of audits, not with the framework's size.
"""

from collections import defaultdict
from typing import Any

from django.db.models import Q

from core.models import (
    Actor,
    ComplianceAssessment,
    RequirementAssessment,
    RequirementNode,
)
from core.utils import get_respondent_scoped_folder_ids, is_field_visible_to
from iam.models import Folder, RoleAssignment

TREE_CONTENT_TYPES = (Folder.ContentType.ROOT, Folder.ContentType.DOMAIN)

# Count tuple layout: [audit, section, signature, compliant, partial,
# non_compliant, not_applicable, not_assessed, score_sum, score_weight].
# score_sum is the weighted sum of scores rebased to 0..1 on each
# requirement's resolved scale; score_weight the sum of those weights.
RESULT_COLUMN = {
    RequirementAssessment.Result.COMPLIANT: 3,
    RequirementAssessment.Result.PARTIALLY_COMPLIANT: 4,
    RequirementAssessment.Result.NON_COMPLIANT: 5,
    RequirementAssessment.Result.NOT_APPLICABLE: 6,
    RequirementAssessment.Result.NOT_ASSESSED: 7,
}


def _order_key(node: dict) -> tuple:
    return (node["order_id"] is None, node["order_id"] or 0, node["ref_id"] or "")


def framework_structure(framework) -> dict[str, Any]:
    """Sections, IG signatures and per-requirement placement for a framework.

    Sections are the top-level requirement nodes; a framework wrapped in a single
    top-level node uses that node's children instead.
    """
    nodes = list(
        RequirementNode.objects.filter(framework=framework).values(
            "id",
            "urn",
            "parent_urn",
            "ref_id",
            "name",
            "assessable",
            "implementation_groups",
            "order_id",
        )
    )
    by_urn = {n["urn"]: n for n in nodes}
    children: dict[str | None, list[dict]] = defaultdict(list)
    for n in nodes:
        parent = n["parent_urn"] if n["parent_urn"] in by_urn else None
        children[parent].append(n)

    top = sorted(children[None], key=_order_key)
    if len(top) == 1 and children[top[0]["urn"]]:
        top = sorted(children[top[0]["urn"]], key=_order_key)
    section_index = {n["urn"]: i for i, n in enumerate(top)}

    def section_of(node: dict) -> int | None:
        current = node
        while current is not None:
            if current["urn"] in section_index:
                return section_index[current["urn"]]
            current = by_urn.get(current["parent_urn"])
        return None

    ig_order = {
        g["ref_id"]: i
        for i, g in enumerate(framework.implementation_groups_definition or [])
        if isinstance(g, dict) and g.get("ref_id")
    }
    signatures: list[tuple[str, ...]] = []
    signature_index: dict[tuple[str, ...], int] = {}
    placement: dict[Any, tuple[int, int, frozenset]] = {}
    scope: dict[tuple[int, int], int] = defaultdict(int)
    for n in nodes:
        if not n["assessable"]:
            continue
        section = section_of(n)
        if section is None:
            continue
        igs = n["implementation_groups"] or []
        sig = tuple(sorted(set(igs), key=lambda g: (ig_order.get(g, len(ig_order)), g)))
        if sig not in signature_index:
            signature_index[sig] = len(signatures)
            signatures.append(sig)
        placement[n["id"]] = (section, signature_index[sig], frozenset(igs))
        scope[(section, signature_index[sig])] += 1

    return {
        "sections": [
            {"id": str(n["id"]), "ref_id": n["ref_id"] or "", "name": n["name"] or ""}
            for n in top
        ],
        "signatures": [list(s) for s in signatures],
        "scope": [[s, g, c] for (s, g), c in sorted(scope.items())],
        "placement": placement,
    }


def select_audits(cas: list[ComplianceAssessment]) -> list[ComplianceAssessment]:
    """At most one audit per domain.

    Real data rarely moves audits to done (most
    carry no status at all), so any other status qualifies; a started audit wins
    over a planned one, then the most recently updated wins.
    """
    chosen: dict[Any, ComplianceAssessment] = {}

    def rank(ca: ComplianceAssessment) -> tuple:
        return (ca.status != ComplianceAssessment.Status.PLANNED, ca.updated_at)

    for ca in cas:
        current = chosen.get(ca.folder_id)
        if current is None or rank(ca) > rank(current):
            chosen[ca.folder_id] = ca
    return list(chosen.values())


def audit_score(
    ca: ComplianceAssessment, requirements: list[RequirementAssessment]
) -> float | None:
    """The audit page's score gauge, as a percentage of its range."""
    maturity = ca.get_global_score(prefetched_requirements=requirements)[
        "maturity_score"
    ]
    if maturity is None or maturity < 0:
        return None
    total_max = ca.get_total_max_score()
    low = (
        0
        if ca.score_calculation_method == ComplianceAssessment.CalculationMethod.SUM
        else (ca.min_score or 0)
    )
    if total_max is None or total_max <= low:
        return None
    return round(min(100.0, max(0.0, (maturity - low) / (total_max - low) * 100)), 1)


def _na_target_ratio(ca: ComplianceAssessment) -> float:
    """Where an anchored N/A sits on its scale, as get_global_score anchors it."""
    lo, hi = ca.min_score, ca.max_score
    if ca.target_score is None or lo is None or hi is None or hi <= lo:
        return 1.0
    return (max(lo, min(ca.target_score, hi)) - lo) / (hi - lo)


def tree_audits(user, respondent_folders=None):
    """Audits the domain tree may show this user, before the one-per-domain pick.

    Respondents only see the audits they are assigned to, as on the audit list.
    """
    qs = ComplianceAssessment.objects.filter(
        id__in=RoleAssignment.get_viewable_object_ids(user, ComplianceAssessment),
        folder__content_type__in=TREE_CONTENT_TYPES,
    ).exclude(status=ComplianceAssessment.Status.DEPRECATED)
    if respondent_folders is None:
        respondent_folders = get_respondent_scoped_folder_ids(user)
    if respondent_folders:
        qs = qs.filter(
            ~Q(folder_id__in=respondent_folders)
            | Q(requirement_assignments__actor__in=Actor.get_all_for_user(user))
        ).distinct()
    return qs


def build_domain_tree(user, framework, campaign_id=None) -> dict[str, Any]:
    folders = {
        f["id"]: f
        for f in Folder.objects.filter(content_type__in=TREE_CONTENT_TYPES).values(
            "id", "name", "parent_folder_id"
        )
    }
    viewable_folder_ids = set(RoleAssignment.get_viewable_object_ids(user, Folder))

    respondent_folders = get_respondent_scoped_folder_ids(user)
    ca_qs = tree_audits(user, respondent_folders).filter(framework=framework)
    if campaign_id:
        ca_qs = ca_qs.filter(campaign_id=campaign_id)
    audits = sorted(select_audits(list(ca_qs)), key=lambda ca: ca.name)

    # A domain hosting a viewable audit is named anyway through that audit.
    viewable_folder_ids |= {ca.folder_id for ca in audits}

    # Viewable domains, plus their non-viewable ancestors (sent without a name).
    kept: set = set()
    for fid in folders:
        if fid not in viewable_folder_ids:
            continue
        path = []
        current = fid
        while current in folders and current not in kept:
            path.append(current)
            current = folders[current]["parent_folder_id"]
        if current is None or current in kept:
            kept.update(path)

    structure = framework_structure(framework)
    placement = structure["placement"]

    roles = {
        ca.id: "respondent"
        if respondent_folders and ca.folder_id in respondent_folders
        else "auditor"
        for ca in audits
    }
    scored_audits = {
        ca.id: ca
        for ca in audits
        if roles[ca.id] == "auditor"
        and is_field_visible_to(ca, "result", "auditor")
        and is_field_visible_to(ca, "score", "auditor")
    }
    requirements_by_audit: dict[Any, list[RequirementAssessment]] = defaultdict(list)
    for ra in RequirementAssessment.objects.filter(
        compliance_assessment_id__in=scored_audits.keys(),
        requirement__assessable=True,
    ).select_related("requirement"):
        ra.compliance_assessment = scored_audits[ra.compliance_assessment_id]
        requirements_by_audit[ra.compliance_assessment_id].append(ra)

    audit_rows = []
    visible: dict[Any, dict[str, Any]] = {}
    for i, ca in enumerate(audits):
        role = roles[ca.id]
        results_hidden = role == "respondent" or not is_field_visible_to(
            ca, "result", role
        )
        score_visible = is_field_visible_to(ca, "score", role)
        if not results_hidden:
            visible[ca.id] = {
                "index": i,
                "score_visible": score_visible
                and ca.min_score is not None
                and ca.max_score is not None,
                "selected": set(ca.selected_implementation_groups or []),
                "min": ca.min_score,
                "max": ca.max_score,
                "na_ratio": _na_target_ratio(ca) if ca.anchor_na_to_target else None,
            }
        audit_rows.append(
            {
                "id": str(ca.id),
                "name": ca.name,
                "folder_id": str(ca.folder_id),
                "status": ca.status,
                "updated_at": ca.updated_at.isoformat(),
                "selected_implementation_groups": ca.selected_implementation_groups
                or [],
                "results_hidden": results_hidden,
                "score": audit_score(ca, requirements_by_audit[ca.id])
                if ca.id in scored_audits
                else None,
                "progress": None if results_hidden else ca.progress,
            }
        )

    cells: dict[tuple[int, int, int], list] = {}
    ras = RequirementAssessment.objects.filter(
        compliance_assessment_id__in=visible.keys(),
        requirement__framework=framework,
        requirement__assessable=True,
    ).values_list(
        "compliance_assessment_id",
        "requirement_id",
        "result",
        "score",
        "is_scored",
        "requirement__min_score",
        "requirement__max_score",
        "requirement__weight",
    )
    for (
        ca_id,
        req_id,
        result,
        score,
        is_scored,
        req_min,
        req_max,
        weight,
    ) in ras.iterator(chunk_size=5000):
        info = visible[ca_id]
        audit_index = info["index"]
        if req_id not in placement:
            continue
        section, sig, igs = placement[req_id]
        # each audit only counts its selected implementation groups (empty = all)
        if info["selected"] and not (igs & info["selected"]):
            continue
        column = RESULT_COLUMN.get(result)
        if column is None:
            continue
        key = (audit_index, section, sig)
        cell = cells.get(key)
        if cell is None:
            cell = cells[key] = [audit_index, section, sig, 0, 0, 0, 0, 0, 0, 0]
        cell[column] += 1
        if not info["score_visible"]:
            continue
        # same row set and rebasing as ComplianceAssessment.get_global_score (AVG)
        lo = req_min if req_min is not None else info["min"]
        hi = req_max if req_max is not None else info["max"]
        if lo is None or hi is None or hi <= lo:
            continue
        if result == RequirementAssessment.Result.NOT_APPLICABLE:
            ratio = info["na_ratio"]
        elif is_scored and score is not None:
            ratio = (score - lo) / (hi - lo)
        else:
            ratio = None
        if ratio is not None:
            w = weight or 1
            cell[8] += ratio * w
            cell[9] += w

    return {
        "framework": {
            "id": str(framework.id),
            "name": framework.name,
            "implementation_groups": [
                {"ref_id": g["ref_id"], "name": g.get("name") or g["ref_id"]}
                for g in framework.implementation_groups_definition or []
                if isinstance(g, dict) and g.get("ref_id")
            ],
        },
        "sections": structure["sections"],
        "signatures": structure["signatures"],
        "scope": structure["scope"],
        "folders": [
            {
                "id": str(fid),
                "name": f["name"] if fid in viewable_folder_ids else "",
                "parent_id": str(f["parent_folder_id"])
                if f["parent_folder_id"]
                else None,
                "viewable": fid in viewable_folder_ids,
            }
            for fid, f in folders.items()
            if fid in kept
        ],
        "audits": audit_rows,
        "counts": [[*c[:8], round(c[8], 4), c[9]] for c in sorted(cells.values())],
    }
