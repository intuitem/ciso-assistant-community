from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel
from core.models import I18nObjectMixin
from core.validators import validate_file_name, validate_file_size
from iam.models import FolderMixin, User


class DocumentContainer(AbstractBaseModel, FolderMixin):
    """Language-independent identity of a managed document.

    Groups its per-locale ``ManagedDocument`` realizations and owns the
    language-independent facts (type, folder, name) plus the typed object
    links (Stream E.1). Links are purely associative — they never drive the
    document's folder or publication state.
    """

    class DocumentType(models.TextChoices):
        POLICY = "policy", _("Policy")
        PROCEDURE = "procedure", _("Procedure")
        CHARTER = "charter", _("Charter")
        RECORD = "record", _("Record")
        OTHER = "other", _("Other")

    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.POLICY,
        verbose_name=_("Document type"),
    )
    name = models.CharField(max_length=200, blank=True, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    # Typed object links (Stream E.1). Policy is a proxy of AppliedControl, so the
    # two M2Ms must use distinct reverse names or Django's E304 check fails (the
    # proxy inherits the base's reverse accessor). The frontend labels both "Documents".
    policies = models.ManyToManyField(
        "core.Policy", blank=True, related_name="documents"
    )
    applied_controls = models.ManyToManyField(
        "core.AppliedControl", blank=True, related_name="control_documents"
    )
    task_templates = models.ManyToManyField(
        "core.TaskTemplate", blank=True, related_name="documents"
    )
    processings = models.ManyToManyField(
        "privacy.Processing", blank=True, related_name="documents"
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Document container")
        verbose_name_plural = _("Document containers")

    def __str__(self):
        return self.name or str(self.id)


class ManagedDocument(AbstractBaseModel, FolderMixin, I18nObjectMixin):
    """A single-locale realization of a DocumentContainer, owning the versioned
    content (its DocumentRevision chain) and per-locale lifecycle."""

    container = models.ForeignKey(
        DocumentContainer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
    )
    name = models.CharField(max_length=200, blank=True, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    current_revision = models.ForeignKey(
        "DocumentRevision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    template_used = models.CharField(max_length=200, null=True, blank=True)
    fields_to_check = ["container", "locale"]

    class Meta:
        verbose_name = _("Managed document")
        verbose_name_plural = _("Managed documents")

    def save(self, *args, **kwargs):
        if self.container_id:
            self.folder = self.container.folder
            self.is_published = self.container.is_published
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        if self.name:
            return self.name
        if self.container_id and self.container.name:
            return self.container.name
        return str(self.id)

    def __str__(self):
        return self.display_name


class DocumentRevision(AbstractBaseModel, FolderMixin):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        IN_REVIEW = "in_review", _("In review")
        CHANGE_REQUESTED = "change_requested", _("Change requested")
        VALIDATED = "validated", _("Validated")
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

    class Source(models.TextChoices):
        AUTHORED = "authored", _("Authored")
        UPLOADED = "uploaded", _("Uploaded")

    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.AUTHORED
    )
    # Source-of-truth file for uploaded revisions (authored revisions render
    # markdown from `content` instead).
    file = models.FileField(
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
        self.is_published = self.document.is_published
        if self.status == self.Status.DRAFT:
            existing = self.document.revisions.filter(status=self.Status.DRAFT).exclude(
                pk=self.pk
            )
            if existing.exists():
                raise ValidationError("Only one draft revision allowed per document.")
        super().save(*args, **kwargs)

    def validate(self, reviewer=None):
        """Validate this revision: mark as approved, pending publication."""
        self.status = self.Status.VALIDATED
        if reviewer:
            self.reviewer = reviewer
        self.save()

    def publish(self):
        """Publish this revision: set PUBLISHED, deprecate old, set as current."""
        with transaction.atomic():
            self.status = self.Status.PUBLISHED
            self.published_at = timezone.now()
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

    def delete(self, *args, **kwargs):
        if self.pdf_snapshot:
            self.pdf_snapshot.delete(save=False)
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)

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
        self.is_published = self.document.is_published
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)

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
        self.is_published = self.revision.is_published
        super().save(*args, **kwargs)

    def __str__(self):
        editor_str = self.editor.email if self.editor else "unknown"
        return f"Edit by {editor_str} on {self.created_at}"


class DocumentTemplate(AbstractBaseModel, FolderMixin, I18nObjectMixin):
    """A reusable content skeleton for seeding a document's markdown.

    Built-ins are synced from ``backend/library/policy_templates/`` by the
    ``sync_document_templates`` management command; customers can add their own.
    Locale variants of one logical template share a ``ref_id``.
    """

    document_type = models.CharField(
        max_length=20,
        choices=DocumentContainer.DocumentType.choices,
        default=DocumentContainer.DocumentType.POLICY,
        verbose_name=_("Document type"),
    )
    ref_id = models.CharField(max_length=100, verbose_name=_("Reference"))
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    content = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    builtin = models.BooleanField(default=False)
    fields_to_check = ["ref_id", "locale"]

    class Meta:
        verbose_name = _("Document template")
        verbose_name_plural = _("Document templates")
        constraints = [
            models.UniqueConstraint(
                fields=["ref_id", "locale"], name="unique_template_ref_locale"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.locale})"
