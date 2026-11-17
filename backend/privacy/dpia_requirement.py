from django.db import transaction
from django.utils import timezone

from privacy.models import DpiaRequirementChange, DpiaRequirementSource, Processing


@transaction.atomic
def set_dpia_required(
    processing: Processing,
    value: bool,
    *,
    source: str = DpiaRequirementSource.MANUAL,
    user=None,
    note: str = "",
    response=None,
) -> DpiaRequirementChange | None:
    """The only way `dpia_required` changes: updates the processing and appends
    the history row.

    A manual re-save of the same value is a no-op (editing other fields must not
    write history); an accepted screening always records itself, since it
    re-dates the verdict even when it confirms it."""
    previous = (
        Processing.objects.filter(pk=processing.pk)
        .values_list("dpia_required", flat=True)
        .first()
    )
    if source == DpiaRequirementSource.MANUAL and previous == value:
        return None

    now = timezone.now()
    fields = {
        "dpia_required": value,
        "dpia_required_source": source,
        "dpia_required_set_at": now,
        "updated_at": now,
    }
    # A manual change keeps the last screening on record: the card says it was
    # set by hand, and the screening stays one click away in the history.
    if response is not None:
        fields["dpia_screening"] = response
    # `.update()`, as the other quick-form writes: no save signals re-fire.
    Processing.objects.filter(pk=processing.pk).update(**fields)
    for name, field_value in fields.items():
        setattr(processing, name, field_value)

    return DpiaRequirementChange.objects.create(
        processing=processing,
        dpia_required=value,
        previous_dpia_required=previous,
        source=source,
        response=response,
        changed_by=user if getattr(user, "is_authenticated", False) else None,
        note=note or "",
    )
