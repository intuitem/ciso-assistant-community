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

        # Detect intent: structured ORM query vs semantic search
        from .rag import (
            search,
            graph_expand,
            format_context,
            build_context_refs,
            get_accessible_folder_ids,
        )
        from .orm_query import (
            detect_intent,
            detect_followup,
            execute_query,
            execute_followup,
            format_query_result,
        )

        accessible_folders = get_accessible_folder_ids(request.user)
        intent = detect_intent(user_content)
        context_refs = []
        query_result = None

        # Check for follow-up to a previous ORM query
        followup = detect_followup(user_content)
        if followup and intent != "query":
            # Look for previous ORM query metadata in recent assistant messages
            previous_meta = _get_last_query_meta(session)
            if previous_meta:
                query_result = execute_followup(
                    followup, previous_meta, accessible_folders
                )
                if query_result:
                    intent = "query"

        if intent == "query" and not query_result:
            # Structured ORM query
            query_result = execute_query(user_content, accessible_folders)
            if not query_result:
                # Fallback to semantic search if ORM query couldn't parse
                intent = "search"

        if query_result:
            context = format_query_result(query_result)
            # Build refs from query results
            for obj in query_result.get("objects", []):
                context_refs.append(
                    {
                        "type": query_result["model_name"],
                        "id": obj.get("id", ""),
                        "name": obj.get("name", ""),
                        "source": "orm_query",
                    }
                )
            # Save query metadata for follow-up queries
            context_refs.append(
                {
                    "source": "orm_query_meta",
                    "model_name": query_result["model_name"],
                    "app_label": _get_app_label(query_result["model_name"]),
                    "display_name": query_result["display_name"],
                    "filters_applied": query_result.get("filters_applied", []),
                    "filters": _extract_saved_filters(query_result),
                    "page": query_result.get("page", 1),
                    "total_count": query_result["total_count"],
                    "query_type": query_result["query_type"],
                }
            )

        if intent != "query":
            # Semantic RAG search
            results = search(user_content, request.user, top_k=10)

            # Graph expansion for structured objects
            structured = [r for r in results if r.get("source_type") == "model"]
            expanded = (
                graph_expand(structured, accessible_folders) if structured else []
            )

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


def _get_last_query_meta(session) -> dict | None:
    """
    Find the most recent ORM query metadata from the session's assistant messages.
    Returns the saved query meta dict if found.
    """
    last_assistant_msgs = session.messages.filter(
        role=ChatMessage.Role.ASSISTANT
    ).order_by("-created_at")[:3]
    for msg in last_assistant_msgs:
        if not msg.context_refs:
            continue
        for ref in msg.context_refs:
            if isinstance(ref, dict) and ref.get("source") == "orm_query_meta":
                return ref
    return None


def _get_app_label(model_name: str) -> str:
    """Map a model name back to its app_label."""
    from .orm_query import MODEL_REGISTRY

    for _alias, (app_label, mname, _display) in MODEL_REGISTRY.items():
        if mname == model_name:
            return app_label
    return "core"


def _extract_saved_filters(query_result: dict) -> dict:
    """
    Extract the ORM filter kwargs from a query result so they can be
    re-applied in a follow-up query. We rebuild from filters_applied labels.
    """
    # The filters_applied are human-readable labels like "domain = DEMO", "status = active"
    # We need to save the actual ORM filter kwargs.
    # For now, we extract what we can from the result metadata.
    filters = {}

    for label in query_result.get("filters_applied", []):
        if label.startswith("domain = "):
            # Need to look up folder IDs by name
            domain_name = label[len("domain = ") :]
            from iam.models import Folder

            folder_ids = list(
                Folder.objects.filter(name__in=domain_name.split(", ")).values_list(
                    "id", flat=True
                )
            )
            if folder_ids:
                filters["folder_id__in"] = [str(fid) for fid in folder_ids]
        elif label.startswith("status = "):
            filters["status"] = label[len("status = ") :]
        elif label.startswith("treatment = "):
            filters["treatment"] = label[len("treatment = ") :]
        elif label.startswith("result = "):
            filters["result"] = label[len("result = ") :]
        elif label.startswith("priority = P"):
            try:
                filters["priority"] = int(label[len("priority = P") :])
            except ValueError:
                pass
        elif label.startswith("category = "):
            filters["category"] = label[len("category = ") :]
        elif label.startswith("effort = "):
            filters["effort"] = label[len("effort = ") :]
        elif label.startswith("severity = "):
            try:
                filters["severity"] = int(label[len("severity = ") :])
            except ValueError:
                pass

    return filters
