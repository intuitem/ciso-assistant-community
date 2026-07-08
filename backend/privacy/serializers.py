from core.serializers import BaseModelSerializer
from django.db import transaction
from rest_framework import serializers
from core.serializer_fields import FieldsRelatedField
from .models import (
    Purpose,
    PersonalData,
    DataSubject,
    DataRecipient,
    DataContractor,
    DataTransfer,
    Processing,
    RightRequest,
    DataBreach,
)


# Purpose Serializers
class PurposeWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Purpose
        exclude = ["folder"]


class PurposeReadSerializer(BaseModelSerializer):
    processing = FieldsRelatedField()
    folder = FieldsRelatedField()

    class Meta:
        model = Purpose
        fields = "__all__"


# PersonalData Serializers
class PersonalDataWriteSerializer(BaseModelSerializer):
    class Meta:
        model = PersonalData
        exclude = ["folder"]


class PersonalDataReadSerializer(BaseModelSerializer):
    processing = FieldsRelatedField()
    folder = FieldsRelatedField()
    category = FieldsRelatedField()
    assets = FieldsRelatedField(["id", "name", "type", "folder"], many=True)

    class Meta:
        model = PersonalData
        fields = "__all__"


# DataSubject Serializers
class DataSubjectWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataSubject
        exclude = ["folder"]


class DataSubjectReadSerializer(BaseModelSerializer):
    processing = FieldsRelatedField()
    folder = FieldsRelatedField()

    class Meta:
        model = DataSubject
        fields = "__all__"


# DataRecipient Serializers
class DataRecipientWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataRecipient
        exclude = ["folder"]


class DataRecipientReadSerializer(BaseModelSerializer):
    processing = FieldsRelatedField()
    folder = FieldsRelatedField()

    class Meta:
        model = DataRecipient
        fields = "__all__"


# DataContractor Serializers
class DataContractorWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataContractor
        exclude = ["folder"]


class DataContractorReadSerializer(BaseModelSerializer):
    processing = FieldsRelatedField()
    folder = FieldsRelatedField()
    entity = FieldsRelatedField()

    class Meta:
        model = DataContractor
        fields = "__all__"


# DataTransfer Serializers
class DataTransferWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataTransfer
        exclude = ["folder"]


class DataTransferReadSerializer(BaseModelSerializer):
    processing = FieldsRelatedField()
    folder = FieldsRelatedField()
    entity = FieldsRelatedField()

    class Meta:
        model = DataTransfer
        fields = "__all__"


# Processing Serializers
class ProcessingWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Processing
        fields = "__all__"

    def update(self, instance, validated_data):
        old_folder_id = instance.folder_id
        with transaction.atomic():
            updated_instance = super().update(instance, validated_data)
            if old_folder_id != updated_instance.folder_id:
                related_models = [
                    Purpose,
                    PersonalData,
                    DataSubject,
                    DataRecipient,
                    DataContractor,
                    DataTransfer,
                ]
                for model in related_models:
                    model.objects.filter(processing=updated_instance).update(
                        folder=updated_instance.folder
                    )
        return updated_instance


class ProcessingReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(many=True)
    nature = FieldsRelatedField(many=True)
    associated_controls = FieldsRelatedField(["id", "name"], many=True)
    assigned_to = FieldsRelatedField(many=True)
    purposes = FieldsRelatedField(["name", "id", "legal_basis"], many=True)
    perimeters = FieldsRelatedField(many=True)
    personal_data_categories = serializers.SerializerMethodField()
    data_subject_categories = serializers.SerializerMethodField()

    def get_personal_data_categories(self, obj):
        seen = {}
        for pd in obj.personal_data.all():
            if pd.category_id:
                seen[pd.category_id] = pd.category.name
        return [{"str": name} for name in sorted(seen.values())]

    def get_data_subject_categories(self, obj):
        return [
            {"str": category}
            for category in sorted({ds.category for ds in obj.data_subjects.all()})
        ]

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
        model = Processing
        fields = "__all__"


# RightRequest Serializers
class RightRequestWriteSerializer(BaseModelSerializer):
    class Meta:
        model = RightRequest
        fields = "__all__"


class RightRequestReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owner = FieldsRelatedField(many=True)
    processings = FieldsRelatedField(many=True)

    class Meta:
        model = RightRequest
        fields = "__all__"


# DataBreach Serializers
class DataBreachWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataBreach
        fields = "__all__"


class DataBreachReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    assigned_to = FieldsRelatedField(many=True)
    authorities = FieldsRelatedField(many=True)
    affected_processings = FieldsRelatedField(many=True)
    affected_personal_data = FieldsRelatedField(many=True)
    remediation_measures = FieldsRelatedField(["id", "name"], many=True)
    incident = FieldsRelatedField()
    evidences = FieldsRelatedField(many=True)

    class Meta:
        model = DataBreach
        fields = "__all__"
