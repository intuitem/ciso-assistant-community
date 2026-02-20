"""Data migration: JSON questions/answers → relational Question/QuestionChoice/Answer models.

1. Set all existing frameworks to status="published"
2. Migrate RequirementNode.questions JSON → Question + QuestionChoice rows
3. Migrate RequirementAssessment.answers JSON → Answer rows
4. Normalize scores_definition from list to dict format
"""

from django.db import migrations

TYPE_MAPPING = {
    "unique_choice": "single_choice",
    "single_choice": "single_choice",
    "multiple_choice": "multiple_choice",
    "text": "text",
    "number": "number",
    "boolean": "boolean",
    "date": "date",
}


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
    root_folder = Folder.objects.filter(content_type="GLOBAL").first()

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

    # Now create choices for each question
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

    # 3. Migrate RequirementAssessment.answers → Answer rows
    answer_bulk = []
    ras_with_answers = RequirementAssessment.objects.filter(
        answers_json__isnull=False
    ).exclude(answers_json={}).select_related("requirement")

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

    Answer.objects.bulk_create(answer_bulk, batch_size=1000, ignore_conflicts=True)

    # 4. Normalize scores_definition: list → {"scale": list}
    for fw in Framework.objects.filter(scores_definition__isnull=False):
        if isinstance(fw.scores_definition, list):
            fw.scores_definition = {"scale": fw.scores_definition}
            fw.save(update_fields=["scores_definition"])


def migrate_backward(apps, schema_editor):
    """Reverse: delete all Question/QuestionChoice/Answer rows, reset framework status."""
    Question = apps.get_model("core", "Question")
    QuestionChoice = apps.get_model("core", "QuestionChoice")
    Answer = apps.get_model("core", "Answer")
    Framework = apps.get_model("core", "Framework")

    Answer.objects.all().delete()
    QuestionChoice.objects.all().delete()
    Question.objects.all().delete()
    Framework.objects.all().update(status="draft")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0138_framework_status_question_questionchoice_answer"),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrate_backward),
    ]
