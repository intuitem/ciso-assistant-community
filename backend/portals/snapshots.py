"""Audit → FrameworkSnapshot projection. Pure computation: takes a ComplianceAssessment
and a chosen implementation-group set, returns the frozen payload to capture.

`content` is the requirement tree: an ordered list of root nodes, each carrying its
children recursively. Section (non-assessable) nodes are kept so the tree reads as a
hierarchy; leaves carry the captured result/score. When implementation groups are
selected, only matching leaves and their ancestor sections survive."""

from collections import defaultdict


def compute_snapshot(audit, implementation_groups):
    from core.models import RequirementAssessment, RequirementNode

    igs = set(implementation_groups or [])
    framework = audit.framework

    nodes = list(RequirementNode.objects.filter(framework=framework))
    by_urn = {n.urn: n for n in nodes}
    ras = (
        RequirementAssessment.objects.filter(compliance_assessment=audit)
        .select_related("requirement")
        .prefetch_related("applied_controls")
    )
    ra_by_req = {ra.requirement_id: ra for ra in ras}

    def in_scope(node):
        """An assessable leaf is in scope when no IG filter is set, or it shares one."""
        if not node.assessable:
            return False
        if not igs:
            return True
        return bool(
            node.implementation_groups and igs & set(node.implementation_groups)
        )

    # Tally the summary from in-scope leaves, and mark which urns to render (each kept
    # leaf pulls in its whole ancestor chain so sections aren't orphaned).
    result_counts = {r.value: 0 for r in RequirementAssessment.Result}
    scored = []
    control_ids = set()
    keep = set()
    for n in nodes:
        if not in_scope(n):
            continue
        ra = ra_by_req.get(n.id)
        if ra is None:
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
        keep.add(n.urn)
        parent = n.parent_urn
        while parent in by_urn and parent not in keep:
            keep.add(parent)
            parent = by_urn[parent].parent_urn

    children = defaultdict(list)
    for n in nodes:
        children[n.parent_urn].append(n)

    def sort_key(n):
        return n.order_id if n.order_id is not None else 0

    def build(parent_urn):
        out = []
        for n in sorted(children.get(parent_urn, []), key=sort_key):
            if n.urn not in keep:
                continue
            ra = ra_by_req.get(n.id) if n.assessable else None
            out.append(
                {
                    "ref_id": n.ref_id or "",
                    "name": n.get_name_translated or "",
                    "description": n.get_description_translated or "",
                    "assessable": n.assessable,
                    "result": ra.result if ra else None,
                    "score": ra.score if (ra and ra.score is not None) else None,
                    "children": build(n.urn),
                }
            )
        return out

    # Roots are children of any parent_urn that isn't itself a node (None or the framework).
    root_parents = sorted(
        {n.parent_urn for n in nodes} - set(by_urn), key=lambda p: p or ""
    )
    content = []
    for rp in root_parents:
        content.extend(build(rp))

    score = round(sum(scored) / len(scored), 1) if scored else None
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
        "requirement_count": sum(result_counts.values()),
    }

    return {
        "framework_name": framework.name if framework else "",
        "framework_ref_id": (framework.ref_id or "") if framework else "",
        "framework_version": str(getattr(framework, "version", "") or ""),
        "summary": summary,
        "content": content,
        "control_ids": sorted(control_ids),
    }
