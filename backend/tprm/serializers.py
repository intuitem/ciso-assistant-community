from django.db import transaction
from rest_framework import serializers
from ciso_assistant.settings import EMAIL_HOST, EMAIL_HOST_RESCUE
from core.models import ComplianceAssessment, Framework

from core.serializer_fields import FieldsRelatedField, HashSlugRelatedField
from core.serializers import BaseModelSerializer
from core.utils import RoleCodename, UserGroupCodename
from iam.models import Folder, Role, RoleAssignment, UserGroup
from django.contrib.auth import get_user_model
from tprm.models import Entity, EntityAssessment, Representative, Solution, Contract
from django.utils.translation import gettext_lazy as _

import structlog

logger = structlog.get_logger(__name__)

User = get_user_model()


class EntityReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owned_folders = FieldsRelatedField(many=True)
    parent_entity = FieldsRelatedField()
    branches = FieldsRelatedField(many=True)
    relationship = FieldsRelatedField(many=True)
    contracts = FieldsRelatedField(many=True)
    legal_identifiers = serializers.SerializerMethodField()
    default_criticality = serializers.ReadOnlyField()
    filtering_labels = FieldsRelatedField(many=True)

    def get_legal_identifiers(self, obj):
        """Format legal identifiers as a readable string for display"""
        if not obj.legal_identifiers:
            return ""
        return "\n".join(
            [f"{key}: {value}" for key, value in obj.legal_identifiers.items()]
        )

    class Meta:
        model = Entity
        exclude = []


class EntityWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Entity
        exclude = ["owned_folders"]

    def to_internal_value(self, data):
        """Convert None to empty string for CharField DORA fields before validation"""
        dora_char_fields = [
            "country",
            "currency",
            "dora_entity_type",
            "dora_entity_hierarchy",
            "dora_provider_person_type",
        ]
        for field in dora_char_fields:
            if field in data and data[field] is None:
                data[field] = ""
        return super().to_internal_value(data)

    def validate_legal_identifiers(self, value):
        """
        Validate legal identifiers, ensuring LEI is exactly 20 characters if provided.
        """
        if value and isinstance(value, dict):
            lei = value.get("LEI", "")
            # Strip whitespace and check if LEI exists
            if lei:
                lei_stripped = lei.strip()
                if lei_stripped and len(lei_stripped) != 20:
                    raise serializers.ValidationError(_("leiLengthError"))
        return value

    def validate_parent_entity(self, value):
        """
        Validate that an entity cannot be set as its own parent.
        """
        if value and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError(
                _("An entity cannot be set as its own parent")
            )
        return value


class EntityImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    owned_folders = HashSlugRelatedField(slug_field="pk", many=True, read_only=True)

    class Meta:
        model = Entity
        fields = [
            "name",
            "description",
            "folder",
            "mission",
            "reference_link",
            "owned_folders",
            "country",
            "currency",
            "dora_entity_type",
            "dora_entity_hierarchy",
            "dora_assets_value",
            "dora_competent_authority",
            "created_at",
            "updated_at",
        ]


class EntityAssessmentReadSerializer(BaseModelSerializer):
    compliance_assessment = FieldsRelatedField(fields=["id", "name"])
    evidence = FieldsRelatedField()
    perimeter = FieldsRelatedField()
    entity = FieldsRelatedField()
    folder = FieldsRelatedField()
    solutions = FieldsRelatedField(many=True)
    representatives = FieldsRelatedField(many=True)
    authors = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)
    validation_flows = FieldsRelatedField(
        many=True,
        fields=[
            "id",
            "ref_id",
            "status",
            {"approver": ["id", "email", "first_name", "last_name"]},
        ],
        source="validationflow_set",
    )

    class Meta:
        model = EntityAssessment
        exclude = ["penetration", "dependency", "maturity", "trust"]


class EntityAssessmentWriteSerializer(BaseModelSerializer):
    create_audit = serializers.BooleanField(default=False)
    framework = serializers.PrimaryKeyRelatedField(
        queryset=Framework.objects.all(), required=False
    )
    selected_implementation_groups = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    def _extract_audit_data(self, validated_data):
        audit_data = {
            "create_audit": validated_data.pop("create_audit", False),
            "framework": validated_data.pop("framework", None),
            "selected_implementation_groups": validated_data.pop(
                "selected_implementation_groups", None
            ),
        }
        return audit_data

    def _create_or_update_audit(self, instance, audit_data):
        if audit_data["create_audit"]:
            if not audit_data.get("framework"):
                raise serializers.ValidationError(
                    {"framework": [_("Framework required")]}
                )

            with transaction.atomic():
                locked = EntityAssessment.objects.select_for_update().get(
                    pk=instance.pk
                )  # lock entity assessment until the end of the transaction
                if getattr(locked, "compliance_assessment_id", None):
                    raise serializers.ValidationError(
                        {
                            "create_audit": [
                                _("An audit already exists for this assessment")
                            ]
                        }
                    )
                audit = ComplianceAssessment.objects.create(
                    name=locked.name,
                    framework=audit_data["framework"],
                    perimeter=locked.perimeter,
                    selected_implementation_groups=audit_data[
                        "selected_implementation_groups"
                    ],
                )

                enclave = Folder.objects.create(
                    content_type=Folder.ContentType.ENCLAVE,
                    name=f"{instance.entity.name}/{instance.name}",
                    parent_folder=instance.folder,
                )
                audit.folder = enclave
                audit.save()

                audit.create_requirement_assessments()
                audit.reviewers.set(instance.reviewers.all())
                representatives = instance.representatives.all()
                audit.authors.set([rep.actor for rep in representatives])
                instance.compliance_assessment = audit
                instance.save()
        else:
            if instance.compliance_assessment:
                audit = instance.compliance_assessment
                audit.reviewers.set(instance.reviewers.all())
                representatives = instance.representatives.all()
                audit.authors.set([rep.actor for rep in representatives])
            instance.save()

    def _assign_third_party_respondents(
        self,
        instance: EntityAssessment,
        third_party_users: set[User],
        old_third_party_users: set[User] = set(),
    ):
        if instance.compliance_assessment:
            enclave = instance.compliance_assessment.folder
            respondents, _ = UserGroup.objects.get_or_create(
                name=UserGroupCodename.THIRD_PARTY_RESPONDENT,
                folder=enclave,
                builtin=True,
            )
            role_assignment, _ = RoleAssignment.objects.get_or_create(
                user_group=respondents,
                role=Role.objects.get(name=RoleCodename.THIRD_PARTY_RESPONDENT),
                builtin=True,
                folder=enclave,
                is_recursive=True,
            )
            role_assignment.perimeter_folders.add(enclave)
            for user in third_party_users:
                if not user.is_third_party:
                    logger.warning("User is not a third-party", user=user)
                user.user_groups.add(respondents)
            for user in old_third_party_users:
                if not user.is_third_party:
                    logger.warning("User is not a third-party", user=user)
                user.user_groups.remove(respondents)

    def create(self, validated_data):
        audit_data = self._extract_audit_data(validated_data)
        with transaction.atomic():
            instance = super().create(validated_data)
            self._create_or_update_audit(instance, audit_data)
            self._assign_third_party_respondents(
                instance, set(instance.representatives.all())
            )
        return instance

    def update(self, instance: EntityAssessment, validated_data):
        audit_data = self._extract_audit_data(validated_data)
        representatives = set(validated_data.get("representatives", []))
        old_representatives = set(instance.representatives.all()) - set(
            validated_data.get("representatives", [])
        )

        # If perimeter is being changed, update folder to match the new perimeter's folder
        if "perimeter" in validated_data:
            new_perimeter = validated_data["perimeter"]
            if new_perimeter and new_perimeter.folder:
                validated_data["folder"] = new_perimeter.folder

        with transaction.atomic():
            instance = super().update(instance, validated_data)
            self._create_or_update_audit(instance, audit_data)
            if "representatives" in validated_data:
                self._assign_third_party_respondents(
                    instance, representatives, old_representatives
                )
        return instance

    class Meta:
        model = EntityAssessment
        exclude = []


class RepresentativeReadSerializer(BaseModelSerializer):
    entity = FieldsRelatedField()
    user = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(many=True)

    class Meta:
        model = Representative
        exclude = []


class RepresentativeWriteSerializer(BaseModelSerializer):
    IMMUTABLE_FIELDS = ["entity"]
    create_user = serializers.BooleanField(default=False)

    def _create_or_update_user(self, instance, user):
        if not user:
            return
        user = User.objects.filter(
            email=instance.email,
        ).first()
        if not user:
            send_mail = EMAIL_HOST or EMAIL_HOST_RESCUE
            try:
                user = User.objects.create_user(
                    email=instance.email,
                    first_name=instance.first_name,
                    last_name=instance.last_name,
                    is_third_party=True,
                    keep_local_login=True,
                )
            except Exception as e:
                logger.error(e)
                user = User.objects.filter(email=instance.email).first()
                if user and send_mail:
                    user.is_third_party = True
                    user.keep_local_login = True
                    user.save()
                    instance.user = user
                    instance.save()
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
        user.is_third_party = True
        user.keep_local_login = True
        user.save()
        instance.user = user
        instance.save()

    def create(self, validated_data):
        user = validated_data.pop("create_user", False)
        instance = super().create(validated_data)
        self._create_or_update_user(instance, user)
        return instance

    def update(self, instance, validated_data):
        user = validated_data.pop("create_user", False)
        instance = super().update(instance, validated_data)
        self._create_or_update_user(instance, user)
        return instance

    class Meta:
        model = Representative
        exclude = []


class SolutionReadSerializer(BaseModelSerializer):
    provider_entity = FieldsRelatedField()
    recipient_entity = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    contracts = FieldsRelatedField(many=True)
    owner = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(many=True)

    class Meta:
        model = Solution
        exclude = []


class SolutionWriteSerializer(BaseModelSerializer):
    IMMUTABLE_FIELDS = ["provider_entity"]

    def to_internal_value(self, data):
        """Convert None to empty string for CharField DORA fields before validation"""
        dora_char_fields = [
            "dora_ict_service_type",
            "data_location_storage",
            "data_location_processing",
            "dora_data_sensitiveness",
            "dora_reliance_level",
            "dora_substitutability",
            "dora_non_substitutability_reason",
            "dora_has_exit_plan",
            "dora_reintegration_possibility",
            "dora_discontinuing_impact",
            "dora_alternative_providers_identified",
        ]
        for field in dora_char_fields:
            if field in data and data[field] is None:
                data[field] = ""
        return super().to_internal_value(data)

    class Meta:
        model = Solution
        exclude = ["recipient_entity"]


class ContractReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owner = FieldsRelatedField(many=True)
    provider_entity = FieldsRelatedField()
    beneficiary_entity = FieldsRelatedField()
    evidences = FieldsRelatedField(many=True)
    solutions = FieldsRelatedField(many=True)
    overarching_contract = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(many=True)

    class Meta:
        model = Contract
        exclude = []


class ContractWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Contract
        exclude = []

    def validate_overarching_contract(self, value):
        """
        Validate that a contract cannot be set as its own overarching contract.
        """
        if value and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError(
                _("A contract cannot be set as its own overarching contract")
            )
        return value
