from dateutil.relativedelta import relativedelta
from rest_framework import serializers

from core.models import Terminology
from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField, PathField
from custom_fields.serializers import CustomFieldsSerializerMixin
from pmbok.models import (
    GenericCollection,
    Accreditation,
    Project,
    ResponsibilityRole,
    ResponsibilityMatrix,
    ResponsibilityMatrixActivity,
    ResponsibilityMatrixActor,
    ResponsibilityAssignment,
)


class GenericCollectionReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    compliance_assessments = FieldsRelatedField(["id", "status"], many=True)
    risk_assessments = FieldsRelatedField(["id", "status"], many=True)
    crq_studies = FieldsRelatedField(["id", "status"], many=True)
    ebios_studies = FieldsRelatedField(["id", "status"], many=True)
    entity_assessments = FieldsRelatedField(["id", "status"], many=True)
    findings_assessments = FieldsRelatedField(["id", "status"], many=True)
    documents = FieldsRelatedField(["id", "status"], many=True)
    security_exceptions = FieldsRelatedField(["id", "status"], many=True)
    policies = FieldsRelatedField(["id", "status"], many=True)
    dependencies = FieldsRelatedField(many=True)
    projects = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)

    class Meta:
        model = GenericCollection
        fields = "__all__"


class GenericCollectionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = GenericCollection
        fields = "__all__"


class AccreditationReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    author = FieldsRelatedField()
    authority = FieldsRelatedField()
    linked_collection = FieldsRelatedField()
    collection_data = serializers.SerializerMethodField()
    checklist = FieldsRelatedField()
    decision_evidence = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    status = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    checklist_progress = serializers.SerializerMethodField()
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

    def get_status(self, obj):
        return obj.status.get_name_translated

    def get_category(self, obj):
        return obj.category.get_name_translated

    def get_collection_data(self, obj):
        if obj.linked_collection:
            return GenericCollectionReadSerializer(obj.linked_collection).data
        return None

    def get_checklist_progress(self, obj):
        if obj.checklist:
            return obj.checklist.progress
        return None

    class Meta:
        model = Accreditation
        fields = "__all__"


class AccreditationWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Accreditation
        fields = "__all__"

    def validate(self, data):
        commission_date = data.get(
            "commission_date",
            getattr(getattr(self, "instance", None), "commission_date", None),
        )
        duration_months = data.get(
            "duration_months",
            getattr(getattr(self, "instance", None), "duration_months", None),
        )

        if commission_date and duration_months and not data.get("expiry_date"):
            data["expiry_date"] = commission_date + relativedelta(
                months=duration_months
            )

        return super().validate(data)


class ProjectReadSerializer(CustomFieldsSerializerMixin, BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    owner = FieldsRelatedField()
    sponsor = FieldsRelatedField()
    parent_project = FieldsRelatedField()
    sub_projects = FieldsRelatedField(many=True)
    linked_collection = FieldsRelatedField()
    responsibility_matrices = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    status = FieldsRelatedField(["id", "name"])
    health = FieldsRelatedField(["id", "name"])

    class Meta:
        model = Project
        fields = "__all__"


class ProjectWriteSerializer(CustomFieldsSerializerMixin, BaseModelSerializer):
    status = serializers.PrimaryKeyRelatedField(
        queryset=Terminology.objects.filter(
            field_path=Terminology.FieldPath.PROJECT_STATUS, is_visible=True
        ),
        required=False,
        allow_null=True,
    )
    responsibility_matrices = serializers.PrimaryKeyRelatedField(
        queryset=ResponsibilityMatrix.objects.all(),
        many=True,
        required=False,
    )
    create_collection = serializers.BooleanField(
        write_only=True, required=False, default=True
    )

    class Meta:
        model = Project
        fields = "__all__"

    def create(self, validated_data):
        create_collection = validated_data.pop("create_collection", True)
        # Only the collection auto-created by Project.save() is subject to opt-out;
        # an explicitly provided collection is never touched.
        explicit_collection = validated_data.get("linked_collection")
        instance = super().create(validated_data)
        # linked_collection is on_delete=SET_NULL, so the FK clears automatically.
        if (
            not create_collection
            and not explicit_collection
            and instance.linked_collection_id
        ):
            instance.linked_collection.delete()
            instance.linked_collection = None
        return instance

    def update(self, instance, validated_data):
        validated_data.pop("create_collection", None)
        return super().update(instance, validated_data)

    def validate(self, data):
        instance = getattr(self, "instance", None)

        def current(field):
            return data.get(field, getattr(instance, field, None) if instance else None)

        start = current("start_date")
        end = current("end_date")
        eta = current("eta")
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be earlier than start date."}
            )
        if start and eta and eta < start:
            raise serializers.ValidationError(
                {"eta": "ETA cannot be earlier than start date."}
            )
        return super().validate(data)

    def validate_parent_project(self, value):
        if value is None:
            return value
        instance = getattr(self, "instance", None)
        if instance is None:
            return value
        if value.pk == instance.pk:
            raise serializers.ValidationError("A project cannot be its own parent.")
        descendants = set()
        queue = list(
            Project.objects.filter(parent_project=instance.pk).values_list(
                "pk", flat=True
            )
        )
        while queue:
            current = queue.pop()
            if current in descendants:
                continue
            descendants.add(current)
            queue.extend(
                Project.objects.filter(parent_project=current).values_list(
                    "pk", flat=True
                )
            )
        if value.pk in descendants:
            raise serializers.ValidationError(
                "Setting this project as parent would create a cycle."
            )
        return value


class ResponsibilityRoleReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()

    class Meta:
        model = ResponsibilityRole
        fields = "__all__"


class ResponsibilityRoleWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ResponsibilityRole
        fields = "__all__"


class ResponsibilityMatrixReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    roles = FieldsRelatedField(
        ["id", "code", "name", "color", "order", "taxonomy"], many=True
    )
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    activities_count = serializers.SerializerMethodField()

    def get_activities_count(self, obj):
        return obj.activities.count()

    class Meta:
        model = ResponsibilityMatrix
        fields = "__all__"


class ResponsibilityMatrixWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ResponsibilityMatrix
        fields = "__all__"

    def create(self, validated_data):
        roles = validated_data.pop("roles", None)
        instance = super().create(validated_data)
        preset = instance.preset
        if not roles and preset != ResponsibilityMatrix.Preset.CUSTOM:
            instance.roles.set(
                ResponsibilityRole.objects.filter(
                    taxonomy=preset, builtin=True, is_visible=True
                )
            )
        elif roles:
            instance.roles.set(roles)
        return instance


class ResponsibilityMatrixActivityReadSerializer(BaseModelSerializer):
    matrix = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    applied_controls = FieldsRelatedField(many=True)
    task_templates = FieldsRelatedField(many=True)
    risk_assessments = FieldsRelatedField(many=True)
    compliance_assessments = FieldsRelatedField(many=True)
    findings_assessments = FieldsRelatedField(many=True)
    business_impact_analyses = FieldsRelatedField(many=True)
    assignments_count = serializers.SerializerMethodField()

    def get_assignments_count(self, obj):
        return obj.assignments.count()

    class Meta:
        model = ResponsibilityMatrixActivity
        fields = "__all__"


class ResponsibilityMatrixActivityWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ResponsibilityMatrixActivity
        fields = "__all__"


class ResponsibilityMatrixActorReadSerializer(BaseModelSerializer):
    matrix = FieldsRelatedField()
    actor = FieldsRelatedField()

    class Meta:
        model = ResponsibilityMatrixActor
        fields = "__all__"


class ResponsibilityMatrixActorWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ResponsibilityMatrixActor
        fields = "__all__"


class ResponsibilityAssignmentReadSerializer(BaseModelSerializer):
    activity = FieldsRelatedField()
    actor = FieldsRelatedField()
    role = FieldsRelatedField(["id", "code", "name", "color"])

    class Meta:
        model = ResponsibilityAssignment
        fields = "__all__"


class ResponsibilityAssignmentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ResponsibilityAssignment
        fields = "__all__"

    def validate(self, data):
        activity = data.get(
            "activity", getattr(getattr(self, "instance", None), "activity", None)
        )
        role = data.get("role", getattr(getattr(self, "instance", None), "role", None))
        actor = data.get(
            "actor", getattr(getattr(self, "instance", None), "actor", None)
        )
        if activity and role and role not in activity.matrix.roles.all():
            raise serializers.ValidationError(
                {
                    "role": "Role is not part of this matrix's taxonomy. "
                    "Add it to the matrix first or pick a role already attached."
                }
            )
        # Mirrors cycle_cell: blocks POST/PATCH from creating rows for off-matrix actors.
        if (
            activity
            and actor
            and not activity.matrix.matrix_actors.filter(actor=actor).exists()
        ):
            raise serializers.ValidationError(
                {"actor": "Actor is not a member of this matrix."}
            )
        return super().validate(data)
