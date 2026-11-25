"""Commitment management: the promise an owner makes to deliver by a date.

Distinct from `ValidationFlow`, where a reviewer approves an object as it stands.
One row per negotiation cycle, so promised dates are not overwritten; the host keeps
no columns and the machine runs off serializer fields, so every write path enforces it.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from core.models import Actor, Commitment
from global_settings.utils import ff_is_enabled
from iam.models import Folder

State = Commitment.State


@dataclass(frozen=True)
class ValidatedStep:
    """The commitment a step was validated against: its state and its current cycle.

    Both are needed: a delay closes a cycle and opens the next one in the same state, so
    the state alone would let a stale step land on a cycle it never saw.
    """

    state: str
    cycle: UUID | None


# Exposed on the host serializer; only the first three are writable.
COMMITMENT_LIST_FIELDS = ("commitment_state", "committed_eta")

COMMITMENT_FIELDS = (
    "commitment_state",
    "commitment_notes",
    "commitment_date",
    "committed_eta",
    "committed_by",
    "commitment_reopen_count",
    "commitment_history",
)

# Who may take a step.
ANY = "any"  # anyone with change permission on the object
OWNER = "owner"  # an accountable actor for the object
COUNTERPARTY = "counterparty"  # someone who is *not* an accountable actor
REVIEWER = "reviewer"  # anyone but a respondent of the third party's workspace

# (from, to) -> who may move it, and what the move demands.
TRANSITIONS = {
    (State.UNDEFINED, State.IN_NEGOTIATION): {"side": REVIEWER},
    # The date is the promise: made in one step, frozen on the way in.
    (State.IN_NEGOTIATION, State.COMMITTED): {"side": OWNER, "requires_date": True},
    (State.IN_NEGOTIATION, State.DECLINED): {"side": OWNER, "requires_note": True},
    (State.COMMITTED, State.IN_NEGOTIATION): {"side": ANY, "requires_note": True},
    # Segregation of duties: an owner who can both make and close their own promise is a
    # self-certification loop.
    (State.COMMITTED, State.FULFILLED): {"side": COUNTERPARTY},
    (State.DECLINED, State.IN_NEGOTIATION): {"side": REVIEWER},
    (State.FULFILLED, State.IN_NEGOTIATION): {"side": REVIEWER, "requires_note": True},
}


def changed_meanwhile() -> serializers.ValidationError:
    # Raised after validation, so DRF does not wrap it: the list keeps the field-error
    # shape the client reads.
    return serializers.ValidationError(
        {"commitment_state": ["commitmentChangedMeanwhile"]}
    )


SIDE_REFUSALS = {
    OWNER: "onlyTheAccountableActorCanDoThis",
    COUNTERPARTY: "theAccountableActorCannotCloseTheirOwnCommitment",
    REVIEWER: "onlyTheReviewerCanDoThis",
}


def allowed_targets(current_state: str) -> dict:
    """Every legal next state from *current_state*, with its requirements."""
    return {
        to: config for (frm, to), config in TRANSITIONS.items() if frm == current_state
    }


def user_is_accountable(instance, user, incoming: dict | None = None):
    """Is *user* one of the actors accountable for *instance*?

    None when nothing is accountable — no sides to be on. An empty incoming list falls
    back to the stored actors, else clearing the field would open the no-sides hatch.
    """
    actor_field = instance.COMMITMENT_ACTOR_FIELD
    actors = (incoming or {}).get(actor_field)
    if not actors:
        actors = list(getattr(instance, actor_field).all())
    if not actors:
        return None
    user_actor_ids = {actor.id for actor in Actor.get_all_for_user(user)}
    return any(actor.id in user_actor_ids for actor in actors)


def side_allows(side: str, accountable: bool | None) -> bool:
    """Whether someone whose accountability is *accountable* may take a *side* step.

    Nobody accountable (None) means no sides, so unassigned objects do not deadlock.
    """
    if side == ANY or accountable is None:
        return True
    return accountable if side == OWNER else not accountable


def folders_involved(instance, incoming: dict | None) -> list[Folder]:
    """The object's folder, plus the incoming one when the request creates or moves it."""
    candidates = [getattr(instance, "folder", None), (incoming or {}).get("folder")]
    return list({folder for folder in candidates if folder is not None})


def user_is_respondent_for(folders: list[Folder], user) -> bool:
    """Is *user* answering, rather than reviewing, in any of *folders*?

    A respondent is the promising side by construction; otherwise they fall into the
    no-sides hatch and can run the whole lifecycle alone.
    """
    from core.utils import get_respondent_scoped_folder_ids

    if user is None or not folders:
        return False
    respondent_folder_ids = get_respondent_scoped_folder_ids(user)
    return any(folder.id in respondent_folder_ids for folder in folders)


def user_answers_for_vendor(folders: list[Folder], user) -> bool:
    """Is *user* a respondent in a third party's workspace among *folders*?

    A workspace is an enclave and every folder nested in it, since the respondent role
    reaches sub-folders too. Only there does the reviewer alone drive the commitment: an
    internal auditee still opens negotiations on the controls they own.
    """
    in_workspace = [
        folder
        for folder in folders
        if any(
            ancestor.content_type == Folder.ContentType.ENCLAVE
            for ancestor in folder.get_parent_folders(include_self=True)
        )
    ]
    return user_is_respondent_for(in_workspace, user)


def user_may_take(instance, user, side: str, incoming: dict | None = None) -> bool:
    """Whether *user* is on the right side of the table for a *side* step.

    *instance* is None on create. The sides are judged in both folders of a move, else
    moving an object and taking a step in one request would skip the rule of one of them.
    """
    if side == ANY:
        return True
    folders = folders_involved(instance, incoming)
    if side == REVIEWER:
        return not user_answers_for_vendor(folders, user)
    if side == COUNTERPARTY and user_is_respondent_for(folders, user):
        return False
    return side_allows(side, user_is_accountable(instance, user, incoming))


def serialize_commitment(entry) -> dict:
    return {
        "id": str(entry.id),
        "state": entry.state,
        "committed_eta": entry.committed_eta,
        "committed_by": str(entry.committed_by) if entry.committed_by else None,
        "committed_at": entry.committed_at,
        "notes": entry.notes,
        "opened_at": entry.created_at,
        "closed_at": None if entry.is_current else entry.updated_at,
    }


def apply_transition(
    instance,
    target: str,
    user=None,
    notes: str | None = None,
    promised_date: date | None = None,
    validated: ValidatedStep | None = None,
):
    """Move *instance* to *target*, writing the commitment rows. Assumes the step is legal
    from *validated*.

    The live row is re-read under a lock: validation ran against a cached read, and two
    counterparties transitioning at once would otherwise each persist from the state
    they saw.

    Raises ValidationError when the locked commitment is no longer *validated*, or when
    another request opened the first cycle meanwhile: the step was authorised for what it
    was validated against, not for whatever another request moved it to.
    """
    # Discard the cached cycles: the state validated against may already be stale.
    instance.__dict__.pop("commitment_entries", None)
    current = (
        Commitment.objects.select_for_update()
        .filter(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            is_current=True,
        )
        .first()
    )
    locked = ValidatedStep(
        state=current.state if current else State.UNDEFINED,
        cycle=current.id if current else None,
    )
    if validated is not None and locked != validated:
        raise changed_meanwhile()

    if current is None:
        current = Commitment(target=instance, state=State.IN_NEGOTIATION)
    elif target == State.IN_NEGOTIATION and current.state in Commitment.CLOSING_STATES:
        current.is_current = False
        current.save(update_fields=["is_current", "updated_at"])
        # A renegotiation carries the promise so a breach stays visible. A fulfilled one
        # was kept: reopening it asks for a new promise, the old date stays in history.
        current = Commitment(
            target=instance,
            state=State.IN_NEGOTIATION,
            committed_eta=None
            if current.state == State.FULFILLED
            else current.committed_eta,
        )

    current.state = target
    if notes:
        current.notes = notes

    if target == State.COMMITTED:
        current.committed_eta = promised_date or instance.commitment_date
        current.committed_at = timezone.now()
        actors = Actor.get_all_for_user(user) if user else []
        if actors:
            current.committed_by = actors[0]

    try:
        with transaction.atomic():
            current.save()
    except IntegrityError:
        # A first opening has no row to lock: two at once both pass the check above,
        # and the one-current-row constraint is what turns the second away.
        raise changed_meanwhile() from None
    instance.__dict__.pop("commitment_entries", None)
    return current


class CommitmentSerializerMixin:
    """Enforces the commitment state machine on a write serializer.

    The fields are declared here, not on the model, so the ordinary update path drives it.
    """

    # Which of the commitment fields this serializer carries. A list serializer trims it
    # to what the table renders, so a row does not pay for the whole history.
    COMMITMENT_FIELD_NAMES = COMMITMENT_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Injected, not declared: DRF's metaclass cannot see a plain mixin's
        # attributes, and SerializerMethodField needs binding.
        if not ff_is_enabled("commitment_management"):
            return
        # A recurrent task template is a definition, not a single promise.
        if getattr(self.instance, "is_recurrent", False):
            return
        fields = _commitment_fields()
        for field_name in self.COMMITMENT_FIELD_NAMES:
            self.fields[field_name] = fields[field_name]

    def get_committed_by(self, obj):
        entry = obj.commitment
        actor = entry.committed_by if entry else None
        return {"id": str(actor.id), "str": str(actor)} if actor else None

    def get_commitment_history(self, obj):
        return [serialize_commitment(entry) for entry in obj.commitment_history]

    def _commitment_date(self, attrs: dict):
        """The date a commitment would freeze: the one supplied, else the object's own."""
        if attrs.get("commitment_date"):
            return attrs["commitment_date"]
        field_name = self.Meta.model.COMMITMENT_DATE_FIELD
        if field_name in attrs:
            return attrs[field_name]
        return getattr(self.instance, field_name, None)

    def validate_commitment(self, attrs: dict) -> dict:
        self._commitment_move = None
        # Becoming recurrent hides the lifecycle fields, so a promise still in play
        # would be left with no way to resolve it.
        if (
            attrs.get("is_recurrent")
            and self.instance is not None
            and not getattr(self.instance, "is_recurrent", False)
        ):
            live = self.instance.commitment
            if live is not None and live.state in (
                State.IN_NEGOTIATION,
                State.COMMITTED,
            ):
                raise serializers.ValidationError(
                    {"is_recurrent": "resolveCommitmentBeforeRecurrence"}
                )
        if "commitment_state" not in attrs:
            # A recurrent template carries no commitment fields, so DRF drops the key
            # before validation: refuse the write rather than answering 200 to one
            # that did nothing.
            if getattr(self.instance, "is_recurrent", False) and "commitment_state" in (
                getattr(self, "initial_data", None) or {}
            ):
                raise serializers.ValidationError(
                    {"commitment_state": "commitmentNotAvailableOnRecurrentTask"}
                )
            return attrs

        target = attrs["commitment_state"]
        current = (
            self.instance.commitment_state if self.instance else State.UNDEFINED
        ) or State.UNDEFINED
        if target == current:
            return attrs

        is_recurrent = attrs.get(
            "is_recurrent", getattr(self.instance, "is_recurrent", False)
        )
        if is_recurrent:
            raise serializers.ValidationError(
                {"commitment_state": "commitmentNotAvailableOnRecurrentTask"}
            )

        config = TRANSITIONS.get((current, target))
        if config is None:
            raise serializers.ValidationError(
                {
                    "commitment_state": f"Invalid commitment transition from '{current}' to '{target}'."
                }
            )

        request = self.context.get("request")
        if request is not None and not user_may_take(
            self.instance, request.user, config["side"], attrs
        ):
            raise serializers.ValidationError(
                {"commitment_state": SIDE_REFUSALS[config["side"]]}
            )

        if (
            config.get("requires_note")
            and not (attrs.get("commitment_notes") or "").strip()
        ):
            raise serializers.ValidationError(
                {"commitment_notes": "aNoteIsRequiredForThisTransition"}
            )

        promised_date = self._commitment_date(attrs)
        if config.get("requires_date") and not promised_date:
            raise serializers.ValidationError(
                {"commitment_state": "aDateIsRequiredToCommit"}
            )

        cycle = self.instance.commitment if self.instance else None
        self._commitment_move = (
            target,
            promised_date,
            ValidatedStep(state=current, cycle=cycle.id if cycle else None),
        )
        return attrs

    def pop_commitment(self, validated_data: dict) -> None:
        """Take the commitment fields out before the model serializer saves."""
        for field_name in COMMITMENT_FIELDS:
            validated_data.pop(field_name, None)

    def apply_commitment(self, instance, validated_data: dict) -> None:
        """Write the commitment rows. Runs after the host object is saved."""
        move = getattr(self, "_commitment_move", None)
        if move is None:
            return
        target, promised_date, validated = move
        request = self.context.get("request")
        # One transaction: the row lock taken inside is only worth anything while it
        # is held, and closing a cycle then opening the next must not half-apply.
        with transaction.atomic():
            apply_transition(
                instance,
                target,
                user=request.user if request else None,
                notes=(validated_data.get("commitment_notes") or "").strip() or None,
                promised_date=promised_date,
                validated=validated,
            )


def _commitment_fields() -> dict:
    """The fields a host serializer exposes for the machine."""
    return {
        "commitment_state": serializers.ChoiceField(
            choices=State.choices, required=False
        ),
        "commitment_notes": serializers.CharField(
            required=False, allow_blank=True, allow_null=True, write_only=True
        ),
        "commitment_date": serializers.DateField(
            required=False, allow_null=True, write_only=True
        ),
        "committed_eta": serializers.DateField(read_only=True),
        "committed_by": serializers.SerializerMethodField(),
        "commitment_reopen_count": serializers.IntegerField(read_only=True),
        "commitment_history": serializers.SerializerMethodField(),
    }
