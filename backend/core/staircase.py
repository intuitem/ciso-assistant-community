"""Staircase outcome rules (`kind: staircase` in a framework's outcomes_definition).

A level is reached only when every requirement of that level passes, and every
level below it is reached too (ASD Essential Eight, ASVS, CMMC style):

    - ref_id: maturity_level
      kind: staircase
      label: Maturity level
      staircase_levels: ['1', '2', '3']  # implementation group ref_ids, lowest first
      per: depth_1                # optional: a level per top-level node; omitted = one for the audit
      cumulative: false           # optional: level L also needs requirements tagged below L
      floor_label: Maturity Level Zero  # optional: name of level 0
      section_label: mitigation strategies  # optional: what the sections are called

Rules of every kind share one list, so a kind reuses another kind's key only
with the same meaning and shape: ratings have `levels`, hence `staircase_levels`.

Each section (a top-level node, or the whole audit) lists its levels in order,
`levels[n - 1]` being level n, each with its implementation group, `passing` and
`total` (None when the audit does not include that level) and a status: `met`
when all pass (compliant or not applicable, or none is tagged with that level in
the section), `not_met` when one fails, `pending` when none fails but some are
not assessed, `out_of_scope` when the audit does not include them. A section's
level is the number of levels met in a row from the lowest, and `blocking` lists
what keeps it from the next one. When that climb stops at a level of the audit's
target that the audit does not include, the level reached cannot be told and is
None. The overall level is the lowest section level, None when one is or when
the audit includes none of the levels. Only a known overall level is stored
(`computed_values[ref_id]`, readable as `values.<ref_id>`); the sections are
computed on read.
"""

PASS = {"compliant", "not_applicable"}
FAIL = {"non_compliant", "partially_compliant"}


def staircase_rules(rules) -> list[dict]:
    return [
        rule
        for rule in rules or []
        if isinstance(rule, dict)
        and rule.get("kind") == "staircase"
        and rule.get("ref_id")
        and rule.get("staircase_levels")
    ]


def expand_scope(outcomes_definition, selected) -> list:
    """A target level brings the levels below it: they are needed to tell
    which level is reached."""
    selected = list(selected or [])
    for rule in staircase_rules(outcomes_definition):
        levels = [str(level) for level in rule["staircase_levels"]]
        picked = [levels.index(g) for g in selected if g in levels]
        if picked:
            selected += [lv for lv in levels[: max(picked)] if lv not in selected]
    return selected


def staircase_errors(rule, known_groups) -> list[str]:
    levels = rule.get("staircase_levels")
    if not isinstance(levels, list) or not levels:
        return ["A staircase rule needs a non-empty list of staircase_levels"]
    errors = [
        f"Unknown implementation group '{level}'"
        for level in levels
        if str(level) not in known_groups
    ]
    if rule.get("per") not in (None, "depth_1"):
        errors.append("per must be 'depth_1' or left out")
    if len({str(level) for level in levels}) != len(levels):
        errors.append("Each level must appear only once")
    if not isinstance(rule.get("cumulative", False), bool):
        errors.append("cumulative must be true or false")
    return errors


def _level_status(results: list) -> str:
    if any(r is None for r in results):
        return "out_of_scope"
    if any(r in FAIL for r in results):
        return "not_met"
    if all(r in PASS for r in results):
        return "met"
    return "pending"


def compute_staircase(rule: dict, nodes: list[dict], ras: dict, scope=None) -> dict:
    """nodes: the framework's requirement nodes (urn, parent_urn, ref_id, name,
    assessable, implementation_groups); ras: {requirement urn: (ra id, result)}
    for the audit's requirement assessments."""
    levels = [str(level) for level in rule["staircase_levels"]]
    parents = {n["urn"]: n.get("parent_urn") for n in nodes}

    def top(urn):
        seen = set()
        while parents.get(urn) in parents and urn not in seen:
            seen.add(urn)
            urn = parents[urn]
        return urn

    sections: dict = {}
    if rule.get("per") == "depth_1":
        for n in nodes:
            if not n.get("parent_urn") or n.get("parent_urn") not in parents:
                sections[n["urn"]] = {"node": n, "members": []}
    else:
        sections[None] = {"node": None, "members": []}
    for n in nodes:
        if not n.get("assessable"):
            continue
        key = top(n["urn"]) if None not in sections else None
        if key in sections:
            sections[key]["members"].append(n)

    out = []
    for section in sections.values():
        steps, level, blocking, climbing = [], 0, [], True
        in_audit = False
        for index, lv in enumerate(levels):
            wanted = set(levels[: index + 1]) if rule.get("cumulative") else {lv}
            members = [
                m
                for m in section["members"]
                if wanted & {str(g) for g in m.get("implementation_groups") or []}
            ]
            results = [ras.get(m["urn"], (None, None))[1] for m in members]
            in_target = scope is None or lv in scope
            in_audit = in_audit or (in_target and any(r is not None for r in results))
            status = _level_status(results) if in_target else "out_of_scope"
            counted = status != "out_of_scope"
            steps.append(
                {
                    "implementation_group": lv,
                    "status": status,
                    "passing": sum(r in PASS for r in results) if counted else None,
                    "total": len(results) if counted else None,
                }
            )
            if climbing and status == "met":
                level += 1
            elif climbing:
                climbing = False
                if in_target and status == "out_of_scope":
                    # A level below the target is missing from the audit.
                    level = None
                blocking = (
                    [
                        {
                            "id": ras[m["urn"]][0] if m["urn"] in ras else None,
                            "urn": m["urn"],
                            "ref_id": m.get("ref_id"),
                            "name": m.get("name"),
                            "result": ras.get(m["urn"], (None, None))[1],
                        }
                        for m, result in zip(members, results)
                        if result not in PASS
                    ]
                    if counted
                    else []
                )
        # Sections the audit does not reach, or with nothing tagged with a level.
        if not in_audit:
            continue
        node = section["node"] or {}
        out.append(
            {
                "urn": node.get("urn"),
                "ref_id": node.get("ref_id"),
                "name": node.get("name"),
                "level": level,
                "levels": steps,
                "blocking": blocking,
            }
        )
    section_levels = [s["level"] for s in out]
    return {
        # No section in the audit (none of its levels selected): nothing to tell.
        "level": None if None in section_levels else min(section_levels, default=None),
        "sections": out,
    }


def evaluate_staircases(ca, rules) -> tuple[dict, list]:
    """({ref_id: overall level}, [detail per rule]) for an audit's staircase rules."""
    from django.utils.translation import get_language

    from core.models import RequirementAssessment, RequirementNode

    rules = staircase_rules(rules)
    if not rules:
        return {}, []
    # Names in the request's language, as get_name_translated gives them.
    language = get_language()
    nodes = []
    for node in RequirementNode.objects.filter(framework_id=ca.framework_id).values(
        "urn",
        "parent_urn",
        "ref_id",
        "name",
        "assessable",
        "implementation_groups",
        "translations",
    ):
        translated = (node.pop("translations") or {}).get(language) or {}
        nodes.append({**node, "name": translated.get("name", node["name"])})
    selected = set(ca.selected_implementation_groups or [])
    in_scope = {
        n["urn"]
        for n in nodes
        if not selected or selected & set(n.get("implementation_groups") or [])
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
        levels = [str(level) for level in rule["staircase_levels"]]
        picked = [i for i, level in enumerate(levels) if level in selected]
        scope = set(levels[: max(picked) + 1] if picked else []) if selected else None
        result = compute_staircase(rule, nodes, ras, scope)
        if result["level"] is not None:
            values[rule["ref_id"]] = float(result["level"])
        details.append({"ref_id": rule["ref_id"], **result})
    return values, details
