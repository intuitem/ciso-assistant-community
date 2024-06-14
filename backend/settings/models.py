from django.db import models

from iam.models import Folder, FolderMixin


class GlobalSettings(models.Model):
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
        primary_key=True,
        choices=Names,
        default=Names.GENERAL,
    )
    # Value of the setting.
    value = models.JSONField()

    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name="%(class)s_folder",
        default=Folder.get_root_folder,
    )

    def __str__(self):
        return self.name
