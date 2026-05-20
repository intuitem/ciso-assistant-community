"""Backfill RequirementAssessment.result with the semantic compute_result aggregation."""

from django.db import migrations

BATCH_SIZE = 500


def backfill_results(apps, schema_editor):
    from core.utils import (
        _build_answer_context,
        _is_question_visible,
        aggregate_compute_results,
        resolve_compute_result,
    )

    RequirementAssessment = apps.get_model("core", "RequirementAssessment")
    db_alias = schema_editor.connection.alias

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
        questions_qs = ra.requirement.questions.prefetch_related("choices").all()
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
                    resolved = resolve_compute_result(choice.compute_result)
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
            aggregated = aggregate_compute_results(results)
            ra.result = result_map.get(aggregated, RESULT_NOT_ASSESSED)

    fields = ["score", "result", "is_scored"]
    queryset = RequirementAssessment.objects.using(db_alias).select_related(
        "compliance_assessment", "requirement"
    )

    batch = []
    for ra in queryset.iterator(chunk_size=BATCH_SIZE):
        recompute(ra)
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
