"""CEL-based outcome evaluation for compliance assessments and quick forms."""

from __future__ import annotations

import celpy
import celpy.celtypes as celtypes
import structlog

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
        .values("id", "urn", "visibility_expression")
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
    return {"pages": pages, "per_question": per_question}


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

    for entry in snapshot["per_question"].values():
        if entry["page_id"] in hidden_page_ids or not entry["visible"]:
            continue
        question = entry["question"]
        stats = page_stats[entry["page_id"]]
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

    for page in snapshot["pages"]:
        node_id = extract_node_id(page["urn"])
        if not node_id:
            continue
        stats = page_stats[page["id"]]
        pages[node_id] = {
            "visible": page["id"] not in hidden_page_ids,
            "answered_count": stats["answered_count"],
            "total_count": stats["total_count"],
        }

    return {
        "response": {
            "score_sum": score_sum,
            "score_max": score_max,
            "answered_count": answered_count,
            "total_count": total_count,
            "complete": required_missing == 0,
        },
        "pages": pages,
        "answers": answers,
        "computed_outcomes": computed_outcomes or {},
    }


def _quick_form_score(response, context, snapshot, hidden_page_ids) -> int | None:
    """Aggregate score of the visible, answered, scorable questions, clamped
    to the form's bounds. None until the response is complete."""
    if not context["response"]["complete"]:
        return None
    form = response.quick_form
    scorable = [
        e
        for e in snapshot["per_question"].values()
        if e["scorable"]
        and e["visible"]
        and e["page_id"] not in hidden_page_ids
        and e["answered"]
    ]
    if not scorable:
        return None
    total = sum(e["score"] for e in scorable)
    if form.score_aggregation == "mean":
        total_weight = sum(e["question"].weight for e in scorable) or 1
        total = total / total_weight
    lo, hi = form.score_bounds
    return int(max(lo, min(hi, round(total))))


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

    computed = {}
    if form.outcomes_definition:
        cel_context = {k: _python_to_cel(v) for k, v in context.items()}
        for rule in form.outcomes_definition:
            expression = rule.get("expression", "")
            ref_id = rule.get("ref_id", "")
            if not expression or not ref_id:
                continue
            try:
                prog = env.program(env.compile(expression))
                if prog.evaluate(cel_context):
                    computed[ref_id] = {
                        k: v
                        for k, v in rule.items()
                        if k not in ("expression", "ref_id")
                    }
            except Exception:
                logger.warning(
                    "cel_evaluation_error",
                    expression=expression,
                    quick_form_response_id=str(response.pk),
                    exc_info=True,
                )
    computed_outcome = computed if form.outcomes_definition else None

    score = _quick_form_score(response, context, snapshot, hidden_page_ids)

    if persist and (
        response.computed_outcome != computed_outcome or response.score != score
    ):
        QuickFormResponse.objects.filter(pk=response.pk).update(
            computed_outcome=computed_outcome, score=score
        )
    response.computed_outcome = computed_outcome
    response.score = score

    return {
        "context": context,
        "hidden_pages": sorted(hidden_page_urns),
        "progress": {
            "answered_count": context["response"]["answered_count"],
            "total_count": context["response"]["total_count"],
            "complete": context["response"]["complete"],
        },
        "score": score,
        "computed_outcome": computed_outcome,
    }
