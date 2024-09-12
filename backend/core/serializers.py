import importlib
from typing import Any
from ciso_assistant.settings import EMAIL_HOST, EMAIL_HOST_RESCUE


from core.models import *
from iam.models import *

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db import models
from core.serializer_fields import FieldsRelatedField

import structlog

logger = structlog.get_logger(__name__)

User = get_user_model()


class SerializerFactory:
    """Factory to get a serializer class from a list of modules.

    Attributes:
    modules (list): List of module names to search for the serializer.
    """

    def __init__(self, *modules: str):
        self.modules = list(reversed(modules))  # Reverse to prioritize later modules

    def get_serializer(self, base_name: str, action: str):
        if action in ["list", "retrieve"]:
            serializer_name = f"{base_name}ReadSerializer"
        elif action in ["create", "update", "partial_update"]:
            serializer_name = f"{base_name}WriteSerializer"
        else:
            return None

        return self._get_serializer_class(serializer_name)

    def _get_serializer_class(self, serializer_name: str):
        for module_name in self.modules:
            try:
                serializer_module = importlib.import_module(module_name)
                serializer_class = getattr(serializer_module, serializer_name)
                return serializer_class
            except (ModuleNotFoundError, AttributeError):
                continue

        raise ValueError(
            f"Serializer {serializer_name} not found in any provided modules"
        )


class BaseModelSerializer(serializers.ModelSerializer):
    def update(self, instance: models.Model, validated_data: Any) -> models.Model:
        if hasattr(instance, "urn") and getattr(instance, "urn"):
            raise PermissionDenied({"urn": "Imported objects cannot be modified"})
        try:
            object_updated = super().update(instance, validated_data)
            return object_updated
        except Exception as e:
            logger.error(e)
            raise serializers.ValidationError(e.args[0])

    def create(self, validated_data: Any):
        logger.debug("validated data", **validated_data)
        folder = Folder.get_folder(validated_data)
        folder = folder if folder else Folder.get_root_folder()
        can_create_in_folder = RoleAssignment.is_access_allowed(
            user=self.context["request"].user,
            perm=Permission.objects.get(
                codename=f"add_{self.Meta.model._meta.model_name}"
            ),
            folder=folder,
        )
        if not can_create_in_folder:
            raise PermissionDenied(
                {
                    "folder": "You do not have permission to create objects in this folder"
                }
            )
        try:
            object_created = super().create(validated_data)
            return object_created
        except Exception as e:
            logger.error(e)
            raise serializers.ValidationError(e.args[0])

    class Meta:
        model: models.Model


class ReferentialSerializer(BaseModelSerializer):
    name = serializers.CharField(source="get_name_translated")
    description = serializers.CharField(
        source="get_description_translated", allow_blank=True, allow_null=True
    )
    annotation = serializers.CharField(
        source="get_annotation_translated", allow_blank=True, allow_null=True
    )

    class Meta:
        model: ReferentialObjectMixin
        exclude = ["translations"]


class AssessmentReadSerializer(BaseModelSerializer):
    project = FieldsRelatedField()
    authors = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)


# Risk Assessment


class RiskMatrixReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    json_definition = serializers.JSONField(source="get_json_translated")

    class Meta:
        model = RiskMatrix
        exclude = ["translations"]


class RiskMatrixWriteSerializer(RiskMatrixReadSerializer):
    pass


class RiskAcceptanceWriteSerializer(BaseModelSerializer):
    # NOTE: This is a workaround to filter the approvers on api view
    #       but it causes some problems in api_tests. Serializers are
    #       called before to create users, so the approvers_id list
    #       is empty and the api_tests fail.
    # approvers_id = []
    # try:
    #     for candidate in User.objects.all():
    #         if RoleAssignment.has_permission(candidate, 'approve_riskacceptance'):
    #             approvers_id.append(candidate.id)
    # except:
    #     pass
    # approver = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(id__in=approvers_id))

    class Meta:
        model = RiskAcceptance
        exclude = ["accepted_at", "rejected_at", "revoked_at", "state"]


class RiskAcceptanceReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    risk_scenarios = FieldsRelatedField(many=True)
    approver = FieldsRelatedField(["id", "first_name", "last_name"])
    state = serializers.CharField(source="get_state_display")

    class Meta:
        model = RiskAcceptance
        fields = "__all__"


class ProjectWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Project
        exclude = ["created_at"]


class ProjectReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    lc_status = serializers.CharField(source="get_lc_status_display")

    class Meta:
        model = Project
        fields = "__all__"


class RiskAssessmentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = RiskAssessment
        exclude = ["created_at", "updated_at"]


class RiskAssessmentDuplicateSerializer(BaseModelSerializer):
    class Meta:
        model = RiskAssessment
        fields = ["name", "version", "project", "description"]


class RiskAssessmentReadSerializer(AssessmentReadSerializer):
    str = serializers.CharField(source="__str__")
    project = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    risk_scenarios = FieldsRelatedField(many=True)
    risk_scenarios_count = serializers.IntegerField(source="risk_scenarios.count")
    risk_matrix = FieldsRelatedField()

    class Meta:
        model = RiskAssessment
        fields = "__all__"


class AssetWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Asset
        fields = "__all__"


class AssetReadSerializer(AssetWriteSerializer):
    folder = FieldsRelatedField()
    parent_assets = FieldsRelatedField(many=True)

    type = serializers.CharField(source="get_type_display")


class ReferenceControlWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ReferenceControl
        exclude = ["translations"]


class ReferenceControlReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "urn"])

    class Meta:
        model = ReferenceControl
        exclude = ["translations"]


"""class LibraryReadSerializer(BaseModelSerializer):
    class Meta:
        model = LoadedLibrary
        fields = "__all__"


class LibraryWriteSerializer(BaseModelSerializer):
    class Meta:
        model = LoadedLibrary
        fields = "__all__"
"""


class ThreatWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Threat
        exclude = ["translations"]

    # ["id", "folder", "ref_id", "name", "description", "provider"] # TODO: check why not all?


class ThreatReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "urn"])

    class Meta:
        model = Threat
        exclude = ["translations"]


class RiskScenarioWriteSerializer(BaseModelSerializer):
    risk_matrix = serializers.PrimaryKeyRelatedField(
        read_only=True, source="risk_assessment.risk_matrix"
    )

    class Meta:
        model = RiskScenario
        fields = "__all__"


class RiskScenarioReadSerializer(RiskScenarioWriteSerializer):
    risk_assessment = FieldsRelatedField(["id", "name"])
    risk_matrix = FieldsRelatedField(source="risk_assessment.risk_matrix")
    project = FieldsRelatedField(
        source="risk_assessment.project", fields=["id", "name", "folder"]
    )
    version = serializers.StringRelatedField(source="risk_assessment.version")
    threats = FieldsRelatedField(many=True)
    assets = FieldsRelatedField(many=True)

    treatment = serializers.CharField()

    current_proba = serializers.JSONField(source="get_current_proba")
    current_impact = serializers.JSONField(source="get_current_impact")
    current_level = serializers.JSONField(source="get_current_risk")
    residual_proba = serializers.JSONField(source="get_residual_proba")
    residual_impact = serializers.JSONField(source="get_residual_impact")
    residual_level = serializers.JSONField(source="get_residual_risk")

    strength_of_knowledge = serializers.JSONField(source="get_strength_of_knowledge")

    applied_controls = FieldsRelatedField(many=True)
    rid = serializers.CharField()

    owner = FieldsRelatedField(many=True)


class AppliedControlWriteSerializer(BaseModelSerializer):
    class Meta:
        model = AppliedControl
        fields = "__all__"


class AppliedControlReadSerializer(AppliedControlWriteSerializer):
    folder = FieldsRelatedField()
    reference_control = FieldsRelatedField()

    category = serializers.CharField(
        source="get_category_display"
    )  # type : get_type_display
    csf_function = serializers.CharField(
        source="get_csf_function_display"
    )  # type : get_type_display
    evidences = FieldsRelatedField(many=True)
    effort = serializers.CharField(source="get_effort_display")

    ranking_score = serializers.IntegerField(source="get_ranking_score")
    owner = FieldsRelatedField(many=True)


class PolicyWriteSerializer(AppliedControlWriteSerializer):
    class Meta:
        model = Policy
        fields = "__all__"


class PolicyReadSerializer(AppliedControlReadSerializer):
    class Meta:
        model = Policy
        fields = "__all__"


class UserReadSerializer(BaseModelSerializer):
    user_groups = FieldsRelatedField(many=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "user_groups",
            "is_sso",
        ]


class UserWriteSerializer(BaseModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "user_groups",
        ]

    def validate_email(self, email):
        validate_email(email)
        return email

    def create(self, validated_data):
        send_mail = EMAIL_HOST or EMAIL_HOST_RESCUE
        if not RoleAssignment.is_access_allowed(
            user=self.context["request"].user,
            perm=Permission.objects.get(codename="add_user"),
            folder=Folder.get_root_folder(),
        ):
            raise PermissionDenied(
                {"error": ["You do not have permission to create users"]}
            )
        try:
            user = User.objects.create_user(**validated_data)
        except Exception as e:
            logger.error(e)
            if (
                User.objects.filter(email=validated_data["email"]).exists()
                and send_mail
            ):
                logger.warning("mailing failed")
                raise serializers.ValidationError(
                    {
                        "warning": [
                            "User created successfully but an error occurred while sending the email"
                        ]
                    }
                )
            else:
                raise serializers.ValidationError(
                    {"error": ["An error occurred while creating the user"]}
                )
        return user

    def update(self, instance: User, validated_data: Any) -> User:
        user_groups_data = validated_data.get("user_groups")
        if user_groups_data is not None:
            initial_groups = set(instance.user_groups.all())
            new_groups = set(group for group in user_groups_data)

            if initial_groups != new_groups:
                logger.info(
                    "user groups updated",
                    user=instance,
                    initial_user_groups=initial_groups,
                    new_user_groups=new_groups,
                )
                # instance.user_groups.set(user_groups_data)
        return super().update(instance, validated_data)


class UserGroupReadSerializer(BaseModelSerializer):
    name = serializers.CharField(source="__str__")
    localization_dict = serializers.JSONField(source="get_localization_dict")
    folder = FieldsRelatedField()

    class Meta:
        model = UserGroup
        fields = "__all__"


class UserGroupWriteSerializer(BaseModelSerializer):
    class Meta:
        model = UserGroup
        fields = "__all__"


class RoleReadSerializer(BaseModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class RoleWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class RoleAssignmentReadSerializer(BaseModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = "__all__"


class RoleAssignmentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = "__all__"


class FolderWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Folder
        exclude = [
            "builtin",
            "content_type",
        ]


class FolderReadSerializer(BaseModelSerializer):
    parent_folder = FieldsRelatedField()

    content_type = serializers.CharField(source="get_content_type_display")

    class Meta:
        model = Folder
        fields = "__all__"


# Compliance Assessment


class FrameworkReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "urn"])

    class Meta:
        model = Framework
        exclude = ["translations"]


class FrameworkWriteSerializer(FrameworkReadSerializer):
    pass


class RequirementNodeReadSerializer(ReferentialSerializer):
    reference_controls = FieldsRelatedField(many=True)
    threats = FieldsRelatedField(many=True)
    display_short = serializers.CharField()
    display_long = serializers.CharField()

    class Meta:
        model = RequirementNode
        exclude = ["translations"]


class RequirementNodeWriteSerializer(RequirementNodeReadSerializer):
    pass


class EvidenceReadSerializer(BaseModelSerializer):
    attachment = serializers.CharField(source="filename")
    size = serializers.CharField(source="get_size")
    folder = FieldsRelatedField()
    applied_controls = FieldsRelatedField(many=True)
    requirement_assessments = FieldsRelatedField(many=True)

    class Meta:
        model = Evidence
        fields = "__all__"


class EvidenceWriteSerializer(BaseModelSerializer):
    applied_controls = serializers.PrimaryKeyRelatedField(
        many=True, queryset=AppliedControl.objects.all()
    )
    requirement_assessments = serializers.PrimaryKeyRelatedField(
        many=True, queryset=RequirementAssessment.objects.all()
    )

    class Meta:
        model = Evidence
        fields = "__all__"


class AttachmentUploadSerializer(serializers.Serializer):
    attachment = serializers.FileField(required=True)

    class Meta:
        model = Evidence
        fields = ["attachment"]


class ComplianceAssessmentReadSerializer(AssessmentReadSerializer):
    project = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    framework = FieldsRelatedField(
        ["id", "min_score", "max_score", "implementation_groups_definition", "ref_id"]
    )
    selected_implementation_groups = serializers.ReadOnlyField(
        source="get_selected_implementation_groups"
    )

    class Meta:
        model = ComplianceAssessment
        fields = "__all__"


class ComplianceAssessmentWriteSerializer(BaseModelSerializer):
    baseline = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=ComplianceAssessment.objects.all(),
        required=False,
        allow_null=True,
    )

    def create(self, validated_data: Any):
        return super().create(validated_data)

    class Meta:
        model = ComplianceAssessment
        fields = "__all__"


class RequirementAssessmentReadSerializer(BaseModelSerializer):
    name = serializers.CharField(source="__str__")
    description = serializers.CharField(source="get_requirement_description")
    compliance_assessment = FieldsRelatedField()
    folder = FieldsRelatedField()

    class Meta:
        model = RequirementAssessment
        fields = "__all__"


class RequirementAssessmentWriteSerializer(BaseModelSerializer):
    def validate_score(self, value):
        compliance_assessment = self.get_compliance_assessment()

        if value is not None:
            if (
                value < compliance_assessment.min_score
                or value > compliance_assessment.max_score
            ):
                raise serializers.ValidationError(
                    {
                        "score": f"Score must be between {compliance_assessment.min_score} and {compliance_assessment.max_score}"
                    }
                )
        return value

    def get_compliance_assessment(self):
        if hasattr(self, "instance") and self.instance:
            return self.instance.compliance_assessment
        try:
            compliance_assessment_id = self.context.get("request", {}).data.get(
                "compliance_assessment", {}
            )
            compliance_assessment = ComplianceAssessment.objects.get(
                id=compliance_assessment_id
            )
            return compliance_assessment
        except ComplianceAssessment.DoesNotExist:
            raise serializers.ValidationError(
                "The specified Compliance Assessment does not exist."
            )

    class Meta:
        model = RequirementAssessment
        fields = "__all__"


class RequirementMappingSetReadSerializer(BaseModelSerializer):
    source_framework = FieldsRelatedField()
    target_framework = FieldsRelatedField()
    library = FieldsRelatedField(["name", "urn"])
    folder = FieldsRelatedField()

    class Meta:
        model = RequirementMappingSet
        fields = "__all__"


class RequirementMappingSetWriteSerializer(RequirementMappingSetReadSerializer):
    pass


class ComputeMappingSerializer(serializers.Serializer):
    mapping_set = serializers.PrimaryKeyRelatedField(
        queryset=RequirementMappingSet.objects.all()
    )
    source_assessment = serializers.PrimaryKeyRelatedField(
        queryset=ComplianceAssessment.objects.all()
    )
