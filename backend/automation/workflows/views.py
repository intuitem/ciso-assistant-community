import hashlib
import hmac
import json

import yaml
from django.contrib.auth.models import Permission
import django_filters as df
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from core.views import BaseModelViewSet, GenericFilterSet
from iam.models import Folder, RoleAssignment

from .actions import required_permissions
from .engine import (
    EngineError,
    abort_token,
    coerce_variable_value,
    retry_token,
    skip_token,
    trigger_instance,
)
from .graph import GraphValidationError, save_graph, serialize_graph
from .import_export import (
    WorkflowImportError,
    export_workflow_library,
    import_workflow_library,
)
from .models import (
    ConditionGroup,
    DraftExistsError,
    Workflow,
    WorkflowInstance,
    WorkflowNode,
    WorkflowSecret,
    WorkflowToken,
    WorkflowTrigger,
    WorkflowVersion,
    generate_webhook_secret,
)
from .serializers import (
    WorkflowInstanceLogReadSerializer,
    WorkflowInstanceReadSerializer,
)
from .validation import validate_graph

LONG_CACHE_TTL = 60


class WorkflowFilterSet(GenericFilterSet):
    trigger_type = df.MultipleChoiceFilter(
        choices=WorkflowNode.TriggerType.choices, method="filter_trigger_type"
    )

    def filter_trigger_type(self, queryset, name, value):
        # Matches trigger nodes of non-archived versions. Slightly wider than
        # the displayed trigger_types (published else draft) when a draft
        # diverges from the published version, which is the useful behavior
        # for "find my schedule workflows".
        return queryset.filter(
            versions__status__in=[
                WorkflowVersion.Status.DRAFT,
                WorkflowVersion.Status.PUBLISHED,
            ],
            versions__nodes__type=WorkflowNode.Type.TRIGGER,
            versions__nodes__trigger_config__type__in=value,
        ).distinct()

    class Meta:
        model = Workflow
        fields = ["folder", "filtering_labels", "is_active"]


class WorkflowViewSet(BaseModelViewSet):
    model = Workflow
    serializers_module = "automation.workflows.serializers"
    filterset_class = WorkflowFilterSet
    search_fields = ["name", "description", "ref_id"]
    ordering = ["created_at"]

    def get_queryset(self):
        # trigger_types/versions are serialized per row; prefetch so the list
        # view doesn't re-query per workflow.
        return (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch(
                    "versions",
                    queryset=WorkflowVersion.objects.select_related("run_as")
                    .annotate(instance_count=Count("instances"))
                    .order_by("-version_number"),
                ),
                Prefetch(
                    "versions__nodes",
                    queryset=WorkflowNode.objects.filter(
                        type=WorkflowNode.Type.TRIGGER
                    ),
                    to_attr="trigger_nodes",
                ),
            )
        )

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
                    "match_on": entry.get("match_on", "name"),
                }
                for key, entry in CREATABLE_MODELS.items()
            ]
        )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get readable models", url_path="readable-models")
    def readable_models(self, request):
        """The read_objects registry (spec D26): field lists double as the
        filter/order whitelist the builder offers."""
        from .actions import BASE_READ_FIELDS, READABLE_MODELS

        return Response(
            [
                {
                    "key": key,
                    "fields": BASE_READ_FIELDS + entry["fields"],
                    # Output-only aggregates; not filterable/orderable.
                    "computed": sorted((entry.get("computed") or {}).keys()),
                }
                for key, entry in READABLE_MODELS.items()
            ]
        )

    @action(detail=True, methods=["get"], url_path="export-yaml")
    def export_yaml(self, request, pk=None):
        workflow = self.get_object()
        content = yaml.dump(
            export_workflow_library(workflow),
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
        response = HttpResponse(content, content_type="application/x-yaml")
        filename = slugify(workflow.name) or "workflow"
        response["Content-Disposition"] = f'attachment; filename="{filename}.yaml"'
        return response

    @action(detail=False, methods=["post"], url_path="import-yaml")
    def import_yaml(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"error": "noFileProvided"}, status=status.HTTP_400_BAD_REQUEST
            )
        if uploaded_file.size > 1024 * 1024:
            return Response(
                {"error": "fileTooLarge"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            data = yaml.safe_load(uploaded_file.read())
        except yaml.YAMLError:
            return Response(
                {"error": "invalidYamlFile"}, status=status.HTTP_400_BAD_REQUEST
            )

        folder_id = request.data.get("folder")
        if folder_id:
            folder = Folder.objects.filter(id=folder_id).first()
            if folder is None:
                return Response(
                    {"error": "invalidFolder"}, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            folder = Folder.get_root_folder()
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_workflow"),
            folder=folder,
        ):
            return Response(
                {"error": "permissionDenied"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            provided_secrets = json.loads(request.data.get("secrets") or "{}")
        except json.JSONDecodeError:
            provided_secrets = {}

        try:
            with transaction.atomic():
                # Secrets are workflow-scoped: import_workflow attaches the
                # dialog-provided values to each new workflow before computing
                # its missing-secrets warning.
                workflows, warnings = import_workflow_library(
                    data, folder, user=request.user, secrets=provided_secrets
                )
        except WorkflowImportError as e:
            return Response({"error": e.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "id": str(workflows[0].id),
                "name": workflows[0].name,
                "count": len(workflows),
                "warnings": warnings,
            },
            status=status.HTTP_201_CREATED,
        )


class WorkflowVersionViewSet(BaseModelViewSet):
    model = WorkflowVersion
    serializers_module = "automation.workflows.serializers"
    filterset_fields = ["workflow", "status", "folder"]
    search_fields = []
    ordering = ["-version_number"]
    # POST detail actions map to add_* by default; discarding is a delete.
    permission_overrides = {"discard": "delete_workflowversion"}

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
        errors += _deputization_errors(request.user, version)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        version.publish(request.user)
        return Response(serialize_graph(version))

    @action(detail=True, methods=["get"], url_path="required-permissions")
    def required_permissions(self, request, pk=None):
        """Deputization report (spec D34): the permissions this version's
        actions will exercise, shown by the publish dialog so the publisher
        sees the authority they are about to lend."""
        return Response(collect_required_permissions(self.get_object()))

    @action(detail=True, methods=["post"])
    def discard(self, request, pk=None):
        """Drop a draft and fall back to the published version (framework-
        builder-style discard). Refused when there is nothing to fall back
        to — discarding the only version would orphan the workflow."""
        version = self.get_object()
        if not version.is_draft:
            return Response(
                {"error": "onlyDraftVersionsCanBeDiscarded"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        published = version.workflow.published_version
        if published is None:
            return Response(
                {"error": "noPublishedVersionToFallBackTo"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            # Conditions PROTECT their variables; clear the trees before the
            # cascade so the version delete cannot trip ProtectedError.
            ConditionGroup.objects.filter(branch__node__version=version).delete()
            version.delete()
        return Response({"published_id": str(published.id)})

    @action(detail=True, methods=["post"], url_path="new-draft")
    def new_draft(self, request, pk=None):
        version = self.get_object()
        existing_draft = version.workflow.draft_version
        if existing_draft is not None:
            return Response(
                {
                    "error": "draftAlreadyExists",
                    "draft_id": str(existing_draft.id),
                    "draft_version_number": existing_draft.version_number,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            draft = version.clone_as_draft()
        except DraftExistsError as e:
            return Response(
                {
                    "error": "draftAlreadyExists",
                    "draft_id": str(e.draft.id),
                    "draft_version_number": e.draft.version_number,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"id": str(draft.id), "version_number": draft.version_number},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """Clone any archived version into a new draft (spec D32). Blocked
        while a draft exists — one draft at a time, no silent forking."""
        version = self.get_object()
        if version.status != WorkflowVersion.Status.ARCHIVED:
            return Response(
                {"error": "onlyArchivedVersionsCanBeRestored"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing_draft = version.workflow.draft_version
        if existing_draft is not None:
            return Response(
                {
                    "error": "draftAlreadyExists",
                    "draft_id": str(existing_draft.id),
                    "draft_version_number": existing_draft.version_number,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            draft = version.clone_as_draft()
        except DraftExistsError as e:
            return Response(
                {
                    "error": "draftAlreadyExists",
                    "draft_id": str(e.draft.id),
                    "draft_version_number": e.draft.version_number,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"id": str(draft.id), "version_number": draft.version_number},
            status=status.HTTP_201_CREATED,
        )


class WorkflowTriggerViewSet(BaseModelViewSet):
    """Registration rows are publish-managed (workflows.triggers): the API
    surface is read + PATCH of the runtime state, never create/delete."""

    model = WorkflowTrigger
    serializers_module = "automation.workflows.serializers"
    filterset_fields = ["workflow", "folder", "enabled", "type", "event_key"]
    search_fields = ["node_ref", "event_key"]
    ordering = ["created_at"]
    # POST detail actions map to add_* by default; rotation is a state change
    # on an existing row and no role holds add_workflowtrigger (publish-managed).
    permission_overrides = {"rotate_secret": "change_workflowtrigger"}

    def create(self, request, *args, **kwargs):
        return Response(
            {"error": "triggersAreManagedByPublish"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"error": "triggersAreManagedByPublish"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], url_path="rotate-secret")
    def rotate_secret(self, request, pk=None):
        trigger = self.get_object()
        if trigger.type != WorkflowTrigger.Type.WEBHOOK:
            return Response(
                {"error": "notAWebhookTrigger"}, status=status.HTTP_400_BAD_REQUEST
            )
        trigger.secret = generate_webhook_secret()
        trigger.save(update_fields=["secret", "updated_at"])
        return Response({"secret": trigger.secret})

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get event key catalog", url_path="event-keys")
    def event_keys(self, request):
        from .events import event_key_catalog

        return Response(event_key_catalog())


class WorkflowSecretViewSet(BaseModelViewSet):
    model = WorkflowSecret
    serializers_module = "automation.workflows.serializers"
    filterset_fields = ["workflow", "folder"]
    search_fields = ["name"]
    ordering = ["name"]


class WorkflowTokenViewSet(BaseModelViewSet):
    """Operator recovery for stuck runs (spec D10). Tokens are engine-managed,
    so the only writes are the retry/skip/abort actions, gated by
    change_workflowtoken (domain manager / administrator)."""

    model = WorkflowToken
    serializers_module = "automation.workflows.serializers"
    filterset_fields = ["instance", "status", "current_node", "folder"]
    search_fields = []
    ordering = ["created_at"]
    permission_overrides = {
        "retry": "change_workflowtoken",
        "skip": "change_workflowtoken",
        "abort": "change_workflowtoken",
    }

    def create(self, request, *args, **kwargs):
        return Response(
            {"error": "tokensAreEngineManaged"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"error": "tokensAreEngineManaged"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"error": "tokensAreEngineManaged"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _run_op(self, op):
        token = self.get_object()
        try:
            op(token)
        except EngineError as e:
            return Response(
                {"error": e.user_message}, status=status.HTTP_400_BAD_REQUEST
            )
        token.refresh_from_db()
        return Response(WorkflowInstanceReadSerializer(token.instance).data)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        return self._run_op(retry_token)

    @action(detail=True, methods=["post"])
    def skip(self, request, pk=None):
        return self._run_op(skip_token)

    @action(detail=True, methods=["post"])
    def abort(self, request, pk=None):
        return self._run_op(abort_token)


def collect_required_permissions(version):
    """Deputization report (spec D34): per action node, the permission
    codenames its config exercises. Feeds both the publish lint and the
    publish dialog."""
    report = []
    for node in version.nodes.filter(type=WorkflowNode.Type.ACTION):
        codenames = required_permissions(node.action_config)
        if codenames:
            report.append(
                {
                    "node_id": str(node.id),
                    "label": node.label or "",
                    "codenames": codenames,
                }
            )
    return report


def _deputization_errors(user, version):
    """Spec D18: the publisher must hold the permissions the workflow's
    actions exercise. The workflow then acts as its publisher's deputy."""
    errors = []
    if getattr(user, "is_superuser", False):
        return errors
    for entry in collect_required_permissions(version):
        for codename in entry["codenames"]:
            permission = Permission.objects.filter(codename=codename).first()
            if permission is None:
                continue
            if not RoleAssignment.is_access_allowed(
                user=user, perm=permission, folder=version.folder
            ):
                errors.append(
                    {
                        "code": "publisher_permission_missing",
                        "message": f"Publishing this action requires the '{codename}' permission",
                        "node_id": entry["node_id"],
                        "edge_id": None,
                    }
                )
    return errors


class WorkflowInstanceViewSet(BaseModelViewSet):
    model = WorkflowInstance
    serializers_module = "automation.workflows.serializers"
    filterset_fields = ["workflow", "version", "status", "trigger", "folder"]
    search_fields = []
    ordering = ["-created_at"]

    def create(self, request, *args, **kwargs):
        """Launching a run: POST {version: uuid, entry_node_ref?: str}.
        Without an entry ref the engine's default rule applies (the manual
        trigger node, or the sole trigger node)."""
        # Scope the lookup to versions the user can view, so out-of-scope
        # UUIDs 404 like everywhere else instead of confirming existence.
        (viewable_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, WorkflowVersion
        )
        version = get_object_or_404(
            WorkflowVersion.objects.filter(id__in=viewable_ids),
            id=request.data.get("version"),
        )
        # Authorization: starting a run creates a WorkflowInstance in the
        # version's folder, so require add_workflowinstance there (this custom
        # create bypasses the base viewset's queryset scoping otherwise).
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_workflowinstance"),
            folder=version.folder,
        ):
            return Response(
                {"error": "permissionDenied"}, status=status.HTTP_403_FORBIDDEN
            )
        # Only the workflow's actual current draft or published version is
        # runnable. Checking status alone is insufficient if malformed/imported
        # data contains more than one non-archived version.
        current_version_ids = {
            candidate.id
            for candidate in (
                version.workflow.draft_version,
                version.workflow.published_version,
            )
            if candidate is not None
        }
        if version.id not in current_version_ids:
            return Response(
                {"error": "onlyCurrentVersionsCanBeRun"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Spec D34: published versions run as their run_as (definer rights);
        # a published version without one predates the identity model and
        # must be republished. Drafts run as the invoker (request.user).
        if not version.is_draft and version.run_as is None:
            return Response(
                {"error": "republishRequired"}, status=status.HTTP_400_BAD_REQUEST
            )
        entry = None
        entry_node_ref = request.data.get("entry_node_ref")
        if entry_node_ref:
            entry = version.nodes.filter(
                type=WorkflowNode.Type.TRIGGER, ref=entry_node_ref
            ).first()
            if entry is None:
                return Response(
                    {"error": "unknownTriggerNode"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        # Debug seeds (spec D33): only declared variables, values checked
        # against the declared type.
        initial_variables = request.data.get("initial_variables")
        if initial_variables is not None:
            if not isinstance(initial_variables, dict):
                return Response(
                    {"error": "initialVariablesInvalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            declared = {v.key: v for v in version.variables.all()}
            seeded = {}
            for key, value in initial_variables.items():
                variable = declared.get(key)
                if variable is None:
                    return Response(
                        {"error": "unknownVariable", "variable": key},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                try:
                    seeded[key] = coerce_variable_value(value, variable.type)
                except ValueError:
                    return Response(
                        {"error": "variableTypeMismatch", "variable": key},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            initial_variables = seeded
        try:
            instance = trigger_instance(
                version,
                trigger="manual",
                initiated_by=request.user,
                entry_node=entry,
                initial_variables=initial_variables,
            )
        except EngineError as e:
            return Response(
                {"error": e.user_message}, status=status.HTTP_400_BAD_REQUEST
            )
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


class WebhookRateThrottle(SimpleRateThrottle):
    """Rate-limit the unauthenticated hook ingress per sender IP. Keyed on the
    TRAILING X-Forwarded-For entry: the frontend passthrough (spec D23) appends
    the real client IP last, so the leading (client-supplied) entries are not
    trusted."""

    scope = "workflow_webhook"

    def get_rate(self):
        from django.conf import settings

        return getattr(settings, "WORKFLOWS_WEBHOOK_THROTTLE_RATE", "120/min")

    def get_cache_key(self, request, view):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ident = (
            xff.split(",")[-1].strip() if xff else request.META.get("REMOTE_ADDR", "")
        )
        return self.cache_format % {"scope": self.scope, "ident": ident or "anon"}


class WorkflowWebhookView(APIView):
    """Inbound trigger: POST /api/workflows/hooks/{workflow_id}/{node_ref}/{secret}/.

    Unauthenticated by design (n8n-style); the per-trigger-node secret in the
    URL is the credential. Starts an instance of the published version at the
    named webhook trigger node, with the request body as payload mapped into
    variables via that node's input_mapping. A disabled or unknown trigger is
    indistinguishable from a wrong URL (404 — no oracle).
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def post(self, request, workflow_id, node_ref, secret):
        from django.conf import settings

        if not getattr(settings, "WORKFLOWS_INBOUND_HOOKS", True):
            return Response(status=status.HTTP_404_NOT_FOUND)
        registration = (
            WorkflowTrigger.objects.filter(
                workflow_id=workflow_id,
                node_ref=node_ref,
                type=WorkflowTrigger.Type.WEBHOOK,
                enabled=True,
            )
            .select_related("workflow")
            .first()
        )
        if (
            registration is None
            or not registration.workflow.is_active
            or not constant_time_compare(secret, registration.secret)
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)
        if registration.hmac_secret and not self._signature_valid(
            request, registration.hmac_secret
        ):
            return Response(
                {"error": "invalidSignature"}, status=status.HTTP_403_FORBIDDEN
            )
        version = registration.workflow.published_version
        entry = None
        if version is not None:
            entry = version.nodes.filter(
                type=WorkflowNode.Type.TRIGGER, ref=node_ref
            ).first()
        if entry is None:
            return Response(
                {"error": "workflowNotPublished"},
                status=status.HTTP_409_CONFLICT,
            )
        # Spec D34: no run identity, no automatic execution — 404 like the
        # inactive case above (no oracle for unauthenticated callers).
        if version.run_as is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        payload = request.data if isinstance(request.data, dict) else {}
        try:
            instance = trigger_instance(
                version,
                trigger="webhook",
                payload=payload,
                entry_node=entry,
                trigger_registration=registration,
            )
        except EngineError as e:
            return Response(
                {"error": e.user_message}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {"instance": str(instance.id), "status": instance.status},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _signature_valid(request, hmac_secret):
        provided = request.headers.get("X-Hub-Signature-256") or request.headers.get(
            "X-Signature-256", ""
        )
        provided = provided.removeprefix("sha256=")
        expected = hmac.new(
            hmac_secret.encode(), request.body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(provided, expected)
