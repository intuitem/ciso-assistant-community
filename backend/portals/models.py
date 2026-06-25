from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import NameDescriptionMixin
from iam.models import FolderMixin, UserGroup


class PortalPreset(NameDescriptionMixin, FolderMixin):
    """A portal definition / catalog entry. Library-backed (urn set) or user-authored.
    Cloned into a live Portal; never referenced live (no sync). Exports to YAML.
    `content` holds the whole design: {"sections": [{"title", "items": [...]}]}."""

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


class PublicDocument(NameDescriptionMixin, FolderMixin):
    """A file published to a trust center. Deliberately isolated from internal Evidence:
    its own storage path + its own token-served AllowAny endpoint, holding a frozen copy of
    the bytes — so a vuln in the public path can never reach internal attachments."""

    token = models.CharField(
        max_length=64, unique=True, default=_public_document_token, editable=False
    )
    file = models.FileField(upload_to="public_documents/%Y/%m/")
    mime_type = models.CharField(max_length=120, blank=True)
    size = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
