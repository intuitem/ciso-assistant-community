import importlib
from typing import Any

import structlog
from django.contrib.auth import get_user_model
from django.db import models

from ciso_assistant.settings import EMAIL_HOST, EMAIL_HOST_RESCUE
from core.models import *
from core.serializer_fields import FieldsRelatedField, HashSlugRelatedField
from core.utils import time_state
from ebios_rm.models import EbiosRMStudy
from iam.models import *

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

logger = structlog.get_logger(__name__)

User = get_user_model()


class SerializerFactory:
    """Factory to get a serializer class from a list of modules.

    Attributes:
    modules (list): List of module names to search for the serializer.
    """

    def __init__(self, *modules: str):
        # Reverse to prioritize later modules
        self.modules = list(reversed(modules))

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
        except ValidationError as e:
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
    perimeter = FieldsRelatedField(["id", "folder"])
    authors = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)
    folder = FieldsRelatedField()


# Risk Assessment


class RiskMatrixReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    json_definition = serializers.JSONField(source="get_json_translated")
    library = FieldsRelatedField(["name", "id"])

    class Meta:
        model = RiskMatrix
        exclude = ["translations"]


class RiskMatrixWriteSerializer(RiskMatrixReadSerializer):
    pass


class RiskMatrixImportExportSerializer(BaseModelSerializer):
    library = serializers.SlugRelatedField(slug_field="urn", read_only=True)

    class Meta:
        model = RiskMatrix
        fields = [
            "created_at",
            "updated_at",
            "urn",
            "name",
            "description",
            "ref_id",
            "annotation",
            "translations",
            "locale",
            "default_locale",
            "library",
            "is_enabled",
            "provider",
            "json_definition",
        ]


class VulnerabilityReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    applied_controls = FieldsRelatedField(many=True)
    assets = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(["folder"], many=True)
    security_exceptions = FieldsRelatedField(many=True)
    severity = serializers.CharField(source="get_severity_display")

    class Meta:
        model = Vulnerability
        exclude = ["created_at", "updated_at", "is_published"]


class VulnerabilityWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Vulnerability
        exclude = ["created_at", "updated_at", "is_published"]


class VulnerabilityImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    applied_controls = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)

    class Meta:
        model = Vulnerability
        fields = [
            "ref_id",
            "name",
            "description",
            "folder",
            "status",
            "severity",
            "applied_controls",
            "created_at",
            "updated_at",
        ]


class RiskAcceptanceWriteSerializer(BaseModelSerializer):
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


class PerimeterWriteSerializer(BaseModelSerializer):
    def validate_name(self, value):
        """
        Check that the folder perimeter name does not contain the character "/"
        """
        if "/" in value:
            raise serializers.ValidationError(
                "The name cannot contain '/' for a Perimeter."
            )
        return value

    class Meta:
        model = Perimeter
        exclude = ["created_at"]


class PerimeterReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    lc_status = serializers.CharField(source="get_lc_status_display")

    class Meta:
        model = Perimeter
        fields = "__all__"


class PerimeterImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = Perimeter
        fields = [
            "ref_id",
            "name",
            "description",
            "folder",
            "lc_status",
            "created_at",
            "updated_at",
        ]


class RiskAssessmentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = RiskAssessment
        exclude = ["created_at", "updated_at"]


class RiskAssessmentDuplicateSerializer(BaseModelSerializer):
    class Meta:
        model = RiskAssessment
        fields = ["name", "version", "perimeter", "description"]


class RiskAssessmentReadSerializer(AssessmentReadSerializer):
    str = serializers.CharField(source="__str__")
    perimeter = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    risk_scenarios = FieldsRelatedField(many=True, fields=["id", "name", "ref_id"])
    risk_scenarios_count = serializers.IntegerField(source="risk_scenarios.count")
    risk_matrix = FieldsRelatedField()
    ebios_rm_study = FieldsRelatedField(["id", "name"])

    class Meta:
        model = RiskAssessment
        exclude = []


class RiskAssessmentImportExportSerializer(BaseModelSerializer):
    risk_matrix = serializers.SlugRelatedField(slug_field="urn", read_only=True)

    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    perimeter = HashSlugRelatedField(slug_field="pk", read_only=True)
    ebios_rm_study = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = RiskAssessment
        fields = [
            "ref_id",
            "name",
            "version",
            "description",
            "folder",
            "perimeter",
            "eta",
            "due_date",
            "status",
            "observation",
            "risk_matrix",
            "ebios_rm_study",
            "created_at",
            "updated_at",
        ]


class AssetWriteSerializer(BaseModelSerializer):
    ebios_rm_studies = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=EbiosRMStudy.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Asset
        exclude = ["business_value"]

    def validate_parent_assets(self, parent_assets):
        """
        Check that the assets graph will not contain cycles
        """
        if not self.instance:
            return parent_assets
        if parent_assets:
            for asset in parent_assets:
                if self.instance in asset.ancestors_plus_self():
                    raise serializers.ValidationError(
                        "errorAssetGraphMustNotContainCycles"
                    )
        return parent_assets


class AssetReadSerializer(AssetWriteSerializer):
    folder = FieldsRelatedField()
    parent_assets = FieldsRelatedField(many=True)
    children_assets = FieldsRelatedField(["id"], many=True)
    owner = FieldsRelatedField(many=True)
    security_objectives = serializers.JSONField(
        source="get_security_objectives_display"
    )
    disaster_recovery_objectives = serializers.JSONField(
        source="get_disaster_recovery_objectives_display"
    )
    filtering_labels = FieldsRelatedField(["folder"], many=True)
    type = serializers.CharField(source="get_type_display")
    security_exceptions = FieldsRelatedField(many=True)

    asset_class = FieldsRelatedField(["name"])


class AssetImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    parent_assets = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)

    class Meta:
        model = Asset
        fields = [
            "type",
            "name",
            "description",
            "reference_link",
            "security_objectives",
            "disaster_recovery_objectives",
            "parent_assets",
            "folder",
            "created_at",
            "updated_at",
        ]


class AssetClassReadSerializer(BaseModelSerializer):
    parent = FieldsRelatedField()
    full_path = serializers.CharField()

    class Meta:
        model = AssetClass
        exclude = ["created_at", "updated_at", "folder", "is_published"]


class AssetClassWriteSerializer(BaseModelSerializer):
    class Meta:
        model = AssetClass
        exclude = ["created_at", "updated_at", "folder", "is_published"]


class ReferenceControlWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ReferenceControl
        exclude = ["translations"]


class ReferenceControlReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    filtering_labels = FieldsRelatedField(["folder"], many=True)

    class Meta:
        model = ReferenceControl
        exclude = ["translations"]


class ReferenceControlImportExportSerializer(BaseModelSerializer):
    library = serializers.SlugRelatedField(slug_field="urn", read_only=True)

    folder = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = ReferenceControl
        fields = [
            "ref_id",
            "name",
            "description",
            "urn",
            "provider",
            "category",
            "csf_function",
            "typical_evidence",
            "annotation",
            "translations",
            "locale",
            "default_locale",
            "folder",
            "library",
            "created_at",
            "updated_at",
        ]


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


class ThreatReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    filtering_labels = FieldsRelatedField(["folder"], many=True)

    class Meta:
        model = Threat
        exclude = ["translations"]


class ThreatImportExportSerializer(BaseModelSerializer):
    library = serializers.SlugRelatedField(slug_field="urn", read_only=True)

    folder = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = Threat
        fields = [
            "created_at",
            "updated_at",
            "folder",
            "urn",
            "ref_id",
            "provider",
            "name",
            "description",
            "annotation",
            "translations",
            "locale",
            "default_locale",
            "library",
        ]


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
    perimeter = FieldsRelatedField(
        source="risk_assessment.perimeter", fields=["id", "name", "folder"]
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
    existing_applied_controls = FieldsRelatedField(many=True)

    owner = FieldsRelatedField(many=True)
    security_exceptions = FieldsRelatedField(many=True)


class RiskScenarioImportExportSerializer(BaseModelSerializer):
    threats = HashSlugRelatedField(slug_field="pk", many=True, read_only=True)
    risk_assessment = HashSlugRelatedField(slug_field="pk", read_only=True)
    vulnerabilities = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)
    assets = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)
    existing_applied_controls = HashSlugRelatedField(
        slug_field="pk", read_only=True, many=True
    )
    applied_controls = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)

    class Meta:
        model = RiskScenario
        fields = [
            "ref_id",
            "name",
            "description",
            "risk_assessment",
            "treatment",
            "threats",
            "vulnerabilities",
            "assets",
            "existing_controls",
            "existing_applied_controls",
            "applied_controls",
            "current_proba",
            "current_impact",
            "residual_proba",
            "residual_impact",
            "strength_of_knowledge",
            "justification",
            "created_at",
            "updated_at",
            "qualifications",
        ]


class AppliedControlWriteSerializer(BaseModelSerializer):
    findings = serializers.PrimaryKeyRelatedField(
        many=True, required=False, queryset=Finding.objects.all()
    )

    def create(self, validated_data: Any):
        applied_control = super().create(validated_data)
        findings = validated_data.pop("findings", [])
        if findings:
            applied_control.findings.set(findings)
        return applied_control

    class Meta:
        model = AppliedControl
        fields = "__all__"


class AppliedControlReadSerializer(AppliedControlWriteSerializer):
    folder = FieldsRelatedField()
    reference_control = FieldsRelatedField()
    priority = serializers.CharField(source="get_priority_display")
    category = serializers.CharField(
        source="get_category_display"
    )  # type : get_type_display
    csf_function = serializers.CharField(
        source="get_csf_function_display"
    )  # type : get_type_display
    evidences = FieldsRelatedField(many=True)
    effort = serializers.CharField(source="get_effort_display")
    control_impact = serializers.CharField(source="get_control_impact_display")
    cost = serializers.FloatField()
    filtering_labels = FieldsRelatedField(["folder"], many=True)
    assets = FieldsRelatedField(many=True)

    ranking_score = serializers.IntegerField(source="get_ranking_score")
    owner = FieldsRelatedField(many=True)
    security_exceptions = FieldsRelatedField(many=True)
    state = serializers.SerializerMethodField()
    findings_count = serializers.IntegerField(source="findings.count")

    def get_state(self, obj):
        if not obj.eta:
            return None
        return time_state(obj.eta.isoformat())


class ComplianceAssessmentActionPlanSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    reference_control = FieldsRelatedField()
    priority = serializers.CharField(source="get_priority_display")
    category = serializers.CharField(
        source="get_category_display"
    )  # type : get_type_display
    csf_function = serializers.CharField(
        source="get_csf_function_display"
    )  # type : get_type_display
    evidences = FieldsRelatedField(many=True)
    effort = serializers.CharField(source="get_effort_display")
    control_impact = serializers.CharField(source="get_control_impact_display")
    status = serializers.CharField(source="get_status_display")
    cost = serializers.FloatField()

    ranking_score = serializers.IntegerField(source="get_ranking_score")
    owner = FieldsRelatedField(many=True)
    requirement_assessments = serializers.SerializerMethodField(
        method_name="get_requirement_assessments"
    )

    def get_requirement_assessments(self, obj):
        pk = self.context.get("pk")
        if pk is None:
            return None
        requirement_assessments = RequirementAssessment.objects.filter(
            compliance_assessment=pk, applied_controls=obj
        )
        return [
            {
                "str": str(req.requirement.display_short or req.requirement.urn),
                "id": str(req.id),
            }
            for req in requirement_assessments
        ]

    class Meta:
        model = AppliedControl
        fields = [
            "id",
            "ref_id",
            "name",
            "description",
            "folder",
            "status",
            "eta",
            "expiry_date",
            "priority",
            "category",
            "csf_function",
            "effort",
            "control_impact",
            "cost",
            "ranking_score",
            "requirement_assessments",
            "reference_control",
            "evidences",
            "owner",
        ]


class AppliedControlDuplicateSerializer(BaseModelSerializer):
    class Meta:
        model = AppliedControl
        fields = ["name", "description", "folder"]


class AppliedControlImportExportSerializer(BaseModelSerializer):
    reference_control = HashSlugRelatedField(slug_field="pk", read_only=True)
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    evidences = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)

    class Meta:
        model = AppliedControl
        fields = [
            "folder",
            "ref_id",
            "name",
            "description",
            "priority",
            "reference_control",
            "created_at",
            "updated_at",
            "category",
            "csf_function",
            "status",
            "start_date",
            "eta",
            "expiry_date",
            "link",
            "effort",
            "control_impact",
            "cost",
            "evidences",
        ]


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
            "keep_local_login",
            "is_third_party",
        ]


class UserWriteSerializer(BaseModelSerializer):
    is_local = serializers.BooleanField(required=False)

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
            "keep_local_login",
            "is_third_party",
            "is_local",
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

    def validate_name(self, value):
        """
        Check that the folder name does not contain the character "/"
        """
        if "/" in value:
            raise serializers.ValidationError(
                "The name cannot contain '/' for a Folder."
            )
        return value


class FolderReadSerializer(BaseModelSerializer):
    parent_folder = FieldsRelatedField()

    content_type = serializers.CharField(source="get_content_type_display")

    class Meta:
        model = Folder
        fields = "__all__"


class FolderImportExportSerializer(BaseModelSerializer):
    parent_folder = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = Folder
        fields = [
            "parent_folder",
            "name",
            "description",
            "content_type",
            "created_at",
            "updated_at",
        ]


# Compliance Assessment


class FrameworkReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    reference_controls = FieldsRelatedField(many=True)

    class Meta:
        model = Framework
        exclude = ["translations"]


class FrameworkWriteSerializer(FrameworkReadSerializer):
    pass


class FrameworkImportExportSerializer(BaseModelSerializer):
    library = serializers.SlugRelatedField(slug_field="urn", read_only=True)

    class Meta:
        model = Framework
        fields = [
            "urn",
            "ref_id",
            "name",
            "library",
            "min_score",
            "max_score",
            "implementation_groups_definition",
            "provider",
            "annotation",
            "translations",
            "locale",
            "default_locale",
            "created_at",
            "updated_at",
        ]


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
    filtering_labels = FieldsRelatedField(["folder"], many=True)

    class Meta:
        model = Evidence
        fields = "__all__"


class EvidenceWriteSerializer(BaseModelSerializer):
    applied_controls = serializers.PrimaryKeyRelatedField(
        many=True, queryset=AppliedControl.objects.all(), required=False
    )
    requirement_assessments = serializers.PrimaryKeyRelatedField(
        many=True, queryset=RequirementAssessment.objects.all(), required=False
    )

    class Meta:
        model = Evidence
        fields = "__all__"


class EvidenceImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    attachment = serializers.CharField(allow_blank=True)
    size = serializers.CharField(source="get_size", read_only=True)
    attachment_hash = serializers.CharField(read_only=True)

    class Meta:
        model = Evidence
        fields = [
            "folder",
            "name",
            "description",
            "attachment",
            "created_at",
            "updated_at",
            "size",
            "attachment_hash",
        ]


class AttachmentUploadSerializer(serializers.Serializer):
    attachment = serializers.FileField(required=True)

    class Meta:
        model = Evidence
        fields = ["attachment"]


class ComplianceAssessmentReadSerializer(AssessmentReadSerializer):
    perimeter = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    framework = FieldsRelatedField(
        [
            "id",
            "min_score",
            "max_score",
            "implementation_groups_definition",
            "ref_id",
            "reference_controls",
        ]
    )
    selected_implementation_groups = serializers.ReadOnlyField(
        source="get_selected_implementation_groups"
    )
    progress = serializers.ReadOnlyField(source="get_progress")
    assets = FieldsRelatedField(many=True)

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
    ebios_rm_studies = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=EbiosRMStudy.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    create_applied_controls_from_suggestions = serializers.BooleanField(
        write_only=True, required=False, default=False
    )

    def create(self, validated_data: Any):
        validated_data.pop("create_applied_controls_from_suggestions", None)
        return super().create(validated_data)

    class Meta:
        model = ComplianceAssessment
        fields = "__all__"


class ComplianceAssessmentImportExportSerializer(BaseModelSerializer):
    framework = serializers.SlugRelatedField(slug_field="urn", read_only=True)

    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    perimeter = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = ComplianceAssessment
        fields = [
            "ref_id",
            "name",
            "version",
            "description",
            "folder",
            "perimeter",
            "eta",
            "due_date",
            "status",
            "observation",
            "framework",
            "selected_implementation_groups",
            "min_score",
            "max_score",
            "scores_definition",
            "created_at",
            "updated_at",
        ]


class RequirementAssessmentReadSerializer(BaseModelSerializer):
    class FilteredNodeSerializer(RequirementNodeReadSerializer):
        class Meta:
            model = RequirementNode
            fields = [
                "id",
                "urn",
                "annotation",
                "name",
                "description",
                "typical_evidence",
                "ref_id",
                "associated_reference_controls",
                "associated_threats",
                "parent_requirement",
                "questions",
            ]

    name = serializers.CharField(source="__str__")
    description = serializers.CharField(source="get_requirement_description")
    evidences = FieldsRelatedField(many=True)
    compliance_assessment = FieldsRelatedField()
    folder = FieldsRelatedField()
    assessable = serializers.BooleanField(source="requirement.assessable")
    requirement = FilteredNodeSerializer()
    security_exceptions = FieldsRelatedField(many=True)

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
    library = FieldsRelatedField(["name", "id"])
    folder = FieldsRelatedField()

    class Meta:
        model = RequirementMappingSet
        fields = "__all__"


class RequirementAssessmentImportExportSerializer(BaseModelSerializer):
    requirement = serializers.SlugRelatedField(slug_field="urn", read_only=True)

    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    compliance_assessment = HashSlugRelatedField(slug_field="pk", read_only=True)
    evidences = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)
    applied_controls = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)

    class Meta:
        model = RequirementAssessment
        fields = [
            "created_at",
            "updated_at",
            "eta",
            "due_date",
            "folder",
            "status",
            "result",
            "score",
            "is_scored",
            "observation",
            "compliance_assessment",
            "requirement",
            "selected",
            "mapping_inference",
            "answers",
            "evidences",
            "applied_controls",
        ]


class RequirementMappingSetWriteSerializer(RequirementMappingSetReadSerializer):
    pass


class ComputeMappingSerializer(serializers.Serializer):
    mapping_set = serializers.PrimaryKeyRelatedField(
        queryset=RequirementMappingSet.objects.all()
    )
    source_assessment = serializers.PrimaryKeyRelatedField(
        queryset=ComplianceAssessment.objects.all()
    )


class FilteringLabelReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()

    class Meta:
        model = FilteringLabel
        fields = "__all__"


class FilteringLabelWriteSerializer(BaseModelSerializer):
    class Meta:
        model = FilteringLabel
        exclude = ["folder", "is_published"]


class QualificationReadSerializer(ReferentialSerializer):
    class Meta:
        model = Qualification
        exclude = ["translations"]


class QualificationWriteSerializer(QualificationReadSerializer):
    pass


class SecurityExceptionWriteSerializer(BaseModelSerializer):
    requirement_assessments = serializers.PrimaryKeyRelatedField(
        many=True, queryset=RequirementAssessment.objects.all(), required=False
    )
    applied_controls = serializers.PrimaryKeyRelatedField(
        many=True, queryset=AppliedControl.objects.all(), required=False
    )

    class Meta:
        model = SecurityException
        fields = "__all__"


class SecurityExceptionReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owners = FieldsRelatedField(many=True)
    approver = FieldsRelatedField()
    severity = serializers.CharField(source="get_severity_display")

    class Meta:
        model = SecurityException
        fields = "__all__"


class FindingsAssessmentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = FindingsAssessment
        exclude = ["created_at", "updated_at"]


class FindingsAssessmentReadSerializer(AssessmentReadSerializer):
    owner = FieldsRelatedField(many=True)
    findings_count = serializers.IntegerField(source="findings.count")

    class Meta:
        model = FindingsAssessment
        fields = "__all__"


class FindingWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Finding
        exclude = ["created_at", "updated_at", "folder"]

    def create(self, validated_data):
        findings_assessment = validated_data.get("findings_assessment")
        if not findings_assessment:
            raise serializers.ValidationError({"findings_assessment": "mandatory"})
        validated_data["folder"] = findings_assessment.folder

        return super().create(validated_data)


class FindingReadSerializer(FindingWriteSerializer):
    owner = FieldsRelatedField(many=True)
    findings_assessment = FieldsRelatedField()
    vulnerabilities = FieldsRelatedField(many=True)
    reference_controls = FieldsRelatedField(many=True)
    applied_controls = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(many=True)
    perimeter = FieldsRelatedField(
        source="findings_assessment.perimeter", fields=["id", "name", "folder"]
    )
    folder = FieldsRelatedField()
    severity = serializers.CharField(source="get_severity_display")

    class Meta:
        model = Finding
        fields = "__all__"


class QuickStartSerializer(serializers.Serializer):
    folder = serializers.UUIDField(required=False)
    audit_name = serializers.CharField()
    framework = serializers.CharField()
    create_risk_assessment = serializers.BooleanField()
    risk_assessment_name = serializers.CharField(required=False)
    risk_matrix = serializers.CharField(required=False)

    def save(self, **kwargs):
        return self.create(self.validated_data)

    def create(self, validated_data):
        folder_data = {
            "content_type": Folder.ContentType.DOMAIN,
            "name": "Starter",
        }
        folder = Folder.objects.filter(**folder_data).first()
        if not folder:
            folder_serializer = FolderWriteSerializer(
                data=folder_data, context=self.context
            )
            if not folder_serializer.is_valid(raise_exception=True):
                return None
            folder = folder_serializer.save()
            Folder.create_default_ug_and_ra(folder)

        perimeter_data = {
            "folder": folder.id,
            "name": "Starter",
        }
        perimeter = Perimeter.objects.filter(**perimeter_data).first()
        if not perimeter:
            perimeter_serializer = PerimeterWriteSerializer(
                data=perimeter_data, context=self.context
            )
            if not perimeter_serializer.is_valid(raise_exception=True):
                return None
            perimeter = perimeter_serializer.save()

        framework_lib_urn = validated_data["framework"]
        if not LoadedLibrary.objects.filter(urn=framework_lib_urn).exists():
            framework_stored_lib = StoredLibrary.objects.get(urn=framework_lib_urn)
            try:
                framework_stored_lib.load()
            except Exception as e:
                logger.error(e)
                raise serializers.ValidationError(
                    {"error": "Could not load the selected framework library"}
                )
        framework_lib = LoadedLibrary.objects.get(urn=framework_lib_urn)
        framework = Framework.objects.get(library=framework_lib)
        compliance_assessment_data = {
            "folder": folder.id,
            "perimeter": perimeter.id,
            "framework": framework.id,
            "name": validated_data["audit_name"],
        }
        compliance_asssessment_serializer = ComplianceAssessmentWriteSerializer(
            data=compliance_assessment_data, context=self.context
        )
        if not compliance_asssessment_serializer.is_valid(raise_exception=True):
            return None
        audit = compliance_asssessment_serializer.save()
        audit.create_requirement_assessments()

        created_objects = {
            "folder": FolderReadSerializer(folder).data,
            "perimeter": PerimeterReadSerializer(perimeter).data,
            "complianceassessment": ComplianceAssessmentReadSerializer(audit).data,
        }

        if not validated_data["create_risk_assessment"]:
            return created_objects

        matrix_lib_urn = validated_data["risk_matrix"]
        if not LoadedLibrary.objects.filter(urn=matrix_lib_urn).exists():
            matrix_stored_lib = StoredLibrary.objects.get(urn=matrix_lib_urn)
            try:
                matrix_stored_lib.load()
            except Exception as e:
                logger.error(e)
                raise serializers.ValidationError(
                    {"error": "Could not load the selected risk matrix library"}
                )
        matrix_lib = LoadedLibrary.objects.get(urn=matrix_lib_urn)
        matrix = RiskMatrix.objects.get(library=matrix_lib)

        risk_assessment_data = {
            "folder": folder.id,
            "perimeter": perimeter.id,
            "risk_matrix": matrix.id,
            "name": validated_data["risk_assessment_name"],
        }
        risk_asssessment_serializer = RiskAssessmentWriteSerializer(
            data=risk_assessment_data, context=self.context
        )
        if not risk_asssessment_serializer.is_valid(raise_exception=True):
            return created_objects
        risk_assessment = risk_asssessment_serializer.save()
        created_objects["riskassessment"] = RiskAssessmentReadSerializer(
            risk_assessment
        ).data

        return created_objects


class TimelineEntryWriteSerializer(BaseModelSerializer):
    class Meta:
        model = TimelineEntry
        exclude = ["created_at", "updated_at"]


class TimelineEntryReadSerializer(TimelineEntryWriteSerializer):
    str = serializers.CharField(source="__str__", read_only=True)
    author = FieldsRelatedField()
    folder = FieldsRelatedField()
    incident = FieldsRelatedField()

    class Meta:
        model = TimelineEntry
        exclude = ["evidences"]


class IncidentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Incident
        exclude = ["created_at", "updated_at"]


class IncidentReadSerializer(IncidentWriteSerializer):
    threats = FieldsRelatedField(many=True)
    owners = FieldsRelatedField(many=True)
    assets = FieldsRelatedField(many=True)
    qualifications = FieldsRelatedField(["name"], many=True)
    severity = serializers.CharField(source="get_severity_display", read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)
    folder = FieldsRelatedField()

    class Meta:
        model = Incident
        fields = "__all__"

    def get_timeline_entries(self, obj):
        """Returns a serialized list of timeline entries related to the incident."""
        return TimelineEntryReadSerializer(obj.timeline_entries.all(), many=True).data


class TaskTemplateReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    applied_controls = FieldsRelatedField(many=True)
    compliance_assessments = FieldsRelatedField(many=True)
    risk_assessments = FieldsRelatedField(many=True)
    assigned_to = FieldsRelatedField(many=True)

    next_occurrence = serializers.DateField(read_only=True)
    last_occurrence_status = serializers.CharField(read_only=True)

    # Expose task_node fields directly
    status = serializers.SerializerMethodField()
    observation = serializers.SerializerMethodField()
    evidences = serializers.SerializerMethodField()

    class Meta:
        model = TaskTemplate
        exclude = ["schedule"]

    def get_task_node(self, obj):
        """
        Helper to fetch the related TaskNode for non-recurrent templates.
        """
        if obj.is_recurrent:
            return None
        return TaskNode.objects.filter(task_template=obj).order_by("due_date").first()

    def get_status(self, obj):
        task_node = self.get_task_node(obj)
        return task_node.status if task_node else None

    def get_observation(self, obj):
        task_node = self.get_task_node(obj)
        return task_node.observation if task_node else ""

    def get_evidences(self, obj):
        task_node = self.get_task_node(obj)
        if task_node:
            return [{"id": e.id, "str": e.name} for e in task_node.evidences.all()]
        return []


class TaskTemplateWriteSerializer(BaseModelSerializer):
    status = serializers.CharField(required=False)
    observation = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    evidences = serializers.PrimaryKeyRelatedField(
        queryset=Evidence.objects.all(), many=True, required=False
    )

    class Meta:
        model = TaskTemplate
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not instance.is_recurrent:
            task_node = (
                TaskNode.objects.filter(task_template=instance)
                .order_by("due_date")
                .first()
            )
            if task_node:
                data["status"] = task_node.status
                data["observation"] = task_node.observation
                data["evidences"] = [e.id for e in task_node.evidences.all()]
            else:
                data["status"] = None
                data["observation"] = ""
                data["evidences"] = []
        return data

    def create(self, validated_data):
        tasknode_data = self._extract_tasknode_fields(validated_data)
        instance = super().create(validated_data)
        self._sync_task_node(instance, tasknode_data, False, False)
        return instance

    def update(self, instance, validated_data):
        was_recurrent = instance.is_recurrent  # Store the previous state
        tasknode_data = self._extract_tasknode_fields(validated_data)
        instance = super().update(instance, validated_data)
        now_recurrent = instance.is_recurrent
        self._sync_task_node(instance, tasknode_data, was_recurrent, now_recurrent)
        return instance

    def _extract_tasknode_fields(self, validated_data):
        """
        Separate the TaskNode-specific fields from validated_data.
        """
        return {
            "status": validated_data.pop("status", None),
            "observation": validated_data.pop("observation", None),
            "evidences": validated_data.pop("evidences", []),
        }

    def _sync_task_node(
        self, task_template, tasknode_data, was_recurrent, now_recurrent
    ):
        """
        Synchronize or create the TaskNode linked to a non-recurrent TaskTemplate.
        """
        if now_recurrent:
            return  # Only sync for non-recurrent templates

        task_nodes = TaskNode.objects.filter(task_template=task_template)
        if was_recurrent:
            # Was recurrent, now non-recurrent: must clean
            task_nodes.delete()
            task_node = TaskNode.objects.create(
                task_template=task_template,
                due_date=task_template.task_date,
                folder=task_template.folder,
            )
        else:
            # Was already non-recurrent: reuse if possible
            if task_nodes.count() == 1:
                task_node = task_nodes.first()
            else:
                task_nodes.delete()
                task_node = TaskNode.objects.create(
                    task_template=task_template,
                    due_date=task_template.task_date,
                    folder=task_template.folder,
                )

        task_node.to_delete = False
        task_node.due_date = task_template.task_date
        if tasknode_data.get("status") is not None:
            task_node.status = tasknode_data["status"]
        if tasknode_data.get("observation") is not None:
            task_node.observation = tasknode_data["observation"]
        task_node.save()

        evidences = tasknode_data.get("evidences")
        if evidences is not None:
            task_node.evidences.set(evidences)


class TaskNodeReadSerializer(BaseModelSerializer):
    task_template = FieldsRelatedField()
    folder = FieldsRelatedField()
    name = serializers.SerializerMethodField()
    assigned_to = FieldsRelatedField(many=True)
    evidences = FieldsRelatedField(many=True)
    is_recurrent = serializers.BooleanField(source="task_template.is_recurrent")
    applied_controls = FieldsRelatedField(many=True)
    compliance_assessments = FieldsRelatedField(many=True)
    assets = FieldsRelatedField(many=True)
    risk_assessments = FieldsRelatedField(many=True)

    def get_name(self, obj):
        return obj.task_template.name if obj.task_template else ""

    class Meta:
        model = TaskNode
        exclude = ["to_delete"]


class TaskNodeWriteSerializer(BaseModelSerializer):
    class Meta:
        model = TaskNode
        exclude = ["task_template"]
