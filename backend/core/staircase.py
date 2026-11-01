"""Staircase outcome rules (`kind: staircase` in a framework's outcomes_definition).

A level is reached only when every requirement of that level passes, and every
level below it is reached too (ASD Essential Eight, ASVS, CMMC style):

    - ref_id: maturity_level
      kind: staircase
      label: Maturity level
      levels: ['1', '2', '3']     # implementation group ref_ids, lowest first
      per: depth_1                # optional: a level per top-level node; omitted = one for the audit
      cumulative: false           # optional: level L also needs requirements tagged below L
      floor_label: Maturity Level Zero  # optional: name of level 0
      unit_label: mitigation strategies  # optional: what the units are called

Per unit and level, `progress` is [passing, total] and the status is `met` when
all pass (compliant or not applicable), `not_met` when one fails, `pending` when none fails but some are not assessed, `out_of_scope`
when the audit does not include them. A unit's level is the number of levels met
in a row from the lowest; the overall level is the lowest unit level. Only the
overall level is stored (`computed_values[ref_id]`, readable as `values.<ref_id>`);
the grid is computed on read.
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
        and rule.get("levels")
    ]


def expand_scope(outcomes_definition, selected) -> list:
    """A target level brings the levels below it: they are needed to tell
    which level is reached."""
    selected = list(selected or [])
    for rule in staircase_rules(outcomes_definition):
        levels = [str(level) for level in rule["levels"]]
        picked = [levels.index(g) for g in selected if g in levels]
        if picked:
            selected += [lv for lv in levels[: max(picked)] if lv not in selected]
    return selected


def staircase_errors(rule, known_groups) -> list[str]:
    levels = rule.get("levels")
    if not isinstance(levels, list) or not levels:
        return ["A staircase rule needs a non-empty list of levels"]
    errors = [
        f"Unknown implementation group '{level}'"
        for level in levels
        if str(level) not in known_groups
    ]
    if rule.get("per") not in (None, "depth_1"):
        errors.append("per must be 'depth_1' or left out")
    return errors


def _level_status(results: list) -> str:
    if not results or any(r is None for r in results):
        return "out_of_scope"
    if any(r in FAIL for r in results):
        return "not_met"
    if all(r in PASS for r in results):
        return "met"
    return "pending"


def compute_staircase(rule: dict, nodes: list[dict], ras: dict) -> dict:
    """nodes: the framework's requirement nodes (urn, parent_urn, ref_id, name,
    assessable, implementation_groups); ras: {requirement urn: (ra id, result)}
    for the audit's requirement assessments."""
    from core.utils import extract_node_id

    levels = [str(level) for level in rule["levels"]]
    parents = {n["urn"]: n.get("parent_urn") for n in nodes}

    def top(urn):
        seen = set()
        while parents.get(urn) in parents and urn not in seen:
            seen.add(urn)
            urn = parents[urn]
        return urn

    units: dict = {}
    if rule.get("per") == "depth_1":
        for n in nodes:
            if not n.get("parent_urn") or n.get("parent_urn") not in parents:
                units[n["urn"]] = {"node": n, "members": []}
    else:
        units[None] = {"node": None, "members": []}
    for n in nodes:
        if not n.get("assessable"):
            continue
        key = top(n["urn"]) if None not in units else None
        if key in units:
            units[key]["members"].append(n)

    out = []
    for unit in units.values():
        statuses, progress, level, blocking, climbing = {}, {}, 0, [], True
        for index, lv in enumerate(levels):
            wanted = set(levels[: index + 1]) if rule.get("cumulative") else {lv}
            members = [
                m
                for m in unit["members"]
                if wanted & {str(g) for g in m.get("implementation_groups") or []}
            ]
            results = [ras.get(m["urn"], (None, None))[1] for m in members]
            statuses[lv] = _level_status(results)
            progress[lv] = [sum(r in PASS for r in results), len(results)]
            if climbing and statuses[lv] == "met":
                level += 1
            elif climbing:
                climbing = False
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
                    if statuses[lv] != "out_of_scope"
                    else []
                )
        node = unit["node"] or {}
        out.append(
            {
                "node_id": extract_node_id(node["urn"]) if node else None,
                "ref_id": node.get("ref_id"),
                "name": node.get("name"),
                "level": level,
                "levels": statuses,
                "progress": progress,
                "blocking": blocking,
            }
        )
    out = [u for u in out if any(s != "out_of_scope" for s in u["levels"].values())]
    return {
        "level": min((u["level"] for u in out), default=0),
        "units": out,
    }


def evaluate_staircases(ca, rules) -> tuple[dict, list]:
    """({ref_id: overall level}, [detail per rule]) for an audit's staircase rules."""
    from core.models import RequirementAssessment, RequirementNode

    rules = staircase_rules(rules)
    if not rules:
        return {}, []
    nodes = list(
        RequirementNode.objects.filter(framework_id=ca.framework_id).values(
            "urn", "parent_urn", "ref_id", "name", "assessable", "implementation_groups"
        )
    )
    ras = {
        urn: (str(pk), result)
        for pk, urn, result in RequirementAssessment.objects.filter(
            compliance_assessment=ca
        ).values_list("id", "requirement__urn", "result")
    }
    values, details = {}, []
    for rule in rules:
        result = compute_staircase(rule, nodes, ras)
        values[rule["ref_id"]] = float(result["level"])
        details.append({"ref_id": rule["ref_id"], **result})
    return values, details
