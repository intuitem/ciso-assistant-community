"""
Add unique_together constraint on QuestionChoice(question, ref_id).

This must come after the data migration so any duplicate (question, ref_id)
rows are handled first. The deduplication step merges duplicates by keeping
the first row and updating any FK references.
"""
import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def deduplicate_question_choices(apps, schema_editor):
    """Remove duplicate (question, ref_id) rows, keeping the first by order."""
    QuestionChoice = apps.get_model("core", "QuestionChoice")
    Answer = apps.get_model("core", "Answer")

    from django.db.models import Count

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

        # Re-point any FK references to the keeper
        for old_choice in to_remove:
            Answer.objects.filter(selected_choice=old_choice).update(
                selected_choice=keeper
            )
            # Re-point M2M references
            for answer in Answer.objects.filter(
                selected_choices=old_choice
            ):
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


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0142_populate_answer_choice_relations"),
    ]

    operations = [
        migrations.RunPython(deduplicate_question_choices, noop),
        migrations.AlterUniqueTogether(
            name="questionchoice",
            unique_together={("question", "ref_id")},
        ),
    ]
