from django.db import transaction
from django.utils import timezone

from tprm.models import Entity, EntityTierChange, Tier, TierSource


@transaction.atomic
def set_entity_tier(
    entity: Entity,
    tier: Tier | None,
    *,
    source: str = TierSource.MANUAL,
    user=None,
    note: str = "",
    value: float | None = None,
    response=None,
) -> EntityTierChange | None:
    """The only way an entity's tier changes: updates the current tier and
    appends the history row.

    A manual re-save of the same tier is a no-op (editing other fields must not
    write history); an accepted assessment always records itself, since it
    re-dates the tier even when it confirms it."""
    previous_id = entity.tier_id
    if source == TierSource.MANUAL and previous_id == (tier.id if tier else None):
        return None

    entity.tier = tier
    entity.tier_source = source if tier else ""
    entity.tier_set_at = timezone.now() if tier else None
    entity.tier_value = value if tier else None
    entity.tier_response = response if tier else None
    entity.save(
        update_fields=[
            "tier",
            "tier_source",
            "tier_set_at",
            "tier_value",
            "tier_response",
            "updated_at",
        ]
    )

    return EntityTierChange.objects.create(
        entity=entity,
        tier=tier,
        previous_tier_id=previous_id,
        source=source,
        value=value,
        response=response,
        changed_by=user if getattr(user, "is_authenticated", False) else None,
        note=note or "",
    )
