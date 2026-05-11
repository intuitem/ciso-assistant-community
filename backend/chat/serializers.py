from rest_framework import serializers

from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField
from .models import (
    ChatSession,
    ChatMessage,
    IndexedDocument,
    QuestionnaireRun,
    QuestionnaireQuestion,
    AgentRun,
    AgentAction,
)


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "context_refs", "created_at"]
        read_only_fields = ["id", "role", "context_refs", "created_at"]


class ChatSessionReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owner = FieldsRelatedField()
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        exclude = []

    def get_message_count(self, obj) -> int:
        return obj.messages.count()


class ChatSessionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ChatSession
        exclude = ["created_at", "updated_at", "owner", "workflow_state"]


class ChatSessionListSerializer(BaseModelSerializer):
    """Lightweight serializer for listing sessions (no messages)."""

    folder = FieldsRelatedField()
    owner = FieldsRelatedField()
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "title",
            "folder",
            "owner",
            "message_count",
            "created_at",
            "updated_at",
        ]

    def get_message_count(self, obj) -> int:
        return obj.messages.count()


class SendMessageSerializer(serializers.Serializer):
    """Input serializer for sending a message to a chat session."""

    content = serializers.CharField(max_length=10000)
    page_context = serializers.DictField(required=False, default=dict)

    def validate_page_context(self, value):
        """Whitelist page_context keys and sanitize values."""
        if not value:
            return {}
        allowed_keys = {"path", "model", "title"}
        sanitized = {}
        for key in allowed_keys:
            if key in value and isinstance(value[key], str):
                # Strip control characters and limit length
                sanitized[key] = value[key][:200].strip()
        return sanitized


class IndexedDocumentReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()

    class Meta:
        model = IndexedDocument
        exclude = []


class IndexedDocumentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = IndexedDocument
        exclude = [
            "created_at",
            "updated_at",
            "status",
            "chunk_count",
            "error_message",
            "indexed_at",
        ]


class QuestionnaireRunReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owner = FieldsRelatedField()

    class Meta:
        model = QuestionnaireRun
        exclude = []


class QuestionnaireRunListSerializer(BaseModelSerializer):
    """Lightweight listing — drops the heavy parsed_data blob."""

    folder = FieldsRelatedField()
    owner = FieldsRelatedField()

    class Meta:
        model = QuestionnaireRun
        fields = [
            "id",
            "title",
            "filename",
            "folder",
            "owner",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]


class QuestionnaireRunWriteSerializer(BaseModelSerializer):
    """Generic CRUD writer. ``column_mapping`` / ``value_mapping`` go through
    dedicated validated endpoints (set_mapping / suggest_value_mapping) — keep
    them out of the writable surface here so a generic PATCH can't store
    arbitrary blobs that the extract step then trusts.
    """

    class Meta:
        model = QuestionnaireRun
        exclude = [
            "created_at",
            "updated_at",
            "owner",
            "status",
            "error_message",
            "parsed_data",
            "column_mapping",
            "value_mapping",
        ]


class QuestionnaireRunMappingSerializer(serializers.Serializer):
    """Input for PATCHing column_mapping on a parsed run."""

    sheet = serializers.CharField(max_length=200)
    question_col = serializers.IntegerField(min_value=0)
    answer_col = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    comment_col = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    section_col = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class QuestionnaireQuestionReadSerializer(BaseModelSerializer):
    questionnaire_run = FieldsRelatedField()

    class Meta:
        model = QuestionnaireQuestion
        exclude = []


class QuestionnaireQuestionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = QuestionnaireQuestion
        exclude = ["created_at", "updated_at"]


class AgentRunReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owner = FieldsRelatedField()

    class Meta:
        model = AgentRun
        exclude = []


class AgentRunListSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owner = FieldsRelatedField()

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "kind",
            "status",
            "strictness",
            "folder",
            "owner",
            "total_steps",
            "completed_steps",
            "current_step_label",
            "last_heartbeat_at",
            "started_at",
            "finished_at",
            "error_message",
            "model_used",
            "total_tokens",
            "estimated_cost_usd",
            "created_at",
        ]


class AgentRunWriteSerializer(BaseModelSerializer):
    """Belt-and-braces: generic create/update on AgentRun is already 405'd at
    the ViewSet, but if a future contributor re-enables it, the writable
    surface here is locked down so a client can never aim a run at an
    arbitrary object or stuff worker-owned counters.
    """

    class Meta:
        model = AgentRun
        exclude = [
            "created_at",
            "updated_at",
            "owner",
            "status",
            "total_steps",
            "completed_steps",
            "current_step_label",
            "last_heartbeat_at",
            "total_tokens",
            "estimated_cost_usd",
            "model_used",
            "started_at",
            "finished_at",
            "error_message",
        ]
        # Targeting + scope fields are set by the spawn action only;
        # ``config`` is worker-owned scratch space.
        read_only_fields = [
            "kind",
            "target_content_type",
            "target_object_id",
            "chat_session",
            "folder",
            "config",
        ]


class AgentActionWriteSerializer(BaseModelSerializer):
    """Same defence-in-depth as AgentRunWriteSerializer. Agent actions are
    AI proposals: the worker creates them, users only flip ``state`` via
    approve/reject, and the rest of the row is immutable audit data.
    """

    class Meta:
        model = AgentAction
        exclude = ["created_at", "updated_at", "approved_by", "approved_at"]
        read_only_fields = [
            "agent_run",
            "kind",
            "target_content_type",
            "target_object_id",
            "payload",
            "rationale",
            "source_refs",
            "confidence",
            "iteration",
        ]


class AgentActionReadSerializer(BaseModelSerializer):
    agent_run = FieldsRelatedField()
    approved_by = FieldsRelatedField()

    class Meta:
        model = AgentAction
        exclude = []


class StartQuestionnairePrefillSerializer(serializers.Serializer):
    """Input for kicking off a questionnaire-prefill agent run."""

    questionnaire_run = serializers.UUIDField()
    strictness = serializers.ChoiceField(
        choices=AgentRun.Strictness.choices,
        default=AgentRun.Strictness.FAST,
    )
