from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls.base import reverse_lazy
from django.core.exceptions import ValidationError
import uuid

from ciso_assistant import settings


class AbstractBaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("UpdatedÒ at"))
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
        return not scope.filter(
            **{
                f"{field}__iexact": getattr(self, field)
                for field in fields_to_check
                if hasattr(self, field)
            }
        ).exists()

    def display_path(self):
        pass

    def display_name(self):
        pass

    @property
    def edit_url(self):
        return reverse_lazy(
            f"{self.__class__.__name__.lower()}-update", kwargs={"pk": self.pk}
        )

    def get_scope(self):
        if hasattr(self, "risk_scenario") and self.risk_scenario is not None:
            return self.__class__.objects.filter(risk_scenario=self.risk_scenario)
        if hasattr(self, "risk_assessment") and self.risk_assessment is not None:
            return self.__class__.objects.filter(risk_assessment=self.risk_assessment)
        if hasattr(self, "project") and self.project is not None:
            return self.__class__.objects.filter(project=self.project)
        if hasattr(self, "folder") and self.folder is not None:
            return self.__class__.objects.filter(folder=self.folder)
        if hasattr(self, "parent_folder") and self.parent_folder is not None:
            return self.__class__.objects.filter(parent_folder=self.parent_folder)
        return self.__class__.objects.all()

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
                    field_errors[field] = f"{getattr(self, field)} is already used in this scope. Please choose another value."
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
