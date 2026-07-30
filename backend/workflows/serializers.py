from rest_framework import serializers

from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField, PathField

from workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowSecret,
    WorkflowToken,
    WorkflowTrigger,
    WorkflowVersion,
)


class WorkflowReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    versions = serializers.SerializerMethodField()

    def get_versions(self, workflow):
        # Versions-panel rows (spec D32): newest first, with run counts.
        return [
            {
                "id": str(version.id),
                "version_number": version.version_number,
                "status": version.status,
                "published_at": version.published_at,
                "run_count": version.instances.count(),
            }
            for version in workflow.versions.order_by("-version_number")
        ]

    class Meta:
        model = Workflow
        fields = "__all__"


class WorkflowWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Workflow
        fields = "__all__"

    def create(self, validated_data):
        workflow = super().create(validated_data)
        WorkflowVersion.objects.create(workflow=workflow)
        return workflow


class WorkflowVersionReadSerializer(BaseModelSerializer):
    workflow = FieldsRelatedField()
    folder = FieldsRelatedField()
    # Versions-panel row data (spec D32); versions per workflow are few, the
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


class WorkflowInstanceReadSerializer(BaseModelSerializer):
    workflow = FieldsRelatedField()
    version = FieldsRelatedField(["id", "version_number"])
    folder = FieldsRelatedField()
    initiated_by = FieldsRelatedField(["id", "email"])
    active_nodes = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = "__all__"

    def get_active_nodes(self, obj):
        return [
            {
                "id": str(token.current_node_id),
                "label": token.current_node.label or token.current_node.type,
                "status": token.status,
                "error_message": token.error_message,
            }
            for token in obj.tokens.filter(
                status__in=[
                    WorkflowToken.Status.ACTIVE,
                    WorkflowToken.Status.WAITING,
                    WorkflowToken.Status.RETRYING,
                    WorkflowToken.Status.ERROR,
                ]
            ).select_related("current_node")
        ]


class WorkflowInstanceWriteSerializer(BaseModelSerializer):
    class Meta:
        model = WorkflowInstance
        fields = ["version"]


class WorkflowSecretReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    workflow = FieldsRelatedField()

    class Meta:
        model = WorkflowSecret
        # Write-only store: the value never leaves the server (spec D17).
        fields = ["id", "name", "workflow", "folder", "created_at", "updated_at"]


class WorkflowSecretWriteSerializer(BaseModelSerializer):
    class Meta:
        model = WorkflowSecret
        # Workflow-scoped: folder is derived from the workflow on save.
        fields = ["name", "workflow", "value"]
        extra_kwargs = {"value": {"write_only": True}}


class WorkflowTriggerReadSerializer(BaseModelSerializer):
    workflow = FieldsRelatedField()
    folder = FieldsRelatedField()
    has_hmac = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTrigger
        # secret stays readable (builders need the hook URL; view permission
        # gates it, matching the old workflow-level webhook_secret exposure).
        exclude = ["hmac_secret"]

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

            from workflows.scheduling import next_occurrence

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
