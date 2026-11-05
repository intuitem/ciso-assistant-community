"""Generate page questions with golden answers computed from a seed_demo instance.

Templates per main page; every golden answer and fact is read from the database,
so the set stays exact when the demo data changes. Writes the same format as
evals/page_questions.json. Facts check only what the question asks.

  SQLITE_FILE=.../llm-eval.sqlite3 ../.venv/bin/python cli/build_page_eval.py \\
      --out cli/evals/page_questions_large.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
MAX_LIST = 15  # longer lists become count questions

out = []


def item(obj):
    ref = getattr(obj, "ref_id", None)
    return f"{ref} {obj.name}" if ref else obj.name


def add(qid, page, title, question, golden, facts, obj=None):
    q = {"id": qid, "page": page, "title": title, "question": question}
    if obj:
        q["object"] = obj
    out.append(q | {"golden": golden, "facts": facts})


def add_list(qid, page, title, question, rows, what, obj=None, none="none"):
    """A "which X?" question: one fact per item, plus nothing else listed."""
    names = [item(r) for r in rows]
    if not names:
        add(
            qid,
            page,
            title,
            question,
            f"There are {none}.",
            [f"says there are {none}"],
            obj,
        )
    elif len(names) > MAX_LIST:
        return
    else:
        golden = f"{len(names)}: " + "; ".join(names) + "."
        add(
            qid,
            page,
            title,
            question,
            golden,
            names + [f"no other {what} is listed"],
            obj,
        )


def slug(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")[:40]


def analytics(m):
    from core.models import ComplianceAssessment, Finding, Incident

    page, title = "/analytics", "Analytics"
    for value, label in Incident.Status.choices:
        rows = Incident.objects.filter(status=value).order_by("ref_id")
        if rows:
            add_list(
                f"inc-status-{value}",
                page,
                title,
                f"Which incidents are {label.lower()}?",
                rows,
                "incident",
            )
    add_list(
        "inc-open",
        page,
        title,
        "Which incidents are still open?",
        Incident.objects.filter(status__in=["new", "ongoing"]).order_by("ref_id"),
        "incident",
    )
    for value, label in Incident.Severity.choices:
        rows = Incident.objects.filter(severity=value).order_by("ref_id")
        if rows:
            add_list(
                f"inc-sev-{value}",
                page,
                title,
                f"Which incidents have {label.lower()} severity?",
                rows,
                "incident",
            )
    for value, label in Finding._meta.get_field("severity").flatchoices:
        rows = Finding.objects.filter(severity=value).order_by("ref_id")
        if rows and value >= 3:
            add_list(
                f"finding-sev-{value}",
                page,
                title,
                f"List the {label} findings.",
                rows,
                "finding",
            )
    for value, label in Finding._meta.get_field("status").flatchoices:
        rows = Finding.objects.filter(status=value).order_by("ref_id")
        if rows:
            add_list(
                f"finding-status-{value}",
                page,
                title,
                f"Which findings are {label.lower()}?",
                rows,
                "finding",
            )
    for value, label in ComplianceAssessment.Status.choices:
        rows = ComplianceAssessment.objects.filter(status=value).order_by(
            "ref_id", "name"
        )
        if rows:
            add_list(
                f"audit-status-{value}",
                page,
                title,
                f"Which audits are {label.lower()}?",
                rows,
                "audit",
            )


def controls(m):
    from core.models import AppliedControl

    page, title = "/applied-controls", "Applied controls"
    for value, label in AppliedControl.Status.choices:
        rows = AppliedControl.objects.filter(status=value).order_by("ref_id")
        if rows:
            add_list(
                f"ctrl-status-{slug(value)}",
                page,
                title,
                f"Which controls are {label.lower()}?",
                rows,
                "control",
            )
    for p in (1, 2, 3, 4):
        rows = (
            AppliedControl.objects.filter(priority=p)
            .exclude(status="active")
            .order_by("ref_id")
        )
        add_list(
            f"ctrl-p{p}-not-active",
            page,
            title,
            f"Which priority {p} controls are not active yet?",
            rows,
            "control",
            none="no such controls",
        )
    for field in ("category", "csf_function"):
        for value, label in AppliedControl._meta.get_field(field).flatchoices:
            rows = AppliedControl.objects.filter(**{field: value}).order_by("ref_id")
            if rows:
                question = (
                    f"Which {label.lower()} controls do we have?"
                    if field == "category"
                    else f"Which controls cover the {label} function?"
                )
                add_list(
                    f"ctrl-{field}-{value}", page, title, question, rows, "control"
                )


def risk_assessments(m):
    from chat.risk_levels import level_label
    from core.models import RiskAssessment

    for ra in RiskAssessment.objects.order_by("ref_id"):
        page, title = "/risk-assessments", ra.name
        obj = {"api": "risk-assessments", "ref_id": ra.ref_id}
        matrix = ra.risk_matrix
        scenarios = list(ra.risk_scenarios.order_by("ref_id"))
        rated = [
            s for s in scenarios if s.current_level is not None and s.current_level >= 0
        ]
        if rated:
            top = max(s.current_level for s in rated)
            highest = [s for s in rated if s.current_level == top]
            # a single top risk: the next level is part of "the highest risks" too
            if len(highest) == 1 and len(rated) > 1:
                second = max(s.current_level for s in rated if s.current_level < top)
                highest += [s for s in rated if s.current_level == second]
            facts = [
                f"{item(s)}: {level_label(matrix, s.current_level)}" for s in highest
            ]
            add(
                f"ra-{ra.ref_id}-highest",
                page,
                title,
                "What are the highest risks in this assessment?",
                "; ".join(facts) + ".",
                facts,
                obj,
            )
        add_list(
            f"ra-{ra.ref_id}-accepted",
            page,
            title,
            "Which risks are accepted rather than mitigated?",
            [s for s in scenarios if s.treatment == "accept"],
            "risk",
            obj,
            none="no accepted risks",
        )
        for s in scenarios:
            existing = [
                f"{item(c)} (existing)"
                for c in s.existing_applied_controls.order_by("ref_id")
            ]
            additional = [
                f"{item(c)} (additional)" for c in s.applied_controls.order_by("ref_id")
            ]
            if existing or additional:
                facts = existing + additional
                add(
                    f"ra-{ra.ref_id}-{s.ref_id}-controls",
                    page,
                    title,
                    f"Which controls address the risk '{s.name}'?",
                    "; ".join(facts) + ".",
                    facts,
                    obj,
                )
            if s.residual_level is not None and s.residual_level >= 0:
                label = level_label(matrix, s.residual_level)
                add(
                    f"ra-{ra.ref_id}-{s.ref_id}-residual",
                    page,
                    title,
                    f"What is the residual risk of '{s.name}'?",
                    f"{label}.",
                    [f"residual risk is {label}"],
                    obj,
                )


def audits(m):
    from core.models import ComplianceAssessment, RequirementAssessment

    Result = RequirementAssessment.Result
    for ca in ComplianceAssessment.objects.order_by("ref_id", "name"):
        page, title = "/compliance-assessments", ca.name
        key = ca.ref_id or slug(ca.name)
        obj = {
            "api": "compliance-assessments",
            **({"ref_id": ca.ref_id} if ca.ref_id else {"name": ca.name}),
        }
        counts = ca.get_requirements_result_count()
        total = sum(c for c, _ in counts)
        if not total:
            continue
        not_assessed = sum(c for c, r in counts if r == Result.NOT_ASSESSED)
        add(
            f"aud-{key}-progress",
            page,
            title,
            "How far along is this audit?",
            f"{total - not_assessed} of {total} requirements assessed, {not_assessed} not assessed.",
            [
                f"{total - not_assessed} of {total} assessed (or the matching percentage)",
                f"{not_assessed} not assessed",
            ],
            obj,
        )
        ras = RequirementAssessment.objects.filter(
            compliance_assessment=ca, requirement__assessable=True
        ).select_related("requirement")
        non = sorted(
            ras.filter(result=Result.NON_COMPLIANT),
            key=lambda r: r.requirement.ref_id or "",
        )
        if len(non) <= MAX_LIST:
            refs = [r.requirement.ref_id or r.requirement.name for r in non]
            facts = (
                refs + ["no requirement with another result is listed"]
                if refs
                else ["says none are non-compliant"]
            )
            add(
                f"aud-{key}-noncompliant",
                page,
                title,
                "Which requirements are non-compliant?",
                "; ".join(refs) + "." if refs else "None.",
                facts,
                obj,
            )
        else:
            add(
                f"aud-{key}-noncompliant-count",
                page,
                title,
                "How many requirements are non-compliant?",
                f"{len(non)}.",
                [f"{len(non)} non-compliant"],
                obj,
            )
        for result in (Result.NON_COMPLIANT, Result.COMPLIANT):
            ra = next(
                (
                    r
                    for r in sorted(ras.filter(result=result), key=lambda r: r.id)
                    if r.requirement.ref_id
                ),
                None,
            )
            if ra:
                ref = ra.requirement.ref_id
                add(
                    f"aud-{key}-{slug(ref)}",
                    page,
                    title,
                    f"Is {ref} compliant in this audit?",
                    f"{ref} is {Result(result).label.lower()}.",
                    [f"{ref} is {Result(result).label.lower()}"],
                    obj,
                )


def assets(m):
    from core.models import AppliedControl, Asset

    page, title = "/assets", "Assets"
    add_list(
        "asset-primary",
        page,
        title,
        "What are our primary assets?",
        Asset.objects.filter(type="PR").order_by("name"),
        "asset",
    )
    add_list(
        "asset-support",
        page,
        title,
        "Which supporting assets do we have?",
        Asset.objects.filter(type="SP").order_by("name"),
        "asset",
    )
    for a in Asset.objects.filter(type="PR").order_by("name"):
        add_list(
            f"asset-{slug(a.name)}-supported-by",
            page,
            title,
            f"Which supporting assets does {a.name} rely on?",
            a.child_assets.order_by("name"),
            "asset",
            none="no supporting assets",
        )
    for a in Asset.objects.filter(type="SP").order_by("name"):
        parents = a.parent_assets.order_by("name")
        if parents:
            add_list(
                f"asset-{slug(a.name)}-supports",
                page,
                title,
                f"Which primary asset does {a.name} support?",
                parents,
                "asset",
            )
    uncovered = [
        a
        for a in Asset.objects.filter(type="PR").order_by("name")
        if not AppliedControl.objects.filter(assets=a).exists()
    ]
    add_list(
        "asset-primary-no-controls",
        page,
        title,
        "Which primary assets have no applied controls?",
        uncovered,
        "asset",
    )


def entities(m):
    from tprm.models import Entity, EntityAssessment, Tier

    page, title = "/entities", "Entities"
    for tier in Tier.objects.order_by("-rank"):
        add_list(
            f"ent-tier-{tier.key}",
            page,
            title,
            f"Which third parties are {tier.name}?",
            Entity.objects.filter(tier=tier).order_by("name"),
            "entity",
        )
    for value, label in EntityAssessment.Status.choices:
        rows = EntityAssessment.objects.filter(status=value).order_by("name")
        if rows:
            add_list(
                f"ea-status-{value}",
                page,
                title,
                f"Which vendor assessments are {label.lower()}?",
                rows,
                "assessment",
            )
    for value, label in EntityAssessment.Conclusion.choices:
        rows = EntityAssessment.objects.filter(conclusion=value).order_by("name")
        if rows:
            add_list(
                f"ea-conclusion-{value}",
                page,
                title,
                f"Which vendor assessments ended with a {label.lower()} conclusion?",
                rows,
                "assessment",
            )
    for e in (
        Entity.objects.filter(entityassessment__isnull=False)
        .distinct()
        .order_by("name")
    ):
        add_list(
            f"ent-{slug(e.name)}-assessments",
            page,
            title,
            f"Which assessments do we have for {e.name}?",
            EntityAssessment.objects.filter(entity=e).order_by("name"),
            "assessment",
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
    import django

    django.setup()
    for build in (analytics, controls, risk_assessments, audits, assets, entities):
        build(None)
    ids = [q["id"] for q in out]
    assert len(ids) == len(set(ids)), "duplicate question ids"
    Path(args.out).write_text(
        json.dumps(
            {
                "_about": "Generated by build_page_eval.py from a seed_demo instance; golden computed from the data.",
                "questions": out,
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    by_page = {}
    for q in out:
        by_page[q["page"]] = by_page.get(q["page"], 0) + 1
    print(len(out), "questions", by_page)


if __name__ == "__main__":
    main()
