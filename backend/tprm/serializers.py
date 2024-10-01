from rest_framework import serializers
from core.models import ComplianceAssessment, Framework

from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer
from core.utils import RoleCodename, UserGroupCodename
from iam.models import Folder, Role, RoleAssignment, UserGroup
from django.contrib.auth import get_user_model
from tprm.models import Entity, EntityAssessment, Representative, Solution
from django.utils.translation import gettext_lazy as _

import structlog

logger = structlog.get_logger(__name__)

User = get_user_model()


class EntityReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owned_folders = FieldsRelatedField(many=True)

    class Meta:
        model = Entity
        exclude = []


class EntityWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Entity
        exclude = ["owned_folders"]


class EntityAssessmentReadSerializer(BaseModelSerializer):
    compliance_assessment = FieldsRelatedField()
    evidence = FieldsRelatedField()
    project = FieldsRelatedField()
    entity = FieldsRelatedField()
    folder = FieldsRelatedField()
    solutions = FieldsRelatedField(many=True)
    representatives = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)

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
            if not audit_data["framework"]:
                raise serializers.ValidationError(
                    {"framework": [_("Framework required")]}
                )

            audit = ComplianceAssessment.objects.create(
                name=instance.name,
                framework=audit_data["framework"],
                project=instance.project,
                selected_implementation_groups=audit_data[
                    "selected_implementation_groups"
                ],
            )

            enclave = Folder.objects.create(
                content_type=Folder.ContentType.ENCLAVE,
                name=f"{instance.project.name}/{instance.name}",
                parent_folder=instance.folder,
            )
            audit.folder = enclave
            audit.save()

            audit.create_requirement_assessments()
            audit.reviewers.set(instance.reviewers.all())
            audit.authors.set(instance.representatives.all())
            instance.compliance_assessment = audit
            instance.save()
        else:
            if instance.compliance_assessment:
                audit = instance.compliance_assessment
                audit.reviewers.set(instance.reviewers.all())
                audit.authors.set(instance.representatives.all())
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
        instance = super().update(instance, validated_data)

        self._create_or_update_audit(instance, audit_data)
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

    class Meta:
        model = Representative
        exclude = []


class RepresentativeWriteSerializer(BaseModelSerializer):
    create_user = serializers.BooleanField(default=False)

    def _create_or_update_user(self, instance, user):
        if not user:
            return
        user = User.objects.filter(
            email=instance.email,
        ).first()
        if not user:
            user = User.objects.create_user(
                email=instance.email,
                first_name=instance.first_name,
                last_name=instance.last_name,
            )
            user.is_third_party = True
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

    class Meta:
        model = Solution
        exclude = []


class SolutionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Solution
        exclude = ["recipient_entity"]
