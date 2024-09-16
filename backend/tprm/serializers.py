from rest_framework import serializers
from core.models import ComplianceAssessment, Framework

from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer
from core.utils import RoleCodename, UserGroupCodename
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from tprm.models import Entity, EntityAssessment, Representative, Solution
from django.utils.translation import gettext_lazy as _
from ciso_assistant.settings import EMAIL_HOST, EMAIL_HOST_RESCUE

import structlog

logger = structlog.get_logger(__name__)


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
    authors = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)

    class Meta:
        model = EntityAssessment
        exclude = ["penetration", "dependency", "maturity", "trust"]


class EntityAssessmentWriteSerializer(BaseModelSerializer):
    create_audit = serializers.BooleanField(default=True)
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

            if not instance.compliance_assessment:
                enclave = Folder.objects.create(
                    content_type=Folder.ContentType.ENCLAVE,
                    name=f"{instance.project.name}/{instance.name}",
                    parent_folder=instance.folder,
                )
                audit.folder = enclave
                audit.save()

            audit.create_requirement_assessments()
            instance.compliance_assessment = audit
            instance.save()

    def _assign_third_party_respondents(
        self, instance: EntityAssessment, third_party_users: set[User]
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

    def _send_author_emails(self, instance, authors_to_email: set):
        if EMAIL_HOST or EMAIL_HOST_RESCUE:
            for author in authors_to_email:
                try:
                    author.mailing(
                        email_template_name="tprm/third_party_email.html",
                        subject=_(
                            "CISO Assistant: A questionnaire has been assigned to you"
                        ),
                        object="entity-assessments",
                        object_id=instance.id,
                    )
                except Exception as e:
                    print(f"Failed to send email to {author}: {e}")

    def create(self, validated_data):
        audit_data = self._extract_audit_data(validated_data)
        instance = super().create(validated_data)
        self._create_or_update_audit(instance, audit_data)
        self._assign_third_party_respondents(instance, set(instance.authors.all()))
        self._send_author_emails(instance, set(instance.authors.all()))
        return instance

    def update(self, instance: EntityAssessment, validated_data):
        audit_data = self._extract_audit_data(validated_data)
        new_authors = set(validated_data.get("authors", [])) - set(
            instance.authors.all()
        )
        instance = super().update(instance, validated_data)

        if not instance.compliance_assessment:
            self._create_or_update_audit(instance, audit_data)

        self._assign_third_party_respondents(instance, new_authors)
        self._send_author_emails(instance, new_authors)
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
    create_user = serializers.BooleanField(default=False, read_only=True)

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
