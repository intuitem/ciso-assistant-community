from core.serializers import BaseModelSerializer, ReferentialSerializer
from core.serializer_fields import FieldsRelatedField
from .models import (
    ProcessingNature,
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
    assets = FieldsRelatedField(["name", "type", "folder"], many=True)

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


class ProcessingReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(many=True)
    nature = FieldsRelatedField(["name"], many=True)
    associated_controls = FieldsRelatedField(["name"], many=True)
    assigned_to = FieldsRelatedField(many=True)

    class Meta:
        model = Processing
        fields = "__all__"


class ProcessingNatureReadSerializer(ReferentialSerializer):
    class Meta:
        model = ProcessingNature
        exclude = ["translations"]


class ProcessingNatureWriteSerializer(ProcessingNatureReadSerializer):
    pass


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
    remediation_measures = FieldsRelatedField(["name"], many=True)
    incident = FieldsRelatedField()

    class Meta:
        model = DataBreach
        fields = "__all__"
