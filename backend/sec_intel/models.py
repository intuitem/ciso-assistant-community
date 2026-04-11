from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import (
    FilteringLabelMixin,
    I18nObjectMixin,
    LoadedLibrary,
    ReferentialObjectMixin,
)
from iam.models import PublishInRootFolderMixin


class SecurityAdvisory(
    ReferentialObjectMixin,
    I18nObjectMixin,
    PublishInRootFolderMixin,
    FilteringLabelMixin,
):
    class Source(models.TextChoices):
        CVE = "CVE", "CVE"
        EUVD = "EUVD", "EUVD"
        GHSA = "GHSA", "GHSA"
        OTHER = "other", "Other"

    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="security_advisories",
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.CVE,
        verbose_name=_("Source"),
    )
    aliases = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Aliases"),
    )
    published_date = models.DateField(
        null=True, blank=True, verbose_name=_("Published date")
    )
    cvss_base_score = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name=_("CVSS base score"),
    )
    cvss_vector = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("CVSS vector")
    )
    epss_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("EPSS score"),
    )
    epss_percentile = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("EPSS percentile"),
    )
    references = models.JSONField(null=True, blank=True, verbose_name=_("References"))
    is_actively_exploited = models.BooleanField(
        default=False, verbose_name=_("Actively exploited")
    )
    exploited_date_added = models.DateField(
        null=True, blank=True, verbose_name=_("KEV date added")
    )
    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["ref_id"]

    class Meta:
        verbose_name = _("Security advisory")
        verbose_name_plural = _("Security advisories")

    def __str__(self):
        return self.ref_id or self.name or str(self.id)


class CWE(
    ReferentialObjectMixin,
    I18nObjectMixin,
    PublishInRootFolderMixin,
    FilteringLabelMixin,
):
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cwes",
    )
    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["ref_id"]

    class Meta:
        verbose_name = _("CWE")
        verbose_name_plural = _("CWEs")

    def __str__(self):
        return self.ref_id or self.name or str(self.id)
