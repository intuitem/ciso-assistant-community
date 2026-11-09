"""Weakest-link outcome rules (`kind: weakest_link` in a framework's outcomes_definition).

A node is rated by its weakest requirement, and each section reports how many
of its rated nodes sit at each rating, with a weighted score (ASD Essentials:
principles rated by their lowest action, reported per domain):

    - ref_id: effectiveness
      kind: weakest_link
      label: Effectiveness
      rated_depth: 2              # the nodes rated: 1 = top-level nodes, 2 = their children...
      per: depth_1                # optional: a summary per top-level node; omitted = one for the audit
      result_weights:             # optional, this is the default
        compliant: 1
        partially_compliant: 0.5
        non_compliant: 0
      result_labels:              # optional: what the results are called
        compliant: Fully effective
      section_label: domains      # optional: what the sections are called

A rated node covers the audit's visible assessable requirements below it, or
itself when it is assessable. It is `not_assessed` while one of them is, else the worst
of their results (non compliant, then partially compliant, then compliant),
not applicable ones aside; a node whose requirements are all not applicable is
`not_applicable`, and one with none in the audit is left out. `drivers` lists
the requirements that set its rating.

A section's score is the mean weight of its applicable rated nodes, a not
assessed node counting as 0, and None when none is assessed. Not assessed nodes
keep their own count. The overall score is the same mean over the nodes of the
sections that have a score, stored as a percentage (`computed_values[ref_id]`,
readable as `values.<ref_id>`) when known; the sections are computed on read.
"""

RESULTS = ["non_compliant", "partially_compliant", "compliant"]
DEFAULT_WEIGHTS = {"compliant": 1.0, "partially_compliant": 0.5, "non_compliant": 0.0}
LABELLED = {*RESULTS, "not_assessed", "not_applicable"}


def weakest_link_rules(rules) -> list[dict]:
    return [
        rule
        for rule in rules or []
        if isinstance(rule, dict)
        and rule.get("kind") == "weakest_link"
        and rule.get("ref_id")
        and not weakest_link_errors(rule)
    ]


def weakest_link_errors(rule) -> list[str]:
    errors = []
    depth = rule.get("rated_depth")
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
        errors.append("rated_depth must be a whole number from 1")
    if rule.get("per") not in (None, "depth_1"):
        errors.append("per must be 'depth_1' or left out")
    elif rule.get("per") and isinstance(depth, int) and depth < 2:
        errors.append("per: depth_1 needs rated_depth 2 or more")
    weights = rule.get("result_weights")
    if weights is not None and not (
        isinstance(weights, dict)
        and set(weights) <= set(RESULTS)
        and all(
            isinstance(w, (int, float)) and not isinstance(w, bool) and 0 <= w <= 1
            for w in weights.values()
        )
    ):
        errors.append(
            "result_weights maps compliant, partially_compliant or non_compliant "
            "to a number from 0 to 1"
        )
    labels = rule.get("result_labels")
    if labels is not None and not (
        isinstance(labels, dict)
        and set(labels) <= LABELLED
        and all(isinstance(v, str) for v in labels.values())
    ):
        errors.append("result_labels maps results to names")
    return errors


def _rating(results: list) -> str:
    if any(r in (None, "not_assessed") for r in results):
        return "not_assessed"
    rated = [r for r in results if r != "not_applicable"]
    if not rated:
        return "not_applicable"
    return min(rated, key=RESULTS.index)


def _score(ratings: list, weights: dict) -> float | None:
    applicable = [r for r in ratings if r != "not_applicable"]
    if not any(r in RESULTS for r in applicable):
        return None
    return sum(weights.get(r, 0.0) for r in applicable) / len(applicable)


def compute_weakest_link(rule: dict, nodes: list[dict], ras: dict) -> dict:
    """nodes: the framework's requirement nodes (urn, parent_urn, ref_id, name,
    assessable), in tree order; ras: {requirement urn: (ra id, result)} for the
    audit's requirement assessments in scope."""
    weights = {**DEFAULT_WEIGHTS, **(rule.get("result_weights") or {})}
    by_urn = {n["urn"]: n for n in nodes}

    def path(urn):
        chain, seen = [], set()
        while urn in by_urn and urn not in seen:
            seen.add(urn)
            chain.append(urn)
            urn = by_urn[urn].get("parent_urn")
        return chain[::-1]

    depth = rule["rated_depth"]
    rated: dict = {}
    for n in nodes:
        if not n.get("assessable") or n["urn"] not in ras:
            continue
        chain = path(n["urn"])
        if len(chain) >= depth:
            rated.setdefault(chain[depth - 1], []).append(n)

    per_section = rule.get("per") == "depth_1"
    sections: dict = {}
    for urn, members in rated.items():
        results = [ras[m["urn"]][1] for m in members]
        rating = _rating(results)
        drivers = [
            {
                "id": ras[m["urn"]][0],
                "urn": m["urn"],
                "ref_id": m.get("ref_id"),
                "name": m.get("name"),
                "result": result,
            }
            for m, result in zip(members, results)
            if (result or "not_assessed") == rating
        ]
        node = by_urn[urn]
        key = path(urn)[0] if per_section else None
        sections.setdefault(key, []).append(
            {
                "urn": urn,
                "ref_id": node.get("ref_id"),
                "name": node.get("name"),
                "rating": rating,
                "drivers": drivers
                if rating in RESULTS or rating == "not_assessed"
                else [],
            }
        )

    out = []
    for key, rated_nodes in sections.items():
        ratings = [r["rating"] for r in rated_nodes]
        node = by_urn.get(key) or {}
        out.append(
            {
                "urn": node.get("urn"),
                "ref_id": node.get("ref_id"),
                "name": node.get("name"),
                "score": _score(ratings, weights),
                "counts": {
                    r: ratings.count(r) for r in [*RESULTS[::-1], "not_assessed"]
                },
                "nodes": rated_nodes,
            }
        )
    all_ratings = [
        n["rating"] for s in out if s["score"] is not None for n in s["nodes"]
    ]
    return {"score": _score(all_ratings, weights), "sections": out}


def evaluate_weakest_links(ca, rules, hidden_urns=None) -> tuple[dict, list]:
    """({ref_id: overall score in %}, [detail per rule]) for an audit's weakest-link rules."""
    from django.utils.translation import get_language

    from core.models import RequirementAssessment, RequirementNode

    rules = weakest_link_rules(rules)
    if not rules:
        return {}, []
    if hidden_urns is None:
        from core.cel_service import build_cel_context

        _ctx, hidden_urns = build_cel_context(ca)
    language = get_language()
    nodes = []
    for node in (
        RequirementNode.objects.filter(framework_id=ca.framework_id)
        .order_by("order_id", "id")
        .values(
            "urn",
            "parent_urn",
            "ref_id",
            "name",
            "assessable",
            "implementation_groups",
            "translations",
        )
    ):
        translated = (node.pop("translations") or {}).get(language) or {}
        nodes.append({**node, "name": translated.get("name", node["name"])})
    selected = set(ca.selected_implementation_groups or [])
    in_scope = {
        n["urn"]
        for n in nodes
        if n["urn"] not in hidden_urns
        and (not selected or selected & set(n.get("implementation_groups") or []))
    }
    ras = {
        urn: (str(pk), result)
        for pk, urn, result in RequirementAssessment.objects.filter(
            compliance_assessment=ca
        ).values_list("id", "requirement__urn", "result")
        if urn in in_scope
    }
    values, details = {}, []
    for rule in rules:
        result = compute_weakest_link(rule, nodes, ras)
        if result["score"] is not None:
            values[rule["ref_id"]] = round(result["score"] * 100, 2)
        details.append({"ref_id": rule["ref_id"], **result})
    return values, details
