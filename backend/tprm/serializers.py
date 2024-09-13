from rest_framework import serializers
from core.models import ComplianceAssessment, Framework

from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer
from iam.models import Folder
from tprm.models import Entity, EntityAssessment, Representative, Solution
from django.utils.translation import gettext_lazy as _


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

    def update(self, instance, validated_data):
        for author in validated_data.get("authors", []):
            if author not in instance.authors.all():
                author.mailing(
                    email_template_name="tprm/third_party_email.html",
                    subject=_(
                        "CISO Assistant: A questionnaire has been assigned to you"
                    ),
                    object="entity-assessments",
                    object_id=instance.id,
                )
        _audit = instance.compliance_assessment
        if not _audit:
            create_audit = validated_data.pop("create_audit")
            _framework = validated_data.pop("framework", None)
            _selected_implementation_groups = validated_data.pop(
                "selected_implementation_groups", None
            )
            instance = super().update(instance, validated_data)
            if create_audit:
                if not _framework:
                    raise serializers.ValidationError(
                        {"framework": [_("Framework required")]}
                    )
                audit = ComplianceAssessment.objects.create(
                    name=validated_data["name"],
                    framework=_framework,
                    project=validated_data["project"],
                    selected_implementation_groups=_selected_implementation_groups,
                )
                audit.create_requirement_assessments()
                instance.compliance_assessment = audit
                instance.save()
        return instance

    class Meta:
        model = EntityAssessment
        exclude = ["penetration", "dependency", "maturity", "trust"]


class EntityAssessmentCreateSerializer(BaseModelSerializer):
    create_audit = serializers.BooleanField(default=True)
    framework = serializers.PrimaryKeyRelatedField(
        queryset=Framework.objects.all(), required=False
    )
    selected_implementation_groups = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    def create(self, validated_data):
        create_audit = validated_data.pop("create_audit")
        _framework = validated_data.pop("framework", None)
        _selected_implementation_groups = validated_data.pop(
            "selected_implementation_groups", None
        )
        instance = super().create(validated_data)
        if create_audit:
            if not _framework:
                raise serializers.ValidationError(
                    {"framework": [_("Framework required")]}
                )
            enclave = Folder.objects.create(
                content_type=Folder.ContentType.ENCLAVE,
                name=f"{instance.project.name}/{instance.name}",
                parent_folder=instance.folder,
            )
            audit = ComplianceAssessment.objects.create(
                folder=enclave,
                name=validated_data["name"],
                framework=_framework,
                project=validated_data["project"],
                selected_implementation_groups=_selected_implementation_groups,
            )
            audit.create_requirement_assessments()
            instance.compliance_assessment = audit
            instance.save()
        if instance.authors:
            for author in instance.authors.all():
                author.mailing(
                    email_template_name="tprm/third_party_email.html",
                    subject=_(
                        "CISO Assistant: A questionnaire has been assigned to you"
                    ),
                    object="entity-assessments",
                    object_id=instance.id,
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
