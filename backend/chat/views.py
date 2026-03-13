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
from .providers import get_llm, is_ollama_available

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
        page_context = serializer.validated_data.get("page_context", {})

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

        # Try tool calling first, fall back to RAG semantic search
        from .rag import (
            search,
            graph_expand,
            format_context,
            build_context_refs,
            get_accessible_folder_ids,
        )
        from .orm_query import format_query_result
        from .tools import get_tools, dispatch_tool_call

        accessible_folders = get_accessible_folder_ids(request.user)
        context_refs = []
        context = ""
        query_result = None

        # Step 1: Ask the LLM if this is a tool call (structured query)
        llm = get_llm()

        # Build page context prefix for the LLM
        page_context_prefix = ""
        if page_context:
            page_path = page_context.get("path", "")
            page_model = page_context.get("model", "")
            page_title = page_context.get("title", "")
            parts = []
            if page_path:
                parts.append(f"path={page_path}")
            if page_model:
                parts.append(f"model={page_model}")
            if page_title:
                parts.append(f"title={page_title}")
            if parts:
                page_context_prefix = (
                    f"The user is currently viewing: {', '.join(parts)}. "
                    "Use this context if the user refers to 'this', 'these', 'here', "
                    "or asks about items on their current page.\n\n"
                )

        # Inject previous query metadata so the LLM can handle follow-ups
        # like "give me more", "next page", "show me page 3"
        last_query_meta = _get_last_query_meta(session)
        tool_prompt = user_content
        if page_context_prefix or last_query_meta:
            tool_prompt = page_context_prefix
            if last_query_meta:
                tool_prompt += (
                    f"Previous query context: model={last_query_meta.get('model')}, "
                    f"domain={last_query_meta.get('domain', 'all')}, "
                    f"page={last_query_meta.get('page', 1)}, "
                    f"total_pages={last_query_meta.get('total_pages', 1)}, "
                    f"total_count={last_query_meta.get('total_count', 0)}. "
                    f"If the user asks for 'more', 'next', 'next page', etc., "
                    f"repeat the same query with page={last_query_meta.get('page', 1) + 1}.\n\n"
                )
            tool_prompt += f"User message: {user_content}"

        tool_response = llm.tool_call(
            tool_prompt,
            get_tools(),
            history=list(
                session.messages.order_by("created_at").values("role", "content")
            )[-20:],
        )

        if tool_response and tool_response.get("name"):
            logger.info(
                "Tool call: %s(%s)",
                tool_response["name"],
                tool_response.get("arguments", {}),
            )
            query_result = dispatch_tool_call(
                tool_response["name"],
                tool_response.get("arguments", {}),
                accessible_folders,
            )

        # Track if this is a creation proposal (different SSE flow)
        creation_proposal = None

        if query_result and query_result.get("type") == "propose_create":
            # Creation proposal — don't execute, let the user confirm via UI
            creation_proposal = query_result
            item_names = [i["name"] for i in query_result.get("items", [])]
            context = (
                "INSTRUCTIONS: You have proposed creating the following "
                f"{query_result['display_name']}:\n"
                + "\n".join(f"  - {name}" for name in item_names)
                + "\n\nTell the user you're proposing to create these items. "
                "The confirmation cards are shown in the UI — tell them to review and confirm. "
                "Do NOT say you have created them. Be brief."
            )
            # Store proposal in context_refs for persistence
            context_refs.append(
                {
                    "source": "pending_action",
                    "action": "create",
                    "model_key": query_result["model_key"],
                    "url_slug": query_result["url_slug"],
                    "display_name": query_result["display_name"],
                    "items": query_result["items"],
                }
            )
        elif query_result:
            context = (
                "INSTRUCTIONS: The following data comes from a database query. "
                "Present ONLY this data to the user. Use the total_count as the authoritative count. "
                "The listed items are one page of results. Do NOT add explanations, "
                "framework references, or commentary beyond what is in the data. "
                "Do NOT hallucinate additional information.\n\n"
                + format_query_result(query_result)
            )
            url_slug = query_result.get("url_slug", "")
            for obj in query_result.get("objects", []):
                context_refs.append(
                    {
                        "type": query_result["model_name"],
                        "id": obj.get("id", ""),
                        "name": obj.get("name", ""),
                        "url": f"/{url_slug}/{obj.get('id', '')}",
                        "source": "orm_query",
                    }
                )
            # Save query metadata for follow-up (next page, etc.)
            context_refs.append(
                {
                    "source": "query_meta",
                    "model": tool_response.get("arguments", {}).get("model"),
                    "domain": tool_response.get("arguments", {}).get("domain"),
                    "page": query_result.get("page", 1),
                    "total_pages": query_result.get("total_pages", 1),
                    "total_count": query_result.get("total_count", 0),
                }
            )
        else:
            # Step 2: Semantic RAG search
            results = search(user_content, request.user, top_k=10)

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

        # Prepend page context to the LLM context so it knows where the user is
        if page_context_prefix and not query_result:
            context = page_context_prefix + context

        def stream_response():
            """Generator for SSE streaming."""
            full_response = ""

            try:
                # Emit pending_action event before streaming text if this is a creation proposal
                if creation_proposal:
                    action_data = json.dumps(
                        {
                            "type": "pending_action",
                            "action": "create",
                            "model_key": creation_proposal["model_key"],
                            "url_slug": creation_proposal["url_slug"],
                            "display_name": creation_proposal["display_name"],
                            "items": creation_proposal["items"],
                        }
                    )
                    yield f"data: {action_data}\n\n"

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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ollama_models(request):
    """List available models from the Ollama server."""
    from .providers import get_chat_settings

    settings = get_chat_settings()
    base_url = settings["ollama_base_url"]

    try:
        import httpx

        resp = httpx.get(f"{base_url}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = [
            {
                "name": m["name"],
                "size": m.get("size"),
                "modified_at": m.get("modified_at"),
            }
            for m in data.get("models", [])
        ]
        return Response({"models": models})
    except Exception as e:
        logger.warning("Failed to fetch Ollama models: %s", e)
        return Response(
            {"models": [], "error": "Unable to connect to Ollama service."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def _get_last_query_meta(session) -> dict | None:
    """
    Find the most recent query metadata from the session's assistant messages.
    Used to support follow-up queries like 'next page', 'give me more'.
    """
    last_msgs = session.messages.filter(role=ChatMessage.Role.ASSISTANT).order_by(
        "-created_at"
    )[:3]
    for msg in last_msgs:
        if not msg.context_refs:
            continue
        for ref in msg.context_refs:
            if isinstance(ref, dict) and ref.get("source") == "query_meta":
                return ref
    return None
