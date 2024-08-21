from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer
from iam.models import Folder
from tprm.models import Entity, Representative, Solution, Product, EntityAssessment
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class EntityReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owned_folders = FieldsRelatedField(many=True)

    class Meta:
        model = Entity
        exclude = []


class EntityWriteSerializer(BaseModelSerializer):
    owned_folders = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.filter(owner=None),
        many=True,
        required=False,
    )

    def validate_owned_folders(self, owned_folders):
        for folder in owned_folders:
            if folder.owner.exists():
                raise serializers.ValidationError(
                    _("Folder {} is already owned by another entity").format(folder)
                )
        return owned_folders

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
    products = FieldsRelatedField(many=True)

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


class ProductReadSerializer(BaseModelSerializer):
    solution = FieldsRelatedField()

    class Meta:
        model = Product
        exclude = []


class ProductWriteSerializer(BaseModelSerializer):
    solution = serializers.PrimaryKeyRelatedField(
        queryset=Solution.objects.all(),
        required=True,
    )

    class Meta:
        model = Product
        exclude = []
