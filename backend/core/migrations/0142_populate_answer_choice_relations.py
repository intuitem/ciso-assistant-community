"""
Data migration: populate Answer.selected_choice (FK) and Answer.selected_choices (M2M)
from the legacy Answer.value JSONField, then clear value for choice-type answers.
"""

import logging

from django.db import migrations

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


def forwards(apps, schema_editor):
    Answer = apps.get_model("core", "Answer")
    QuestionChoice = apps.get_model("core", "QuestionChoice")

    # --- SINGLE_CHOICE: resolve value string → FK ---
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
            answer.selected_choice = choice
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
            Answer.objects.bulk_update(batch, ["selected_choice", "value"])
            batch = []
    if batch:
        Answer.objects.bulk_update(batch, ["selected_choice", "value"])

    # --- MULTIPLE_CHOICE: resolve value list → M2M ---
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
        answer.value = None
        batch.append(answer)
        if len(batch) >= BATCH_SIZE:
            Answer.objects.bulk_update(batch, ["value"])
            batch = []
    if batch:
        Answer.objects.bulk_update(batch, ["value"])


def backwards(apps, schema_editor):
    """Reverse: copy FK/M2M back to value JSONField."""
    Answer = apps.get_model("core", "Answer")

    # SINGLE_CHOICE → value = ref_id string
    for answer in (
        Answer.objects.filter(question__type="single_choice")
        .exclude(selected_choice__isnull=True)
        .select_related("selected_choice")
        .iterator(chunk_size=BATCH_SIZE)
    ):
        answer.value = answer.selected_choice.ref_id
        answer.selected_choice = None
        answer.save(update_fields=["value", "selected_choice"])

    # MULTIPLE_CHOICE → value = list of ref_id strings
    for answer in (
        Answer.objects.filter(question__type="multiple_choice")
        .prefetch_related("selected_choices")
        .iterator(chunk_size=BATCH_SIZE)
    ):
        refs = list(answer.selected_choices.values_list("ref_id", flat=True))
        answer.value = refs if refs else []
        answer.selected_choices.clear()
        answer.save(update_fields=["value"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0141_answer_selected_choice_selected_choices"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
