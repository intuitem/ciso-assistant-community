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
    summary = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Rolling summary"),
        help_text=_(
            "Compact summary of older exchanges that have fallen off the "
            "verbatim window. Updated incrementally one exchange at a time."
        ),
    )
    summary_until_ts = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Summarized up to"),
        help_text=_(
            "Watermark — created_at of the most recent message folded into "
            "the rolling summary. Null = nothing folded yet."
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
    tool_observation = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Tool observation"),
        help_text=_(
            "Captured read-only tool result (tool name, args, truncated text). "
            "Replayed in the next ~2 turns; not enforced beyond that window."
        ),
    )
    metrics = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Turn metrics"),
        help_text=_(
            "Token utilization snapshot for this turn (prompt/context/"
            "history/summary tokens, over_budget, high_watermark)."
        ),
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


class QuestionnaireRun(AbstractBaseModel, FolderMixin):
    """Experimental: a customer security questionnaire being prefilled.

    Lifecycle: PENDING -> PARSING -> PARSED (ready for review) -> FAILED.
    LLM prefill is layered on top later; this model is shape-stable enough
    to absorb that step without a schema rewrite.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PARSING = "parsing", _("Parsing")
        PARSED = "parsed", _("Parsed")
        FAILED = "failed", _("Failed")

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="questionnaire_runs",
        verbose_name=_("Owner"),
    )
    title = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Title")
    )
    file = models.FileField(
        upload_to="questionnaires/",
        validators=[validate_file_size, validate_file_name],
        verbose_name=_("File"),
    )
    filename = models.CharField(max_length=255, verbose_name=_("Filename"))

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
    )
    error_message = models.TextField(
        blank=True, default="", verbose_name=_("Error message")
    )
    parsed_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Parsed data"),
        help_text=_(
            "{sheets: [{name, header_row, headers, row_count, rows_preview}], "
            "active_sheet}. Populated by the parse task."
        ),
    )
    column_mapping = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Column mapping"),
        help_text=_(
            "{sheet, question_col, answer_col, comment_col, section_col}. "
            "Indices are 0-based positions inside that sheet's headers."
        ),
    )
    value_mapping = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Value mapping"),
        help_text=_(
            "{yes, partial, no, needs_info, source} — maps internal status "
            "labels onto the customer's vocabulary, plus a 'source' tag "
            "('data_validation' | 'distinct_values' | 'fallback'). Computed "
            "asynchronously after column mapping is saved; export uses it "
            "when present."
        ),
    )

    class Meta:
        verbose_name = _("Questionnaire run")
        verbose_name_plural = _("Questionnaire runs")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or self.filename or f"Run {self.id}"


class QuestionnaireQuestion(AbstractBaseModel):
    """A single question materialized from a QuestionnaireRun's mapped sheet.

    Created by the extract-questions step. The latest `propose_answer`
    AgentAction targeting this row is the current answer.
    Named `QuestionnaireQuestion` to avoid permission-codename collision
    with `core.Question`.
    """

    questionnaire_run = models.ForeignKey(
        QuestionnaireRun,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name=_("Questionnaire run"),
    )
    ord = models.IntegerField(
        verbose_name=_("Order"),
        help_text=_("0-based row index in the source sheet, used for export."),
    )
    ref_id = models.CharField(
        max_length=100, blank=True, default="", verbose_name=_("Reference ID")
    )
    section = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Section")
    )
    text = models.TextField(verbose_name=_("Question text"))

    answer_candidates = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Answer candidates"),
        help_text=_(
            "Controlled vocabulary the customer expects in this question's "
            "answer cell, captured from the Excel data-validation list (or "
            "distinct existing values). Empty list = free-text cell."
        ),
    )
    answer_mapping = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Answer mapping"),
        help_text=_(
            "{yes, partial, no, source} mapping our internal status onto this "
            "question's vocabulary. Filled by suggest_value_mapping after "
            "extract; export uses it per-question (rather than the run-level "
            "value_mapping) so questionnaires with mixed vocabularies still "
            "produce a clean fill."
        ),
    )

    class Meta:
        verbose_name = _("Questionnaire question")
        verbose_name_plural = _("Questionnaire questions")
        ordering = ["ord"]
        unique_together = [("questionnaire_run", "ord")]

    def __str__(self):
        prefix = f"{self.ref_id} — " if self.ref_id else ""
        return f"{prefix}{self.text[:80]}"


class AgentRun(AbstractBaseModel, FolderMixin):
    """An agent execution. Generic over kind; first kind is questionnaire_prefill."""

    class Kind(models.TextChoices):
        QUESTIONNAIRE_PREFILL = "questionnaire_prefill", _("Questionnaire prefill")

    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued")
        RUNNING = "running", _("Running")
        SUCCEEDED = "succeeded", _("Succeeded")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    class Strictness(models.TextChoices):
        FAST = "fast", _("Fast")
        THOROUGH = "thorough", _("Thorough")

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="agent_runs",
        verbose_name=_("Owner"),
    )
    kind = models.CharField(max_length=40, choices=Kind.choices, verbose_name=_("Kind"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        verbose_name=_("Status"),
    )
    strictness = models.CharField(
        max_length=20,
        choices=Strictness.choices,
        default=Strictness.FAST,
        verbose_name=_("Strictness"),
    )

    target_content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Target content type"),
    )
    target_object_id = models.UUIDField(
        null=True, blank=True, verbose_name=_("Target object ID")
    )
    target = GenericForeignKey("target_content_type", "target_object_id")

    chat_session = models.ForeignKey(
        ChatSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="agent_runs",
        verbose_name=_("Chat session"),
        help_text=_("Optional — only set when the run uses chat (e.g. ask_user)."),
    )

    total_steps = models.IntegerField(default=0, verbose_name=_("Total steps"))
    completed_steps = models.IntegerField(default=0, verbose_name=_("Completed steps"))
    current_step_label = models.CharField(
        max_length=300, blank=True, default="", verbose_name=_("Current step label")
    )
    last_heartbeat_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last heartbeat")
    )

    total_tokens = models.IntegerField(default=0, verbose_name=_("Total tokens"))
    estimated_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name=_("Estimated cost (USD)"),
    )
    model_used = models.CharField(
        max_length=200, blank=True, default="", verbose_name=_("Model used")
    )

    started_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Started at")
    )
    finished_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Finished at")
    )
    error_message = models.TextField(
        blank=True, default="", verbose_name=_("Error message")
    )

    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Config"),
        help_text=_(
            "Per-run scratch space for mode flags, source pointers, and "
            "other kind-specific knobs (e.g. {mode: 'external', "
            "ingest_namespace: 'agentrun:<uuid>'}). Read by the worker, "
            "not exposed to clients for direct write."
        ),
    )

    class Meta:
        verbose_name = _("Agent run")
        verbose_name_plural = _("Agent runs")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} ({self.status})"


class AgentAction(AbstractBaseModel):
    """One unit of agent work — a single tool call, LLM call, or proposal."""

    class Kind(models.TextChoices):
        RETRIEVE = "retrieve", _("Retrieve")
        PROPOSE_ANSWER = "propose_answer", _("Propose answer")
        CRITIQUE = "critique", _("Critique")
        RETRY = "retry", _("Retry")

    class State(models.TextChoices):
        PROPOSED = "proposed", _("Proposed")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        EXPIRED = "expired", _("Expired")

    agent_run = models.ForeignKey(
        AgentRun,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name=_("Agent run"),
    )
    kind = models.CharField(max_length=30, choices=Kind.choices, verbose_name=_("Kind"))

    target_content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Target content type"),
    )
    target_object_id = models.UUIDField(
        null=True, blank=True, verbose_name=_("Target object ID")
    )
    target = GenericForeignKey("target_content_type", "target_object_id")

    payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Payload"),
        help_text=_("Action result. For propose_answer: {status, comment}."),
    )
    rationale = models.TextField(blank=True, default="", verbose_name=_("Rationale"))
    source_refs = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Source references"),
        help_text=_("[{kind, id, name, score, snippet}]"),
    )
    confidence = models.FloatField(null=True, blank=True, verbose_name=_("Confidence"))
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.PROPOSED,
        verbose_name=_("State"),
    )
    iteration = models.IntegerField(default=0, verbose_name=_("Iteration"))

    tokens = models.IntegerField(default=0, verbose_name=_("Tokens"))
    duration_ms = models.IntegerField(default=0, verbose_name=_("Duration (ms)"))

    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_actions",
        verbose_name=_("Approved by"),
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Approved at")
    )

    class Meta:
        verbose_name = _("Agent action")
        verbose_name_plural = _("Agent actions")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.kind} [{self.state}]"
