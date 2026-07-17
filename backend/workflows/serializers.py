from rest_framework import serializers

from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField, PathField

from workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowSchedule,
    WorkflowSecret,
    WorkflowToken,
    WorkflowVersion,
)
from workflows.scheduling import (
    CronValidationError,
    validate_cron_expression,
    validate_timezone,
)


class WorkflowReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    versions = FieldsRelatedField(["id", "version_number", "status"], many=True)

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

    class Meta:
        model = WorkflowSecret
        # Write-only store: the value never leaves the server (spec D17).
        fields = ["id", "name", "folder", "created_at", "updated_at"]


class WorkflowSecretWriteSerializer(BaseModelSerializer):
    class Meta:
        model = WorkflowSecret
        fields = ["name", "folder", "value"]
        extra_kwargs = {"value": {"write_only": True}}


class WorkflowScheduleReadSerializer(BaseModelSerializer):
    workflow = FieldsRelatedField()
    folder = FieldsRelatedField()

    class Meta:
        model = WorkflowSchedule
        fields = "__all__"


class WorkflowScheduleWriteSerializer(BaseModelSerializer):
    class Meta:
        model = WorkflowSchedule
        fields = [
            "name",
            "description",
            "workflow",
            "cron_expression",
            "timezone",
            "enabled",
        ]

    def validate_timezone(self, value):
        try:
            validate_timezone(value)
        except CronValidationError as e:
            raise serializers.ValidationError(str(e))
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        expression = attrs.get(
            "cron_expression",
            getattr(self.instance, "cron_expression", None),
        )
        tz_name = attrs.get("timezone", getattr(self.instance, "timezone", "UTC"))
        try:
            validate_cron_expression(expression, tz_name)
        except CronValidationError as e:
            raise serializers.ValidationError({"cron_expression": str(e)})
        return attrs


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
