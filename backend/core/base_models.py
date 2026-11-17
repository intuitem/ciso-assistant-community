import re
import uuid
from typing import TYPE_CHECKING

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.urls.base import reverse_lazy
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class _IAMNotImplemented:
    pass


class _IAMSpecialCase:
    pass


class AbstractBaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    if TYPE_CHECKING:
        IAM_SCOPE_FIELD: str | _IAMNotImplemented | _IAMSpecialCase  # pragma: no cover
        """
        An `IAM_SCOPE_FIELD` attribute MUST be set for all the models which don't have a `folder` field.

        For example if a model `RiskObject` has `IAM_SCOPE_FIELD` set to `"risk_assessment"`.

        Then IAM will use `obj.risk_assessment.folder_id` for the permission checks (for `obj = RiskObject(...)`).

        `IAM_SCOPE_FIELD` can also be set to `Folder.IAM_NOT_IMPLEMENTED` to explicitely declare a model as being expected not be supported by the IAM.
        """

    class Meta:
        abstract = True

    def scoped_id(self, scope: models.QuerySet) -> int:
        """
        Returns the ID of the object in the given scope.

        Args:
            scope: the scope in which to run the check

        Returns:
            The ID of the object in the given scope
        """
        if self.pk:
            scope = scope.exclude(pk=self.pk)
        return scope.filter(created_at__lt=self.created_at).count() + 1

    def __str__(self) -> str:
        return self.name if hasattr(self, "name") and self.name else str(self.id)

    def get_additional_data(self) -> dict:
        # Attached to every django-auditlog LogEntry at creation (create/update/
        # delete and m2m). Runs with the instance in memory, so the folder is
        # captured even on delete — used to scope audit events forwarded to SIEMs.
        folder_id = getattr(self, "folder_id", None)
        if folder_id is None:
            from iam.models import Folder

            # Runs in auditlog's synchronous delete receiver: a cascade may have
            # already removed the FK target get_folder traverses, raising
            # DoesNotExist. Never let metadata enrichment break the delete.
            try:
                folder = Folder.get_folder(self)
                folder_id = folder.id if folder else None
            except ObjectDoesNotExist:
                folder_id = None
        return {"folder_id": str(folder_id) if folder_id else None}

    def is_unique_in_scope(self, scope: models.QuerySet, fields_to_check: list) -> bool:
        """
        Checks if the object is unique in the given scope based on the given fields.

        Args:
            scope: the scope in which to run the check
            fields_to_check: the fields to check for uniqueness

        Returns:
            True if the object is unique in the given scope, False otherwise
        """
        # if the object already exists (i.e. has a primary key), exclude it from the scope
        # to avoid false positives as a result of the object being compared to itself
        if self.pk:
            scope = scope.exclude(pk=self.pk)
        filters = {}
        for field in fields_to_check:
            if hasattr(self, field):
                field_value = getattr(self, field)
                # Blank/None values are not meaningful identifiers and must not
                # collide with each other (e.g. an optional ref_id left empty).
                if field_value is None or field_value == "":
                    continue
                model_field = self._meta.get_field(field)

                # Use the appropriate lookup based on the field type
                if isinstance(
                    model_field,
                    (
                        models.ForeignKey,
                        models.IntegerField,
                        models.FloatField,
                        models.BooleanField,
                        models.DateField,
                    ),
                ):
                    filters[f"{field}__exact"] = field_value
                else:
                    filters[f"{field}__iexact"] = field_value

        if not filters:
            return True

        return not scope.filter(**filters).exists()

    @property
    def edit_url(self):
        return reverse_lazy(
            f"{self.__class__.__name__.lower()}-update", kwargs={"pk": self.pk}
        )

    def get_scope(self):
        if hasattr(self, "risk_scenario") and self.risk_scenario is not None:
            return self.__class__.objects.filter(
                risk_scenario=self.risk_scenario
            ).order_by("created_at", "id")
        if hasattr(self, "risk_assessment") and self.risk_assessment is not None:
            return self.__class__.objects.filter(
                risk_assessment=self.risk_assessment
            ).order_by("created_at", "id")
        if hasattr(self, "perimeter") and self.perimeter is not None:
            return self.__class__.objects.filter(perimeter=self.perimeter).order_by(
                "created_at", "id"
            )
        if hasattr(self, "folder") and self.folder is not None:
            return self.__class__.objects.filter(folder=self.folder).order_by(
                "created_at", "id"
            )
        if hasattr(self, "parent_folder") and self.parent_folder is not None:
            return self.__class__.objects.filter(
                parent_folder=self.parent_folder
            ).order_by("created_at", "id")
        return self.__class__.objects.all().order_by("created_at", "id")

    def clean(self) -> None:
        scope = self.get_scope()
        field_errors = {}
        _fields_to_check = (
            self.fields_to_check if hasattr(self, "fields_to_check") else []
        )
        # TODO: define fields_to_check explicitly where it is needed. ref_id should be preferred over name for referential objects

        if not self.is_unique_in_scope(scope=scope, fields_to_check=_fields_to_check):
            for field in _fields_to_check:
                if not self.is_unique_in_scope(scope=scope, fields_to_check=[field]):
                    field_errors[field] = (
                        f"{getattr(self, field)} is already used in this scope. Please choose another value."
                    )
        super().clean()
        if field_errors:
            raise ValidationError(field_errors)

    def _validate_char_max_lengths(self):
        errors = {}
        for field in self._meta.fields:
            if not isinstance(field, models.CharField):
                continue
            value = field.to_python(getattr(self, field.attname))
            if value is not None and len(value) > field.max_length:
                errors[field.name] = ValidationError(
                    f"Ensure this value has at most {field.max_length} characters (it has {len(value)}).",
                    code="max_length",
                    params={"max_length": field.max_length, "length": len(value)},
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs) -> None:
        self._validate_char_max_lengths()
        self.clean()
        super().save(*args, **kwargs)


# Admin-set prefix: letters, digits, "-" or "_", at most 8 characters.
AUTO_REF_ID_PREFIX_RE = re.compile(r"^[A-Za-z0-9_-]{1,8}$")


def _general_settings() -> dict:
    from global_settings.models import GlobalSettings

    return (
        GlobalSettings.objects.filter(name="general")
        .values_list("value", flat=True)
        .first()
        or {}
    )


def _ref_id_number(ref_id: str, prefix: str) -> int | None:
    """N of a ref_id shaped `<prefix>N` (prefix compared case-insensitively, as the
    uniqueness check does), None for anything else."""
    if ref_id[: len(prefix)].upper() != prefix.upper():
        return None
    suffix = ref_id[len(prefix) :]
    return int(suffix) if suffix.isascii() and suffix.isdigit() else None


def _lock_parents(model, parent_ids) -> None:
    """Serialize ref_id allocation per parent. NO KEY UPDATE, unlike a plain FOR
    UPDATE, does not block the foreign-key inserts other objects make in the parent."""
    if None in parent_ids:
        # Objects without a parent (a finding outside any assessment) have no row to
        # lock, so their group locks the root folder, always taken before parents.
        from iam.models import Folder

        list(
            Folder.objects.select_for_update(no_key=True)
            .filter(pk=Folder.get_root_folder_id())
            .values_list("pk", flat=True)
        )
    ids = [pk for pk in parent_ids if pk is not None]
    if ids:
        list(
            model.objects.select_for_update(no_key=True)
            .filter(pk__in=ids)
            .order_by("pk")
            .values_list("pk", flat=True)
        )


class AutoRefIdMixin:
    """Fills a blank ref_id on creation, numbered within its parent, when the
    `auto_ref_id` general setting is on. List it first in the model's bases;
    a plain mixin so it does not replace the Meta the model inherits.

    A model whose save() derives the parent defines `resolve_auto_ref_id_parent()`
    so the number is taken in the parent the object is saved in."""

    auto_ref_id_prefix: str = ""
    auto_ref_id_parent: str = "folder"

    @classmethod
    def current_auto_ref_id_prefix(cls, general: dict | None = None) -> str:
        """The admin's override while auto ref_id is on, else the built-in prefix.
        Proxies (Policy) share their table, hence their concrete model's prefix."""
        concrete = cls._meta.concrete_model
        general = _general_settings() if general is None else general
        if general.get("auto_ref_id"):
            overrides = general.get("auto_ref_id_prefixes") or {}
            return (
                overrides.get(concrete._meta.model_name) or concrete.auto_ref_id_prefix
            )
        return concrete.auto_ref_id_prefix

    def next_ref_id(self, prefix: str) -> str:
        prefix = f"{prefix}."
        # _base_manager: a proxy's default manager (Policy) hides rows sharing the sequence.
        taken = (
            type(self)
            ._base_manager.filter(
                **{f"{self.auto_ref_id_parent}_id": self._ref_id_parent_id},
                ref_id__istartswith=prefix,
            )
            .values_list("ref_id", flat=True)
        )
        numbers = [n for r in taken if (n := _ref_id_number(r, prefix)) is not None]
        return f"{prefix}{max(numbers, default=0) + 1:02d}"

    @property
    def _ref_id_parent_id(self):
        return getattr(self, f"{self.auto_ref_id_parent}_id")

    def save(self, *args, **kwargs):
        if self._state.adding and not self.ref_id:
            general = _general_settings()
            if general.get("auto_ref_id"):
                if resolve := getattr(self, "resolve_auto_ref_id_parent", None):
                    resolve()
                with transaction.atomic():
                    _lock_parents(
                        self._meta.get_field(self.auto_ref_id_parent).related_model,
                        [self._ref_id_parent_id],
                    )
                    blank, self.ref_id = (
                        self.ref_id,
                        self.next_ref_id(self.current_auto_ref_id_prefix(general)),
                    )
                    try:
                        return super().save(*args, **kwargs)
                    except Exception:
                        # A retry of this instance must allocate again, not keep a number
                        # someone else may get meanwhile.
                        self.ref_id = blank
                        raise
        return super().save(*args, **kwargs)


def auto_ref_id_models() -> dict:
    """{model_name: model} of every model that can get an automatic ref_id.
    Proxies are left out: they share their concrete model's table and sequence."""
    from django.apps import apps

    return {
        m._meta.model_name: m
        for m in apps.get_models()
        if issubclass(m, AutoRefIdMixin) and not m._meta.proxy
    }


def backfill_auto_ref_ids() -> int:
    """Number the existing objects whose ref_id is blank, oldest first, after the
    highest number already used in their parent. Filled ref_ids are left alone."""
    from collections import defaultdict

    general = _general_settings()
    updated = 0
    with transaction.atomic():
        for model in auto_ref_id_models().values():
            prefix = f"{model.current_auto_ref_id_prefix(general)}."
            parent = f"{model.auto_ref_id_parent}_id"
            blank = models.Q(ref_id="") | models.Q(ref_id__isnull=True)
            # _base_manager: custom default managers may hide rows that still need an id.
            parents = set(
                model._base_manager.filter(blank).values_list(parent, flat=True)
            )
            if not parents:
                continue
            # Same parent lock as creation, taken before reading the sequences.
            _lock_parents(
                model._meta.get_field(model.auto_ref_id_parent).related_model, parents
            )
            in_parents = models.Q(**{f"{parent}__in": parents - {None}})
            if None in parents:
                in_parents |= models.Q(**{f"{parent}__isnull": True})
            # Only the locked parents: a row blanked since the scan waits for the next run.
            blanks = list(
                model._base_manager.select_for_update()
                .filter(blank & in_parents)
                .order_by("created_at", "pk")
                .only("pk", parent)
            )
            last = defaultdict(int)
            for parent_id, ref_id in (
                model._base_manager.filter(in_parents, ref_id__istartswith=prefix)
                .values_list(parent, "ref_id")
                .iterator()
            ):
                if (n := _ref_id_number(ref_id, prefix)) is not None:
                    last[parent_id] = max(last[parent_id], n)
            for obj in blanks:
                last[getattr(obj, parent)] += 1
                obj.ref_id = f"{prefix}{last[getattr(obj, parent)]:02d}"
            # shortcut: bulk_update skips save() and signals (no audit log entry per object).
            model._base_manager.bulk_update(blanks, ["ref_id"], batch_size=500)
            updated += len(blanks)
    return updated


class NameDescriptionMixin(AbstractBaseModel):
    """
    Mixin for models that have a name and a description.
    """

    name = models.CharField(max_length=200, verbose_name=_("Name"), unique=False)
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ETADueDateMixin(models.Model):
    """
    Mixin for models that have an ETA and a due date.
    """

    eta = models.DateField(null=True, blank=True, verbose_name=_("ETA"))
    due_date = models.DateField(null=True, blank=True, verbose_name=_("Due date"))

    class Meta:
        abstract = True


class ActorSyncMixin(models.Model):
    """
    Intercepts save() to ensure an Actor exists for individual records.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        with transaction.atomic():
            is_new = self._state.adding
            super().save(*args, **kwargs)

            # If this is a new record, create the actor.
            # We use get_or_create to be safe against race conditions/re-saves.
            if is_new:
                from .models import Actor

                field_name = self.__class__.__name__.lower()
                Actor.objects.get_or_create(**{field_name: self})


class ActorSyncManager(models.Manager):
    """
    Intercepts bulk_create to ensure Actors are created for every new record.
    """

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False, **kwargs):
        # Perform the standard bulk_create
        created_objs = super().bulk_create(
            objs, batch_size=batch_size, ignore_conflicts=ignore_conflicts, **kwargs
        )

        # Extract the newly created instances
        from .models import Actor  # Import inside to avoid circular dependency

        # Determine the field name on the Actor model (user/team/entity)
        field_name = self.model.__name__.lower()

        actors = []
        for obj in created_objs:
            if obj.pk:  # Only link if the object was actually created
                actor = Actor(**{field_name: obj})
                actors.append(actor)

        # Bulk create the corresponding Actors
        if actors:
            Actor.objects.bulk_create(actors, ignore_conflicts=True)

        return created_objs
