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


def build_cel_context(compliance_assessment) -> dict:
    """Build the evaluation context dict from a ComplianceAssessment.

    Issues exactly two DB queries regardless of data size.
    """
    from core.models import RequirementAssessment, RequirementNode

    ca = compliance_assessment
    framework = ca.framework

    # Query 1: all assessable requirement nodes for the framework
    all_nodes = list(
        RequirementNode.objects.filter(
            framework=framework,
            assessable=True,
        ).values("id", "urn", "ref_id", "implementation_groups")
    )

    # Implementation-groups filtering (Python-side for DB portability)
    selected_igs = (
        set(ca.selected_implementation_groups)
        if ca.selected_implementation_groups
        else None
    )
    if selected_igs:
        in_scope = [
            n for n in all_nodes if selected_igs & set(n["implementation_groups"] or [])
        ]
    else:
        in_scope = all_nodes

    in_scope_node_ids = [n["id"] for n in in_scope]
    urn_set = {n["urn"] for n in in_scope}

    # Query 2: all requirement assessments for in-scope nodes
    ra_rows = {
        row["requirement__urn"]: row
        for row in RequirementAssessment.objects.filter(
            compliance_assessment=ca,
            requirement_id__in=in_scope_node_ids,
        ).values("requirement__urn", "score", "result", "status", "is_scored")
    }

    max_score = ca.max_score or 100
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

    return {
        "assessment": {
            "score_sum": score_sum,
            "score_max": score_max,
            "answered_count": answered_count,
            "total_count": total_count,
        },
        "requirements": requirements,
        "ref_ids": ref_ids,
    }


def evaluate_outcomes(compliance_assessment) -> None:
    """Evaluate CEL outcome rules and store the result on the assessment."""
    ca = compliance_assessment
    outcomes_def = ca.framework.outcomes_definition

    if not outcomes_def:
        if ca.computed_outcome is not None:
            ca.computed_outcome = None
            ca.save(update_fields=["computed_outcome"])
        return

    context = build_cel_context(ca)
    cel_context = {k: _python_to_cel(v) for k, v in context.items()}

    computed = None
    env = celpy.Environment()
    for rule in outcomes_def:
        expression = rule.get("expression", "")
        if not expression:
            continue
        try:
            ast = env.compile(expression)
            prog = env.program(ast)
            result = prog.evaluate(cel_context)
            if result:
                computed = {k: v for k, v in rule.items() if k != "expression"}
                break
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
