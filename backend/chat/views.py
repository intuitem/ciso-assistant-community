import json
import logging

from django.http import StreamingHttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .models import ChatSession, ChatMessage, IndexedDocument
from .serializers import (
    ChatSessionListSerializer,
    SendMessageSerializer,
)
from .providers import get_llm, get_embedder, is_ollama_available

logger = logging.getLogger(__name__)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "chat.serializers"


class ChatSessionViewSet(BaseModelViewSet):
    """ViewSet for chat sessions with streaming message endpoint."""

    model = ChatSession

    def get_queryset(self):
        # Users can only see their own sessions
        return ChatSession.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = ChatSessionListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="message")
    def send_message(self, request, pk=None):
        """
        Send a message and get a streaming SSE response.
        The response includes RAG retrieval + LLM generation.
        """
        session = self.get_object()

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_content = serializer.validated_data["content"]

        # Save user message
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_content,
        )

        # Auto-set title from first message
        if not session.title:
            session.title = user_content[:100]
            session.save(update_fields=["title"])

        # Perform RAG retrieval
        from .rag import (
            search,
            graph_expand,
            format_context,
            build_context_refs,
            get_accessible_folder_ids,
        )

        results = search(user_content, request.user, top_k=10)
        accessible_folders = get_accessible_folder_ids(request.user)

        # Graph expansion for structured objects
        structured = [r for r in results if r.get("source_type") == "model"]
        expanded = graph_expand(structured, accessible_folders) if structured else []

        context = format_context(results, expanded)
        context_refs = build_context_refs(results, expanded)

        # Build conversation history for the LLM (exclude the message we just saved)
        history_messages = list(
            session.messages.order_by("created_at").values("role", "content")
        )
        # Remove the last entry (the user message we just created) — it's passed separately
        if (
            history_messages
            and history_messages[-1]["role"] == "user"
            and history_messages[-1]["content"] == user_content
        ):
            history_messages = history_messages[:-1]
        # Keep only the last 20 messages to stay within context limits
        history_messages = history_messages[-20:]

        def stream_response():
            """Generator for SSE streaming."""
            llm = get_llm()
            full_response = ""

            try:
                for token in llm.stream(
                    user_content, context, history=history_messages
                ):
                    full_response += token
                    # SSE format
                    data = json.dumps({"type": "token", "content": token})
                    yield f"data: {data}\n\n"

                # Save assistant message
                ChatMessage.objects.create(
                    session=session,
                    role=ChatMessage.Role.ASSISTANT,
                    content=full_response,
                    context_refs=context_refs,
                )

                # Send completion event with context refs
                done_data = json.dumps(
                    {
                        "type": "done",
                        "context_refs": context_refs,
                    }
                )
                yield f"data: {done_data}\n\n"

            except Exception as e:
                logger.error("Chat stream error: %s", e)
                error_msg = "Sorry, I encountered an error generating a response. Please check that the LLM service is configured and running."
                ChatMessage.objects.create(
                    session=session,
                    role=ChatMessage.Role.ASSISTANT,
                    content=error_msg,
                )
                error_data = json.dumps({"type": "error", "content": error_msg})
                yield f"data: {error_data}\n\n"

        response = StreamingHttpResponse(
            stream_response(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(detail=True, methods=["post"], url_path="upload")
    def upload_document(self, request, pk=None):
        """Upload a document to be indexed for RAG in this session's folder context."""
        session = self.get_object()
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        from django.contrib.contenttypes.models import ContentType

        doc = IndexedDocument.objects.create(
            folder=session.folder,
            file=file,
            filename=file.name,
            content_type=file.content_type or "application/octet-stream",
            source_type=IndexedDocument.SourceType.CHAT,
            source_content_type=ContentType.objects.get_for_model(ChatSession),
            source_object_id=session.id,
        )

        # Queue async indexing
        from .tasks import ingest_document

        ingest_document(str(doc.id))

        return Response(
            {"id": str(doc.id), "filename": doc.filename, "status": doc.status},
            status=status.HTTP_201_CREATED,
        )


class IndexedDocumentViewSet(BaseModelViewSet):
    """ViewSet for managing indexed documents."""

    model = IndexedDocument
    filterset_fields = ["folder", "source_type", "status"]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_status(request):
    """Check chat service health: Ollama availability, index status."""
    from .providers import get_chat_settings

    settings = get_chat_settings()
    ollama_ok = is_ollama_available()

    return Response(
        {
            "ollama_available": ollama_ok,
            "ollama_url": settings["ollama_base_url"],
            "ollama_model": settings["ollama_model"],
            "embedding_backend": settings["embedding_backend"],
        }
    )
