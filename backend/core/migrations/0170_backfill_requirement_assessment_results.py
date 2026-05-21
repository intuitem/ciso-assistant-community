"""Backfill RequirementAssessment.result with the semantic compute_result aggregation."""

import logging

from django.db import migrations

logger = logging.getLogger(__name__)

BATCH_SIZE = 500

CHOICE_QUESTION_TYPES = {"unique_choice", "multiple_choice"}


def _resolve_compute_result(compute_result):
    if compute_result is None:
        return None
    value = compute_result.strip().lower()
    if value == "":
        return None
    if value in ("true", "1", "compliant"):
        return "compliant"
    if value in ("false", "0", "non_compliant"):
        return "non_compliant"
    if value == "partially_compliant":
        return "partially_compliant"
    if value == "not_applicable":
        return "not_applicable"
    logger.warning("Unknown compute_result value ignored: %s", compute_result)
    return None


def _aggregate_compute_results(resolved_results):
    contributing = [r for r in resolved_results if r is not None]
    if not contributing:
        return None
    if any(r == "not_applicable" for r in contributing):
        return "not_applicable"
    has_compliant = any(r == "compliant" for r in contributing)
    has_non_compliant = any(r == "non_compliant" for r in contributing)
    has_partial = any(r == "partially_compliant" for r in contributing)
    if has_partial or (has_compliant and has_non_compliant):
        return "partially_compliant"
    if has_non_compliant:
        return "non_compliant"
    return "compliant"


def _is_question_visible(question, answers_by_urn, questions_by_urn=None, visited=None):
    depends_on = getattr(question, "depends_on", None)
    if not depends_on:
        return True
    dep_ref = depends_on.get("question") if isinstance(depends_on, dict) else None
    if not dep_ref:
        return True
    if visited is None:
        visited = set()
    q_urn = getattr(question, "urn", None)
    if q_urn:
        if q_urn in visited:
            return True
        visited = visited | {q_urn}
    if questions_by_urn:
        parent_question = questions_by_urn.get(dep_ref)
        if parent_question and not _is_question_visible(
            parent_question, answers_by_urn, questions_by_urn, visited
        ):
            return False
    target_answer = answers_by_urn.get(dep_ref)
    if target_answer is None or (isinstance(target_answer, list) and not target_answer):
        return False
    condition = depends_on.get("condition", "any")
    dep_answers = depends_on.get("answers", [])
    if condition == "any":
        if isinstance(target_answer, list):
            return any(a in dep_answers for a in target_answer)
        return target_answer in dep_answers
    if condition == "all":
        if isinstance(target_answer, list):
            return all(a in target_answer for a in dep_answers)
        return len(dep_answers) == 1 and target_answer == dep_answers[0]
    return True


def _build_answer_context(questions_qs, answers_qs):
    selected_choice_pks_by_qid = {}
    answers_by_urn = {}
    questions_by_urn = {}
    has_answer_by_qid = {}

    for a in answers_qs:
        q_type = a.question.type
        if q_type in CHOICE_QUESTION_TYPES:
            choices = list(a.selected_choices.all())
            pks = {c.id for c in choices}
            selected_choice_pks_by_qid[a.question_id] = pks
            has_answer_by_qid[a.question_id] = len(pks) > 0
        else:
            choices = None
            has_answer_by_qid[a.question_id] = a.value is not None and a.value != ""

        if a.question.urn:
            if q_type == "unique_choice":
                refs = [c.urn for c in choices]
                answers_by_urn[a.question.urn] = refs[0] if refs else None
            elif q_type == "multiple_choice":
                answers_by_urn[a.question.urn] = [c.urn for c in choices]
            else:
                answers_by_urn[a.question.urn] = a.value

    for q in questions_qs:
        questions_by_urn[q.urn] = q

    return (
        selected_choice_pks_by_qid,
        answers_by_urn,
        questions_by_urn,
        has_answer_by_qid,
    )


def _normalize_legacy_choice_values(apps, db_alias):
    """Convert legacy boolean compute_result literals in QuestionChoice rows.

    Existing rows may store "true"/"false" from older library imports.
    Normalize them to the semantic values so the framework builder UI
    (which only offers compliant/non_compliant/…) renders them correctly.
    """
    QuestionChoice = apps.get_model("core", "QuestionChoice")
    LEGACY_MAP = {
        "true": "compliant",
        "false": "non_compliant",
    }
    for old, new in LEGACY_MAP.items():
        updated = (
            QuestionChoice.objects.using(db_alias)
            .filter(compute_result=old)
            .update(compute_result=new)
        )
        if updated:
            logger.info(
                "Normalized %d QuestionChoice.compute_result '%s' -> '%s'",
                updated,
                old,
                new,
            )


def backfill_results(apps, schema_editor):
    RequirementAssessment = apps.get_model("core", "RequirementAssessment")
    db_alias = schema_editor.connection.alias

    # --- Step 1: normalize legacy "true"/"false" in QuestionChoice rows ---
    _normalize_legacy_choice_values(apps, db_alias)

    # --- Step 2: recompute results for question-driven RAs only -----------
    RESULT_NOT_ASSESSED = "not_assessed"
    RESULT_COMPLIANT = "compliant"
    RESULT_NON_COMPLIANT = "non_compliant"
    RESULT_PARTIALLY_COMPLIANT = "partially_compliant"
    RESULT_NOT_APPLICABLE = "not_applicable"
    CALCULATION_METHOD_SUM = "sum"

    result_map = {
        "compliant": RESULT_COMPLIANT,
        "partially_compliant": RESULT_PARTIALLY_COMPLIANT,
        "non_compliant": RESULT_NON_COMPLIANT,
        "not_applicable": RESULT_NOT_APPLICABLE,
    }

    def recompute(ra):
        """Recompute score/result. Return True if the RA was modified."""
        questions_qs = ra.requirement.questions.prefetch_related("choices").all()

        # No questions → this RA is manual or respondent-alignment-driven.
        # Leave it untouched to avoid corrupting manually-set results.
        if not questions_qs:
            return False

        answers_qs = (
            ra.answers.select_related("question")
            .prefetch_related("selected_choices")
            .all()
        )
        (
            selected_choice_pks_by_qid,
            answers_by_urn,
            questions_by_urn,
            has_answer_by_qid,
        ) = _build_answer_context(questions_qs, answers_qs)

        ca = ra.compliance_assessment
        min_score = ca.min_score or 0
        max_score = ca.max_score or 100

        aggregation = None
        scores_def = ca.scores_definition
        if isinstance(scores_def, dict):
            aggregation = scores_def.get("aggregation")
        if not aggregation:
            aggregation = (
                "sum"
                if ca.score_calculation_method == CALCULATION_METHOD_SUM
                else "mean"
            )

        total_score = 0
        total_weight = 0
        results = []
        visible_questions = 0
        answered_visible_questions = 0
        is_score_computed = False

        for question in questions_qs:
            if not _is_question_visible(question, answers_by_urn, questions_by_urn):
                continue
            visible_questions += 1
            if not has_answer_by_qid.get(question.id):
                continue
            answered_visible_questions += 1
            selected_pks = selected_choice_pks_by_qid.get(question.id, set())
            for choice in question.choices.all():
                if choice.id not in selected_pks:
                    continue
                if choice.add_score is not None:
                    is_score_computed = True
                    total_score += choice.add_score * question.weight
                    total_weight += question.weight
                if choice.compute_result is not None:
                    resolved = _resolve_compute_result(choice.compute_result)
                    if resolved is not None:
                        results.append(resolved)

        if is_score_computed:
            if aggregation == "mean" and total_weight > 0:
                computed_score = total_score / total_weight
            else:
                computed_score = total_score
            ra.score = max(min(int(computed_score), max_score), min_score)
        else:
            ra.score = None
        ra.is_scored = is_score_computed

        if visible_questions == 0:
            ra.result = RESULT_NOT_APPLICABLE
        elif answered_visible_questions < visible_questions or not results:
            ra.result = RESULT_NOT_ASSESSED
        else:
            aggregated = _aggregate_compute_results(results)
            ra.result = result_map.get(aggregated, RESULT_NOT_ASSESSED)

        return True

    fields = ["score", "result", "is_scored"]
    queryset = RequirementAssessment.objects.using(db_alias).select_related(
        "compliance_assessment", "requirement"
    )

    batch = []
    for ra in queryset.iterator(chunk_size=BATCH_SIZE):
        if not recompute(ra):
            continue
        batch.append(ra)
        if len(batch) >= BATCH_SIZE:
            RequirementAssessment.objects.using(db_alias).bulk_update(batch, fields)
            batch = []
    if batch:
        RequirementAssessment.objects.using(db_alias).bulk_update(batch, fields)


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0169_tasktemplate_filtering_labels"),
    ]

    operations = [
        migrations.RunPython(backfill_results, reverse_backfill),
    ]
