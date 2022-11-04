from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class AbstractBaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    description = models.TextField(verbose_name=_('Description'), blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self) -> str:
        return self.name
