"""CEL-based outcome evaluation for compliance assessments and quick forms."""

from __future__ import annotations

import re

import celpy
import celpy.celtypes as celtypes
import structlog

from core.quick_form_scoring import (
    aggregate_form,
    aggregate_page,
    clamp,
    normalize_form_aggregation,
    score_bounds,
)

logger = structlog.get_logger(__name__)


def _python_to_cel(value):
    """Recursively convert Python values to CEL types."""
    if isinstance(value, bool):
        return celtypes.BoolType(value)
    if isinstance(value, int):
        return celtypes.IntType(value)
    if isinstance(value, float):
        return celtypes.DoubleType(value)
    if isinstance(value, str):
        return celtypes.StringType(value)
    if isinstance(value, dict):
        return celtypes.MapType(
            {celtypes.StringType(k): _python_to_cel(v) for k, v in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return celtypes.ListType([_python_to_cel(item) for item in value])
    if value is None:
        return celtypes.BoolType(False)
    return celtypes.StringType(str(value))


def _build_answer_data(ca, in_scope_node_ids) -> dict[str, dict]:
    """Build per-question answer data for the CEL context.

    Returns a dict keyed by question node_id.
    """
    from core.models import Answer
    from core.utils import extract_node_id

    answers = (
        Answer.objects.filter(
            requirement_assessment__compliance_assessment=ca,
            requirement_assessment__requirement_id__in=in_scope_node_ids,
        )
        .select_related("question")
        .prefetch_related("selected_choices")
    )

    result: dict[str, dict] = {}
    for answer in answers:
        q = answer.question
        selected = list(answer.selected_choices.all())
        score = sum(
            (c.add_score or 0) * q.weight for c in selected if c.add_score is not None
        )
        entry = {
            "value": answer.value,
            "score": score,
            "selected_choices": [
                extract_node_id(c.urn) for c in selected if extract_node_id(c.urn)
            ],
            "weight": q.weight,
            "type": q.type,
        }
        q_node_id = extract_node_id(q.urn)
        if q_node_id:
            result[q_node_id] = entry
    return result


def _requirement_layers(ca, node, ra) -> dict:
    """A requirement's documentation and maturity scores on its own scale,
    counted as the audit's aggregates count it: -1 when it does not count (or
    the audit has no documentation score), N/A at the target when the audit
    anchors N/A, a missing documentation score at the bottom of the scale."""
    none = {"documentation_score": -1.0, "maturity_score": -1.0}
    if ca is None or not ra:
        return none
    low = node.get("min_score")
    low = ca.min_score if low is None else low
    high = node.get("max_score")
    high = ca.max_score if high is None else high
    if ra["result"] == "not_applicable":
        if not ca.anchor_na_to_target or low is None or high is None:
            return none
        implementation = documentation = ca.na_anchor_score(low, high)
    elif ra["is_scored"] and ra["score"] is not None:
        implementation = ra["score"]
        documentation = ra.get("documentation_score")
        if documentation is None:
            documentation = low or 0
    else:
        return none
    if not ca.show_documentation_score:
        return {"documentation_score": -1.0, "maturity_score": float(implementation)}
    return {
        "documentation_score": float(documentation),
        "maturity_score": (implementation + documentation) / 2,
    }


def _build_context_dict(
    in_scope,
    ra_rows,
    answer_data,
    max_score,
    computed_outcomes=None,
    ca=None,
) -> dict:
    """Build the raw context dict from in-scope nodes, RA rows, and answer data."""
    from core.utils import extract_node_id

    score_sum = 0
    score_max = 0
    answered_count = 0
    total_count = len(in_scope)
    requirements: dict[str, dict] = {}

    for node in in_scope:
        urn = node["urn"]
        node_id = extract_node_id(urn)
        ra = ra_rows.get(urn)
        score_max += max_score

        if ra and ra["is_scored"] and ra["result"] != "not_applicable":
            score_sum += ra["score"] or 0
            answered_count += 1
            entry = {
                "score": ra["score"] or 0,
                "max_score": max_score,
                "result": ra["result"],
                "status": ra["status"],
            }
        else:
            entry = {
                "score": 0,
                "max_score": max_score,
                "result": ra["result"] if ra else "not_assessed",
                "status": ra["status"] if ra else "to_do",
            }
        entry.update(_requirement_layers(ca, node, ra))
        entry["implementation_groups"] = list(node.get("implementation_groups") or [])

        if node_id:
            requirements[node_id] = entry

    ctx = {
        "assessment": {
            "score_sum": score_sum,
            "score_max": score_max,
            "answered_count": answered_count,
            "total_count": total_count,
            "selected_implementation_groups": list(
                (ca.selected_implementation_groups if ca else None) or []
            ),
        },
        "requirements": requirements,
        "answers": answer_data,
    }
    if computed_outcomes is not None:
        ctx["computed_outcomes"] = computed_outcomes
    else:
        ctx["computed_outcomes"] = {}
    return ctx


def build_cel_context(compliance_assessment) -> tuple[dict, set[str]]:
    """Build the evaluation context dict from a ComplianceAssessment.

    Returns (context_dict, hidden_urns) where hidden_urns contains URNs of
    requirements whose visibility_expression evaluated to false.
    Hidden URNs may include both assessable and non-assessable (splash screen) nodes.
    """
    from core.models import RequirementAssessment, RequirementNode
    from core.utils import extract_node_id

    ca = compliance_assessment
    framework = ca.framework

    # Query 1a: all assessable requirement nodes (for scoring context)
    assessable_nodes = list(
        RequirementNode.objects.filter(
            framework=framework,
            assessable=True,
        ).values(
            "id",
            "urn",
            "ref_id",
            "implementation_groups",
            "visibility_expression",
            "min_score",
            "max_score",
        )
    )

    # Query 1b: all non-assessable nodes that have a visibility_expression
    # (e.g. splash screen nodes) — needed for visibility evaluation only
    non_assessable_with_visibility = list(
        RequirementNode.objects.filter(
            framework=framework,
            assessable=False,
        )
        .exclude(visibility_expression__isnull=True)
        .exclude(visibility_expression="")
        .values("id", "urn", "ref_id", "implementation_groups", "visibility_expression")
    )

    # Implementation-groups filtering (Python-side for DB portability)
    selected_igs = (
        set(ca.selected_implementation_groups)
        if ca.selected_implementation_groups
        else None
    )
    if selected_igs:
        in_scope = [
            n
            for n in assessable_nodes
            if selected_igs & set(n["implementation_groups"] or [])
        ]
    else:
        in_scope = assessable_nodes

    in_scope_node_ids = [n["id"] for n in in_scope]

    # Query 2: all requirement assessments for in-scope nodes
    ra_rows = {
        row["requirement__urn"]: row
        for row in RequirementAssessment.objects.filter(
            compliance_assessment=ca,
            requirement_id__in=in_scope_node_ids,
        ).values(
            "requirement__urn",
            "score",
            "documentation_score",
            "result",
            "status",
            "is_scored",
        )
    }

    # Query 3: answer-level data for in-scope requirements
    answer_data = _build_answer_data(ca, in_scope_node_ids)

    max_score = ca.max_score or 100
    computed_outcomes = ca.computed_outcome if ca.computed_outcome else {}
    scale = {"ca": ca}

    # Phase 1: build initial context with assessable in-scope nodes
    initial_context = _build_context_dict(
        in_scope, ra_rows, answer_data, max_score, computed_outcomes, **scale
    )

    # Phase 2: evaluate visibility expressions (single-pass)
    # Evaluate on both assessable and non-assessable nodes
    all_visibility_nodes = in_scope + non_assessable_with_visibility
    hidden_urns: set[str] = set()
    has_visibility = any(n.get("visibility_expression") for n in all_visibility_nodes)

    if has_visibility:
        cel_context = {k: _python_to_cel(v) for k, v in initial_context.items()}
        env = celpy.Environment()
        for node in all_visibility_nodes:
            vis_expr = node.get("visibility_expression")
            if not vis_expr:
                continue
            try:
                ast = env.compile(vis_expr)
                prog = env.program(ast)
                result = prog.evaluate(cel_context)
                if not result:
                    hidden_urns.add(node["urn"])
            except Exception:
                logger.warning(
                    "cel_visibility_error",
                    expression=vis_expr,
                    requirement_urn=node["urn"],
                    compliance_assessment_id=str(ca.pk),
                    exc_info=True,
                )
                # Fail-open: keep requirement visible on error

    # Phase 3: rebuild context excluding hidden assessable requirements
    hidden_assessable = hidden_urns & {n["urn"] for n in in_scope}
    if hidden_assessable:
        visible_scope = [n for n in in_scope if n["urn"] not in hidden_assessable]
        visible_urns = {n["urn"] for n in visible_scope}
        visible_answer_data = {
            k: v
            for k, v in answer_data.items()
            if k in {extract_node_id(u) for u in visible_urns if extract_node_id(u)}
        }
        visible_ra_rows = {k: v for k, v in ra_rows.items() if k in visible_urns}
        visible_outcomes = (
            {k: v for k, v in computed_outcomes.items()} if computed_outcomes else {}
        )
        final_context = _build_context_dict(
            visible_scope,
            visible_ra_rows,
            visible_answer_data,
            max_score,
            visible_outcomes,
            **scale,
        )
        final_context["hidden_requirements"] = [
            extract_node_id(u) for u in hidden_urns if extract_node_id(u)
        ]
    else:
        final_context = initial_context
        final_context["hidden_requirements"] = [
            extract_node_id(u) for u in hidden_urns if extract_node_id(u)
        ]

    return final_context, hidden_urns


_SCORE_LAYERS = ("implementation_score", "documentation_score", "maturity_score")


def _layers(scores: dict) -> dict:
    """Score layers for CEL: -1 when nothing is scored, as the global score."""
    return {
        layer: -1.0
        if scores.get(layer) is None or scores.get(layer) == -1
        else float(scores[layer])
        for layer in _SCORE_LAYERS
    }


def _requirement_maturity(ca, ra) -> float:
    """requirements[k].maturity_score of a requirement assessment."""
    requirement = ra.requirement
    return _requirement_layers(
        ca,
        {"min_score": requirement.min_score, "max_score": requirement.max_score},
        {
            "result": ra.result,
            "is_scored": ra.is_scored,
            "score": ra.score,
            "documentation_score": ra.documentation_score,
        },
    )["maturity_score"]


def _subset_scores(ca, ras) -> dict:
    """A subset's scores, and what level criteria check on its requirements:
    its N/A count and its lowest requirement maturity (-1 when one does not
    count, or when it has none). Rules read them instead of looping over
    `requirements`, which is slow in CEL."""
    scores = ca.get_scores_for(ras)
    return {
        **_layers(scores),
        "scored_count": scores["scored_count"],
        "total_count": len(ras),
        "not_applicable_count": sum(ra.result == "not_applicable" for ra in ras),
        "min_maturity_score": min(
            (_requirement_maturity(ca, ra) for ra in ras), default=-1.0
        ),
    }


def _group_scores(ca, framework, ras) -> dict:
    groups = {}
    for group in framework.implementation_groups_definition or []:
        ref_id = (group or {}).get("ref_id")
        if ref_id:
            groups[ref_id] = _subset_scores(
                ca,
                [
                    ra
                    for ra in ras
                    if ref_id in (ra.requirement.implementation_groups or [])
                ],
            )
    return groups


def _node_depths(parents: dict) -> dict:
    """Depth of each node from its parent links, the top level being 1."""
    depths: dict = {}

    def depth(urn, seen=()):
        if urn not in depths:
            parent = parents.get(urn)
            depths[urn] = (
                depth(parent, (*seen, urn))
                if parent in parents and parent not in seen
                else 0
            ) + 1
        return depths[urn]

    for urn in parents:
        depth(urn)
    return depths


def _section_scores(ca, framework, ras) -> dict:
    from core.models import RequirementNode
    from core.utils import extract_node_id

    nodes = {
        row["urn"]: row
        for row in RequirementNode.objects.filter(framework=framework).values(
            "urn", "parent_urn", "ref_id"
        )
    }
    depths = _node_depths({urn: row["parent_urn"] for urn, row in nodes.items()})
    members: dict[str, list] = {
        row["parent_urn"]: [] for row in nodes.values() if row["parent_urn"] in nodes
    }
    for ra in ras:
        parent, seen = ra.requirement.parent_urn, set()
        while parent in nodes and parent not in seen:
            seen.add(parent)
            members.setdefault(parent, []).append(ra)
            parent = nodes[parent]["parent_urn"]
    sections = {}
    for urn, section_ras in members.items():
        node_id = extract_node_id(urn)
        if node_id:
            sections[node_id] = {
                **_subset_scores(ca, section_ras),
                "depth": depths[urn],
                "ref_id": nodes[urn]["ref_id"] or "",
            }
    return sections


def _add_scores(context: dict, ca, framework, rules) -> None:
    """The audit's scores, unrounded, as its page computes them. Section and
    group scores only when a rule reads them, over the same requirements: those
    in the audit's scope. Every group and section is present; one without
    requirements in scope scores -1."""
    from core.models import RequirementAssessment

    ras = list(
        RequirementAssessment.objects.filter(
            compliance_assessment=ca, requirement__assessable=True
        ).select_related("requirement")
    )
    for ra in ras:
        ra.compliance_assessment = ca
    context["assessment"].update(
        {
            **_layers(ca.get_global_score(prefetched_requirements=ras)),
            "target_score": float(
                ca.target_score if ca.target_score is not None else ca.max_score or 0
            ),
        }
    )
    expressions = " ".join(str(rule.get("expression") or "") for rule in rules)
    selected = set(ca.selected_implementation_groups or [])
    in_scope = [
        ra
        for ra in ras
        if not selected or selected & set(ra.requirement.implementation_groups or [])
    ]
    if re.search(r"\bgroups\b", expressions):
        context["groups"] = _group_scores(ca, framework, in_scope)
    if re.search(r"\bsections\b", expressions):
        context["sections"] = _section_scores(ca, framework, in_scope)


def rule_applies(rule: dict, selected_groups) -> bool:
    """A rule limited to implementation groups applies when the audit's scope
    includes one of them, or covers the whole framework, as for requirements."""
    groups = (rule or {}).get("implementation_groups") or []
    return not groups or not selected_groups or bool(set(groups) & set(selected_groups))


def applicable_rules(framework, selected_groups) -> list[dict]:
    """The framework's outcome rules that apply to an audit's scope."""
    return [
        rule
        for rule in framework.outcomes_definition or []
        if rule_applies(rule, selected_groups)
    ]


def evaluate_outcomes(compliance_assessment) -> None:
    """Evaluate the framework's outcome rules that apply to the audit's scope and
    store the yes/no rules that fired and the numbers computed."""
    from core.models import ComplianceAssessment, Framework

    ca = compliance_assessment
    # Refresh framework from DB to pick up any changes to outcomes_definition
    # (the FK cache may be stale when called from deferred on_commit hooks)
    framework = Framework.objects.get(pk=ca.framework_id)
    rules = applicable_rules(framework, ca.selected_implementation_groups)

    computed = values = None
    if rules:
        context, _hidden = build_cel_context(ca)
        _add_scores(context, ca, framework, rules)
        computed, values = _evaluate_rules(
            celpy.Environment(),
            rules,
            context,
            compliance_assessment_id=str(ca.pk),
        )
        if not any(is_numeric_rule(rule) for rule in rules):
            values = None

    if ca.computed_outcome != computed or ca.computed_values != values:
        ca.computed_outcome = computed
        ca.computed_values = values
        ComplianceAssessment.objects.filter(pk=ca.pk).update(
            computed_outcome=computed, computed_values=values
        )


# ---------------------------------------------------------------------------
# Quick forms
# ---------------------------------------------------------------------------


def _question_max_score(question) -> int:
    """Best achievable score on a choice question: the top choice for a
    unique choice, every positive choice for a multiple choice."""
    scores = [
        (c.add_score or 0) * question.weight
        for c in question.choices.all()
        if c.add_score is not None
    ]
    if not scores:
        return 0
    if question.type == "multiple_choice":
        return sum(s for s in scores if s > 0)
    return max(max(scores), 0)


def _quick_form_snapshot(response) -> dict:
    """One pass over the form's pages, questions and answers of *response*.

    Returns everything the context builder and the progress/score
    computation need, keyed to avoid a second round of queries.
    """
    from core.models import Answer, Question, QuickFormPage
    from core.utils import _build_answer_context, _is_question_visible

    pages = list(
        QuickFormPage.objects.filter(quick_form_id=response.quick_form_id)
        .order_by("order")
        .values("id", "urn", "visibility_expression", "aggregation")
    )
    questions = list(
        Question.objects.filter(page__quick_form_id=response.quick_form_id)
        .select_related("page")
        .prefetch_related("choices")
        .order_by("page__order", "order")
    )
    answers = list(
        Answer.objects.filter(response=response)
        .select_related("question")
        .prefetch_related("selected_choices")
    )
    (
        _selected_pks_by_qid,
        answers_by_urn,
        questions_by_urn,
        has_answer_by_qid,
    ) = _build_answer_context(questions, answers)
    answers_by_qid = {a.question_id: a for a in answers}

    per_question = {}
    for question in questions:
        visible = _is_question_visible(question, answers_by_urn, questions_by_urn)
        answer = answers_by_qid.get(question.id)
        selected = list(answer.selected_choices.all()) if answer else []
        score = sum(
            (c.add_score or 0) * question.weight
            for c in selected
            if c.add_score is not None
        )
        per_question[question.id] = {
            "question": question,
            "page_id": question.page_id,
            "visible": visible,
            "answered": bool(has_answer_by_qid.get(question.id)),
            "answer": answer,
            "selected": selected,
            "score": score,
            "max_score": _question_max_score(question),
            "scorable": question.type in ("unique_choice", "multiple_choice")
            and any(c.add_score is not None for c in question.choices.all()),
        }
    form = response.quick_form
    return {
        "pages": pages,
        "per_question": per_question,
        "aggregation": form.score_aggregation,
        "bounds": form.score_bounds,
    }


def _quick_form_context(snapshot, hidden_page_ids, computed_outcomes) -> dict:
    """Build the CEL context for a quick form response, excluding questions
    that sit on hidden pages or are hidden by depends_on."""
    from core.utils import extract_node_id

    answers: dict[str, dict] = {}
    pages: dict[str, dict] = {}
    page_stats = {
        p["id"]: {"answered_count": 0, "total_count": 0, "required_missing": 0}
        for p in snapshot["pages"]
    }
    score_sum = 0
    score_max = 0
    answered_count = 0
    total_count = 0
    required_missing = 0
    scorable_by_page: dict = {p["id"]: [] for p in snapshot["pages"]}

    for entry in snapshot["per_question"].values():
        if entry["page_id"] in hidden_page_ids or not entry["visible"]:
            continue
        question = entry["question"]
        stats = page_stats[entry["page_id"]]
        if entry["scorable"]:
            scorable_by_page[entry["page_id"]].append(
                {
                    "score": entry["score"],
                    "max_score": entry["max_score"],
                    "weight": question.weight,
                    "answered": entry["answered"],
                }
            )
        stats["total_count"] += 1
        total_count += 1
        if entry["answered"]:
            stats["answered_count"] += 1
            answered_count += 1
        elif question.required:
            stats["required_missing"] += 1
            required_missing += 1
        if entry["scorable"]:
            score_max += entry["max_score"]
            if entry["answered"]:
                score_sum += entry["score"]
        answer = entry["answer"]
        q_node_id = extract_node_id(question.urn)
        if q_node_id:
            answers[q_node_id] = {
                "value": answer.value if answer else None,
                "score": entry["score"],
                "selected_choices": [
                    extract_node_id(c.urn)
                    for c in entry["selected"]
                    if extract_node_id(c.urn)
                ],
                "weight": question.weight,
                "type": question.type,
                "answered": entry["answered"],
            }

    page_results = []
    for page in snapshot["pages"]:
        result = aggregate_page(scorable_by_page[page["id"]], page.get("aggregation"))
        if result is not None:
            page_results.append(result)
        node_id = extract_node_id(page["urn"])
        if not node_id:
            continue
        stats = page_stats[page["id"]]
        pages[node_id] = {
            "visible": page["id"] not in hidden_page_ids,
            "answered_count": stats["answered_count"],
            "total_count": stats["total_count"],
            "score": result["score"] if result else 0.0,
            "score_max": result["score_max"] if result else 0.0,
        }

    items = [item for page_items in scorable_by_page.values() for item in page_items]
    score = clamp(
        aggregate_form(items, page_results, snapshot["aggregation"]),
        snapshot["bounds"],
    )

    return {
        "response": {
            "score": score,
            "score_sum": score_sum,
            "score_max": score_max,
            "answered_count": answered_count,
            "total_count": total_count,
            "complete": required_missing == 0,
            "scored_complete": all(item["answered"] for item in items),
        },
        "pages": pages,
        "answers": answers,
        "computed_outcomes": computed_outcomes or {},
    }


def _quick_form_score(context) -> float | None:
    """The stored score: the context's aggregated score to two decimals, so an
    average reads 2.4 rather than 2. None until the response is complete."""
    score = context["response"]["score"]
    if not context["response"]["complete"] or score is None:
        return None
    return round(score, 2)


_PROBE_VALUE_BY_TYPE = {
    "boolean": False,
    "number": 0,
    "text": "",
    "date": "",
    "unique_choice": "",
    "multiple_choice": "",
}


RULE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

RULE_ID_MESSAGES = {
    "outcomeRuleIdRequired": "needs an ID",
    "outcomeRuleIdInvalid": "ID must use letters, digits and _, not starting with a digit",
    "outcomeRuleIdDuplicate": "ID is already used by another rule",
}


def outcome_rule_id_errors(rules) -> list[dict]:
    """{index, ref_id, error} per outcome rule whose ref_id is missing, not a
    CEL name, or taken by an earlier rule. Results are keyed by ref_id and a
    number rule is read as `values.<ref_id>`: a rule without one never runs,
    a duplicate hides the other, and a hyphen reads as a minus."""
    errors, seen = [], set()
    for index, rule in enumerate(rules or []):
        ref_id = str((rule or {}).get("ref_id") or "").strip()
        if not ref_id:
            code = "outcomeRuleIdRequired"
        elif not RULE_ID.match(ref_id):
            code = "outcomeRuleIdInvalid"
        elif ref_id in seen:
            code = "outcomeRuleIdDuplicate"
        else:
            code = None
        if code:
            errors.append({"index": index, "ref_id": ref_id, "error": code})
        seen.add(ref_id)
    return errors


def _rule_id_problems(rules) -> list[dict]:
    return [
        {
            "where": "outcome",
            "ref_id": e["ref_id"] or f"#{e['index'] + 1}",
            "expression": str((rules[e["index"]] or {}).get("expression") or ""),
            "error": e["error"],
        }
        for e in outcome_rule_id_errors(rules)
    ]


def is_numeric_rule(rule: dict) -> bool:
    return (rule or {}).get("kind") == "number"


def _as_number(result) -> float | None:
    """A CEL result as a float, or None when it is not a number. Booleans are
    ints in Python, so they are ruled out first."""
    if isinstance(result, (bool, celtypes.BoolType)):
        return None
    if isinstance(result, (int, float)):
        return float(result)
    return None


_NOT_PASSED_ON = ("expression", "ref_id", "implementation_groups")


def _evaluate_rules(env, rules, context: dict, **log_fields):
    """Run outcome rules against `context`, in their order.

    Number rules (`kind: number`) run first, each seeing the values computed
    before it as `values.<ref_id>`; the yes/no rules then see them all, and
    each sees the yes/no rules above it that fired as `computed_outcomes`.
    Returns (fired, values): the classifications that fired, keyed by ref_id
    with their pass-through attributes, and {ref_id: float}. Fail-open per rule:
    an expression error or a non-number result is logged and skipped.
    """
    values: dict[str, float] = {}
    fired: dict[str, dict] = {}
    rules = [r for r in rules or [] if r.get("expression") and r.get("ref_id")]
    base = {
        k: _python_to_cel(v)
        for k, v in context.items()
        if k not in ("values", "computed_outcomes")
    }

    def run(rule):
        return env.program(env.compile(rule["expression"])).evaluate(
            {
                **base,
                "values": _python_to_cel(values),
                "computed_outcomes": _python_to_cel(fired),
            }
        )

    for rule in [r for r in rules if is_numeric_rule(r)]:
        try:
            result = run(rule)
        except Exception:
            logger.warning(
                "cel_value_error",
                expression=rule["expression"],
                rule=rule["ref_id"],
                exc_info=True,
                **log_fields,
            )
            continue
        number = _as_number(result)
        if number is None:
            logger.warning(
                "cel_value_not_a_number",
                expression=rule["expression"],
                rule=rule["ref_id"],
                **log_fields,
            )
            continue
        values[rule["ref_id"]] = number

    for rule in [r for r in rules if not is_numeric_rule(r)]:
        try:
            if run(rule):
                fired[rule["ref_id"]] = {
                    k: v for k, v in rule.items() if k not in _NOT_PASSED_ON
                }
        except Exception:
            logger.warning(
                "cel_evaluation_error",
                expression=rule["expression"],
                rule=rule["ref_id"],
                exc_info=True,
                **log_fields,
            )
    return fired, values


def _quick_form_probe(quick_form: dict) -> dict:
    """A context with the real shape of `quick_form` but empty values.

    Evaluating a rule against it proves the expression compiles, only touches
    roots the quick-form evaluator actually provides, and only indexes page and
    question node_ids that exist — the three ways an outcome rule silently never
    fires at runtime.
    """
    from core.utils import extract_node_id

    pages, answers = {}, {}
    for page in quick_form.get("pages") or []:
        node_id = extract_node_id(str(page.get("urn") or ""))
        if node_id:
            pages[node_id] = {
                "visible": True,
                "answered_count": 0,
                "total_count": 0,
                "score": 0.0,
                "score_max": 0.0,
            }
        for q_urn, question in (page.get("questions") or {}).items():
            q_node_id = extract_node_id(str(q_urn))
            if not q_node_id:
                continue
            q_type = str((question or {}).get("type") or "text")
            answers[q_node_id] = {
                "value": _PROBE_VALUE_BY_TYPE.get(q_type, ""),
                "score": 0,
                "selected_choices": [],
                "weight": int((question or {}).get("weight") or 1),
                "type": q_type,
                "answered": False,
            }
    return {
        "response": {
            "score": 0.0,
            "score_sum": 0,
            "score_max": 0,
            "answered_count": 0,
            "total_count": 0,
            "complete": False,
            "scored_complete": False,
        },
        "pages": pages,
        "answers": answers,
        "computed_outcomes": {
            str(rule.get("ref_id")): {}
            for rule in quick_form.get("outcomes_definition") or []
            if rule.get("ref_id") and not is_numeric_rule(rule)
        },
        "values": {
            str(rule.get("ref_id")): 1.0
            for rule in quick_form.get("outcomes_definition") or []
            if rule.get("ref_id") and is_numeric_rule(rule)
        },
        "hidden_pages": [],
    }


_STRINGS = re.compile(r"""\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'""")
_ROOT = re.compile(r"(?<![\w.])([A-Za-z_]\w*)\s*[.\[]")
_SINGULAR = {
    "pages": "page",
    "answers": "answer",
    "requirements": "requirement",
    "sections": "section",
    "groups": "implementation group",
}


def _explain(expression, error, context, scopes, container) -> str:
    """Why `expression` failed against `context`, for its author.

    Built from the expression and the names the context offers, never from the
    exception's text: that reaches API responses, and must not carry internals.
    """
    if isinstance(error, celpy.CELParseError):
        return "Syntax error in this expression"
    for scope in scopes:
        for ref in re.findall(rf"""\b{scope}\[\s*["']([^"']*)["']\s*\]""", expression):
            if ref not in (context.get(scope) or {}):
                known = ", ".join(sorted(context.get(scope) or {})) or "none"
                return (
                    f"No {_SINGULAR[scope]} '{ref}' in this {container}. Known: {known}"
                )[:300]
    if "values" in context:
        for name in re.findall(r"\bvalues\.(\w+)", expression):
            if name not in context["values"]:
                return (
                    f"No number rule '{name}' above this one: a rule reads only "
                    "the number rules listed before it"
                )
    for root in _ROOT.findall(_STRINGS.sub('""', expression)):
        if root not in context:
            available = ", ".join(sorted(context))
            return f"Unknown name '{root}'. Available: {available}"[:300]
    return f"This expression cannot be evaluated against this {container}'s data"


_SUBSET_PROBE = {
    "implementation_score": 0.0,
    "documentation_score": 0.0,
    "maturity_score": 0.0,
    "scored_count": 0,
    "total_count": 0,
    "not_applicable_count": 0,
    "min_maturity_score": 0.0,
}

# Computed only when outcome rules run, never for visibility.
RULE_ONLY_ASSESSMENT_FIELDS = (*_SCORE_LAYERS, "target_score")


def _framework_probe(framework: dict) -> dict:
    """A context with the real shape of a framework's audits but empty values:
    every assessable requirement, section, group and question, so an id that
    exists is never flagged and one that does not always is."""
    from core.utils import extract_node_id

    nodes = framework.get("requirement_nodes") or []
    parents = {str(node.get("parent_urn") or "") for node in nodes}
    depths = _node_depths(
        {str(node.get("urn") or ""): node.get("parent_urn") for node in nodes}
    )
    requirements, sections, answers = {}, {}, {}
    for node in nodes:
        urn = str(node.get("urn") or "")
        node_id = extract_node_id(urn)
        if node_id and node.get("assessable"):
            requirements[node_id] = {
                "score": 0,
                "max_score": 100,
                "result": "not_assessed",
                "status": "to_do",
                "documentation_score": 0.0,
                "maturity_score": 0.0,
                "implementation_groups": [],
            }
        if node_id and urn in parents:
            sections[node_id] = {
                **_SUBSET_PROBE,
                "depth": depths[urn],
                "ref_id": str(node.get("ref_id") or ""),
            }
        for q_urn, question in (node.get("questions") or {}).items():
            q_node_id = extract_node_id(str(q_urn))
            if not q_node_id:
                continue
            q_type = str((question or {}).get("type") or "text")
            answers[q_node_id] = {
                "value": _PROBE_VALUE_BY_TYPE.get(q_type, ""),
                "score": 0,
                "selected_choices": [],
                "weight": int((question or {}).get("weight") or 1),
                "type": q_type,
            }
    rules = framework.get("outcomes_definition") or []
    return {
        "assessment": {
            "score_sum": 0,
            "score_max": 0,
            "answered_count": 0,
            "total_count": 0,
            "selected_implementation_groups": [],
            **{field: 0.0 for field in RULE_ONLY_ASSESSMENT_FIELDS},
        },
        "requirements": requirements,
        "sections": sections,
        "groups": {
            str(group.get("ref_id")): dict(_SUBSET_PROBE)
            for group in framework.get("implementation_groups_definition") or []
            if (group or {}).get("ref_id")
        },
        "answers": answers,
        "values": {
            str(rule.get("ref_id")): 1.0
            for rule in rules
            if rule.get("ref_id") and is_numeric_rule(rule)
        },
        "computed_outcomes": {
            str(rule.get("ref_id")): {}
            for rule in rules
            if rule.get("ref_id") and not is_numeric_rule(rule)
        },
        "hidden_requirements": [],
    }


def _framework_visibility_probe(probe: dict) -> dict:
    """Visibility runs before the rules and the hidden requirements are known,
    and without the scores, as at runtime."""
    context = {
        k: v
        for k, v in probe.items()
        if k not in ("hidden_requirements", "values", "sections", "groups")
    }
    context["assessment"] = {
        k: v
        for k, v in probe["assessment"].items()
        if k not in RULE_ONLY_ASSESSMENT_FIELDS
    }
    return context


_OUTCOME_REF = re.compile(
    r"""["'](\w+)["']\s+in\s+computed_outcomes\b"""
    r"""|\bcomputed_outcomes\s*(?:\.\s*(\w+)\b(?!\s*\()|\[\s*["'](\w+)["']\s*\])"""
)


def _check_rules(rules, probe: dict, check, error) -> None:
    """Check outcome rules in the order they run: a number rule reads the
    number rules above it, a yes/no rule every number rule and the yes/no
    rules above it."""
    for rule in rules:
        kind = rule.get("kind")
        if kind not in (None, "", "boolean", "number"):
            error(
                str(rule.get("ref_id") or ""),
                str(rule.get("expression") or ""),
                f"Unknown rule kind '{kind}': use 'number' or leave it empty",
            )
    values: dict[str, float] = {}
    for rule in [r for r in rules if is_numeric_rule(r)]:
        ref_id = str(rule.get("ref_id") or "")
        expression = str(rule.get("expression") or "")
        result = check(
            ref_id, expression, {**probe, "values": values, "computed_outcomes": {}}
        )
        if expression and result is not None and _as_number(result) is None:
            error(ref_id, expression, "A numeric rule must return a number")
        values = {**values, ref_id: 1.0}
    above: dict[str, dict] = {}
    for rule in [r for r in rules if not is_numeric_rule(r)]:
        ref_id = str(rule.get("ref_id") or "")
        expression = str(rule.get("expression") or "")
        named = {
            name for match in _OUTCOME_REF.findall(expression) for name in match if name
        }
        if missing := sorted(named - set(above)):
            error(
                ref_id,
                expression,
                f"No yes/no rule '{missing[0]}' above this one: a rule reads "
                "only the yes/no rules listed before it",
            )
        else:
            check(
                ref_id,
                expression,
                {**probe, "values": values, "computed_outcomes": above},
            )
        above = {**above, ref_id: {}}


def validate_framework_expressions(framework: dict) -> list[dict]:
    """Check every requirement visibility expression and outcome rule of a
    framework, as `validate_quick_form_expressions` does for forms: an
    expression against the wrong context, or naming an id that does not exist,
    compiles but raises when an audit is evaluated, where it is only logged."""
    probe = _framework_probe(framework)
    env = celpy.Environment()
    rules = framework.get("outcomes_definition") or []
    errors = _rule_id_problems(rules)

    def _error(where, ref_id, expression, message):
        errors.append(
            {
                "where": where,
                "ref_id": ref_id,
                "expression": expression,
                "error": message,
            }
        )

    def _check(where, ref_id, expression, context):
        if not expression:
            return None
        try:
            return env.program(env.compile(expression)).evaluate(
                {k: _python_to_cel(v) for k, v in context.items()}
            )
        except Exception as e:
            _error(
                where,
                ref_id,
                expression,
                _explain(
                    expression,
                    e,
                    context,
                    ("requirements", "sections", "groups", "answers"),
                    "framework",
                ),
            )
            return None

    visibility_probe = _framework_visibility_probe(probe)
    for node in framework.get("requirement_nodes") or []:
        _check(
            "requirement_visibility",
            str(node.get("ref_id") or node.get("urn") or ""),
            str(node.get("visibility_expression") or ""),
            visibility_probe,
        )

    known_groups = set(probe["groups"])
    for rule in rules:
        groups = rule.get("implementation_groups")
        if groups is None:
            continue
        if not isinstance(groups, list) or not all(isinstance(g, str) for g in groups):
            unknown = "implementation_groups must be a list of group ids"
        elif unknown_ids := [g for g in groups if g not in known_groups]:
            unknown = f"Unknown implementation group '{unknown_ids[0]}'"
        else:
            continue
        _error(
            "outcome",
            str(rule.get("ref_id") or ""),
            str(rule.get("expression") or ""),
            unknown,
        )

    _check_rules(
        rules,
        probe,
        lambda ref_id, expression, context: _check(
            "outcome", ref_id, expression, context
        ),
        lambda ref_id, expression, message: _error(
            "outcome", ref_id, expression, message
        ),
    )
    return errors


def validate_quick_form_expressions(quick_form: dict) -> list[dict]:
    """Check every page visibility expression and outcome rule of a quick form.

    Returns a list of {where, ref_id, expression, error}; empty means every
    expression is evaluable. Compilation alone is not enough — the common
    mistake is a valid expression against the wrong context (`assessment.*`
    instead of `response.*`), which raises at evaluation and is swallowed there.
    """
    raw_probe = _quick_form_probe(quick_form)
    env = celpy.Environment()
    errors = _rule_id_problems(quick_form.get("outcomes_definition") or [])

    def _error(where, ref_id, expression, message):
        errors.append(
            {
                "where": where,
                "ref_id": ref_id,
                "expression": expression,
                "error": message,
            }
        )

    def _check(where, ref_id, expression, context=None):
        if not expression:
            return None
        context = raw_probe if context is None else context
        try:
            return env.program(env.compile(expression)).evaluate(
                {k: _python_to_cel(v) for k, v in context.items()}
            )
        except Exception as e:
            _error(
                where,
                ref_id,
                expression,
                _explain(expression, e, context, ("pages", "answers"), "form"),
            )
            return None

    from core.object_references import subject_question_error

    if (subject_error := subject_question_error(quick_form)) is not None:
        _error(
            "subject_question",
            str(quick_form.get("subject_question_urn") or ""),
            "",
            subject_error,
        )

    # Visibility is resolved before any rule runs, so it cannot read `values`.
    visibility_probe = {k: v for k, v in raw_probe.items() if k != "values"}
    for page in quick_form.get("pages") or []:
        _check(
            "page_visibility",
            str(page.get("ref_id") or page.get("urn") or ""),
            str(page.get("visibility_expression") or ""),
            visibility_probe,
        )
    _check_rules(
        quick_form.get("outcomes_definition") or [],
        raw_probe,
        lambda ref_id, expression, context: _check(
            "outcome", ref_id, expression, context
        ),
        lambda ref_id, expression, message: _error(
            "outcome", ref_id, expression, message
        ),
    )
    return errors


def _sync_outcome_rows(response, computed: dict) -> None:
    """Reconcile QuickFormOutcome rows against the outcomes that currently fire.

    Rows are matched by ref_id and left in place when they still fire, so
    `fired_at` records when a classification was first reached rather than when
    it was last recomputed.
    """
    from core.models import QuickFormOutcome

    existing = {row.ref_id: row for row in response.outcomes.all()}
    stale = set(existing) - set(computed)
    if stale:
        response.outcomes.filter(ref_id__in=stale).delete()

    to_create = []
    for ref_id, payload in (computed or {}).items():
        label = str(payload.get("label") or payload.get("annotation") or ref_id)[:255]
        color = str(payload.get("color") or "")[:50]
        row = existing.get(ref_id)
        if row is None:
            to_create.append(
                QuickFormOutcome(
                    response=response,
                    ref_id=ref_id,
                    label=label,
                    color=color,
                    folder_id=response.folder_id,
                )
            )
        elif row.label != label or row.color != color:
            row.label = label
            row.color = color
            row.save(update_fields=["label", "color"])
    if to_create:
        QuickFormOutcome.objects.bulk_create(to_create, ignore_conflicts=True)


def evaluate_quick_form_document(quick_form: dict, answers: dict | None = None) -> dict:
    """Evaluate a quick form straight from an editor document, against trial answers.

    Nothing is queried and nothing is saved: an author previewing a draft has no
    response, and may be looking at pages that do not exist live yet. The rules are
    the real ones — `_is_question_visible` already accepts plain dicts, and page
    visibility and outcomes go through the same CEL programs as a filled response —
    so a preview cannot quietly disagree with what respondents will get.
    """
    from core.utils import _is_question_visible, extract_node_id

    answers = answers or {}
    pages = []
    questions_by_urn = {}
    for page in quick_form.get("pages") or []:
        entries = []
        for urn, question in (page.get("questions") or {}).items():
            entry = {**(question or {}), "urn": urn}
            questions_by_urn[urn] = entry
            entries.append(entry)
        pages.append({**page, "_questions": entries})

    def selected_of(entry):
        q_type = entry.get("type")
        if q_type not in ("unique_choice", "multiple_choice"):
            return []
        value = answers.get(entry["urn"])
        if q_type == "multiple_choice":
            return [v for v in (value or []) if v]
        return [value] if value else []

    def is_answered(entry):
        q_type = entry.get("type")
        if q_type in ("unique_choice", "multiple_choice"):
            return bool(selected_of(entry))
        if q_type == "file":
            # Previews carry no uploads; treat a file question as still to answer.
            return False
        value = answers.get(entry["urn"])
        return value is not None and value != ""

    def score_of(entry):
        weight = int(entry.get("weight") or 1)
        chosen = set(selected_of(entry))
        return sum(
            int(choice.get("add_score") or 0) * weight
            for choice in entry.get("choices") or []
            if choice.get("urn") in chosen and choice.get("add_score") is not None
        )

    def max_score_of(entry):
        weight = int(entry.get("weight") or 1)
        scores = [
            int(choice.get("add_score") or 0) * weight
            for choice in entry.get("choices") or []
            if choice.get("add_score") is not None
        ]
        if not scores:
            return 0
        if entry.get("type") == "multiple_choice":
            return sum(value for value in scores if value > 0)
        return max(max(scores), 0)

    def build_context(hidden_page_urns, computed_outcomes):
        answer_ctx, page_ctx = {}, {}
        # `weight` is the mean's divisor: the summed weight of the questions that
        # actually scored, matching `_quick_form_score`. Dividing by `total` instead
        # counted text and file questions and made the preview disagree with the live
        # response on any form that mixes scorable and non-scorable questions.
        totals = {
            "sum": 0,
            "max": 0,
            "answered": 0,
            "total": 0,
            "missing": 0,
            "weight": 0,
        }
        page_results = []
        items = []
        for page in pages:
            node_id = extract_node_id(str(page.get("urn") or "")) or page.get("ref_id")
            stats = {"answered_count": 0, "total_count": 0}
            page_items = []
            for entry in page["_questions"]:
                if page.get("urn") in hidden_page_urns:
                    continue
                if not _is_question_visible(entry, answers, questions_by_urn):
                    continue
                answered = is_answered(entry)
                stats["total_count"] += 1
                totals["total"] += 1
                if answered:
                    stats["answered_count"] += 1
                    totals["answered"] += 1
                elif entry.get("required", True) is not False:
                    totals["missing"] += 1
                if entry.get("type") in ("unique_choice", "multiple_choice"):
                    totals["max"] += max_score_of(entry)
                    if answered:
                        totals["sum"] += score_of(entry)
                        totals["weight"] += int(entry.get("weight") or 1)
                    if any(
                        c.get("add_score") is not None
                        for c in entry.get("choices") or []
                    ):
                        page_items.append(
                            {
                                "score": score_of(entry),
                                "max_score": max_score_of(entry),
                                "weight": int(entry.get("weight") or 1),
                                "answered": answered,
                            }
                        )
                q_node_id = extract_node_id(entry["urn"])
                if q_node_id:
                    answer_ctx[q_node_id] = {
                        "value": answers.get(entry["urn"]),
                        "score": score_of(entry),
                        "selected_choices": [
                            extract_node_id(u)
                            for u in selected_of(entry)
                            if extract_node_id(u)
                        ],
                        "weight": int(entry.get("weight") or 1),
                        "type": entry.get("type") or "text",
                        "answered": answered,
                    }
            result = aggregate_page(page_items, page.get("aggregation"))
            if result is not None:
                page_results.append(result)
            items.extend(page_items)
            if node_id:
                page_ctx[node_id] = {
                    "visible": page.get("urn") not in hidden_page_urns,
                    **stats,
                    "score": result["score"] if result else 0.0,
                    "score_max": result["score_max"] if result else 0.0,
                }
        definition = quick_form.get("scores_definition") or {}
        score = clamp(
            aggregate_form(
                items,
                page_results,
                normalize_form_aggregation(definition.get("aggregation")),
            ),
            score_bounds(definition),
        )
        return {
            "response": {
                "score": score,
                "score_sum": totals["sum"],
                "score_max": totals["max"],
                "score_weight": totals["weight"],
                "answered_count": totals["answered"],
                "total_count": totals["total"],
                "complete": totals["missing"] == 0,
                "scored_complete": all(item["answered"] for item in items),
            },
            "pages": page_ctx,
            "answers": answer_ctx,
            "computed_outcomes": computed_outcomes or {},
        }

    env = celpy.Environment()
    initial = build_context(set(), {})
    hidden = set()
    cel_context = {k: _python_to_cel(v) for k, v in initial.items()}
    for page in pages:
        expression = page.get("visibility_expression")
        if not expression:
            continue
        try:
            if not env.program(env.compile(expression)).evaluate(cel_context):
                hidden.add(page.get("urn"))
        except Exception:
            # Same fail-open as a real evaluation; the author sees the page.
            logger.warning("preview_visibility_error", expression=expression)

    context = build_context(hidden, {}) if hidden else initial
    context["hidden_pages"] = sorted(u for u in hidden if u)
    computed, values = _evaluate_rules(
        env, quick_form.get("outcomes_definition"), context, preview=True
    )
    context["values"] = values

    missing_required = [
        entry["urn"]
        for page in pages
        if page.get("urn") not in hidden
        for entry in page["_questions"]
        if entry.get("required", True) is not False
        and _is_question_visible(entry, answers, questions_by_urn)
        and not is_answered(entry)
    ]

    # Same rule as the live evaluator, so a preview cannot disagree with a response.
    score = _quick_form_score(context)

    return {
        "hidden_pages": sorted(u for u in hidden if u),
        "missing_required": missing_required,
        "progress": {
            "answered_count": context["response"]["answered_count"],
            "total_count": context["response"]["total_count"],
            "complete": context["response"]["complete"],
        },
        "score": score,
        "computed_outcome": computed,
        "computed_values": values,
        "context": context,
    }


def evaluate_quick_form(response, persist: bool = True) -> dict:
    """Evaluate page visibility, completion, score and outcome rules for a
    QuickFormResponse.

    Same three-phase scheme as build_cel_context: context with every page,
    evaluate page visibility_expression, rebuild without hidden pages, then
    evaluate outcomes_definition. Fail-open on expression errors.

    Returns a dict with `context`, `hidden_pages` (page URNs), `progress`,
    `score` and `computed_outcome`. With persist=True the score and outcome
    are written back to the response when they changed.
    """
    from core.models import QuickForm, QuickFormResponse

    form = QuickForm.objects.get(pk=response.quick_form_id)
    response.quick_form = form
    snapshot = _quick_form_snapshot(response)
    previous_outcomes = response.computed_outcome or {}

    initial = _quick_form_context(snapshot, set(), previous_outcomes)
    hidden_page_ids: set = set()
    hidden_page_urns: set[str] = set()
    env = celpy.Environment()
    if any(p.get("visibility_expression") for p in snapshot["pages"]):
        cel_context = {k: _python_to_cel(v) for k, v in initial.items()}
        for page in snapshot["pages"]:
            expression = page.get("visibility_expression")
            if not expression:
                continue
            try:
                prog = env.program(env.compile(expression))
                if not prog.evaluate(cel_context):
                    hidden_page_ids.add(page["id"])
                    hidden_page_urns.add(page["urn"])
            except Exception:
                logger.warning(
                    "cel_visibility_error",
                    expression=expression,
                    page_urn=page["urn"],
                    quick_form_response_id=str(response.pk),
                    exc_info=True,
                )

    context = (
        _quick_form_context(snapshot, hidden_page_ids, previous_outcomes)
        if hidden_page_ids
        else initial
    )
    context["hidden_pages"] = sorted(hidden_page_urns)

    computed, values = _evaluate_rules(
        env,
        form.outcomes_definition,
        context,
        quick_form_response_id=str(response.pk),
    )
    context["values"] = values
    has_rules = bool(form.outcomes_definition)
    has_numeric = any(is_numeric_rule(r) for r in form.outcomes_definition or [])
    computed_outcome = computed if has_rules else None
    computed_values = values if has_numeric else None

    score = _quick_form_score(context)
    outcome_refs = ",".join(sorted(computed)) if computed else ""

    if persist and (
        response.computed_outcome != computed_outcome
        or response.computed_values != computed_values
        or response.score != score
        or response.outcome_refs != outcome_refs
    ):
        QuickFormResponse.objects.filter(pk=response.pk).update(
            computed_outcome=computed_outcome,
            computed_values=computed_values,
            score=score,
            outcome_refs=outcome_refs,
        )
    if persist:
        _sync_outcome_rows(response, computed)
        response.refresh_subject_from_answers()
    response.computed_outcome = computed_outcome
    response.computed_values = computed_values
    response.score = score
    response.outcome_refs = outcome_refs

    # Which required questions are still blank, so a caller can say *what* is
    # missing rather than only that something is. Visibility is already resolved
    # here; making the client work it out again would duplicate depends_on.
    missing_required = [
        entry["question"].urn
        for entry in snapshot["per_question"].values()
        if entry["question"].required
        and entry["visible"]
        and entry["page_id"] not in hidden_page_ids
        and not entry["answered"]
    ]

    return {
        "context": context,
        "hidden_pages": sorted(hidden_page_urns),
        "missing_required": missing_required,
        "progress": {
            "answered_count": context["response"]["answered_count"],
            "total_count": context["response"]["total_count"],
            "complete": context["response"]["complete"],
        },
        "score": score,
        "computed_outcome": computed_outcome,
        "computed_values": computed_values,
    }
