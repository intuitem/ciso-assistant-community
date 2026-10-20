from django.db import transaction
from django.db.models import F, OuterRef, Q, Subquery
from django.utils import timezone

from global_settings.models import GlobalSettings
from iam.models import RoleAssignment

from tprm.models import (
    Entity,
    EntityTierChange,
    Solution,
    SolutionTierChange,
    Tier,
    TierSource,
)

# The former 1-4 criticality, as default-scale tier keys.
KEY_BY_CRITICALITY = {4: "critical", 3: "important", 2: "standard", 1: "low-impact"}


def tier_for_criticality(value) -> Tier | None:
    """The visible tier a former 1-4 criticality stands for, if the scale
    still has it; None for 0, junk or a reshaped scale."""
    try:
        key = KEY_BY_CRITICALITY.get(int(value))
    except TypeError, ValueError:
        return None
    return Tier.objects.filter(key=key, is_visible=True).first() if key else None


@transaction.atomic
def _set_tier(
    obj,
    tier: Tier | None,
    history_model,
    subject_field: str,
    *,
    source: str,
    user,
    note: str,
    value: float | None,
    response,
):
    """The only way a tier changes: updates the current tier and appends the
    history row.

    A manual re-save of the same tier is a no-op (editing other fields must not
    write history); an accepted assessment always records itself, since it
    re-dates the tier even when it confirms it."""
    previous_id = obj.tier_id
    if source == TierSource.MANUAL and previous_id == (tier.id if tier else None):
        return None

    obj.tier = tier
    obj.tier_source = source if tier else ""
    obj.tier_set_at = timezone.now() if tier else None
    obj.tier_value = value if tier else None
    obj.tier_response = response if tier else None
    obj.save(
        update_fields=[
            "tier",
            "tier_source",
            "tier_set_at",
            "tier_value",
            "tier_response",
            "updated_at",
        ]
    )

    return history_model.objects.create(
        **{subject_field: obj},
        tier=tier,
        previous_tier_id=previous_id,
        source=source,
        value=value,
        response=response,
        changed_by=user if getattr(user, "is_authenticated", False) else None,
        note=note or "",
    )


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
    return _set_tier(
        entity,
        tier,
        EntityTierChange,
        "entity",
        source=source,
        user=user,
        note=note,
        value=value,
        response=response,
    )


@transaction.atomic
def set_solution_tier(
    solution: Solution,
    tier: Tier | None,
    *,
    source: str = TierSource.MANUAL,
    user=None,
    note: str = "",
    value: float | None = None,
    response=None,
    propagate: bool = True,
) -> SolutionTierChange | None:
    change = _set_tier(
        solution,
        tier,
        SolutionTierChange,
        "solution",
        source=source,
        user=user,
        note=note,
        value=value,
        response=response,
    )
    if change is not None and propagate:
        raise_to_floor(solution.provider_entity)
    return change


class Propagation:
    OFF = "off"
    SUGGEST = "suggest"
    FLOOR = "floor"
    MODES = (OFF, SUGGEST, FLOOR)


def propagation_mode() -> str:
    row = GlobalSettings.objects.filter(name=GlobalSettings.Names.TPRM).first()
    mode = (row.value or {}).get("tier_propagation") if row else None
    return mode if mode in Propagation.MODES else Propagation.OFF


def floor_solution(entity: Entity, user=None) -> Solution | None:
    """The entity's active solution with the most critical visible tier."""
    solutions = entity.provided_solutions.filter(is_active=True, tier__is_visible=True)
    if user is not None:
        solutions = solutions.filter(
            id__in=RoleAssignment.get_viewable_object_ids(user, Solution)
        )
    return solutions.select_related("tier").order_by("-tier__rank", "name").first()


def below_floor(entity: Entity, user=None) -> Solution | None:
    if entity.builtin:
        return None
    solution = floor_solution(entity, user)
    if solution is None or (entity.tier and entity.tier.rank >= solution.tier.rank):
        return None
    return solution


def entities_below_floor():
    floors = Solution.objects.filter(
        provider_entity=OuterRef("pk"), is_active=True, tier__is_visible=True
    ).order_by("-tier__rank", "name")
    return (
        Entity.objects.annotate(
            floor_rank=Subquery(floors.values("tier__rank")[:1]),
            floor_solution_id=Subquery(floors.values("id")[:1]),
        )
        .filter(floor_rank__isnull=False, builtin=False)
        .filter(Q(tier__isnull=True) | Q(tier__rank__lt=F("floor_rank")))
    )


@transaction.atomic
def raise_all_to_floor() -> int:
    entities = list(entities_below_floor())
    solutions = Solution.objects.select_related("tier").in_bulk(
        [e.floor_solution_id for e in entities]
    )
    for entity in entities:
        solution = solutions[entity.floor_solution_id]
        set_entity_tier(
            entity,
            solution.tier,
            source=TierSource.ROLLUP,
            note=solution.name,
        )
    return len(entities)


def raise_to_floor(entity: Entity | None) -> EntityTierChange | None:
    if entity is None or propagation_mode() != Propagation.FLOOR:
        return None
    solution = below_floor(entity)
    if solution is None:
        return None
    return set_entity_tier(
        entity, solution.tier, source=TierSource.ROLLUP, note=solution.name
    )
