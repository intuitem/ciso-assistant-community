from django.db import models

from iam.models import FolderMixin
from core.base_models import AbstractBaseModel


class GlobalSettings(AbstractBaseModel, FolderMixin):
    """
    Global settings for the application.
    New setting categories should only be added through data migrations.
    """

    class Names(models.TextChoices):
        GENERAL = "general", "General"
        SSO = "sso", "SSO"

    # Name of the setting category.
    name = models.CharField(
        max_length=30,
        unique=True,
        choices=Names,
        default=Names.GENERAL,
    )
    # Value of the setting.
    value = models.JSONField(default=dict)

    def __str__(self):
        return self.name
