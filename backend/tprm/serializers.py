from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer
from iam.models import Folder
from tprm.models import Entity, Representative
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
