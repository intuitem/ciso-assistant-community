from enum import Enum
import os
from django.core.validators import FileExtensionValidator
from django.db import models
from iam.models import FolderMixin
from core.base_models import AbstractBaseModel
from core.utils import sha256

import base64
import magic


class ClientSettings(AbstractBaseModel, FolderMixin):
    class FileField(Enum):
        LOGO = "logo"
        FAVICON = "favicon"

    name = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(
        upload_to="client_logos",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["png", "jpeg", "jpg", "webp", "svg"])],
    )
    favicon = models.ImageField(
        upload_to="client_favicons",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["ico", "png", "jpeg", "jpg", "webp"])],
    )

    @property
    def logo_base64(self):
        try:
            self.logo.open("rb")
            return base64.b64encode(self.logo.read()).decode("utf-8")
        except Exception:
            return None

    @property
    def logo_hash(self):
        if not self.logo_base64:
            return None
        return sha256(self.logo_base64.encode("utf-8"))

    @property
    def logo_mime_type(self):
        try:
            self.logo.open("rb")
            return magic.Magic(mime=True).from_buffer(self.logo.read())
        except Exception:
            return None

    @property
    def favicon_base64(self):
        try:
            self.favicon.open("rb")
            return base64.b64encode(self.favicon.read()).decode("utf-8")
        except Exception:
            return None

    @property
    def favicon_hash(self):
        if not self.favicon_base64:
            return None
        return sha256(self.favicon_base64.encode("utf-8"))

    @property
    def favicon_mime_type(self):
        try:
            self.favicon.open("rb")
            return magic.Magic(mime=True).from_buffer(self.favicon.read())
        except Exception:
            return None

    def __str__(self):
        return self.name

    def filename(self, field: FileField):
        return os.path.basename(getattr(self, field.value).name)
