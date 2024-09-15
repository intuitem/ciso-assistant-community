from enum import Enum
import os
from django.db import models
from iam.models import FolderMixin
from core.base_models import AbstractBaseModel


class ClientSettings(AbstractBaseModel, FolderMixin):
    class FileField(Enum):
        LOGO = "logo"
        FAVICON = "favicon"

    name = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to="client_logos", null=True, blank=True)
    favicon = models.ImageField(upload_to="client_favicons", null=True, blank=True)

    def __str__(self):
        return self.name

    def filename(self, field: FileField):
        return os.path.basename(getattr(self, field.value).name)
