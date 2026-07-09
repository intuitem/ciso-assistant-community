from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.views import BaseModelViewSet

from .engine import EngineError, start_instance
from .graph import GraphValidationError, save_graph, serialize_graph
from .models import Workflow, WorkflowInstance, WorkflowNode, WorkflowVersion
from .serializers import (
    WorkflowInstanceLogReadSerializer,
    WorkflowInstanceReadSerializer,
)
from .validation import validate_graph

LONG_CACHE_TTL = 60


class WorkflowViewSet(BaseModelViewSet):
    model = Workflow
    serializers_module = "workflows.serializers"
    filterset_fields = ["folder", "filtering_labels"]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["created_at"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get creatable models", url_path="creatable-models")
    def creatable_models(self, request):
        """The create_object registry, so the builder's forms stay in sync
        with what the backend actually accepts."""
        from .actions import CREATABLE_MODELS

        return Response(
            [
                {
                    "key": key,
                    "fields": entry["fields"],
                    "fk_fields": {
                        fk_name: endpoint
                        for fk_name, (_model, endpoint) in entry["fk_fields"].items()
                    },
                }
                for key, entry in CREATABLE_MODELS.items()
            ]
        )


class WorkflowVersionViewSet(BaseModelViewSet):
    model = WorkflowVersion
    serializers_module = "workflows.serializers"
    filterset_fields = ["workflow", "status", "folder"]
    search_fields = []
    ordering = ["-version_number"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(WorkflowVersion.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get node type choices", url_path="node-types")
    def node_types(self, request):
        return Response(dict(WorkflowNode.Type.choices))

    @action(detail=True, methods=["get", "put"])
    def graph(self, request, pk=None):
        version = self.get_object()
        if request.method == "GET":
            return Response(serialize_graph(version))
        if not version.is_draft:
            return Response(
                {"error": "onlyDraftVersionsAreEditable"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            document = save_graph(version, request.data)
        except GraphValidationError as e:
            return Response({"error": e.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(document)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        version = self.get_object()
        if not version.is_draft:
            return Response(
                {"error": "onlyDraftVersionsCanBePublished"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        errors = validate_graph(version)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        version.publish()
        return Response(serialize_graph(version))

    @action(detail=True, methods=["post"], url_path="new-draft")
    def new_draft(self, request, pk=None):
        version = self.get_object()
        existing_draft = version.workflow.draft_version
        if existing_draft is not None:
            return Response(
                {
                    "error": "draftAlreadyExists",
                    "draft_id": str(existing_draft.id),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        draft = version.clone_as_draft()
        return Response(
            {"id": str(draft.id), "version_number": draft.version_number},
            status=status.HTTP_201_CREATED,
        )


class WorkflowInstanceViewSet(BaseModelViewSet):
    model = WorkflowInstance
    serializers_module = "workflows.serializers"
    filterset_fields = ["workflow", "version", "status", "trigger", "folder"]
    search_fields = []
    ordering = ["-created_at"]

    def create(self, request, *args, **kwargs):
        """Launching a run: POST {version: uuid}."""
        version = get_object_or_404(WorkflowVersion, id=request.data.get("version"))
        try:
            instance = start_instance(
                version, trigger="manual", initiated_by=request.user
            )
        except EngineError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            WorkflowInstanceReadSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True)
    def logs(self, request, pk=None):
        instance = self.get_object()
        return Response(
            WorkflowInstanceLogReadSerializer(
                instance.logs.select_related("node"), many=True
            ).data
        )


class WorkflowWebhookView(APIView):
    """Inbound trigger: POST /api/workflows/hooks/{workflow_id}/{secret}/.

    Unauthenticated by design (n8n-style); the per-workflow secret in the URL
    is the credential. Starts an instance of the published version with the
    request body as payload, mapped into variables via the start node's
    input_mapping.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, workflow_id, secret):
        workflow = get_object_or_404(Workflow, id=workflow_id)
        if not constant_time_compare(secret, workflow.webhook_secret):
            return Response(status=status.HTTP_404_NOT_FOUND)
        version = workflow.published_version
        if version is None:
            return Response(
                {"error": "workflowNotPublished"},
                status=status.HTTP_409_CONFLICT,
            )
        payload = request.data if isinstance(request.data, dict) else {}
        try:
            instance = start_instance(version, trigger="webhook", payload=payload)
        except EngineError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"instance": str(instance.id), "status": instance.status},
            status=status.HTTP_201_CREATED,
        )
