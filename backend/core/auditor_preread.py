"""Auditor pre-read (experimental): what a certification auditor will ask for
each requirement of an audit, set against what the audit already holds.

The guidance is static content in `core/audit_guidance/<framework>/*.yaml`;
the audit side reuses the quality-check context, so the whole audit resolves
in a constant number of queries.
"""

from collections import defaultdict
from datetime import date, timedelta
from functools import cache
from pathlib import Path

import yaml

from core.models import (
    AppliedControl,
    Evidence,
    RequirementAssessment,
    _build_requirement_assessment_quality_context,
    _requirement_assessment_quality_findings,
)
from iam.models import RoleAssignment

GUIDANCE_DIR = Path(__file__).parent / "audit_guidance"

# Reason codes, ordered roughly by how badly they will land with an auditor.
NOTHING_LINKED = "nothing_linked"
NON_COMPLIANT = "non_compliant"
QUALITY_ERROR = "quality_error"
NOT_ASSESSED = "not_assessed"
STALE_EVIDENCE = "stale_evidence"
FEWER_EVIDENCES_THAN_REQUESTS = "fewer_evidences_than_requests"
QUALITY_WARNING = "quality_warning"
GAP_REASONS = {NOTHING_LINKED, NON_COMPLIANT, QUALITY_ERROR}


@cache
def load_guidance() -> dict[str, dict]:
    """framework_urn -> {urn_suffix: guidance}, merged over every file."""
    out: dict[str, dict] = {}
    for path in sorted(GUIDANCE_DIR.glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        out.setdefault(data["framework_urn"], {}).update(data.get("guidance") or {})
    return out


def readiness(ra_result, guidance, evidences, findings, today) -> tuple[str, list]:
    """(ready | weak | gap | excluded, reason codes) for one requirement."""
    if ra_result == RequirementAssessment.Result.NOT_APPLICABLE:
        return "excluded", []
    reasons = []
    if not evidences:
        reasons.append(NOTHING_LINKED)
    if ra_result == RequirementAssessment.Result.NON_COMPLIANT:
        reasons.append(NON_COMPLIANT)
    if any(f["severity"] == "error" for f in findings):
        reasons.append(QUALITY_ERROR)
    if ra_result == RequirementAssessment.Result.NOT_ASSESSED:
        reasons.append(NOT_ASSESSED)
    requests = guidance.get("requests") or []
    windows = [r["fresh_days"] for r in requests if r.get("fresh_days")]
    newest = max((e["updated_at"] for e in evidences if e["updated_at"]), default=None)
    if (
        evidences
        and windows
        and (newest is None or newest.date() < today - timedelta(days=max(windows)))
    ):
        reasons.append(STALE_EVIDENCE)
    if evidences and len(evidences) < len(requests):
        reasons.append(FEWER_EVIDENCES_THAN_REQUESTS)
    if any(f["severity"] == "warning" for f in findings):
        reasons.append(QUALITY_WARNING)
    if GAP_REASONS & set(reasons):
        return "gap", reasons
    return ("weak" if reasons else "ready"), reasons


def auditor_preread(compliance_assessment, user) -> dict:
    framework = compliance_assessment.framework
    guidance = load_guidance().get(framework.urn)
    if guidance is None:
        return {"framework_urn": framework.urn, "supported": False, "items": []}

    context = _build_requirement_assessment_quality_context(compliance_assessment)
    evidence_ids = {e for per_ra in context.evidences.values() for e in per_ra}
    control_ids = {c for per_ra in context.controls.values() for c in per_ra}
    # Names only for what the user may view; the rest still counts, unnamed.
    evidence_names = dict(
        Evidence.objects.filter(id__in=evidence_ids)
        .filter(id__in=RoleAssignment.get_viewable_object_ids(user, Evidence))
        .values_list("id", "name")
    )
    control_names = dict(
        AppliedControl.objects.filter(id__in=control_ids)
        .filter(id__in=RoleAssignment.get_viewable_object_ids(user, AppliedControl))
        .values_list("id", "name")
    )
    # Which path brought each evidence in: attached to the requirement itself,
    # or (the nominal setup) to one of its applied controls.
    direct = set(
        RequirementAssessment.evidences.through.objects.filter(
            requirementassessment__compliance_assessment=compliance_assessment
        ).values_list("requirementassessment_id", "evidence_id")
    )
    control_evidences = defaultdict(set)
    for cid, eid in AppliedControl.evidences.through.objects.filter(
        appliedcontrol_id__in=control_ids
    ).values_list("appliedcontrol_id", "evidence_id"):
        control_evidences[cid].add(eid)

    today = date.today()
    items = []
    for ra in compliance_assessment.requirement_assessments.select_related(
        "requirement"
    ).order_by("requirement__order_id", "created_at"):
        node = ra.requirement
        if not node.assessable or not (
            compliance_assessment.requirement_matches_selected_groups(node)
        ):
            continue
        suffix = node.urn.rsplit(":", 1)[-1]
        payload = {
            "id": ra.id,
            "name": str(ra),
            "result": ra.result,
            "status": ra.status,
        }
        errors, warnings, _info = _requirement_assessment_quality_findings(
            ra, payload, context
        )
        findings = [
            {"severity": sev, "msgid": f["msgid"], "msg": f["msg"]}
            for sev, bucket in (("error", errors), ("warning", warnings))
            for f in bucket
        ]
        evidences = []
        ra_controls = context.controls.get(ra.id, {})
        for eid, (ev_status, expiry) in context.evidences.get(ra.id, {}).items():
            has_file, updated_at = context.evidence_revisions.get(eid, (False, None))
            evidences.append(
                {
                    "id": eid,
                    "name": evidence_names.get(eid),
                    "status": ev_status,
                    "expiry_date": expiry,
                    "has_file": has_file,
                    "updated_at": updated_at,
                    "direct": (ra.id, eid) in direct,
                    "via_controls": [
                        cid for cid in ra_controls if eid in control_evidences[cid]
                    ],
                }
            )
        controls = [
            {"id": cid, "name": control_names.get(cid), "status": c_status, "eta": eta}
            for cid, (c_status, eta, _expiry) in ra_controls.items()
        ]
        node_guidance = guidance.get(suffix)
        state, reasons = (
            readiness(ra.result, node_guidance, evidences, findings, today)
            if node_guidance
            else ("no_guidance", [])
        )
        items.append(
            {
                "id": ra.id,
                "urn_suffix": suffix,
                "ref_id": node.ref_id,
                "name": node.get_name_translated or node.name,
                "result": ra.result,
                "status": ra.status,
                "has_observation": bool(ra.observation),
                "guidance": node_guidance,
                "evidences": evidences,
                "applied_controls": controls,
                "findings": findings,
                "readiness": state,
                "reasons": reasons,
            }
        )
    return {"framework_urn": framework.urn, "supported": True, "items": items}
