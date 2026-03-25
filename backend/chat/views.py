import json
import structlog
import time

from django.http import StreamingHttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .models import ChatSession, ChatMessage, IndexedDocument
from .serializers import (
    ChatSessionListSerializer,
    SendMessageSerializer,
)
from .providers import get_llm, is_ollama_available

logger = structlog.get_logger(__name__)

_LANG_MAP = {
    "fr": "French",
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "nl": "Dutch",
    "pt": "Portuguese",
    "ar": "Arabic",
    "pl": "Polish",
    "ro": "Romanian",
    "sv": "Swedish",
    "da": "Danish",
    "cs": "Czech",
    "uk": "Ukrainian",
    "el": "Greek",
    "tr": "Turkish",
    "hr": "Croatian",
    "zh": "Chinese",
    "lt": "Lithuanian",
    "ko": "Korean",
}


import re as _re

# Patterns that attempt to impersonate system/assistant roles or override instructions
_INJECTION_PATTERNS = _re.compile(
    r"(?:"
    r"\[/?(?:SYSTEM|CONTEXT|INST)\]"  # Fake delimiter tags
    r"|<\|(?:im_start|im_end|system)\|>"  # ChatML role markers
    r"|```\s*(?:system|tool_call)"  # Fenced role blocks
    r")",
    _re.IGNORECASE,
)


def _sanitize_user_input(text: str) -> str:
    """
    Neutralize prompt injection patterns in user messages.
    Strips characters that could be interpreted as role markers or
    delimiter tags by the LLM, while preserving the user's intent.
    """
    # Remove injection patterns
    text = _INJECTION_PATTERNS.sub("", text)
    # Strip null bytes and other control characters (keep newlines/tabs)
    text = "".join(
        c for c in text if c == "\n" or c == "\t" or (c >= " " and c <= "\U0010ffff")
    )
    return text.strip()


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "chat.serializers"


class ChatSessionViewSet(BaseModelViewSet):
    """ViewSet for chat sessions with streaming message endpoint."""

    model = ChatSession
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat"

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
        user_content = _sanitize_user_input(serializer.validated_data["content"])
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
        from .tools import (
            get_tools,
            dispatch_tool_call,
            PARENT_CHILD_MAP,
            ATTACHABLE_RELATIONS,
            MODEL_MAP,
        )
        from .page_context import parse_page_context

        accessible_folders = get_accessible_folder_ids(request.user)
        context_refs = []
        context = ""
        query_result = None

        # Parse page context into structured reference
        parsed_context = parse_page_context(page_context) if page_context else None

        # Step 1: Route to tool or workflow
        from .workflows import get_workflow_tools, get_workflow_by_tool_name
        from .workflows.base import WorkflowContext

        llm = get_llm()
        logger.info(
            "llm_provider_selected",
            provider=type(llm).__name__,
            page_context=page_context,
            parsed_context=str(parsed_context) if parsed_context else None,
        )

        # Step 1a: Deterministic pre-routing for workflows.
        # Small LLMs are unreliable at tool selection with 5+ tools,
        # so we match workflows by context + keywords first.
        pre_routed_workflow = _match_workflow(user_content, parsed_context)
        if pre_routed_workflow:
            logger.info("workflow_pre_routed", workflow=pre_routed_workflow.name)
            tool_response = {"name": f"workflow_{pre_routed_workflow.name}"}
        else:
            # Step 1b: LLM-based tool selection
            # Build page context prefix for the LLM
            page_context_prefix = _build_context_prompt(page_context, parsed_context)

            # Inject previous query metadata so the LLM can handle follow-ups
            # like "give me more", "next page", "show me page 3"
            last_query_meta = _get_last_query_meta(session)
            user_lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "en")[:2]
            lang_name = _LANG_MAP.get(user_lang, "English")
            tool_prompt = f"LANGUAGE: Generate all names and descriptions in {lang_name}.\n\n{user_content}"
            if page_context_prefix or last_query_meta:
                tool_prompt = f"LANGUAGE: Generate all names and descriptions in {lang_name}.\n\n{page_context_prefix}"
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

            # Combine standard tools + context-aware workflow tools
            all_tools = get_tools() + get_workflow_tools(parsed_context)

            history_for_tool = list(
                session.messages.order_by("created_at").values("role", "content")
            )[-20:]

            t0 = time.time()
            tool_response = llm.tool_call(
                tool_prompt,
                all_tools,
                history=history_for_tool,
            )
            logger.info(
                "tool_selection_complete",
                duration=round(time.time() - t0, 2),
                tool=tool_response.get("name") if tool_response else "no tool",
            )

        # Check if LLM selected a workflow (or pre-routed)
        if tool_response and tool_response.get("name", "").startswith("workflow_"):
            workflow = get_workflow_by_tool_name(tool_response["name"])
            if workflow:
                logger.info("workflow_selected", workflow=workflow.name)

                # Build conversation history (exclude the message we just saved)
                wf_history = list(
                    session.messages.order_by("created_at").values("role", "content")
                )
                if (
                    wf_history
                    and wf_history[-1]["role"] == "user"
                    and wf_history[-1]["content"] == user_content
                ):
                    wf_history = wf_history[:-1]
                wf_history = wf_history[-20:]

                wf_ctx = WorkflowContext(
                    user_message=user_content,
                    parsed_context=parsed_context,
                    accessible_folder_ids=accessible_folders,
                    llm=llm,
                    history=wf_history,
                    user_lang=request.META.get("HTTP_ACCEPT_LANGUAGE", "en")[:2],
                    session=session,
                )

                def stream_workflow():
                    full_response = ""
                    wf_context_refs = []
                    wf_start = time.time()
                    try:
                        for event in workflow.run(wf_ctx):
                            if event.type == "token":
                                full_response += (
                                    event.content
                                    if isinstance(event.content, str)
                                    else ""
                                )
                            if event.type == "pending_action" and isinstance(
                                event.content, dict
                            ):
                                wf_context_refs.append(
                                    {"source": "pending_action", **event.content}
                                )
                            yield event.encode()

                        # Strip the JSON recommendation block before saving
                        import re

                        saved_response = re.sub(
                            r"\s*```json\s*\{[^}]*\"recommended\"[^}]*\}\s*```\s*",
                            "",
                            full_response,
                        ).rstrip()
                        ChatMessage.objects.create(
                            session=session,
                            role=ChatMessage.Role.ASSISTANT,
                            content=saved_response or full_response,
                            context_refs=wf_context_refs,
                        )
                        logger.info(
                            "workflow_complete",
                            workflow=workflow.name,
                            duration=round(time.time() - wf_start, 2),
                        )
                        done_data = json.dumps(
                            {"type": "done", "context_refs": wf_context_refs}
                        )
                        yield f"data: {done_data}\n\n"

                    except Exception as e:
                        logger.error(
                            "Workflow '%s' error after %.2fs: %s",
                            workflow.name,
                            time.time() - wf_start,
                            e,
                        )
                        error_msg = "Sorry, I encountered an error. Please try again."
                        ChatMessage.objects.create(
                            session=session,
                            role=ChatMessage.Role.ASSISTANT,
                            content=error_msg,
                        )
                        error_data = json.dumps({"type": "error", "content": error_msg})
                        yield f"data: {error_data}\n\n"

                response = StreamingHttpResponse(
                    stream_workflow(), content_type="text/event-stream"
                )
                response["Cache-Control"] = "no-cache"
                response["X-Accel-Buffering"] = "no"
                return response

        if tool_response and tool_response.get("name"):
            logger.info(
                "Tool call: %s(%s)",
                tool_response["name"],
                tool_response.get("arguments", {}),
            )
            t1 = time.time()
            query_result = dispatch_tool_call(
                tool_response["name"],
                tool_response.get("arguments", {}),
                accessible_folders,
                parsed_context,
                user_message=user_content,
            )
            logger.info("tool_dispatch_complete", duration=round(time.time() - t1, 2))

        # Track if this is a creation/attach proposal (different SSE flow)
        creation_proposal = None

        if query_result and query_result.get("type") == "propose_create":
            # Creation proposal — don't execute, let the user confirm via UI
            creation_proposal = query_result
            context = (
                f"The system is proposing to create {len(query_result.get('items', []))} "
                f"{query_result['display_name']}. "
                "Interactive confirmation cards are already displayed in the UI.\n\n"
                "YOUR RESPONSE MUST:\n"
                "- Tell the user you're proposing to create these items (1 sentence).\n"
                "- Tell them to review and use the Confirm/Cancel buttons below.\n\n"
                "YOUR RESPONSE MUST NOT:\n"
                "- List the items (the UI already shows them).\n"
                "- Say you have created them.\n"
                "- Generate links or URLs.\n"
                "Keep it to 2-3 sentences maximum."
            )
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
        elif query_result and query_result.get("type") == "propose_attach":
            # Attach proposal — show existing objects to link
            creation_proposal = query_result
            context = (
                f"The system found {len(query_result.get('items', []))} existing "
                f"{query_result['related_display']} that can be attached to the current "
                f"{query_result['parent_display']}. "
                "Interactive confirmation cards are already displayed in the UI.\n\n"
                "YOUR RESPONSE MUST:\n"
                "- Briefly explain why these items were suggested (1 sentence).\n"
                "- Tell the user to review and use the Confirm/Cancel buttons below.\n\n"
                "YOUR RESPONSE MUST NOT:\n"
                "- List the items (the UI already shows them).\n"
                "- Generate links, URLs, or markdown links.\n"
                "- Include IDs, UUIDs, or technical references.\n"
                "- Describe how to use tools.\n"
                "Keep it to 2-3 sentences maximum."
            )
            context_refs.append(
                {
                    "source": "pending_action",
                    "action": "attach",
                    "parent_model_key": query_result["parent_model_key"],
                    "parent_id": query_result["parent_id"],
                    "parent_url_slug": query_result["parent_url_slug"],
                    "m2m_field": query_result["m2m_field"],
                    "related_model_key": query_result["related_model_key"],
                    "related_display": query_result["related_display"],
                    "items": query_result["items"],
                }
            )
        elif query_result and query_result.get("type") == "search_library":
            context = (
                "INSTRUCTIONS: The following data comes from the frameworks knowledge base. "
                "Present this information to the user in a clear, structured way. "
                "When citing requirements, always include the framework name and reference ID. "
                "Do NOT hallucinate additional information beyond what is provided.\n\n"
                + query_result.get("text", "No results found.")
            )
        elif query_result:
            context = (
                "INSTRUCTIONS: The following data comes from a database query. "
                "Present ONLY this data to the user. Use the total_count as the authoritative count. "
                "The listed items are one page of results. Do NOT add explanations, "
                "framework references, or commentary beyond what is in the data. "
                "Do NOT hallucinate additional information. "
                "IMPORTANT: Items include markdown links like [Name](/path/id) — "
                "you MUST preserve these links exactly as-is in your response so the user "
                "can click them. Do NOT rewrite, shorten, or remove the links.\n\n"
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
            # Step 2: Knowledge graph + Semantic RAG search
            # Check the knowledge graph for framework context, but only for
            # general questions — skip when on action pages (detail/edit)
            # where workflows and attach proposals are the expected path.
            graph_context = ""
            if not (parsed_context and parsed_context.object_id):
                graph_context = _get_graph_context(user_content)

            results = search(user_content, request.user, top_k=10)

            structured = [r for r in results if r.get("source_type") == "model"]
            expanded = (
                graph_expand(structured, accessible_folders) if structured else []
            )

            context = ""
            if graph_context:
                context = "FRAMEWORK KNOWLEDGE BASE:\n" + graph_context + "\n\n"
            context += format_context(results, expanded)
            context_refs = build_context_refs(results, expanded)

            # Step 3: Auto-suggest attachable objects when on a contextual page
            # If the LLM didn't call a tool but we're on a detail/edit page
            # with attachable relations, try attaching relevant objects automatically.
            if parsed_context and parsed_context.object_id:
                from .tools import ATTACHABLE_RELATIONS, _build_attach_proposal

                relations = ATTACHABLE_RELATIONS.get(parsed_context.model_key, [])
                if relations:
                    # Try the first attachable relation (usually applied_controls)
                    first_rel_key = relations[0][0]
                    attach_result = _build_attach_proposal(
                        {"related_model": first_rel_key},
                        accessible_folders,
                        parsed_context,
                    )
                    if attach_result and attach_result.get("items"):
                        creation_proposal = attach_result
                        item_names = [i["name"] for i in attach_result["items"]]
                        # Replace the RAG context entirely — the attach cards ARE the response
                        context = (
                            f"The system found {len(item_names)} existing "
                            f"{attach_result['related_display']} that may be relevant. "
                            "Interactive confirmation cards are already displayed in the UI "
                            "showing each item with a Confirm/Cancel button.\n\n"
                            "YOUR RESPONSE MUST:\n"
                            "- Briefly explain why these items were suggested (1-2 sentences).\n"
                            "- Tell the user to review and use the buttons below to attach them.\n\n"
                            "YOUR RESPONSE MUST NOT:\n"
                            "- List the items (the UI already shows them).\n"
                            "- Generate links, URLs, or markdown links.\n"
                            "- Include IDs, UUIDs, or technical references.\n"
                            "- Describe how to use tools or the attach_existing tool.\n"
                            "- Use emojis.\n"
                            "Keep it to 2-3 sentences maximum."
                        )
                        context_refs.append(
                            {
                                "source": "pending_action",
                                "action": "attach",
                                "parent_model_key": attach_result["parent_model_key"],
                                "parent_id": attach_result["parent_id"],
                                "parent_url_slug": attach_result["parent_url_slug"],
                                "m2m_field": attach_result["m2m_field"],
                                "related_model_key": attach_result["related_model_key"],
                                "related_display": attach_result["related_display"],
                                "items": attach_result["items"],
                            }
                        )

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

        # Assemble context with structured priorities
        from .context import ContextBuilder

        user_lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "en")[:2]
        lang_name = _LANG_MAP.get(user_lang, "English")

        ctx_builder = ContextBuilder(max_chars=12000)
        ctx_builder.add(
            "language",
            f"LANGUAGE: You MUST respond in {lang_name}.",
            priority=10,
        )
        if page_context_prefix and not query_result:
            ctx_builder.add("page_context", page_context_prefix, priority=8)
        ctx_builder.add("main_context", context, priority=9)

        # Enrich context with domain objects when on a detail page
        if parsed_context and parsed_context.object_id:
            enrichment = _enrich_context(parsed_context, accessible_folders)
            if enrichment:
                ctx_builder.add("enrichment", enrichment, priority=5)

        context = ctx_builder.build()

        logger.info(
            "llm_context_size",
            system_prompt_chars=len(llm.system_prompt)
            if hasattr(llm, "system_prompt")
            else 0,
            context_chars=len(context),
            sections=ctx_builder.section_names(),
            history_messages=len(history_messages),
            total_prompt_chars=(
                (len(llm.system_prompt) if hasattr(llm, "system_prompt") else 0)
                + len(context)
                + len(user_content)
                + sum(len(m.get("content", "")) for m in history_messages)
            ),
        )

        def stream_response():
            """Generator for SSE streaming."""
            full_response = ""

            try:
                # Emit pending_action event before streaming text
                if creation_proposal:
                    if creation_proposal.get("type") == "propose_attach":
                        action_data = json.dumps(
                            {
                                "type": "pending_action",
                                "action": "attach",
                                "parent_model_key": creation_proposal[
                                    "parent_model_key"
                                ],
                                "parent_id": creation_proposal["parent_id"],
                                "parent_url_slug": creation_proposal["parent_url_slug"],
                                "m2m_field": creation_proposal["m2m_field"],
                                "related_model_key": creation_proposal[
                                    "related_model_key"
                                ],
                                "related_display": creation_proposal["related_display"],
                                "items": creation_proposal["items"],
                            }
                        )
                    else:
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

                t_stream = time.time()
                t_first_token = None
                t_first_content = None
                thinking_count = 0
                token_count = 0
                for token_type, token in llm.stream(
                    user_content, context, history=history_messages
                ):
                    if t_first_token is None:
                        t_first_token = time.time()
                    if token_type == "token":
                        if t_first_content is None:
                            t_first_content = time.time()
                        full_response += token
                        token_count += 1
                    else:
                        thinking_count += 1
                    # SSE format — "thinking" tokens go to a collapsible block in the UI
                    data = json.dumps({"type": token_type, "content": token})
                    yield f"data: {data}\n\n"
                t_end = time.time()
                ttft = round(t_first_token - t_stream, 2) if t_first_token else None
                thinking_duration = (
                    round(t_first_content - t_first_token, 2)
                    if t_first_content and t_first_token
                    else None
                )
                content_elapsed = t_end - (t_first_content or t_end)
                tps = (
                    round(token_count / content_elapsed, 1)
                    if content_elapsed > 0
                    else None
                )
                logger.info(
                    "llm_stream_complete",
                    duration=round(t_end - t_stream, 2),
                    ttft_s=ttft,
                    thinking_s=thinking_duration,
                    thinking_tokens=thinking_count,
                    tokens=token_count,
                    tokens_per_s=tps,
                )

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
                # Save whatever was generated before the failure
                saved_content = full_response.strip()
                if saved_content:
                    saved_content += "\n\n---\n*Response interrupted due to an error.*"
                else:
                    saved_content = (
                        "Sorry, I encountered an error generating a response. "
                        "Please check that the LLM service is configured and running."
                    )
                ChatMessage.objects.create(
                    session=session,
                    role=ChatMessage.Role.ASSISTANT,
                    content=saved_content,
                )
                error_data = json.dumps({"type": "error", "content": saved_content})
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
            "llm_provider": settings.get("llm_provider", "ollama"),
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


def _build_context_prompt(page_context: dict, parsed_context) -> str:
    """
    Build a rich context prompt for the LLM based on the user's current page.
    Includes structured hints about available contextual actions.
    """
    if not page_context:
        return ""

    from .tools import PARENT_CHILD_MAP, ATTACHABLE_RELATIONS, MODEL_MAP

    parts = []
    page_path = page_context.get("path", "")
    page_model = page_context.get("model", "")
    page_title = page_context.get("title", "")

    info_parts = []
    if page_path:
        info_parts.append(f"path={page_path}")
    if page_model:
        info_parts.append(f"model={page_model}")
    if page_title:
        info_parts.append(f"title={page_title}")

    if not info_parts:
        return ""

    parts.append(
        f"The user is currently viewing: {', '.join(info_parts)}.\n"
        "NOTE: The page title above is for context only — do NOT use it as a search filter. "
        "When querying child objects of this page, rely on the automatic parent scoping (no search needed)."
    )

    # Add contextual action hints when on a detail/edit page
    if parsed_context and parsed_context.object_id:
        actions = []

        # Child creation hints
        for child_key, fk_field in PARENT_CHILD_MAP.get(parsed_context.model_key, []):
            if child_key in MODEL_MAP:
                child_display = MODEL_MAP[child_key][2]
                actions.append(
                    f"- Create {child_display} linked to this {page_model or parsed_context.model_key}"
                )

        # Attachment hints
        for rel_key, m2m_field in ATTACHABLE_RELATIONS.get(
            parsed_context.model_key, []
        ):
            if rel_key in MODEL_MAP:
                rel_display = MODEL_MAP[rel_key][2]
                actions.append(
                    f"- Attach existing {rel_display} to this {page_model or parsed_context.model_key} "
                    f"(use attach_existing tool with related_model='{rel_key}')"
                )

        if actions:
            parts.append("\nContextual actions available on this page:")
            parts.extend(actions)
            parts.append(
                "\nIMPORTANT: When the user asks about implementing, complying, "
                "what controls to add, or what to do for a requirement — "
                "DO NOT just describe actions in text. Instead, USE the attach_existing "
                "or propose_create tools to provide actionable confirmation cards. "
                "The user expects interactive buttons, not instructions."
            )

    parts.append(
        "\nUse this context if the user refers to 'this', 'these', 'here', "
        "or asks about items on their current page.\n"
    )

    return "\n".join(parts) + "\n"


def _enrich_context(parsed_context, accessible_folder_ids: list[str]) -> str:
    """
    Enrich the LLM context with domain objects relevant to the current page.
    For example, when on a risk assessment page, include the domain's assets
    so the LLM can reason about additional risks.
    """
    from django.apps import apps

    from .tools import MODEL_MAP

    # Determine the parent object's folder
    parent_info = MODEL_MAP.get(parsed_context.model_key)
    if not parent_info:
        return ""

    try:
        parent_model = apps.get_model(parent_info[0], parent_info[1])
        parent_obj = parent_model.objects.filter(id=parsed_context.object_id).first()
        if not parent_obj or not hasattr(parent_obj, "folder_id"):
            return ""
        folder_id = str(parent_obj.folder_id)
    except Exception:
        return ""

    parts = []

    # For risk assessments: include assets from the same domain
    if parsed_context.model_key == "risk_assessment":
        Asset = apps.get_model("core", "Asset")
        assets = Asset.objects.filter(
            folder_id=folder_id,
            folder_id__in=accessible_folder_ids,
        )[:30]
        if assets:
            parts.append("ASSETS IN THIS DOMAIN:")
            for asset in assets:
                line = f"  - {asset.name}"
                extras = []
                if hasattr(asset, "type") and asset.type:
                    extras.append(
                        asset.get_type_display()
                        if hasattr(asset, "get_type_display")
                        else asset.type
                    )
                if hasattr(asset, "business_value") and asset.business_value:
                    extras.append(f"business_value={asset.business_value}")
                if extras:
                    line += f" ({', '.join(extras)})"
                if asset.description:
                    line += f" — {asset.description[:150]}"
                parts.append(line)

        # Also include existing risk scenarios for awareness
        RiskScenario = apps.get_model("core", "RiskScenario")
        scenarios = RiskScenario.objects.filter(
            risk_assessment_id=parsed_context.object_id,
        )[:20]
        if scenarios:
            parts.append("\nEXISTING RISK SCENARIOS (already identified):")
            for s in scenarios:
                line = f"  - {s.name}"
                if hasattr(s, "treatment") and s.treatment:
                    line += f" (treatment={s.get_treatment_display()})"
                parts.append(line)

    return "\n".join(parts)


def _get_graph_context(user_message: str) -> str:
    """
    Query the knowledge graph for framework-related context.
    Extracts potential framework references from the user message and
    returns structured graph data if matches are found.

    This runs on every RAG fallback to ensure framework knowledge is always
    available, regardless of whether the LLM selected the search_library tool.
    """
    from .knowledge_graph import (
        find_frameworks,
        get_framework_detail,
        format_graph_result,
    )

    # Try finding frameworks mentioned in the query
    # Split on common separators and try each token + the full query
    tokens = set()
    for sep in [" et ", " and ", " vs ", " versus ", " ou ", " or ", ",", "/"]:
        if sep in user_message.lower():
            for part in user_message.lower().split(sep):
                cleaned = part.strip().strip("?!.\"'")
                if len(cleaned) >= 2:
                    tokens.add(cleaned)

    # Also try individual words (3+ chars) for framework name matching
    for word in user_message.split():
        cleaned = word.strip("?!.,\"'()").strip()
        if len(cleaned) >= 3:
            tokens.add(cleaned.lower())

    # Search the graph for each token
    found_frameworks = {}
    for token in tokens:
        results = find_frameworks(query=token)
        for fw in results:
            if fw["urn"] not in found_frameworks:
                found_frameworks[fw["urn"]] = fw

    if not found_frameworks:
        return ""

    # Get details for found frameworks (cap at 5 to avoid context overflow)
    parts = []
    for urn in list(found_frameworks)[:5]:
        detail = get_framework_detail(found_frameworks[urn]["name"])
        if detail:
            parts.append(format_graph_result(detail))

    if not parts:
        return ""

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Deterministic workflow pre-routing
# ---------------------------------------------------------------------------

# Maps (model_key, keyword_set) → workflow_name.
# If the user is on a matching page and the message contains any keyword,
# the workflow is selected without asking the LLM.
_WORKFLOW_ROUTES: list[tuple[str, set[str], str]] = [
    (
        "requirement_assessment",
        {
            # EN
            "control",
            "controls",
            "implement",
            "comply",
            "compliance",
            "what to do",
            "what should",
            "how to",
            "suggest",
            "recommend",
            "measure",
            "measures",
            # FR
            "contrôle",
            "contrôles",
            "mesure",
            "mesures",
            "implémenter",
            "conformité",
            "conformer",
            "que faire",
            "quoi faire",
            "comment",
            "suggérer",
            "recommander",
        },
        "suggest_controls",
    ),
    (
        "risk_scenario",
        {
            # EN
            "treat",
            "treatment",
            "mitigat",
            "control",
            "controls",
            "reduce",
            "accept",
            "avoid",
            "transfer",
            "what to do",
            "how to",
            "suggest",
            "recommend",
            # FR
            "traitement",
            "traiter",
            "atténuer",
            "contrôle",
            "contrôles",
            "réduire",
            "accepter",
            "éviter",
            "transférer",
            "que faire",
            "comment",
            "suggérer",
            "recommander",
        },
        "risk_treatment",
    ),
    (
        "applied_control",
        {
            # EN
            "evidence",
            "evidences",
            "proof",
            "prove",
            "document",
            "what evidence",
            "how to demonstrate",
            "audit",
            # FR
            "preuve",
            "preuves",
            "documenter",
            "démontrer",
            "audit",
        },
        "evidence_guidance",
    ),
    (
        "ebios_rm_study",
        {
            # EN
            "conduct",
            "assist",
            "help",
            "study",
            "workshop",
            "generate",
            "fill",
            "draft",
            # FR
            "mener",
            "conduire",
            "assister",
            "aider",
            "étude",
            "atelier",
            "générer",
            "remplir",
            "ébauche",
        },
        "ebios_rm_assist",
    ),
    (
        "folder",
        {
            # EN
            "ebios",
            "ebios rm",
            "study",
            "risk study",
            # FR
            "étude",
            "etude",
            "analyse de risque",
            "analyse des risques",
        },
        "ebios_rm_assist",
    ),
]


def _match_workflow(user_message: str, parsed_context) -> "Workflow | None":
    """
    Match a workflow based on page context + message keywords.
    Returns the workflow instance if matched, None otherwise.
    """
    msg_lower = user_message.lower()

    # Context-specific routes (require being on a matching detail page)
    if parsed_context and parsed_context.object_id:
        for model_key, keywords, workflow_name in _WORKFLOW_ROUTES:
            if parsed_context.model_key != model_key:
                continue
            if any(kw in msg_lower for kw in keywords):
                from .workflows import get_workflow_by_tool_name

                return get_workflow_by_tool_name(f"workflow_{workflow_name}")

    # Global routes — match from ANY page when keywords are strong enough
    if any(kw in msg_lower for kw in ("ebios", "ebios rm")):
        from .workflows import get_workflow_by_tool_name

        return get_workflow_by_tool_name("workflow_ebios_rm_assist")
