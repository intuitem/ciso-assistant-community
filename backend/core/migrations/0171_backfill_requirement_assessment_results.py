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
    non_na = [r for r in contributing if r != "not_applicable"]
    if not non_na:
        return "not_applicable"
    has_compliant = any(r == "compliant" for r in non_na)
    has_non_compliant = any(r == "non_compliant" for r in non_na)
    has_partial = any(r == "partially_compliant" for r in non_na)
    if has_partial or (has_compliant and has_non_compliant):
        return "partially_compliant"
    if has_non_compliant:
        return "non_compliant"
    return "compliant"


def _is_question_visible(question, answers_by_urn, questions_by_urn=None, visited=None):
    """Check if a question is visible based on depends_on logic.

    Works with Question model objects (new relational models).
    - question: a Question model instance
    - answers_by_urn: dict of {question.urn: answer_value}
    - questions_by_urn: dict of {question.urn: Question} (optional, for lookups)
    - visited: set of urns already visited (cycle protection)
    """
    depends_on = (
        question.depends_on
        if hasattr(question, "depends_on")
        else question.get("depends_on")
        if isinstance(question, dict)
        else None
    )
    if not depends_on:
        return True

    dep_ref = depends_on.get("question") if isinstance(depends_on, dict) else None
    if not dep_ref:
        return True

    # Cycle protection
    if visited is None:
        visited = set()
    q_urn = getattr(question, "urn", None) or (
        question.get("urn") if isinstance(question, dict) else None
    )
    if q_urn:
        if q_urn in visited:
            return True
        visited = visited | {q_urn}

    # Check parent question visibility first (recursive chain)
    if questions_by_urn:
        parent_question = questions_by_urn.get(dep_ref)
        if parent_question and not _is_question_visible(
            parent_question, answers_by_urn, questions_by_urn, visited
        ):
            return False

    target_answer = answers_by_urn.get(dep_ref)
    # Use explicit None/empty-list check to avoid hiding on falsy values like 0 or False
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
        # Single-value answer can only satisfy "all" if there's exactly one expected answer
        return len(dep_answers) == 1 and target_answer == dep_answers[0]

    return False


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

    Existing rows may store "true"/"false" from older library imports, or
    "True"/"False" from YAML libraries that declared compute_result as a Python
    bool (Django CharField stringifies via str(True) -> "True"). Match
    case-insensitively so all capitalizations are caught.
    """
    QuestionChoice = apps.get_model("core", "QuestionChoice")
    LEGACY_MAP = {
        "true": "compliant",
        "false": "non_compliant",
    }
    for old, new in LEGACY_MAP.items():
        updated = (
            QuestionChoice.objects.using(db_alias)
            .filter(compute_result__iexact=old)
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

    # --- Step 2: recompute result for question-driven RAs only -------------
    # Score computation (add_score) was never affected by the boolean-collapse
    # bug — only result aggregation was.  Leave score/is_scored untouched.
    RESULT_NOT_ASSESSED = "not_assessed"
    RESULT_COMPLIANT = "compliant"
    RESULT_NON_COMPLIANT = "non_compliant"
    RESULT_PARTIALLY_COMPLIANT = "partially_compliant"
    RESULT_NOT_APPLICABLE = "not_applicable"

    result_map = {
        "compliant": RESULT_COMPLIANT,
        "partially_compliant": RESULT_PARTIALLY_COMPLIANT,
        "non_compliant": RESULT_NON_COMPLIANT,
        "not_applicable": RESULT_NOT_APPLICABLE,
    }

    # Memoize the question tree per requirement_id: many RAs reference the
    # same RequirementNode, so we materialize the questions + choices once
    # per distinct requirement instead of refetching per RA.
    question_cache = {}

    def get_question_data(requirement):
        cached = question_cache.get(requirement.id)
        if cached is not None:
            return cached
        questions = list(requirement.questions.prefetch_related("choices").all())
        has_any_compute_result = any(
            _resolve_compute_result(choice.compute_result) is not None
            for question in questions
            for choice in question.choices.all()
        )
        cached = (questions, has_any_compute_result)
        question_cache[requirement.id] = cached
        return cached

    def recompute_result(ra):
        """Recompute result only. Return True if the RA was modified."""
        questions_qs, has_any_compute_result = get_question_data(ra.requirement)

        # No questions → this RA is manual or respondent-alignment-driven.
        # Leave it untouched to avoid corrupting manually-set results.
        if not questions_qs:
            return False

        # No choice defines compute_result → the boolean-collapse bug never
        # applied to this RA.  Skip to avoid wiping a manual result on
        # score-only or plain-question assessments.
        if not has_any_compute_result:
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

        results = []
        visible_questions = 0
        answered_visible_questions = 0

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
                if choice.compute_result is not None:
                    resolved = _resolve_compute_result(choice.compute_result)
                    if resolved is not None:
                        results.append(resolved)

        if visible_questions == 0:
            ra.result = RESULT_NOT_APPLICABLE
        elif answered_visible_questions < visible_questions:
            ra.result = RESULT_NOT_ASSESSED
        elif not results:
            ra.result = RESULT_NOT_ASSESSED
        else:
            aggregated = _aggregate_compute_results(results)
            ra.result = result_map.get(aggregated, RESULT_NOT_ASSESSED)

        return True

    fields = ["result"]
    queryset = RequirementAssessment.objects.using(db_alias).select_related(
        "requirement"
    )

    batch = []
    for ra in queryset.iterator(chunk_size=BATCH_SIZE):
        if not recompute_result(ra):
            continue
        batch.append(ra)
        if len(batch) >= BATCH_SIZE:
            RequirementAssessment.objects.using(db_alias).bulk_update(batch, fields)
            batch = []
    if batch:
        RequirementAssessment.objects.using(db_alias).bulk_update(batch, fields)


def reverse_backfill(apps, schema_editor):
    """No-op. Rollback is logical (schema) only; legacy true/false literals
    and pre-fix RequirementAssessment.result values are not restored."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0170_alter_terminology_field_path"),
    ]

    operations = [
        migrations.RunPython(backfill_results, reverse_backfill),
    ]
