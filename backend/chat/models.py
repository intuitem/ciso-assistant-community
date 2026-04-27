import uuid

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel
from core.validators import validate_file_size, validate_file_name
from iam.models import FolderMixin, User


class ChatSession(AbstractBaseModel, FolderMixin):
    """A chat conversation scoped to a folder for permission filtering."""

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        verbose_name=_("Owner"),
    )
    title = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Title")
    )
    workflow_state = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Workflow state"),
        help_text=_(
            "Persisted checkpoint for multi-step workflows. "
            "Cleared when the workflow completes or the session is reset."
        ),
    )

    class Meta:
        verbose_name = _("Chat session")
        verbose_name_plural = _("Chat sessions")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Chat {self.created_at:%Y-%m-%d %H:%M}"


class ChatMessage(models.Model):
    """A single message in a chat session."""

    class Role(models.TextChoices):
        USER = "user", _("User")
        ASSISTANT = "assistant", _("Assistant")
        SYSTEM = "system", _("System")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Session"),
    )
    role = models.CharField(max_length=10, choices=Role.choices, verbose_name=_("Role"))
    content = models.TextField(verbose_name=_("Content"))
    # References to objects that were retrieved/cited in this message
    context_refs = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Context references"),
        help_text=_("Objects retrieved or cited: [{type, id, name, score}]"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        verbose_name = _("Chat message")
        verbose_name_plural = _("Chat messages")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class IndexedDocument(AbstractBaseModel, FolderMixin):
    """Tracks documents ingested into the vector store for RAG."""

    class SourceType(models.TextChoices):
        CHAT = "chat", _("Chat upload")
        EVIDENCE = "evidence", _("Evidence attachment")
        CUSTOM = "custom", _("Custom upload")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        INDEXED = "indexed", _("Indexed")
        FAILED = "failed", _("Failed")

    file = models.FileField(
        upload_to="rag_documents/",
        validators=[validate_file_size, validate_file_name],
        verbose_name=_("File"),
    )
    filename = models.CharField(max_length=255, verbose_name=_("Filename"))
    content_type = models.CharField(max_length=100, verbose_name=_("Content type"))

    # Polymorphic source linkage
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        verbose_name=_("Source type"),
    )
    source_content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Source content type"),
    )
    source_object_id = models.UUIDField(
        null=True, blank=True, verbose_name=_("Source object ID")
    )
    source_object = GenericForeignKey("source_content_type", "source_object_id")

    # Indexing state
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
    )
    chunk_count = models.IntegerField(default=0, verbose_name=_("Chunk count"))
    error_message = models.TextField(
        blank=True, default="", verbose_name=_("Error message")
    )
    indexed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Indexed at")
    )

    class Meta:
        verbose_name = _("Indexed document")
        verbose_name_plural = _("Indexed documents")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} ({self.status})"
