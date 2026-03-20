from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import NameDescriptionMixin
from iam.models import FolderMixin


class RiskMatrixDraft(NameDescriptionMixin, FolderMixin):
    """
    A draft risk matrix being authored via the visual matrix editor.
    Once published, it becomes a StoredLibrary + LoadedLibrary + RiskMatrix.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")

    json_definition = models.JSONField(
        verbose_name=_("JSON definition"),
        help_text=_(
            "JSON definition of the risk matrix (probability, impact, risk, grid)."
        ),
        default=dict,
    )
    source_matrix = models.ForeignKey(
        "core.RiskMatrix",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_drafts",
        verbose_name=_("Source matrix"),
        help_text=_("The loaded matrix this draft was cloned from, if any."),
    )
    locale = models.CharField(
        max_length=12,
        default="en",
        verbose_name=_("Locale"),
    )
    translations = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Translations"),
    )
    provider = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name=_("Provider"),
    )
    version = models.IntegerField(
        default=1,
        verbose_name=_("Version"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Status"),
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = _("Risk matrix draft")
        verbose_name_plural = _("Risk matrix drafts")

    def __str__(self):
        return f"[{self.get_status_display()}] {self.name}"
