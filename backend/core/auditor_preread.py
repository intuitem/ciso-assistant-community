"""Auditor pre-read (experimental): what a certification auditor will ask for
each requirement of an audit, set against what the audit already holds.

The audit guides are static content in `core/audit_guides/<framework>/*.yaml`;
the audit side reuses the quality-check context, so the whole audit resolves
in a constant number of queries.
"""

import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from functools import cache, reduce
from operator import or_
from pathlib import Path

import yaml
from django.db.models import Q
from django.utils.translation import get_language

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
REQUEST_NOT_ON_FILE = "request_not_on_file"
# Evidence linked to the requirement may answer the request: not missing, not ready.
EVIDENCE_TO_CONFIRM = "evidence_to_confirm"
QUALITY_WARNING = "quality_warning"
MISSING_FILE = "missing_file"
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


@cache
def load_guide_translations(locale: str) -> dict[str, dict]:
    """framework_urn -> {"entries"|"sessions": {key: {item id: text}}} in one locale."""
    out: dict[str, dict] = {}
    for path in sorted(AUDIT_GUIDES_DIR.glob(f"*/i18n/{locale}/*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        t = out.setdefault(data["framework_urn"], {"entries": {}, "sessions": {}})
        for part in t:
            for key, texts in (data.get(part) or {}).items():
                t[part].setdefault(key, {}).update(texts)
    return out


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


@cache
def load_audit_guides(locale: str | None = None) -> dict[str, dict]:
    """framework_urn -> {urn_suffix: entry}, merged over every file."""
    out: dict[str, dict] = {}
    for path in sorted(AUDIT_GUIDES_DIR.glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        out.setdefault(data["framework_urn"], {}).update(data.get("entries") or {})
    for urn, t in load_guide_translations(str(locale)).items():
        entries = out.get(urn, {})
        for key, texts in t["entries"].items():
            if key in entries:
                entries[key] = _localized(entries[key], texts)
    return out


@cache
def load_audit_sessions(locale: str | None = None) -> dict[str, list]:
    """framework_urn -> Stage 2 sessions, in the order an auditor runs them."""
    out: dict[str, list] = {}
    for path in sorted(AUDIT_GUIDES_DIR.glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        out.setdefault(data["framework_urn"], []).extend(data.get("sessions") or [])
    for urn, t in load_guide_translations(str(locale)).items():
        out[urn] = [
            _localized(s, t["sessions"].get(s["id"], {})) for s in out.get(urn, [])
        ]
    return out


def guide_key(ref_id, urn, keys) -> str | None:
    """Guide entry for a requirement: its number, else its parent's (4.2 a) -> 4.2)."""
    for raw in (urn.rsplit(":", 1)[-1], ref_id or ""):
        # A5.1 and A.05.01 read as a.5.1: letters split from digits, no padding.
        parts = [p.lstrip("0") or p for p in re.findall(r"[a-z]+|\d+", raw.lower())]
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
    """(ready | to_confirm | weak | gap | excluded, reason codes) for one requirement.

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
    # A document with neither file nor link is a placeholder: it holds its
    # request (no "not on file") but provides nothing until the file is added.
    fileless = any(not e["has_file"] for e in evidences) or any(
        not e["has_file"] for evs in filed.values() for e in evs
    )
    evidences = [e for e in evidences if e["has_file"]]
    provided = {r: [e for e in evs if e["has_file"]] for r, evs in filed.items()}
    nothing_provided = not evidences and not any(provided.values())
    if nothing_provided:
        reasons.append(MISSING_FILE if fileless else NOTHING_LINKED)
    elif fileless:
        reasons.append(MISSING_FILE)
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
    # Requests without a pairing take whatever evidence is left; it may answer
    # them (own naming, no reference control), so it is to confirm, not missing.
    open_requests = unmatched + [r for r in matchable if not filed.get(r["id"])]
    # shortcut: unpaired evidences cannot be told apart, so the tightest window
    # of the open requests applies to the newest of them.
    windows = [r["fresh_days"] for r in open_requests if r.get("fresh_days")]
    stale = stale or bool(rest and windows and too_old(rest, min(windows)))
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
    fit = resolve_guide(framework, forced_guide)
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
    # A request with a reference control is one document: paired once, it is
    # paired at every requirement asking for it.
    rc_of = _request_references(guidance)
    by_hand_rc = defaultdict(set)
    for pair, eids in by_hand.items():
        if rc_of.get(pair):
            by_hand_rc[rc_of[pair]] |= eids

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
                        "has_file": context.evidence_revisions.get(eid, (False, None))[
                            0
                        ],
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
        "sessions": load_audit_sessions(locale).get(fit["guide"], []),
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
    # An evidence the user may see, linked to this requirement directly or
    # through one of its applied controls; with "attach", any such evidence,
    # linked to the requirement on the way (picked from elsewhere in the domain).
    viewable = Evidence.objects.filter(
        id__in=RoleAssignment.get_viewable_object_ids(user, Evidence)
    )
    linked = viewable.filter(
        Q(requirement_assessments=ra) | Q(applied_controls__requirement_assessments=ra)
    )
    evidence = linked.filter(id=data.get("evidence")).distinct().first()
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
    }
    if data.get("remove"):
        # Unpaired everywhere the same document is asked, wherever it was paired.
        refs = _request_references(load_audit_guides()[fit["guide"]])
        rc = request.get("reference_control")
        same = [p for p, u in refs.items() if rc and u == rc] or [(key, request["id"])]
        links = EvidenceRequestLink.objects.filter(
            evidence=evidence, guide=fit["guide"]
        )
        links.filter(reduce(or_, (Q(entry=e, request=r) for e, r in same))).delete()
    else:
        EvidenceRequestLink.objects.get_or_create(
            **fields, defaults={"created_by": user}
        )
    return None
