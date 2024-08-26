from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer
from iam.models import Folder
from tprm.models import Entity, Representative, Solution, EntityAssessment
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class EntityReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()

    class Meta:
        model = Entity
        exclude = []


class EntityWriteSerializer(BaseModelSerializer):

    class Meta:
        model = Entity
        exclude = []


class EntityAssessmentReadSerializer(BaseModelSerializer):
    compliance_assessment = FieldsRelatedField()
    evidence = FieldsRelatedField()
    project = FieldsRelatedField()
    entity = FieldsRelatedField()

    class Meta:
        model = EntityAssessment
        exclude = []


class EntityAssessmentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = EntityAssessment
        exclude = []


class RepresentativeReadSerializer(BaseModelSerializer):
    entity = FieldsRelatedField()

    class Meta:
        model = Representative
        exclude = []


class RepresentativeWriteSerializer(BaseModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.all(),
        required=True,
    )

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
    provider_entity = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.all(),
        required=True,
    )
    recipient_entity = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.all(),
        required=True,
    )

    class Meta:
        model = Solution
        exclude = []
