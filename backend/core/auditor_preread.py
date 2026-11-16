"""Auditor pre-read (experimental): what a certification auditor will ask for
each requirement of an audit, set against what the audit already holds.

The audit guides are static content in `core/audit_guides/<framework>/*.yaml`;
the audit side reuses the quality-check context, so the whole audit resolves
in a constant number of queries.
"""

import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from functools import cache
from pathlib import Path

import yaml
from django.db.models import Q

from core.models import (
    AppliedControl,
    Evidence,
    EvidenceRequestLink,
    Finding,
    RequirementAssessment,
    Severity,
    _build_requirement_assessment_quality_context,
    _requirement_assessment_quality_findings,
)
from iam.models import RoleAssignment

AUDIT_GUIDES_DIR = Path(__file__).parent / "audit_guides"

# Reason codes, ordered roughly by how badly they will land with an auditor.
OPEN_FINDING = "open_finding"
OPEN_MINOR_FINDING = "open_minor_finding"
NOTHING_LINKED = "nothing_linked"
NON_COMPLIANT = "non_compliant"
QUALITY_ERROR = "quality_error"
NOT_ASSESSED = "not_assessed"
STALE_EVIDENCE = "stale_evidence"
FEWER_EVIDENCES_THAN_REQUESTS = "fewer_evidences_than_requests"
REQUEST_NOT_ON_FILE = "request_not_on_file"
QUALITY_WARNING = "quality_warning"
GAP_REASONS = {OPEN_FINDING, NOTHING_LINKED, NON_COMPLIANT, QUALITY_ERROR}
# A guide written for one framework applies to another (a licensed copy, a
# translation) when nearly all of it lands there by requirement number and
# those numbers make up most of the other framework.
GUIDE_COVERAGE = 0.9
NODE_SHARE = 0.5
# A finding still in one of these was raised and not yet dealt with.
OPEN_FINDING_STATUSES = {"--", "identified", "confirmed", "assigned", "in_progress"}


@cache
def load_audit_guides() -> dict[str, dict]:
    """framework_urn -> {urn_suffix: entry}, merged over every file."""
    out: dict[str, dict] = {}
    for path in sorted(AUDIT_GUIDES_DIR.glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        out.setdefault(data["framework_urn"], {}).update(data.get("entries") or {})
    return out


@cache
def load_audit_sessions() -> dict[str, list]:
    """framework_urn -> Stage 2 sessions, in the order an auditor runs them."""
    out: dict[str, list] = {}
    for path in sorted(AUDIT_GUIDES_DIR.glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        out.setdefault(data["framework_urn"], []).extend(data.get("sessions") or [])
    return out


def guide_key(ref_id, urn, keys) -> str | None:
    """Guide entry for a requirement: its number, else its parent's (4.2 a) -> 4.2)."""
    for raw in (urn.rsplit(":", 1)[-1], ref_id or ""):
        parts = [p for p in re.split(r"[^0-9a-z]+", raw.lower()) if p]
        if parts[:1] in (["clause"], ["annex"]):
            parts = parts[1:]
        while parts:
            if (key := ".".join(parts)) in keys:
                return key
            parts.pop()
    return None


def resolve_guide(framework, forced: str | None = None) -> dict | None:
    """The guide that best fits a framework, and which entry each requirement gets.

    `applies` is true for the guide's own framework, when forced, or when the
    numbers line up (see GUIDE_COVERAGE); otherwise the result is a suggestion.
    """
    nodes = list(
        framework.requirement_nodes.filter(assessable=True).values_list(
            "id", "urn", "ref_id"
        )
    )
    best = None
    for urn, entries in load_audit_guides().items():
        if forced and urn != forced:
            continue
        keys = set(entries)
        mapping = {
            nid: key for nid, nurn, ref in nodes if (key := guide_key(ref, nurn, keys))
        }
        found = {
            "guide": urn,
            "mapping": mapping,
            "coverage": len(set(mapping.values())) / len(keys),
            "matched": len(mapping),
            "total": len(nodes),
            "exact": urn == framework.urn,
        }
        if best is None or (found["exact"], found["coverage"]) > (
            best["exact"],
            best["coverage"],
        ):
            best = found
    if best:
        share = best["matched"] / best["total"] if best["total"] else 0
        best["applies"] = bool(
            best["exact"]
            or forced
            or (best["coverage"] >= GUIDE_COVERAGE and share >= NODE_SHARE)
        )
    return best


def readiness(
    ra_result, guidance, evidences, findings, today, prior_findings=(), filed=None
) -> tuple[str, list]:
    """(ready | weak | gap | excluded, reason codes) for one requirement.

    `filed` maps a request id to the evidences paired with it, through its
    reference control or by hand; unpaired requests fall back to the count.
    """
    filed = filed or {}
    if ra_result == RequirementAssessment.Result.NOT_APPLICABLE:
        return "excluded", []
    reasons = []
    # An earlier stage's finding is the first thing the auditor follows up; medium
    # and above reads as a potential nonconformity, below as a point to watch.
    still_open = [f for f in prior_findings if f["open"]]
    if any(f["severity"] >= Severity.MEDIUM for f in still_open):
        reasons.append(OPEN_FINDING)
    elif still_open:
        reasons.append(OPEN_MINOR_FINDING)
    if not evidences and not any(filed.values()):
        reasons.append(NOTHING_LINKED)
    if ra_result == RequirementAssessment.Result.NON_COMPLIANT:
        reasons.append(NON_COMPLIANT)
    if any(f["severity"] == "error" for f in findings):
        reasons.append(QUALITY_ERROR)
    if ra_result == RequirementAssessment.Result.NOT_ASSESSED:
        reasons.append(NOT_ASSESSED)
    # What the auditor watches on site is never a linked evidence.
    requests = [r for r in guidance.get("requests") or [] if r["kind"] != "observation"]
    matchable = [
        r for r in requests if r.get("reference_control") or r.get("id") in filed
    ]
    unmatched = [r for r in requests if r not in matchable]
    paired = {e["id"] for r in matchable for e in filed.get(r.get("id"), [])}
    rest = [e for e in evidences if e.get("id") not in paired]

    def too_old(evs, days):
        newest = max((e["updated_at"] for e in evs if e["updated_at"]), default=None)
        return newest is None or newest.date() < today - timedelta(days=days)

    stale = any(
        filed.get(r["id"]) and too_old(filed[r["id"]], r["fresh_days"])
        for r in matchable
        if r.get("fresh_days")
    )
    # shortcut: requests without a reference control cannot be paired, so the
    # tightest of their windows applies to the newest unpaired evidence.
    windows = [r["fresh_days"] for r in unmatched if r.get("fresh_days")]
    stale = stale or bool(rest and windows and too_old(rest, min(windows)))
    if stale:
        reasons.append(STALE_EVIDENCE)
    if (evidences or paired) and any(not filed.get(r["id"]) for r in matchable):
        reasons.append(REQUEST_NOT_ON_FILE)
    if rest and len(rest) < len(unmatched):
        reasons.append(FEWER_EVIDENCES_THAN_REQUESTS)
    if any(f["severity"] == "warning" for f in findings):
        reasons.append(QUALITY_WARNING)
    if GAP_REASONS & set(reasons):
        return "gap", reasons
    return ("weak" if reasons else "ready"), reasons


def auditor_preread(compliance_assessment, user, forced_guide=None) -> dict:
    framework = compliance_assessment.framework
    fit = resolve_guide(framework, forced_guide)
    if not fit or not fit["applies"]:
        suggestion = fit and fit["coverage"] >= 0.5 and _guide_summary(fit)
        return {
            "framework_urn": framework.urn,
            "supported": False,
            "items": [],
            "suggestion": suggestion or None,
        }
    guidance = load_audit_guides()[fit["guide"]]

    context = _build_requirement_assessment_quality_context(compliance_assessment)
    evidence_ids = {e for per_ra in context.evidences.values() for e in per_ra}
    control_ids = {c for per_ra in context.controls.values() for c in per_ra}
    # Names only for what the user may view; the rest still counts, unnamed.
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
    evidence_ids |= {e for evs in control_evidences.values() for e in evs}
    evidence_names = dict(
        Evidence.objects.filter(id__in=evidence_ids)
        .filter(id__in=RoleAssignment.get_viewable_object_ids(user, Evidence))
        .values_list("id", "name")
    )
    # A request is answered by any evidence of an applied control in this audit
    # whose reference control is the request's: the same document asked by
    # several requirements is filed once.
    by_reference = defaultdict(set)
    for cid, urn in AppliedControl.objects.filter(
        id__in=control_ids, reference_control__isnull=False
    ).values_list("id", "reference_control__urn"):
        by_reference[urn] |= control_evidences[cid]

    # Findings on these requirements from any audit of the framework: Stage 1,
    # internal audits and earlier cycles live in their own audits.
    prior = defaultdict(list)
    for f in (
        Finding.objects.filter(
            Q(requirement_node__framework=framework)
            | Q(requirement_assessment__requirement__framework=framework)
        )
        .filter(id__in=RoleAssignment.get_viewable_object_ids(user, Finding))
        .select_related("findings_assessment")
        .order_by("-findings_assessment__reported_at", "ref_id")
    ):
        node_id = f.requirement_node_id or f.requirement_assessment.requirement_id
        prior[node_id].append(
            {
                "id": f.id,
                "ref_id": f.ref_id,
                "name": f.name,
                "severity": f.severity,
                "status": f.status,
                "open": f.status in OPEN_FINDING_STATUSES,
                "source": f.findings_assessment and f.findings_assessment.name,
                "reported_at": f.findings_assessment
                and f.findings_assessment.reported_at,
            }
        )

    # Evidences marked by hand as answering a request, wherever they sit in the audit.
    by_hand = defaultdict(set)
    for eid, entry, rid in EvidenceRequestLink.objects.filter(
        guide=fit["guide"], evidence_id__in=evidence_ids
    ).values_list("evidence_id", "entry", "request"):
        by_hand[(entry, rid)].add(eid)

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
        key = fit["mapping"].get(node.id)
        node_guidance = guidance.get(key) if key else None
        here = {e["id"] for e in evidences}
        filed = {}
        for r in (node_guidance or {}).get("requests") or []:
            auto = by_reference.get(r.get("reference_control"), set())
            hand = by_hand.get((key, r["id"]), set())
            if not r.get("reference_control") and not hand:
                continue  # nothing to pair on: falls back to the linked count
            filed[r["id"]] = sorted(
                (
                    {
                        "id": eid,
                        "name": evidence_names.get(eid),
                        "updated_at": context.evidence_revisions.get(
                            eid, (False, None)
                        )[1],
                        "here": eid in here,
                        "manual": eid in hand,
                    }
                    for eid in auto | hand
                ),
                key=lambda e: e["updated_at"] or datetime.min.replace(tzinfo=UTC),
                reverse=True,
            )
        state, reasons = (
            readiness(
                ra.result,
                node_guidance,
                evidences,
                findings,
                today,
                prior[node.id],
                filed,
            )
            if node_guidance
            else ("no_guidance", [])
        )
        items.append(
            {
                "id": ra.id,
                "urn_suffix": suffix,
                "guide_key": key,
                "ref_id": node.ref_id,
                "name": node.get_name_translated or node.name,
                "result": ra.result,
                "status": ra.status,
                "has_observation": bool(ra.observation),
                "guidance": node_guidance,
                "evidences": evidences,
                "applied_controls": controls,
                "findings": findings,
                "prior_findings": prior[node.id],
                "filed": filed,
                "readiness": state,
                "reasons": reasons,
            }
        )
    return {
        "framework_urn": framework.urn,
        "supported": True,
        "guide": _guide_summary(fit),
        "items": items,
        "sessions": load_audit_sessions().get(fit["guide"], []),
    }


def _guide_summary(fit) -> dict:
    return {
        "framework_urn": fit["guide"],
        "exact": fit["exact"],
        "matched": fit["matched"],
        "total": fit["total"],
        "coverage": round(fit["coverage"], 3),
    }


PAIRING_ERRORS = ("unknownRequirementAssessment", "unknownRequest", "unknownEvidence")


def pair_request(compliance_assessment, user, data, forced_guide=None) -> str | None:
    """Mark (or unmark) an evidence of a requirement as answering one request.

    Returns None, or an error code from PAIRING_ERRORS. The caller has checked
    the user may edit the audit.
    """
    ra = compliance_assessment.requirement_assessments.filter(
        id=data.get("requirement_assessment")
    ).first()
    if ra is None:
        return PAIRING_ERRORS[0]
    fit = resolve_guide(compliance_assessment.framework, forced_guide)
    key = fit and fit["applies"] and fit["mapping"].get(ra.requirement_id)
    entry = key and load_audit_guides()[fit["guide"]].get(key)
    request = next(
        (
            r
            for r in (entry or {}).get("requests", [])
            if r["id"] == data.get("request")
        ),
        None,
    )
    if request is None or request["kind"] == "observation":
        return PAIRING_ERRORS[1]
    # Only an evidence already linked to this requirement, directly or through
    # one of its applied controls, and one the user may see.
    linked = Evidence.objects.filter(
        Q(requirement_assessments=ra) | Q(applied_controls__requirement_assessments=ra)
    ).filter(id__in=RoleAssignment.get_viewable_object_ids(user, Evidence))
    evidence = linked.filter(id=data.get("evidence")).distinct().first()
    if evidence is None:
        return PAIRING_ERRORS[2]
    fields = {
        "evidence": evidence,
        "guide": fit["guide"],
        "entry": key,
        "request": request["id"],
    }
    if data.get("remove"):
        EvidenceRequestLink.objects.filter(**fields).delete()
    else:
        EvidenceRequestLink.objects.get_or_create(
            **fields, defaults={"created_by": user}
        )
    return None
