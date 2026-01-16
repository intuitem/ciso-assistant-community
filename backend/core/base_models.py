from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls.base import reverse_lazy
from django.core.exceptions import ValidationError
import uuid


class AbstractBaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    is_published = models.BooleanField(_("published"), default=False)

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
                model_field = self._meta.get_field(field)

                # Use the appropriate lookup based on the field type
                if isinstance(
                    model_field,
                    (
                        models.ForeignKey,
                        models.IntegerField,
                        models.FloatField,
                        models.BooleanField,
                    ),
                ):
                    filters[f"{field}__exact"] = field_value
                else:
                    filters[f"{field}__iexact"] = field_value

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

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)


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
                actors.append(Actor(**{field_name: obj}))

        # Bulk create the corresponding Actors
        if actors:
            Actor.objects.bulk_create(actors, ignore_conflicts=True)

        return created_objs
