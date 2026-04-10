"""CEL-based outcome evaluation for compliance assessments."""

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

    Returns a dict keyed by question URN with score, value, selected choices, etc.
    """
    from core.models import Answer

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
                x
                for c in selected
                for x in ([c.urn] if c.urn else []) + ([c.ref_id] if c.ref_id else [])
            ],
            "weight": q.weight,
            "type": q.type,
        }
        result[q.urn] = entry
        if q.ref_id:
            result[q.ref_id] = entry
    return result


def _build_context_dict(
    in_scope, ra_rows, answer_data, max_score, computed_outcomes=None
) -> dict:
    """Build the raw context dict from in-scope nodes, RA rows, and answer data."""
    score_sum = 0
    score_max = 0
    answered_count = 0
    total_count = len(in_scope)
    requirements: dict[str, dict] = {}
    ref_ids: dict[str, dict] = {}

    for node in in_scope:
        urn = node["urn"]
        ref_id = node.get("ref_id")
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

        requirements[urn] = entry
        if ref_id:
            ref_ids[ref_id] = entry

    ctx = {
        "assessment": {
            "score_sum": score_sum,
            "score_max": score_max,
            "answered_count": answered_count,
            "total_count": total_count,
        },
        "requirements": requirements,
        "ref_ids": ref_ids,
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
        visible_answer_data = {k: v for k, v in answer_data.items()}
        final_context = _build_context_dict(
            visible_scope, ra_rows, visible_answer_data, max_score, computed_outcomes
        )
        final_context["hidden_requirements"] = list(hidden_urns)
    else:
        final_context = initial_context
        final_context["hidden_requirements"] = list(hidden_urns)

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
