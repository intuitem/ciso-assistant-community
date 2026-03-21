from rest_framework import serializers

from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField
from .models import ChatSession, ChatMessage, IndexedDocument


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
        exclude = ["created_at", "updated_at", "owner"]


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
