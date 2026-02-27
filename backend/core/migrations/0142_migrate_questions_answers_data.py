"""Data migration: questionnaire data.

1. Set all existing frameworks to status="published"
2. Migrate RequirementNode.questions_json → Question + QuestionChoice rows
3. Deduplicate QuestionChoice (question, ref_id) before unique constraint
4. Migrate RequirementAssessment.answers_json → Answer rows
5. Populate Answer.selected_choices M2M from Answer.value for choice-type questions
6. Normalize scores_definition from list to dict format
"""

import logging

from django.db import migrations
from django.db.models import Count

logger = logging.getLogger(__name__)

TYPE_MAPPING = {
    "unique_choice": "single_choice",
    "single_choice": "single_choice",
    "multiple_choice": "multiple_choice",
    "text": "text",
    "number": "number",
    "boolean": "boolean",
    "date": "date",
}

BATCH_SIZE = 1000


def migrate_forward(apps, schema_editor):
    Framework = apps.get_model("core", "Framework")
    RequirementNode = apps.get_model("core", "RequirementNode")
    RequirementAssessment = apps.get_model("core", "RequirementAssessment")
    Question = apps.get_model("core", "Question")
    QuestionChoice = apps.get_model("core", "QuestionChoice")
    Answer = apps.get_model("core", "Answer")
    Folder = apps.get_model("iam", "Folder")

    # 1. Set all existing frameworks to published
    Framework.objects.all().update(status="published")

    # Get root folder for FK
    root_folder = Folder.objects.filter(content_type="GL").first()
    if not root_folder:
        raise Exception("Root folder with content_type='GL' not found")

    # 2. Migrate RequirementNode.questions → Question + QuestionChoice
    question_bulk = []
    choice_bulk = []
    question_urn_to_obj = {}  # for later answer migration

    nodes_with_questions = RequirementNode.objects.filter(
        questions_json__isnull=False
    ).exclude(questions_json={})

    for node in nodes_with_questions.iterator(chunk_size=500):
        if not isinstance(node.questions_json, dict):
            continue

        for order, (q_urn, q_data) in enumerate(node.questions_json.items()):
            if not isinstance(q_data, dict):
                continue

            q_type = TYPE_MAPPING.get(q_data.get("type", "text"), "text")
            parts = q_urn.split(":")
            q_ref_id = parts[-1] if parts else q_urn

            question = Question(
                requirement_node=node,
                urn=q_urn,
                ref_id=q_ref_id,
                annotation=q_data.get("text", ""),
                type=q_type,
                depends_on=q_data.get("depends_on"),
                order=order,
                weight=q_data.get("weight", 1),
                folder=root_folder,
                is_published=True,
                translations=q_data.get("translations"),
            )
            question_bulk.append(question)

    # Bulk create questions
    created_questions = Question.objects.bulk_create(question_bulk, batch_size=1000)

    # Build URN → Question lookup
    for q in created_questions:
        question_urn_to_obj[q.urn] = q

    # Now create choices for each question (pre-deduplicate by question+ref_id)
    seen_choice_keys = set()
    for node in nodes_with_questions.iterator(chunk_size=500):
        if not isinstance(node.questions_json, dict):
            continue

        for q_urn, q_data in node.questions_json.items():
            if not isinstance(q_data, dict):
                continue

            question = question_urn_to_obj.get(q_urn)
            if not question:
                continue

            for c_order, choice in enumerate(q_data.get("choices", [])):
                c_urn = choice.get("urn", "")
                c_parts = c_urn.split(":")
                c_ref_id = c_parts[-1] if c_parts else c_urn

                choice_key = (question.pk, c_ref_id)
                if choice_key in seen_choice_keys:
                    logger.warning(
                        "Skipping duplicate choice ref_id=%s for question %s",
                        c_ref_id,
                        question.pk,
                    )
                    continue
                seen_choice_keys.add(choice_key)

                compute_result = choice.get("compute_result")
                if compute_result is not None:
                    compute_result = str(compute_result).lower()

                choice_bulk.append(
                    QuestionChoice(
                        question=question,
                        ref_id=c_ref_id,
                        annotation=choice.get("value", ""),
                        add_score=choice.get("add_score"),
                        compute_result=compute_result,
                        order=c_order,
                        description=choice.get("description"),
                        color=choice.get("color"),
                        select_implementation_groups=choice.get(
                            "select_implementation_groups"
                        ),
                        folder=root_folder,
                        is_published=True,
                        translations=choice.get("translations"),
                    )
                )

    QuestionChoice.objects.bulk_create(choice_bulk, batch_size=1000)

    # 3. Deduplicate QuestionChoice (question, ref_id) before unique constraint
    duplicates = (
        QuestionChoice.objects.values("question", "ref_id")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )

    for dup in duplicates:
        choices = QuestionChoice.objects.filter(
            question_id=dup["question"], ref_id=dup["ref_id"]
        ).order_by("order", "pk")
        keeper = choices.first()
        to_remove = choices.exclude(pk=keeper.pk)

        # Re-point M2M references to the keeper
        for old_choice in to_remove:
            for answer in Answer.objects.filter(selected_choices=old_choice):
                answer.selected_choices.remove(old_choice)
                answer.selected_choices.add(keeper)

        removed_count = to_remove.count()
        to_remove.delete()
        if removed_count:
            logger.info(
                "Deduplicated %d QuestionChoice rows for question=%s ref_id=%s",
                removed_count,
                dup["question"],
                dup["ref_id"],
            )

    # 4. Migrate RequirementAssessment.answers → Answer rows
    answer_bulk = []
    ras_with_answers = (
        RequirementAssessment.objects.filter(answers_json__isnull=False)
        .exclude(answers_json={})
        .select_related("requirement")
    )

    for ra in ras_with_answers.iterator(chunk_size=500):
        if not isinstance(ra.answers_json, dict):
            continue

        for q_urn, answer_value in ra.answers_json.items():
            question = question_urn_to_obj.get(q_urn)
            if question:
                answer_bulk.append(
                    Answer(
                        requirement_assessment=ra,
                        question=question,
                        value=answer_value,
                        folder=ra.folder or root_folder,
                    )
                )

    created_answers = Answer.objects.bulk_create(
        answer_bulk, batch_size=1000, ignore_conflicts=True
    )
    if len(created_answers) < len(answer_bulk):
        logger.warning(
            "Answer bulk_create: %d of %d rows created (duplicates ignored)",
            len(created_answers),
            len(answer_bulk),
        )

    # 5. Populate selected_choices M2M from value for choice-type answers

    # SINGLE_CHOICE: resolve value string → M2M
    single_choice_qs = (
        Answer.objects.filter(question__type="single_choice")
        .exclude(value__isnull=True)
        .select_related("question")
    )

    batch = []
    for answer in single_choice_qs.iterator(chunk_size=BATCH_SIZE):
        if not answer.value:
            continue
        choice = QuestionChoice.objects.filter(
            question=answer.question, ref_id=answer.value
        ).first()
        if choice:
            answer.selected_choices.set([choice])
            answer.value = None
            batch.append(answer)
        else:
            logger.warning(
                "Answer %s: could not resolve single-choice ref_id '%s' "
                "for question %s",
                answer.pk,
                answer.value,
                answer.question_id,
            )
        if len(batch) >= BATCH_SIZE:
            Answer.objects.bulk_update(batch, ["value"])
            batch = []
    if batch:
        Answer.objects.bulk_update(batch, ["value"])

    # MULTIPLE_CHOICE: resolve value list → M2M
    multi_choice_qs = Answer.objects.filter(
        question__type="multiple_choice"
    ).select_related("question")

    batch = []
    for answer in multi_choice_qs.iterator(chunk_size=BATCH_SIZE):
        if isinstance(answer.value, list) and answer.value:
            choices = QuestionChoice.objects.filter(
                question=answer.question, ref_id__in=answer.value
            )
            found_refs = set(choices.values_list("ref_id", flat=True))
            missing = set(answer.value) - found_refs
            if missing:
                logger.warning(
                    "Answer %s: could not resolve multiple-choice ref_ids %s "
                    "for question %s",
                    answer.pk,
                    missing,
                    answer.question_id,
                )
            answer.selected_choices.set(choices)
            # Only clear value when all refs were resolved
            if not missing:
                answer.value = None
                batch.append(answer)
        else:
            answer.value = None
            batch.append(answer)
        if len(batch) >= BATCH_SIZE:
            Answer.objects.bulk_update(batch, ["value"])
            batch = []
    if batch:
        Answer.objects.bulk_update(batch, ["value"])

    # 6. Normalize scores_definition: list → {"scale": list}
    for fw in Framework.objects.filter(scores_definition__isnull=False):
        if isinstance(fw.scores_definition, list):
            fw.scores_definition = {"scale": fw.scores_definition}
            fw.save(update_fields=["scores_definition"])


def migrate_backward(apps, schema_editor):
    """Reverse: delete all Question/QuestionChoice/Answer rows, reset framework status."""
    Answer = apps.get_model("core", "Answer")
    Question = apps.get_model("core", "Question")
    QuestionChoice = apps.get_model("core", "QuestionChoice")
    Framework = apps.get_model("core", "Framework")

    Answer.objects.all().delete()
    QuestionChoice.objects.all().delete()
    Question.objects.all().delete()
    Framework.objects.all().update(status="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0141_framework_status_question_questionchoice_answer"),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrate_backward),
    ]
