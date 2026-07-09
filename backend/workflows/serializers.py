from rest_framework import serializers

from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField, PathField

from workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowToken,
    WorkflowVersion,
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
                    WorkflowToken.Status.ERROR,
                ]
            ).select_related("current_node")
        ]


class WorkflowInstanceWriteSerializer(BaseModelSerializer):
    class Meta:
        model = WorkflowInstance
        fields = ["version"]


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
