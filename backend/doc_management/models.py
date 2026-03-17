from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel
from core.models import I18nObjectMixin, Policy
from core.validators import validate_file_name, validate_file_size
from iam.models import FolderMixin, User


class ManagedDocument(AbstractBaseModel, FolderMixin, I18nObjectMixin):
    class DocumentType(models.TextChoices):
        POLICY = "policy", _("Policy")
        PROCEDURE = "procedure", _("Procedure")
        SOP = "sop", _("Standard Operating Procedure")
        PLAYBOOK = "playbook", _("Playbook")
        GUIDELINE = "guideline", _("Guideline")

    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.POLICY,
        verbose_name=_("Document type"),
    )
    name = models.CharField(max_length=200, blank=True, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    # Optional link to a parent policy — future document types may link to other objects
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
    )
    current_revision = models.ForeignKey(
        "DocumentRevision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    template_used = models.CharField(max_length=200, null=True, blank=True)
    fields_to_check = ["policy", "locale"]

    class Meta:
        verbose_name = _("Managed document")
        verbose_name_plural = _("Managed documents")

    def save(self, *args, **kwargs):
        if self.policy:
            self.folder = self.policy.folder
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        if self.name:
            return self.name
        if self.policy:
            return self.policy.name
        return str(self.id)

    def __str__(self):
        return self.display_name


class DocumentRevision(AbstractBaseModel, FolderMixin):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        IN_REVIEW = "in_review", _("In review")
        CHANGE_REQUESTED = "change_requested", _("Change requested")
        PUBLISHED = "published", _("Published")
        DEPRECATED = "deprecated", _("Deprecated")

    document = models.ForeignKey(
        ManagedDocument, on_delete=models.CASCADE, related_name="revisions"
    )
    version_number = models.PositiveIntegerField(default=1)
    content = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_doc_revisions",
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_doc_revisions",
    )
    reviewer_comments = models.TextField(null=True, blank=True)
    change_summary = models.CharField(max_length=500, blank=True)
    pdf_snapshot = models.FileField(
        null=True,
        blank=True,
        validators=[validate_file_size, validate_file_name],
    )
    published_at = models.DateTimeField(null=True, blank=True)
    editing_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    editing_since = models.DateTimeField(null=True, blank=True)
    fields_to_check = ["document", "version_number"]

    class Meta:
        ordering = ["-version_number"]
        verbose_name = _("Document revision")
        verbose_name_plural = _("Document revisions")

    def save(self, *args, **kwargs):
        self.folder = self.document.folder
        super().save(*args, **kwargs)

    def clean(self):
        if self.status == self.Status.DRAFT:
            existing = self.document.revisions.filter(status=self.Status.DRAFT).exclude(
                pk=self.pk
            )
            if existing.exists():
                raise ValidationError("Only one draft revision allowed per document.")
        super().clean()

    def publish(self, reviewer=None):
        """Publish this revision: set PUBLISHED, deprecate old, set as current."""
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        if reviewer:
            self.reviewer = reviewer
        self.save()

        # Deprecate previous published revisions
        self.document.revisions.filter(status=self.Status.PUBLISHED).exclude(
            pk=self.pk
        ).update(status=self.Status.DEPRECATED)

        # Set as current revision
        self.document.current_revision = self
        self.document.save()

    def mark_change_requested(self, reviewer=None, comments=""):
        """Mark this revision as needing changes."""
        self.status = self.Status.CHANGE_REQUESTED
        if reviewer:
            self.reviewer = reviewer
        self.reviewer_comments = comments
        self.save()

    def revert_to_draft(self):
        """Revert this revision back to draft status."""
        self.status = self.Status.DRAFT
        self.reviewer = None
        self.reviewer_comments = None
        self.save()

    def __str__(self):
        return f"{self.document.display_name} v{self.version_number}"


class DocumentAttachment(AbstractBaseModel, FolderMixin):
    """Image or file attached to a managed document, for embedding in markdown."""

    document = models.ForeignKey(
        ManagedDocument,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(
        validators=[validate_file_size, validate_file_name],
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_attachments",
    )
    fields_to_check = []

    class Meta:
        verbose_name = _("Document attachment")
        verbose_name_plural = _("Document attachments")

    def save(self, *args, **kwargs):
        self.folder = self.document.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Attachment for {self.document.display_name}"


class DocumentEdit(AbstractBaseModel, FolderMixin):
    """Tracks each save of a draft revision for edit history."""

    revision = models.ForeignKey(
        DocumentRevision,
        on_delete=models.CASCADE,
        related_name="edits",
    )
    editor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_edits",
    )
    summary = models.CharField(max_length=500, blank=True)
    content_snapshot = models.TextField(blank=True)
    fields_to_check = []

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Document edit")
        verbose_name_plural = _("Document edits")

    def save(self, *args, **kwargs):
        self.folder = self.revision.folder
        super().save(*args, **kwargs)

    def __str__(self):
        editor_str = self.editor.email if self.editor else "unknown"
        return f"Edit by {editor_str} on {self.created_at}"
