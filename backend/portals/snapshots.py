"""Audit → FrameworkSnapshot projection. Pure computation: takes a ComplianceAssessment
and a chosen implementation-group set, returns the frozen payload to capture."""


def compute_snapshot(audit, implementation_groups):
    from core.models import RequirementAssessment

    igs = set(implementation_groups or [])
    ras = (
        RequirementAssessment.objects.filter(
            compliance_assessment=audit, requirement__assessable=True
        )
        .select_related("requirement")
        .prefetch_related("applied_controls")
    )

    rows = []
    result_counts = {r.value: 0 for r in RequirementAssessment.Result}
    scored = []
    control_ids = set()

    for ra in ras:
        req = ra.requirement
        if igs and not (
            req.implementation_groups and igs & set(req.implementation_groups)
        ):
            continue
        result_counts[ra.result] = result_counts.get(ra.result, 0) + 1
        if (
            ra.is_scored
            and ra.score is not None
            and ra.result != RequirementAssessment.Result.NOT_APPLICABLE
        ):
            scored.append(ra.score)
        for ac in ra.applied_controls.all():
            control_ids.add(str(ac.id))
        rows.append(
            {
                "ref_id": req.ref_id or "",
                "name": req.get_name_translated or "",
                "description": req.get_description_translated or "",
                "result": ra.result,
                "score": ra.score,
            }
        )

    score = round(sum(scored) / len(scored), 1) if scored else None
    framework = audit.framework
    summary = {
        "compliant": result_counts.get(RequirementAssessment.Result.COMPLIANT, 0),
        "partially_compliant": result_counts.get(
            RequirementAssessment.Result.PARTIALLY_COMPLIANT, 0
        ),
        "non_compliant": result_counts.get(
            RequirementAssessment.Result.NON_COMPLIANT, 0
        ),
        "not_applicable": result_counts.get(
            RequirementAssessment.Result.NOT_APPLICABLE, 0
        ),
        "not_assessed": result_counts.get(RequirementAssessment.Result.NOT_ASSESSED, 0),
        "score": score,
        "max_score": audit.max_score,
        "requirement_count": len(rows),
    }

    return {
        "framework_name": framework.name if framework else "",
        "framework_ref_id": (framework.ref_id or "") if framework else "",
        "framework_version": str(getattr(framework, "version", "") or ""),
        "summary": summary,
        "content": rows,
        "control_ids": sorted(control_ids),
    }
