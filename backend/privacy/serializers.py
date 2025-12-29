from core.serializers import BaseModelSerializer, ReferentialSerializer
from core.serializer_fields import IdRelatedField
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
    processing = IdRelatedField()
    folder = IdRelatedField()

    class Meta:
        model = Purpose
        fields = "__all__"


# PersonalData Serializers
class PersonalDataWriteSerializer(BaseModelSerializer):
    class Meta:
        model = PersonalData
        exclude = ["folder"]


class PersonalDataReadSerializer(BaseModelSerializer):
    processing = IdRelatedField()
    folder = IdRelatedField()
    assets = IdRelatedField(["name", "type", "folder"], many=True)

    class Meta:
        model = PersonalData
        fields = "__all__"


# DataSubject Serializers
class DataSubjectWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataSubject
        exclude = ["folder"]


class DataSubjectReadSerializer(BaseModelSerializer):
    processing = IdRelatedField()
    folder = IdRelatedField()

    class Meta:
        model = DataSubject
        fields = "__all__"


# DataRecipient Serializers
class DataRecipientWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataRecipient
        exclude = ["folder"]


class DataRecipientReadSerializer(BaseModelSerializer):
    processing = IdRelatedField()
    folder = IdRelatedField()

    class Meta:
        model = DataRecipient
        fields = "__all__"


# DataContractor Serializers
class DataContractorWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataContractor
        exclude = ["folder"]


class DataContractorReadSerializer(BaseModelSerializer):
    processing = IdRelatedField()
    folder = IdRelatedField()
    entity = IdRelatedField()

    class Meta:
        model = DataContractor
        fields = "__all__"


# DataTransfer Serializers
class DataTransferWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataTransfer
        exclude = ["folder"]


class DataTransferReadSerializer(BaseModelSerializer):
    processing = IdRelatedField()
    folder = IdRelatedField()
    entity = IdRelatedField()

    class Meta:
        model = DataTransfer
        fields = "__all__"


# Processing Serializers
class ProcessingWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Processing
        fields = "__all__"


class ProcessingReadSerializer(BaseModelSerializer):
    folder = IdRelatedField()
    filtering_labels = IdRelatedField(many=True)
    nature = IdRelatedField(["name"], many=True)
    associated_controls = IdRelatedField(["name"], many=True)
    assigned_to = IdRelatedField(many=True)
    purposes = IdRelatedField(["name", "id", "legal_basis"], many=True)

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
    folder = IdRelatedField()
    owner = IdRelatedField(many=True)
    processings = IdRelatedField(many=True)

    class Meta:
        model = RightRequest
        fields = "__all__"


# DataBreach Serializers
class DataBreachWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DataBreach
        fields = "__all__"


class DataBreachReadSerializer(BaseModelSerializer):
    folder = IdRelatedField()
    assigned_to = IdRelatedField(many=True)
    authorities = IdRelatedField(many=True)
    affected_processings = IdRelatedField(many=True)
    affected_personal_data = IdRelatedField(many=True)
    remediation_measures = IdRelatedField(["name"], many=True)
    incident = IdRelatedField()

    class Meta:
        model = DataBreach
        fields = "__all__"
