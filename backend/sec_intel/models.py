from django.db import models
from django.utils.translation import gettext_lazy as _
from core.base_models import ViewableFromDescendantsMode

from core.models import (
    FilteringLabelMixin,
    I18nObjectMixin,
    LoadedLibrary,
    ReferentialObjectMixin,
)


class SecurityAdvisory(
    ReferentialObjectMixin,
    I18nObjectMixin,
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

    fields_to_check = ["ref_id"]

    VIEWABLE_FROM_DESCENDANTS_MODE = ViewableFromDescendantsMode.ALWAYS_VIEWABLE

    class Meta:
        verbose_name = _("Security advisory")
        verbose_name_plural = _("Security advisories")

    def __str__(self):
        return self.ref_id or self.name or str(self.id)


class CWE(
    ReferentialObjectMixin,
    I18nObjectMixin,
    FilteringLabelMixin,
):
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cwes",
    )

    fields_to_check = ["ref_id"]

    VIEWABLE_FROM_DESCENDANTS_MODE = ViewableFromDescendantsMode.ALWAYS_VIEWABLE

    class Meta:
        verbose_name = _("CWE")
        verbose_name_plural = _("CWEs")

    def __str__(self):
        return self.ref_id or self.name or str(self.id)


class TTPCatalog(ReferentialObjectMixin, I18nObjectMixin):
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ttp_catalogs",
    )
    grouping_definition = models.JSONField(
        blank=True, null=True, verbose_name=_("Grouping definition")
    )

    fields_to_check = ["ref_id", "name"]

    VIEWABLE_FROM_DESCENDANTS_MODE = ViewableFromDescendantsMode.ALWAYS_VIEWABLE

    class Meta:
        verbose_name = _("TTP catalog")
        verbose_name_plural = _("TTP catalogs")


class Tactic(ReferentialObjectMixin, I18nObjectMixin):
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tactics",
    )
    catalog = models.ForeignKey(
        TTPCatalog,
        on_delete=models.CASCADE,
        related_name="tactics",
        verbose_name=_("Catalog"),
    )
    # source matrix order, never ref_id order
    order_id = models.IntegerField(null=True, verbose_name=_("Order ID"))

    fields_to_check = ["ref_id", "name"]

    VIEWABLE_FROM_DESCENDANTS_MODE = ViewableFromDescendantsMode.ALWAYS_VIEWABLE

    class Meta:
        verbose_name = _("Tactic")
        verbose_name_plural = _("Tactics")


class Technique(
    ReferentialObjectMixin,
    I18nObjectMixin,
    FilteringLabelMixin,
):
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="techniques",
    )
    catalog = models.ForeignKey(
        TTPCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="techniques",
        verbose_name=_("Catalog"),
    )
    # not a hierarchy: 145 of 697 ATT&CK techniques sit in 2-4 tactics
    tactics = models.ManyToManyField(
        Tactic, blank=True, related_name="techniques", verbose_name=_("Tactics")
    )
    # strict tree: 0 of 475 sub-techniques have more than one parent
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent"),
    )
    order_id = models.IntegerField(null=True, verbose_name=_("Order ID"))
    groups = models.JSONField(null=True, blank=True, verbose_name=_("Groups"))
    reference_controls = models.ManyToManyField(
        "core.ReferenceControl",
        blank=True,
        related_name="techniques",
        verbose_name=_("Reference controls"),
    )
    is_deprecated = models.BooleanField(default=False, verbose_name=_("Deprecated"))

    fields_to_check = ["ref_id", "name"]

    VIEWABLE_FROM_DESCENDANTS_MODE = ViewableFromDescendantsMode.ALWAYS_VIEWABLE

    class Meta:
        verbose_name = _("Technique")
        verbose_name_plural = _("Techniques")

    @property
    def display_short(self) -> str:
        if self.parent_id is None:
            return super().display_short
        return (
            f"{self.ref_id} - {self.parent.get_name_translated}: "
            f"{self.get_name_translated}"
        )
