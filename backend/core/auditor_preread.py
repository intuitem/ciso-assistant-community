"""Auditor pre-read (experimental): what a certification auditor will ask for
each requirement of an audit, set against what the audit already holds.

The audit guides are library objects (`AuditGuide`, see the product docs page
"Audit guides"); the audit side reuses the quality-check context, so the whole
audit resolves in a constant number of queries.
"""

import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from functools import reduce
from operator import or_

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.translation import get_language

from core.models import (
    Actor,
    AppliedControl,
    AuditGuide,
    AuditPreparation,
    AuditPreparationRole,
    AuditPreparationSession,
    AuditPreparationSetAside,
    ComplianceAssessment,
    Evidence,
    EvidenceRequestLink,
    EvidenceRevision,
    Finding,
    Framework,
    RequirementAssessment,
    Severity,
    TaskNode,
    TaskTemplate,
    _build_requirement_assessment_quality_context,
    _requirement_assessment_quality_findings,
)
from iam.models import RoleAssignment
from tprm.models import Entity

# Reason codes, ordered roughly by how badly they will land with an auditor.
OPEN_FINDING = "open_finding"
OPEN_MINOR_FINDING = "open_minor_finding"
NOTHING_LINKED = "nothing_linked"
NON_COMPLIANT = "non_compliant"
QUALITY_ERROR = "quality_error"
NOT_ASSESSED = "not_assessed"
STALE_EVIDENCE = "stale_evidence"
REQUEST_NOT_ON_FILE = "request_not_on_file"
# Evidence linked to the requirement may answer the request: not missing, not ready.
EVIDENCE_TO_CONFIRM = "evidence_to_confirm"
QUALITY_WARNING = "quality_warning"
MISSING_FILE = "missing_file"
# Rejected, expired (by status or date) or marked missing: on file, not usable.
UNUSABLE_EVIDENCE = "unusable_evidence"
EVIDENCE_TO_VALIDATE = "evidence_to_validate"
EXPIRES_BEFORE_AUDIT = "expires_before_audit"
NOT_USABLE = {
    Evidence.Status.REJECTED,
    Evidence.Status.EXPIRED,
    Evidence.Status.MISSING,
}
NOT_VALIDATED = {Evidence.Status.DRAFT, Evidence.Status.IN_REVIEW}
# Quality rules on evidence the pre-read judges itself, over every path
# (tasks included); kept, they would contradict it.
EVIDENCE_RULES = {
    "requirementAssessmentCompliantNoEvidence",
    "requirementAssessmentPartialNoEvidence",
    "requirementAssessmentEvidenceAllDraft",
    "requirementAssessmentEvidenceExpired",
    "requirementAssessmentEvidenceRejected",
    "requirementAssessmentNoUsableEvidence",
    "requirementAssessmentEvidenceStale",
}
GAP_REASONS = {OPEN_FINDING, NOTHING_LINKED, NON_COMPLIANT, QUALITY_ERROR}
# A guide written for one framework applies to another (a licensed copy, a
# translation) when nearly all of it lands there by requirement number and
# those numbers make up most of the other framework.
GUIDE_COVERAGE = 0.9
NODE_SHARE = 0.5
# Below GUIDE_COVERAGE but above this, the guide is offered rather than applied.
SUGGEST_COVERAGE = 0.5
# A finding still in one of these was raised and not yet dealt with.
OPEN_FINDING_STATUSES = {"--", "identified", "confirmed", "assigned", "in_progress"}


# Translated text of a guide item, by the field that holds it.
TEXT_FIELD = {"questions": "text", "requests": "label", "pitfalls": "text"}


def _localized(item: dict, texts: dict) -> dict:
    """An entry or a session with its text in the locale, English where missing."""
    out = {**item, "label": texts.get("label", item.get("label"))}
    if "label" not in item:
        del out["label"]
    for part, field in TEXT_FIELD.items():
        if part in item:
            out[part] = [
                {**x, field: texts[x["id"]]} if x["id"] in texts else x
                for x in item[part]
            ]
    if "sampling" in item:
        out["sampling"] = [{**x, **texts.get(x["id"], {})} for x in item["sampling"]]
    return out


def load_audit_guides(locale: str | None = None) -> dict[str, dict]:
    """guide urn -> {requirement number: entry}, in the locale where translated."""
    out = {}
    for g in AuditGuide.objects.only("urn", "entries", "translations"):
        texts = ((g.translations or {}).get(str(locale)) or {}).get("entries") or {}
        out[g.urn] = {
            key: _localized(entry, texts[key]) if key in texts else entry
            for key, entry in g.entries.items()
        }
    return out


def load_audit_sessions(locale: str | None = None) -> dict[str, list]:
    """guide urn -> Stage 2 sessions, in the order an auditor runs them."""
    out = {}
    for g in AuditGuide.objects.only("urn", "sessions", "translations"):
        texts = ((g.translations or {}).get(str(locale)) or {}).get("sessions") or {}
        out[g.urn] = [_localized(x, texts.get(x["id"], {})) for x in g.sessions]
    return out


def _number_parts(raw: str) -> list[str]:
    # A5.1 and A.05.01 read as a.5.1: letters split from digits, no padding.
    parts = [p.lstrip("0") or p for p in re.findall(r"[a-z]+|\d+", raw.lower())]
    return parts[1:] if parts[:1] in (["clause"], ["annex"]) else parts


def normalize_key(raw: str) -> str:
    """A requirement number as guides key it: "A.05.18" and "Annex A 5.18" read "a.5.18"."""
    return ".".join(_number_parts(str(raw)))


def guide_key(ref_id, urn, keys) -> str | None:
    """Guide entry for a requirement: its number, else its parent's (4.2 a) -> 4.2)."""
    for raw in (urn.rsplit(":", 1)[-1], ref_id or ""):
        parts = _number_parts(raw)
        while parts:
            if (key := ".".join(parts)) in keys:
                return key
            parts.pop()
    return None


def _rank(fit) -> tuple:
    # On a tie between guides written for other frameworks, ours (the reference) wins.
    return (fit["exact"], fit["own"], fit["coverage"], fit["builtin"])


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
    # Fixed order so a tie never flips between requests.
    guides = AuditGuide.objects.only(
        "urn", "name", "translations", "framework_urn", "provider", "entries"
    ).order_by("urn")
    # A forced guide that is no longer loaded falls back to the automatic choice.
    if forced and not guides.filter(urn=forced).exists():
        forced = None
    for g in guides:
        if forced and g.urn != forced:
            continue
        keys = set(g.entries)
        mapping = {
            nid: key for nid, nurn, ref in nodes if (key := guide_key(ref, nurn, keys))
        }
        found = {
            "guide": g.urn,
            "name": g.get_name_translated,
            "framework_urn": g.framework_urn,
            "mapping": mapping,
            "coverage": len(set(mapping.values())) / len(keys) if keys else 0,
            "matched": len(mapping),
            "total": len(nodes),
            "exact": g.framework_urn == framework.urn,
            # Among guides written for this framework, an organisation's own
            # wins over ours; a guide for another framework never jumps ahead.
            "own": g.provider != "intuitem" and g.framework_urn == framework.urn,
            "builtin": g.provider == "intuitem",
        }
        if best is None or _rank(found) > _rank(best):
            best = found
    if best:
        share = best["matched"] / best["total"] if best["total"] else 0
        best["applies"] = bool(
            best["exact"]
            or forced
            or (best["coverage"] >= GUIDE_COVERAGE and share >= NODE_SHARE)
        )
    return best


def evidence_issue(e, today, due_date=None) -> str | None:
    """Why an evidence will not hold on the audit day, or None. The page shows
    this verdict as is: the backend is the only judge."""
    expiry = e.get("expiry_date")
    if not e["has_file"]:
        return "no_file"
    if e.get("status") in NOT_USABLE or (expiry and expiry < today):
        return "unusable"
    if e.get("status") in NOT_VALIDATED:
        return "to_validate"
    if due_date and expiry and expiry < due_date:
        return "expires_before_audit"
    return None


def readiness(
    ra_result,
    guidance,
    evidences,
    findings,
    today,
    prior_findings=(),
    filed=None,
    due_date=None,
) -> tuple[str, list]:
    """(ready | to_confirm | weak | gap | excluded, reason codes) for one requirement.

    `filed` maps a request id to the evidences paired with it, through its
    reference control or by hand; unpaired requests fall back to the count.
    Marks each evidence dict with `stale` (older than the window it must meet).
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

    # An evidence without a file, or rejected, lapsed or marked missing, holds
    # its request (no "not on file") but provides nothing until it is fixed.
    def issue(e):
        return evidence_issue(e, today, due_date)

    def usable(e):
        return issue(e) not in ("no_file", "unusable")

    every = [*evidences, *(e for evs in filed.values() for e in evs)]
    all_evidences = evidences
    evidences = [e for e in evidences if usable(e)]
    provided = {r: [e for e in evs if usable(e)] for r, evs in filed.items()}
    counted = [*evidences, *(e for evs in provided.values() for e in evs)]
    nothing_provided = not counted
    for code, reason in (
        ("no_file", MISSING_FILE),
        ("unusable", UNUSABLE_EVIDENCE),
    ):
        if any(issue(e) == code for e in every):
            reasons.append(reason)
    if nothing_provided and not every:
        reasons.append(NOTHING_LINKED)
    for code, reason in (
        ("to_validate", EVIDENCE_TO_VALIDATE),
        ("expires_before_audit", EXPIRES_BEFORE_AUDIT),
    ):
        if any(issue(e) == code for e in counted):
            reasons.append(reason)
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
        provided.get(r["id"]) and too_old(provided[r["id"]], r["fresh_days"])
        for r in matchable
        if r.get("fresh_days")
    )
    for r in matchable:
        for e in filed.get(r["id"], []):
            e["stale"] = bool(r.get("fresh_days")) and too_old([e], r["fresh_days"])
    # Requests without a pairing take whatever evidence is left; it may answer
    # them (own naming, no reference control), so it is to confirm, not missing.
    open_requests = unmatched + [r for r in matchable if not filed.get(r["id"])]
    # shortcut: unpaired evidences cannot be told apart, so the tightest window
    # of the open requests applies to the newest of them.
    windows = [r["fresh_days"] for r in open_requests if r.get("fresh_days")]
    stale = stale or bool(rest and windows and too_old(rest, min(windows)))
    # A paired evidence is judged on its request's row instead.
    for e in all_evidences:
        e["stale"] = (
            e.get("id") not in paired and bool(windows) and too_old([e], min(windows))
        )
    if stale:
        reasons.append(STALE_EVIDENCE)
    # Any unpaired evidence may answer the open requests, one document often
    # several of them: to confirm by pairing, whatever the count.
    if open_requests and (evidences or paired):
        reasons.append(EVIDENCE_TO_CONFIRM if rest else REQUEST_NOT_ON_FILE)
    if any(f["severity"] == "warning" for f in findings):
        reasons.append(QUALITY_WARNING)
    if nothing_provided or GAP_REASONS & set(reasons):
        return "gap", reasons
    if set(reasons) - {EVIDENCE_TO_CONFIRM}:
        return "weak", reasons
    return ("to_confirm" if reasons else "ready"), reasons


def auditor_preread(compliance_assessment, user, forced_guide=None) -> dict:
    framework = compliance_assessment.framework
    prep = (
        AuditPreparation.objects.filter(compliance_assessment=compliance_assessment)
        .select_related("certification_body")
        .prefetch_related("set_asides", "roles__actors", "sessions__attendees")
        .first()
    )
    fit = resolve_guide(framework, forced_guide or (prep and prep.guide) or None)
    if not fit or not fit["applies"]:
        suggestion = fit and fit["coverage"] >= SUGGEST_COVERAGE and _guide_summary(fit)
        return {
            "framework_urn": framework.urn,
            "supported": False,
            "items": [],
            "suggestion": suggestion or None,
        }
    locale = get_language()
    guidance = load_audit_guides(locale)[fit["guide"]]

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
    # Third path, recurring tasks: each occurrence files a new revision of the
    # evidence its task expects (or adds one of its own), so both count for the
    # requirements and controls the task is linked to. Never filed means no
    # file, which the readiness rule already discounts.
    task_ras = defaultdict(set)
    for tid, ra_id in TaskTemplate.requirement_assessments.through.objects.filter(
        requirementassessment__compliance_assessment=compliance_assessment
    ).values_list("tasktemplate_id", "requirementassessment_id"):
        task_ras[tid].add(ra_id)
    task_controls = defaultdict(set)
    for tid, cid in TaskTemplate.applied_controls.through.objects.filter(
        appliedcontrol_id__in=control_ids
    ).values_list("tasktemplate_id", "appliedcontrol_id"):
        task_controls[tid].add(cid)
    tasks = task_ras.keys() | task_controls.keys()
    task_evidences = defaultdict(set)
    for tid, eid in TaskTemplate.evidences.through.objects.filter(
        tasktemplate_id__in=tasks
    ).values_list("tasktemplate_id", "evidence_id"):
        task_evidences[tid].add(eid)
    for tid, eid in TaskNode.evidences.through.objects.filter(
        tasknode__task_template_id__in=tasks
    ).values_list("tasknode__task_template_id", "evidence_id"):
        task_evidences[tid].add(eid)
    task_evidence_ids = set().union(*task_evidences.values())
    evidence_ids |= task_evidence_ids
    task_names = dict(
        TaskTemplate.objects.filter(id__in=task_evidences.keys())
        .filter(id__in=RoleAssignment.get_viewable_object_ids(user, TaskTemplate))
        .values_list("id", "name")
    )
    evidence_info = {
        eid: (ev_status, expiry)
        for eid, ev_status, expiry in Evidence.objects.filter(
            id__in=evidence_ids
        ).values_list("id", "status", "expiry_date")
    }
    # Same rule as the shared context: the newest revision decides the file.
    revisions = dict(context.evidence_revisions)
    for eid, attachment, link, updated_at in (
        EvidenceRevision.objects.filter(
            evidence_id__in=task_evidence_ids - revisions.keys()
        )
        .order_by("version")
        .values_list("evidence_id", "attachment", "link", "updated_at")
    ):
        latest = revisions.get(eid, (False, None))[1]
        revisions[eid] = (
            bool(attachment) or bool(link),
            updated_at if latest is None else max(latest, updated_at),
        )
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
        for tid, cids in task_controls.items():
            if cid in cids:
                by_reference[urn] |= task_evidences[tid]

    # Findings on these requirements from any audit of the framework: Stage 1,
    # internal audits and earlier cycles live in their own audits.
    # Every finding counts, so readiness is the same whoever looks; names and
    # links only for those who may view the finding.
    prior = defaultdict(list)
    on_framework = Finding.objects.filter(
        Q(requirement_node__framework=framework)
        | Q(requirement_assessment__requirement__framework=framework),
        folder_id=compliance_assessment.folder_id,
    )
    visible_findings = set(
        on_framework.filter(
            id__in=RoleAssignment.get_viewable_object_ids(user, Finding)
        ).values_list("id", flat=True)
    )
    for f in on_framework.select_related(
        "findings_assessment", "requirement_assessment"
    ).order_by("-findings_assessment__reported_at", "ref_id"):
        node_id = f.requirement_node_id or f.requirement_assessment.requirement_id
        shown = f.id in visible_findings
        prior[node_id].append(
            {
                "id": f.id if shown else None,
                "ref_id": f.ref_id if shown else None,
                "name": f.name if shown else None,
                "severity": f.severity,
                "status": f.status,
                "open": f.status in OPEN_FINDING_STATUSES,
                "source": shown
                and f.findings_assessment
                and f.findings_assessment.name,
                "reported_at": f.findings_assessment
                and f.findings_assessment.reported_at,
            }
        )

    # Evidences marked by hand as answering a request in this audit's domain,
    # wherever they sit in the audit.
    by_hand = defaultdict(set)
    for eid, entry, rid in EvidenceRequestLink.objects.filter(
        guide=fit["guide"],
        domain_id=compliance_assessment.folder_id,
        evidence_id__in=evidence_ids,
    ).values_list("evidence_id", "entry", "request"):
        by_hand[(entry, rid)].add(eid)
    # A request with a reference control is one document: paired once, it is
    # paired at every requirement asking for it.
    rc_of = _request_references(guidance)
    by_hand_rc = defaultdict(set)
    for pair, eids in by_hand.items():
        if rc_of.get(pair):
            by_hand_rc[rc_of[pair]] |= eids

    today = date.today()
    # Evidence must hold until the audit's last day, else its due date.
    due_date = (prep and prep.end_date) or compliance_assessment.due_date
    set_asides = {
        (a.entry, a.request): {"reason": a.reason}
        for a in (prep.set_asides.all() if prep else [])
    }
    # Like a pairing, a set-aside holds wherever the same document is asked.
    for pair, info in list(set_asides.items()):
        if rc := rc_of.get(pair):
            for other, u in rc_of.items():
                if u == rc:
                    set_asides.setdefault(other, info)
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
            if f["msgid"] not in EVIDENCE_RULES
        ]
        evidences = []
        ra_controls = context.controls.get(ra.id, {})
        ra_tasks = [
            tid
            for tid in task_evidences
            if ra.id in task_ras[tid] or task_controls[tid] & ra_controls.keys()
        ]
        linked = dict(context.evidences.get(ra.id, {}))
        for tid in ra_tasks:
            for eid in task_evidences[tid]:
                linked.setdefault(eid, evidence_info[eid])
        for eid, (ev_status, expiry) in linked.items():
            has_file, updated_at = revisions.get(eid, (False, None))
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
                    "via_tasks": [
                        task_names.get(tid)
                        for tid in ra_tasks
                        if eid in task_evidences[tid]
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
            hand = by_hand.get((key, r["id"]), set()) | by_hand_rc.get(
                r.get("reference_control"), set()
            )
            if not r.get("reference_control") and not hand:
                continue  # nothing to pair on: falls back to the linked count
            filed[r["id"]] = sorted(
                (
                    {
                        "id": eid,
                        "name": evidence_names.get(eid),
                        "has_file": revisions.get(eid, (False, None))[0],
                        "updated_at": revisions.get(eid, (False, None))[1],
                        "status": evidence_info.get(eid, (None, None))[0],
                        "expiry_date": evidence_info.get(eid, (None, None))[1],
                        "here": eid in here,
                        "manual": eid in hand,
                    }
                    for eid in auto | hand
                ),
                key=lambda e: e["updated_at"] or datetime.min.replace(tzinfo=UTC),
                reverse=True,
            )
        for e in [*evidences, *(f for evs in filed.values() for f in evs)]:
            e["issue"] = evidence_issue(e, today, due_date)
        # A request set aside for this audit no longer counts either way.
        aside = {rid: info for (k, rid), info in set_asides.items() if k == key}
        judged = node_guidance and {
            **node_guidance,
            "requests": [
                r for r in node_guidance.get("requests") or [] if r["id"] not in aside
            ],
        }
        state, reasons = (
            readiness(
                ra.result,
                judged,
                evidences,
                findings,
                today,
                prior[node.id],
                {r: evs for r, evs in filed.items() if r not in aside},
                due_date,
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
                "set_aside": aside,
                "readiness": state,
                "reasons": reasons,
            }
        )
    # What a pairing made by hand also answers: the other requirements here
    # asking the same thing, and the other audits of the domain on this guide.
    others = list(
        ComplianceAssessment.objects.filter(
            folder_id=compliance_assessment.folder_id,
            id__in=RoleAssignment.get_viewable_object_ids(user, ComplianceAssessment),
        )
        .exclude(id=compliance_assessment.id)
        .values_list("framework_id", flat=True)
    )
    on_guide = {
        f.id
        for f in Framework.objects.filter(id__in=others)
        if (other := resolve_guide(f))
        and other["applies"]
        and other["guide"] == fit["guide"]
    }
    other_audits = sum(fid in on_guide for fid in others)
    for item in items:
        for rid, evs in item["filed"].items():
            rc = rc_of.get((item["guide_key"], rid))
            keys = {k for (k, _r), u in rc_of.items() if u == rc} if rc else set()
            keys.add(item["guide_key"])
            refs = [
                o["ref_id"] or o["urn_suffix"]
                for o in items
                if o is not item and o["guide_key"] in keys
            ]
            for e in evs:
                if e["manual"]:
                    e["reach"] = {"requirements": refs, "audits": other_audits}
    return {
        "framework_urn": framework.urn,
        "supported": True,
        "guide": _guide_summary(fit),
        "items": items,
        "sessions": load_audit_sessions(locale).get(fit["guide"], []),
        "preparation": _preparation_payload(prep),
        "previous_set_asides": []
        if set_asides
        else _previous_set_asides(compliance_assessment, fit["guide"]),
    }


def _actors(qs) -> list:
    return [{"id": a.id, "str": str(a)} for a in qs]


def _preparation_payload(prep) -> dict | None:
    if prep is None:
        return None
    body = prep.certification_body
    return {
        "id": prep.id,
        "guide": prep.guide,
        "stage": prep.stage,
        "start_date": prep.start_date,
        "end_date": prep.end_date,
        "certification_body": body and {"id": body.id, "str": str(body)},
        "auditors": prep.auditors,
        "roles": {r.role: _actors(r.actors.all()) for r in prep.roles.all()},
        "sessions": {
            s.session: {
                "date": s.date,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "location": s.location,
                "attendees": _actors(s.attendees.all()),
            }
            for s in prep.sessions.all()
        },
    }


def _previous_set_asides(compliance_assessment, guide) -> list:
    """Set-asides of the latest other preparation in the domain on the same guide."""
    for prep in (
        AuditPreparation.objects.filter(
            compliance_assessment__folder_id=compliance_assessment.folder_id,
            set_asides__isnull=False,
        )
        .exclude(compliance_assessment=compliance_assessment)
        .select_related("compliance_assessment__framework")
        .distinct()
        .order_by("-updated_at")
    ):
        other = resolve_guide(prep.compliance_assessment.framework, prep.guide or None)
        if other and other["applies"] and other["guide"] == guide:
            return [
                {"entry": a.entry, "request": a.request, "reason": a.reason}
                for a in prep.set_asides.all()
            ]
    return []


def _guide_summary(fit) -> dict:
    return {
        "urn": fit["guide"],
        "name": fit["name"],
        "framework_urn": fit["framework_urn"],
        "exact": fit["exact"],
        "matched": fit["matched"],
        "total": fit["total"],
        "coverage": round(fit["coverage"], 3),
    }


PAIRING_ERRORS = ("unknownRequirementAssessment", "unknownRequest", "unknownEvidence")


def _guide_request(compliance_assessment, data, forced_guide=None):
    """(requirement assessment, guide fit, entry key, request) named by `data`,
    or an error code from PAIRING_ERRORS. Observations cannot be filed."""
    ra = compliance_assessment.requirement_assessments.filter(
        id=data.get("requirement_assessment")
    ).first()
    if ra is None:
        return PAIRING_ERRORS[0]
    prep = getattr(compliance_assessment, "preparation", None)
    fit = resolve_guide(
        compliance_assessment.framework, forced_guide or (prep and prep.guide) or None
    )
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
    return ra, fit, key, request


PREPARATION_ERRORS = ("invalidField", "unknownObject", "reasonRequired")


class _Rejected(Exception):
    """Leaves the preparation transaction, undoing a preparation created for nothing."""

    def __init__(self, code):
        self.code = code


def _ids(model, values, user=None):
    """The objects `values` names, or None if any is unknown (or not viewable)."""
    values = values or []
    qs = model.objects.filter(id__in=values)
    if user is not None:
        qs = qs.filter(id__in=RoleAssignment.get_viewable_object_ids(user, model))
    found = list(qs)
    return found if len(found) == len(set(values)) else None


def update_preparation(compliance_assessment, user, data) -> str | None:
    """Store one decision of the audit's preparation, creating it on the way.

    `data` holds one of: "fields" (stage, dates, certification body, auditors,
    guide), "set_aside" (requirement_assessment, request, reason, remove),
    "carry_over" (take the previous preparation's set-asides), "role" (role,
    actors) or "session" (session, date, times, location, attendees). Returns
    None, or a code from PREPARATION_ERRORS / PAIRING_ERRORS. The caller has
    checked the user may change the preparation.
    """
    try:
        with transaction.atomic():
            prep, _created = AuditPreparation.objects.get_or_create(
                compliance_assessment=compliance_assessment
            )

            def guide():
                fit = resolve_guide(compliance_assessment.framework, prep.guide or None)
                if not fit or not fit["applies"]:
                    raise _Rejected(PREPARATION_ERRORS[0])
                return fit["guide"]

            if "fields" in data:
                fields = data["fields"] or {}
                allowed = {
                    "stage",
                    "start_date",
                    "end_date",
                    "auditors",
                    "guide",
                    "certification_body",
                }
                if set(fields) - allowed:
                    raise _Rejected(PREPARATION_ERRORS[0])
                if "guide" in fields and fields["guide"] not in (
                    "",
                    *load_audit_guides(),
                ):
                    raise _Rejected(PREPARATION_ERRORS[0])
                if "certification_body" in fields:
                    body = fields.pop("certification_body")
                    found = _ids(Entity, [body] if body else [], user)
                    if found is None:
                        raise _Rejected(PREPARATION_ERRORS[1])
                    prep.certification_body = found[0] if found else None
                for name, value in fields.items():
                    setattr(
                        prep,
                        name,
                        value
                        or ("" if name in ("stage", "auditors", "guide") else None),
                    )
                prep.full_clean()
                prep.save()
            elif "set_aside" in data:
                aside = data["set_aside"] or {}
                found = _guide_request(compliance_assessment, aside)
                if isinstance(found, str):
                    raise _Rejected(found)
                _ra, fit, key, request = found
                if aside.get("remove"):
                    # Restored everywhere the same document is asked.
                    rc = request.get("reference_control")
                    refs = _request_references(load_audit_guides()[fit["guide"]])
                    same = [p for p, u in refs.items() if rc and u == rc]
                    prep.set_asides.filter(
                        reduce(
                            or_,
                            (
                                Q(entry=e, request=r)
                                for e, r in same or [(key, request["id"])]
                            ),
                        )
                    ).delete()
                elif not (aside.get("reason") or "").strip():
                    raise _Rejected(PREPARATION_ERRORS[2])
                else:
                    AuditPreparationSetAside.objects.update_or_create(
                        preparation=prep,
                        entry=key,
                        request=request["id"],
                        defaults={
                            "reason": aside["reason"].strip(),
                            "created_by": user,
                        },
                    )
            elif data.get("carry_over"):
                for a in _previous_set_asides(compliance_assessment, guide()):
                    AuditPreparationSetAside.objects.get_or_create(
                        preparation=prep,
                        entry=a["entry"],
                        request=a["request"],
                        defaults={"reason": a["reason"], "created_by": user},
                    )
            elif "role" in data:
                role = data["role"] or {}
                actors = _ids(Actor, role.get("actors"), user)
                people = {
                    w
                    for e in load_audit_guides()[guide()].values()
                    for w in e.get("interviewees") or []
                }
                if role.get("role") not in people or actors is None:
                    raise _Rejected(PREPARATION_ERRORS[1])
                row, _ = AuditPreparationRole.objects.get_or_create(
                    preparation=prep, role=role["role"]
                )
                row.actors.set(actors)
            elif "session" in data:
                session = data["session"] or {}
                attendees = _ids(Actor, session.get("attendees"), user)
                sessions = {x["id"] for x in load_audit_sessions().get(guide(), [])}
                if session.get("session") not in sessions or attendees is None:
                    raise _Rejected(PREPARATION_ERRORS[1])
                row, _ = AuditPreparationSession.objects.get_or_create(
                    preparation=prep, session=session["session"]
                )
                for name in ("date", "start_time", "end_time", "location"):
                    if name in session:
                        setattr(
                            row,
                            name,
                            session[name] or ("" if name == "location" else None),
                        )
                row.full_clean(exclude=["preparation"])
                row.save()
                row.attendees.set(attendees)
            else:
                raise _Rejected(PREPARATION_ERRORS[0])
            prep.updated_by = user
            prep.save(update_fields=["updated_by", "updated_at"])
    except _Rejected as rejected:
        return rejected.code
    # clean() still runs after a field failed, so a bad date can reach a comparison.
    except ValidationError, ValueError, TypeError:
        return PREPARATION_ERRORS[0]
    return None


def _request_references(guidance) -> dict:
    """(entry, request id) -> reference control, for requests that have one."""
    return {
        (key, r["id"]): r["reference_control"]
        for key, entry in guidance.items()
        for r in entry.get("requests") or []
        if r.get("reference_control")
    }


def pair_request(compliance_assessment, user, data, forced_guide=None) -> str | None:
    """Mark (or unmark) an evidence of a requirement as answering one request.

    Returns None, or an error code from PAIRING_ERRORS. The caller has checked
    the user may edit the audit.
    """
    found = _guide_request(compliance_assessment, data, forced_guide)
    if isinstance(found, str):
        return found
    ra, fit, key, request = found
    # An evidence the user may see, linked to this requirement directly or
    # through its applied controls or tasks; with "attach", any such evidence,
    # linked to the requirement on the way (picked from any evidence the user can see).
    viewable = Evidence.objects.filter(
        id__in=RoleAssignment.get_viewable_object_ids(user, Evidence)
    )
    linked = viewable.filter(
        Q(requirement_assessments=ra)
        | Q(applied_controls__requirement_assessments=ra)
        | Q(task_templates__requirement_assessments=ra)
        | Q(task_templates__applied_controls__requirement_assessments=ra)
        | Q(task_nodes__task_template__requirement_assessments=ra)
        | Q(task_nodes__task_template__applied_controls__requirement_assessments=ra)
    )
    # Unpairing works wherever the pairing shows, linked here or not.
    pool = viewable if data.get("remove") else linked
    evidence = pool.filter(id=data.get("evidence")).distinct().first()
    if evidence is None and data.get("attach") and not data.get("remove"):
        evidence = viewable.filter(id=data.get("evidence")).first()
        if evidence is not None:
            ra.evidences.add(evidence)
    if evidence is None:
        return PAIRING_ERRORS[2]
    fields = {
        "evidence": evidence,
        "guide": fit["guide"],
        "entry": key,
        "request": request["id"],
        "domain_id": compliance_assessment.folder_id,
    }
    if data.get("remove"):
        # Unpaired everywhere the same document is asked, wherever it was paired.
        refs = _request_references(load_audit_guides()[fit["guide"]])
        rc = request.get("reference_control")
        same = [p for p, u in refs.items() if rc and u == rc] or [(key, request["id"])]
        links = EvidenceRequestLink.objects.filter(
            evidence=evidence,
            guide=fit["guide"],
            domain_id=compliance_assessment.folder_id,
        )
        links.filter(reduce(or_, (Q(entry=e, request=r) for e, r in same))).delete()
    else:
        EvidenceRequestLink.objects.get_or_create(
            **fields, defaults={"created_by": user}
        )
    return None
