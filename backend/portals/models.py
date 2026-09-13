from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import NameDescriptionMixin
from core.models import I18nObjectMixin
from iam.models import FolderMixin, UserGroup


class PortalPreset(NameDescriptionMixin, FolderMixin, I18nObjectMixin):
    """A portal design kept as a starting point. A catalog object like Framework or
    QuickForm: library-backed entries carry a `urn`, refresh on a library update and
    go away on unload; user-authored ones leave it null.

    `content` holds the design: {"sections": [{"title", "items"}]}, naming frameworks
    and quick forms by URN as well as by local id (see portals.references).

    The divorce is one level down: a live Portal is CLONED from a preset and keeps
    only `source_ref`, a string. Nothing here can reach a portal a user built."""

    library = models.ForeignKey(
        "core.LoadedLibrary",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="portal_presets",
        verbose_name=_("Library"),
    )
    urn = models.CharField(max_length=255, null=True, blank=True, unique=True)
    ref_id = models.CharField(max_length=255, null=True, blank=True)
    version = models.IntegerField(default=1)
    provider = models.CharField(max_length=255, null=True, blank=True)
    translations = models.JSONField(default=dict, blank=True)
    content = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Portal(NameDescriptionMixin, FolderMixin):
    """A live portal: owns its own design (`content`), cloned from a preset or built
    from scratch, then tuned locally. Carries audience, branding and publication state."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    enabled = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    audience_groups = models.ManyToManyField(
        UserGroup, related_name="portals", blank=True
    )
    is_default = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    branding = models.JSONField(default=dict, blank=True)
    content = models.JSONField(default=dict, blank=True)
    source_ref = models.CharField(max_length=255, null=True, blank=True)
    # Public (trust center): non-enumerable token minted when first made public.
    public_token = models.CharField(
        max_length=64, null=True, blank=True, unique=True, editable=False
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if self.is_public and not self.public_token:
            import secrets

            self.public_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
        # Only one portal may be the primary trust center.
        if self.is_primary:
            Portal.objects.exclude(pk=self.pk).filter(is_primary=True).update(
                is_primary=False
            )

    def __str__(self):
        return self.name


def _public_document_token():
    import secrets

    return secrets.token_urlsafe(32)


class FrameworkSnapshot(NameDescriptionMixin, FolderMixin):
    """A frozen, audit-derived projection of a framework's compliance posture, mirrored
    from a ComplianceAssessment scoped to chosen implementation groups. Powers the trust
    center donut / drill-down / export. Never a live window: everything (result breakdown,
    score, per-requirement rows, the controls touched) is CAPTURED at sync time and only
    changes on a manual re-sync."""

    class DisplayMode(models.TextChoices):
        BOTH = "both", _("Score and result")
        SCORE = "score", _("Score only")
        RESULT = "result", _("Result only")

    source_audit = models.ForeignKey(
        "core.ComplianceAssessment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="framework_snapshots",
    )
    implementation_groups = models.JSONField(default=list, blank=True)
    display_mode = models.CharField(
        max_length=10, choices=DisplayMode.choices, default=DisplayMode.BOTH
    )
    framework_name = models.CharField(max_length=255, blank=True)
    framework_ref_id = models.CharField(max_length=255, blank=True)
    framework_version = models.CharField(max_length=255, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    content = models.JSONField(default=list, blank=True)
    # Captured set of applied controls touched by the in-scope requirements. Server-side
    # only (never emitted publicly) — feeds the deduped portal-level "# controls".
    control_ids = models.JSONField(default=list, blank=True)
    public_token = models.CharField(
        max_length=64, null=True, blank=True, unique=True, editable=False
    )

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.public_token:
            import secrets

            self.public_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PublicDocument(NameDescriptionMixin, FolderMixin):
    """A file published to a trust center. Deliberately isolated from internal Evidence:
    its own storage path + its own token-served AllowAny endpoint, holding a frozen copy of
    the bytes — so a vuln in the public path can never reach internal attachments."""

    token = models.CharField(
        max_length=64, unique=True, default=_public_document_token, editable=False
    )
    file = models.FileField(upload_to="public_documents/%Y/%m/")
    filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
