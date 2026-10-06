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


def _build_context_dict(
    in_scope, ra_rows, answer_data, max_score, computed_outcomes=None
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

        if node_id:
            requirements[node_id] = entry

    ctx = {
        "assessment": {
            "score_sum": score_sum,
            "score_max": score_max,
            "answered_count": answered_count,
            "total_count": total_count,
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
            "id", "urn", "ref_id", "implementation_groups", "visibility_expression"
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
        ).values("requirement__urn", "score", "result", "status", "is_scored")
    }

    # Query 3: answer-level data for in-scope requirements
    answer_data = _build_answer_data(ca, in_scope_node_ids)

    max_score = ca.max_score or 100
    computed_outcomes = ca.computed_outcome if ca.computed_outcome else {}

    # Phase 1: build initial context with assessable in-scope nodes
    initial_context = _build_context_dict(
        in_scope, ra_rows, answer_data, max_score, computed_outcomes
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


def evaluate_outcomes(compliance_assessment) -> None:
    """Evaluate CEL outcome rules and store all matching results on the assessment."""
    from core.models import Framework

    ca = compliance_assessment
    # Refresh framework from DB to pick up any changes to outcomes_definition
    # (the FK cache may be stale when called from deferred on_commit hooks)
    framework = Framework.objects.get(pk=ca.framework_id)
    outcomes_def = framework.outcomes_definition

    if not outcomes_def:
        if ca.computed_outcome is not None:
            ca.computed_outcome = None
            ca.save(update_fields=["computed_outcome"])
        return

    context, _hidden = build_cel_context(ca)
    cel_context = {k: _python_to_cel(v) for k, v in context.items()}

    computed = {}
    env = celpy.Environment()
    for rule in outcomes_def:
        expression = rule.get("expression", "")
        ref_id = rule.get("ref_id", "")
        if not expression or not ref_id:
            continue
        try:
            ast = env.compile(expression)
            prog = env.program(ast)
            result = prog.evaluate(cel_context)
            if result:
                computed[ref_id] = {
                    k: v for k, v in rule.items() if k not in ("expression", "ref_id")
                }
        except Exception:
            logger.warning(
                "cel_evaluation_error",
                expression=expression,
                compliance_assessment_id=str(ca.pk),
                exc_info=True,
            )
            continue

    if ca.computed_outcome != computed:
        ca.computed_outcome = computed
        ca.save(update_fields=["computed_outcome"])


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


def _evaluate_quick_form_rules(env, rules, context: dict, **log_fields):
    """Run a quick form's outcome rules against `context`.

    Numeric rules (`kind: number`) run first, in order, each seeing the values
    computed before it as `values.<ref_id>`; the yes/no rules then see them all.
    Returns (fired, values): the classifications that fired, keyed by ref_id
    with their pass-through attributes, and {ref_id: float}. Fail-open per rule:
    an expression error or a non-number result is logged and skipped.
    """
    values: dict[str, float] = {}
    fired: dict[str, dict] = {}
    rules = [r for r in rules or [] if r.get("expression") and r.get("ref_id")]

    for rule in [r for r in rules if is_numeric_rule(r)]:
        cel_context = {
            k: _python_to_cel(v) for k, v in {**context, "values": values}.items()
        }
        try:
            result = env.program(env.compile(rule["expression"])).evaluate(cel_context)
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

    cel_context = {
        k: _python_to_cel(v) for k, v in {**context, "values": values}.items()
    }
    for rule in [r for r in rules if not is_numeric_rule(r)]:
        try:
            if env.program(env.compile(rule["expression"])).evaluate(cel_context):
                fired[rule["ref_id"]] = {
                    k: v for k, v in rule.items() if k not in ("expression", "ref_id")
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
            str(rule.get("ref_id")): 0.0
            for rule in quick_form.get("outcomes_definition") or []
            if rule.get("ref_id") and is_numeric_rule(rule)
        },
        "hidden_pages": [],
    }


def _explain(expression, error, raw_probe, scopes, container) -> str:
    """The evaluator's text, or for the usual mistake (an id that does not
    exist) the key and the ids that do."""
    text = str(error).split("\n")[0]
    member = re.search(r"no such member in mapping: '([^']*)'", text)
    if member and f"values.{member[1]}" in expression:
        return (
            f"No number rule '{member[1]}' above this one: a rule reads only "
            "the number rules listed before it"
        )
    key = re.search(r"no such key.*StringType\('([^']*)'\)", text)
    if key is None:
        return text[:300]
    singular = {"pages": "page", "answers": "answer", "requirements": "requirement"}
    for scope in scopes:
        if f'{scope}["{key[1]}"]' in expression or f"{scope}['{key[1]}']" in expression:
            known = ", ".join(sorted(raw_probe.get(scope) or {})) or "none"
            return (
                f"No {singular[scope]} '{key[1]}' in this {container}. Known: {known}"
            )[:300]
    return f"Unknown key '{key[1]}'"


def _framework_probe(framework: dict) -> dict:
    """A context with the real shape of a framework's audits but empty values:
    every assessable requirement and every question, so an id that exists is
    never flagged and one that does not always is."""
    from core.utils import extract_node_id

    requirements, answers = {}, {}
    for node in framework.get("requirement_nodes") or []:
        node_id = extract_node_id(str(node.get("urn") or ""))
        if node_id and node.get("assessable"):
            requirements[node_id] = {
                "score": 0,
                "max_score": 100,
                "result": "not_assessed",
                "status": "to_do",
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
    return {
        "assessment": {
            "score_sum": 0,
            "score_max": 0,
            "answered_count": 0,
            "total_count": 0,
        },
        "requirements": requirements,
        "answers": answers,
        "computed_outcomes": {
            str(rule.get("ref_id")): {}
            for rule in framework.get("outcomes_definition") or []
            if rule.get("ref_id")
        },
        "hidden_requirements": [],
    }


def validate_framework_expressions(framework: dict) -> list[dict]:
    """Check every requirement visibility expression and outcome rule of a
    framework, as `validate_quick_form_expressions` does for forms: an
    expression against the wrong context, or naming an id that does not exist,
    compiles but raises when an audit is evaluated, where it is only logged."""
    raw_probe = _framework_probe(framework)
    # Visibility runs before the hidden requirements are known, as at runtime.
    visibility_probe = {
        k: _python_to_cel(v) for k, v in raw_probe.items() if k != "hidden_requirements"
    }
    probe = {k: _python_to_cel(v) for k, v in raw_probe.items()}
    env = celpy.Environment()
    errors = []

    def _check(where, ref_id, expression, context):
        if not expression:
            return
        try:
            env.program(env.compile(expression)).evaluate(context)
        except Exception as e:
            errors.append(
                {
                    "where": where,
                    "ref_id": ref_id,
                    "expression": expression,
                    "error": _explain(
                        expression,
                        e,
                        raw_probe,
                        ("requirements", "answers"),
                        "framework",
                    ),
                }
            )

    for node in framework.get("requirement_nodes") or []:
        _check(
            "requirement_visibility",
            str(node.get("ref_id") or node.get("urn") or ""),
            str(node.get("visibility_expression") or ""),
            visibility_probe,
        )
    for rule in framework.get("outcomes_definition") or []:
        _check(
            "outcome",
            str(rule.get("ref_id") or ""),
            str(rule.get("expression") or ""),
            probe,
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
    probe = {k: _python_to_cel(v) for k, v in raw_probe.items()}
    env = celpy.Environment()
    errors = []

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
        try:
            return env.program(env.compile(expression)).evaluate(context or probe)
        except Exception as e:
            _error(
                where,
                ref_id,
                expression,
                _explain(expression, e, raw_probe, ("pages", "answers"), "form"),
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
    visibility_probe = {k: v for k, v in probe.items() if k != "values"}
    for page in quick_form.get("pages") or []:
        _check(
            "page_visibility",
            str(page.get("ref_id") or page.get("urn") or ""),
            str(page.get("visibility_expression") or ""),
            visibility_probe,
        )
    rules = quick_form.get("outcomes_definition") or []
    for rule in rules:
        kind = rule.get("kind")
        if kind not in (None, "", "boolean", "number"):
            _error(
                "outcome",
                str(rule.get("ref_id") or ""),
                str(rule.get("expression") or ""),
                f"Unknown rule kind '{kind}': use 'number' or leave it empty",
            )
    # A numeric rule sees only the values computed before it, as at runtime.
    earlier: dict[str, float] = {}
    for rule in [r for r in rules if is_numeric_rule(r)]:
        ref_id = str(rule.get("ref_id") or "")
        expression = str(rule.get("expression") or "")
        context = {
            k: _python_to_cel(v) for k, v in {**raw_probe, "values": earlier}.items()
        }
        result = _check("outcome", ref_id, expression, context)
        if expression and result is not None and _as_number(result) is None:
            _error("outcome", ref_id, expression, "A numeric rule must return a number")
        earlier = {**earlier, ref_id: 0.0}
    for rule in rules:
        if is_numeric_rule(rule):
            continue
        _check(
            "outcome",
            str(rule.get("ref_id") or ""),
            str(rule.get("expression") or ""),
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
    computed, values = _evaluate_quick_form_rules(
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

    computed, values = _evaluate_quick_form_rules(
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
