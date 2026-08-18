from rest_framework import serializers

from core.serializer_fields import FieldsRelatedField, PathField
from core.serializers import BaseModelSerializer
from issues.models import CommitmentVersion, RemediationIssue


class CommitmentVersionReadSerializer(BaseModelSerializer):
    issue = FieldsRelatedField()
    author = FieldsRelatedField()
    lead_acceptance_user = FieldsRelatedField()
    respondent_acceptance_user = FieldsRelatedField()
    is_current = serializers.BooleanField(read_only=True)
    accepted = serializers.BooleanField(read_only=True)

    class Meta:
        model = CommitmentVersion
        fields = "__all__"


class CommitmentVersionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = CommitmentVersion
        fields = "__all__"


class RemediationIssueReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    lead_representatives = FieldsRelatedField(many=True)
    respondent_representatives = FieldsRelatedField(many=True)
    lead_contributors = FieldsRelatedField(many=True)
    respondent_contributors = FieldsRelatedField(many=True)
    requirement_assessments = FieldsRelatedField(many=True)
    findings = FieldsRelatedField(many=True)
    evidences = FieldsRelatedField(many=True)
    applied_controls = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    current_commitment = serializers.SerializerMethodField()
    acceptance_state = serializers.SerializerMethodField()

    class Meta:
        model = RemediationIssue
        fields = "__all__"

    def get_current_commitment(self, obj):
        version = obj.current_commitment
        if version is None:
            return None
        return CommitmentVersionReadSerializer(version).data

    def get_acceptance_state(self, obj):
        return obj.acceptance_state


class RemediationIssueWriteSerializer(BaseModelSerializer):
    class Meta:
        model = RemediationIssue
        # Closure and cancellation data are set through the dedicated actions,
        # never through generic writes.
        exclude = ["closed_at", "resolution", "closure_justification", "cancellation_reason"]

    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("issueDescriptionRequired")
        return value

    def validate_status(self, value):
        # done/cancelled are reachable only through the close/cancel actions,
        # which also enforce their invariants (§10.6).
        if value in (
            RemediationIssue.Status.DONE,
            RemediationIssue.Status.CANCELLED,
        ):
            raise serializers.ValidationError("statusChangeThroughActionOnly")
        return value

    def validate(self, attrs):
        if self.instance is not None and self.instance.status in (
            RemediationIssue.Status.DONE,
            RemediationIssue.Status.CANCELLED,
        ):
            raise serializers.ValidationError({"error": "issueClosedReopenFirst"})
        return super().validate(attrs)
