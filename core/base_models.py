from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import uuid

class AbstractBaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    description = models.TextField(verbose_name=_('Description'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))

    class Meta:
        abstract = True
        ordering = ['name']

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
        return self.name

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
        return not scope.filter(**{field: getattr(self, field) for field in fields_to_check}).exists()

    def display_path(self):
        pass

    def display_name(self):
        pass

    def clean(self) -> None:
        scope = self.__class__.objects.all()
        if not self.is_unique_in_scope(scope=scope, fields_to_check=['name']):
            raise ValidationError({'name': _('A {} with this name already exists.'.format(self._meta.verbose_name))})
        super().clean()
