from django.db import transaction
from rest_framework import serializers

from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField, PathField

from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowNode,
    WorkflowSecret,
    WorkflowToken,
    WorkflowTrigger,
    WorkflowVersion,
)

# Token states shown as a run's "active nodes" (live or stuck, not yet done).
ACTIVE_TOKEN_STATUSES = [
    WorkflowToken.Status.ACTIVE,
    WorkflowToken.Status.WAITING,
    WorkflowToken.Status.RETRYING,
    WorkflowToken.Status.ERROR,
]


class WorkflowReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    versions = serializers.SerializerMethodField()
    trigger_types = serializers.SerializerMethodField()

    def get_trigger_types(self, workflow):
        # Trigger kinds of the current version (published, else draft), for
        # the list view. Iterates the versions relation in Python so the
        # viewset's prefetch is honored; uses the trigger_nodes prefetch when
        # present and falls back to a query for routes without it.
        versions = list(workflow.versions.all())
        version = next(
            (v for v in versions if v.status == WorkflowVersion.Status.PUBLISHED),
            None,
        ) or next(
            (v for v in versions if v.status == WorkflowVersion.Status.DRAFT), None
        )
        if version is None:
            return []
        nodes = getattr(version, "trigger_nodes", None)
        if nodes is None:
            nodes = version.nodes.filter(type=WorkflowNode.Type.TRIGGER)
        return sorted(
            {
                node.trigger_config.get("type")
                for node in nodes
                if node.trigger_config.get("type")
            }
        )

    def get_versions(self, workflow):
        # Versions-panel rows: newest first, with run counts.
        # run_as so the panel can say who each version acts as.
        # .all() honors the viewset's prefetch (which carries run_as and an
        # instance_count annotation); sorting in Python keeps the order stable
        # for routes without it, where the count falls back to a query.
        return [
            {
                "id": str(version.id),
                "version_number": version.version_number,
                "status": version.status,
                "published_at": version.published_at,
                "run_count": version.instance_count
                if hasattr(version, "instance_count")
                else version.instances.count(),
                "run_as": version.run_as.email if version.run_as else None,
            }
            for version in sorted(
                workflow.versions.all(),
                key=lambda v: v.version_number,
                reverse=True,
            )
        ]

    class Meta:
        model = Workflow
        fields = "__all__"


class WorkflowWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Workflow
        fields = "__all__"

    def create(self, validated_data):
        # ATOMIC_REQUESTS is off: without this, a failed first-version create
        # leaves a committed workflow with no version.
        with transaction.atomic():
            workflow = super().create(validated_data)
            WorkflowVersion.objects.create(workflow=workflow)
        return workflow


class WorkflowVersionReadSerializer(BaseModelSerializer):
    workflow = FieldsRelatedField()
    folder = FieldsRelatedField()
    # Run identity: published_by is provenance, run_as is the
    # authority the version's runs wield.
    published_by = FieldsRelatedField(["id", "email"])
    run_as = FieldsRelatedField(["id", "email"])
    # Versions-panel row data; versions per workflow are few, the
    # count query per row is fine.
    run_count = serializers.SerializerMethodField()

    def get_run_count(self, version):
        return version.instances.count()

    class Meta:
        model = WorkflowVersion
        fields = "__all__"


class WorkflowVersionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = WorkflowVersion
        fields = ["workflow"]

    def validate_workflow(self, value):
        # Ownership FK is immutable: reparenting a version to another workflow
        # would move it (and its folder/RBAC scope) out from under the caller.
        self._ensure_immutable("workflow", value)
        return value


class WorkflowInstanceReadSerializer(BaseModelSerializer):
    workflow = FieldsRelatedField()
    version = FieldsRelatedField(["id", "version_number"])
    folder = FieldsRelatedField()
    initiated_by = FieldsRelatedField(["id", "email"])
    active_nodes = serializers.SerializerMethodField()
    run_as = serializers.SerializerMethodField()

    def get_run_as(self, obj):
        # The identity the run acts as: version.run_as, or the
        # invoker for draft runs — mirror of engine.run_identity without the
        # is_active liveness check (display, not enforcement).
        identity = obj.version.run_as if obj.version else None
        if identity is None and obj.version and obj.version.is_draft:
            identity = obj.initiated_by
        return identity.email if identity else None

    class Meta:
        model = WorkflowInstance
        fields = "__all__"

    def get_active_nodes(self, obj):
        # The list viewset prefetches these into `active_tokens`; fall back to a
        # query for any standalone use of this serializer.
        tokens = getattr(obj, "active_tokens", None)
        if tokens is None:
            tokens = obj.tokens.filter(status__in=ACTIVE_TOKEN_STATUSES).select_related(
                "current_node"
            )
        return [
            {
                "id": str(token.current_node_id),
                "label": token.current_node.label or token.current_node.type,
                "status": token.status,
                "error_message": token.error_message,
            }
            for token in tokens
        ]


class WorkflowInstanceWriteSerializer(BaseModelSerializer):
    class Meta:
        model = WorkflowInstance
        fields = ["version"]

    def validate_version(self, value):
        # Ownership FK is immutable: a run belongs to the version it started on.
        self._ensure_immutable("version", value)
        return value


class WorkflowSecretReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    workflow = FieldsRelatedField()

    class Meta:
        model = WorkflowSecret
        # Write-only store: the value never leaves the server.
        fields = ["id", "name", "workflow", "folder", "created_at", "updated_at"]


class WorkflowSecretWriteSerializer(BaseModelSerializer):
    class Meta:
        model = WorkflowSecret
        # Workflow-scoped: folder is derived from the workflow on save.
        fields = ["name", "workflow", "value"]
        extra_kwargs = {"value": {"write_only": True}}

    def validate_workflow(self, value):
        # Ownership FK is immutable: moving a secret into another workflow — a
        # folder the caller may not access — and overwriting its value would let
        # them poison that workflow's credentials. Settable on create only.
        self._ensure_immutable("workflow", value)
        return value

    def create(self, validated_data):
        # No folder field in the payload, so the generic create() would
        # resolve the add_workflowsecret check to the root folder and 403
        # every domain-scoped role. Check in the owning workflow's folder,
        # which is where the secret lands on save.
        self._check_object_perm(
            validated_data, "add", folder=validated_data["workflow"].folder
        )
        return serializers.ModelSerializer.create(self, validated_data)


class WorkflowTriggerReadSerializer(BaseModelSerializer):
    workflow = FieldsRelatedField()
    folder = FieldsRelatedField()
    has_hmac = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTrigger
        # Both credentials stay server-side: secret authorizes inbound
        # deliveries, so read access must not leak it. Builders fetch the
        # hook URL through the change-gated hook-url action instead.
        exclude = ["hmac_secret", "secret"]

    def get_has_hmac(self, obj):
        return bool(obj.hmac_secret)


class WorkflowTriggerWriteSerializer(BaseModelSerializer):
    """Rows are publish-managed: the only user-writable state is the enabled
    flag and the webhook HMAC secret."""

    class Meta:
        model = WorkflowTrigger
        fields = ["enabled", "hmac_secret"]
        extra_kwargs = {"hmac_secret": {"write_only": True}}

    def update(self, instance, validated_data):
        new_enabled = validated_data.get("enabled", instance.enabled)
        if (
            instance.type == WorkflowTrigger.Type.SCHEDULE
            and new_enabled != instance.enabled
        ):
            from django.utils import timezone

            from automation.workflows.scheduling import next_occurrence

            config = instance.config or {}
            instance.next_run_at = (
                next_occurrence(
                    config.get("cron_expression", ""),
                    config.get("timezone", "UTC"),
                    timezone.now(),
                )
                if new_enabled
                else None
            )
        return super().update(instance, validated_data)


class WorkflowTokenReadSerializer(BaseModelSerializer):
    instance = FieldsRelatedField(["id", "status"])
    current_node = FieldsRelatedField(["id", "label", "type"])
    folder = FieldsRelatedField()

    class Meta:
        model = WorkflowToken
        fields = "__all__"


class WorkflowTokenWriteSerializer(BaseModelSerializer):
    # Tokens are engine-managed; there is no user-writable state. Recovery
    # happens through the retry/skip/abort actions, not PATCH.
    class Meta:
        model = WorkflowToken
        fields = []


class WorkflowInstanceLogReadSerializer(BaseModelSerializer):
    node = FieldsRelatedField(["id", "label", "type"])

    class Meta:
        model = WorkflowInstanceLog
        fields = [
            "id",
            "event_type",
            "message",
            "data",
            "node",
            "created_at",
        ]
