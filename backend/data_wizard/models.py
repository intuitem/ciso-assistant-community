from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import NameDescriptionMixin
from iam.models import FolderMixin, User


class ImportMapping(NameDescriptionMixin, FolderMixin):
    """How a recurring spreadsheet layout maps onto our import templates.

    Each entry of `sheets` describes one source sheet: its headers (what a new
    file is matched on), header row, target model type and template sheet, and
    the column and value maps reviewed by a user.
    """

    sheets = models.JSONField(default=list, verbose_name=_("Sheets"))
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Created by"),
    )
    use_count = models.PositiveIntegerField(default=0, verbose_name=_("Use count"))
    last_used_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last used at")
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Import mapping")
        verbose_name_plural = _("Import mappings")
        ordering = ["name"]
