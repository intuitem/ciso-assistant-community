import structlog
from django.contrib.auth import password_validation
from rest_framework import serializers

from core.serializer_fields import FieldsRelatedField

from .models import PersonalAccessToken, ServiceAccount, User

logger = structlog.get_logger(__name__)


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """

    old_password = serializers.CharField(
        max_length=128, write_only=True, required=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        max_length=128, write_only=True, required=True, style={"input_type": "password"}
    )
    confirm_new_password = serializers.CharField(
        max_length=128, write_only=True, required=True, style={"input_type": "password"}
    )

    def validate_new_password(self, data):
        password_validation.validate_password(data)
        return data

    def validate(self, data):
        if data["new_password"] != data["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "The two password fields didn't match."}
            )
        return data


class SetPasswordSerializer(serializers.Serializer):
    """
    Serializer for password set endpoint as an administrator.
    """

    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    new_password = serializers.CharField(
        max_length=128, write_only=True, required=True, style={"input_type": "password"}
    )
    confirm_new_password = serializers.CharField(
        max_length=128, write_only=True, required=True, style={"input_type": "password"}
    )

    def validate_new_password(self, data):
        password_validation.validate_password(data)
        return data

    def validate(self, data):
        if data["new_password"] != data["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "The two password fields didn't match."}
            )
        return data


class ResetPasswordConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset endpoint.
    """

    uidb64 = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        max_length=128, write_only=True, required=True, style={"input_type": "password"}
    )
    confirm_new_password = serializers.CharField(
        max_length=128, write_only=True, required=True, style={"input_type": "password"}
    )

    def validate_new_password(self, data):
        password_validation.validate_password(data)
        return data

    def validate(self, data):
        if data["new_password"] != data["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "The two password fields didn't match."}
            )
        return data


class PersonalAccessTokenReadSerializer(serializers.ModelSerializer):
    """
    Serializer for PersonalAccessToken model.
    """

    user = FieldsRelatedField(["email", "id"])

    class Meta:
        model = PersonalAccessToken
        fields = ["name", "user", "created", "expiry", "digest"]


class ServiceAccountReadSerializer(serializers.ModelSerializer):
    """
    Serializer for ServiceAccount model. Never exposes the client secret.
    """

    client_id = serializers.CharField(read_only=True)
    created_by = FieldsRelatedField(["email", "id"])
    permissions = serializers.SerializerMethodField()
    perimeter_folders = serializers.SerializerMethodField()
    is_recursive = serializers.SerializerMethodField()

    class Meta:
        model = ServiceAccount
        fields = [
            "id",
            "name",
            "description",
            "client_id",
            "is_active",
            "created_at",
            "updated_at",
            "created_by",
            "permissions",
            "perimeter_folders",
            "is_recursive",
        ]

    def get_permissions(self, obj) -> list[dict]:
        return [
            {
                "id": permission.id,
                "codename": permission.codename,
                "app_label": permission.content_type.app_label,
                "model": permission.content_type.model,
            }
            for permission in obj.role.permissions.select_related("content_type").all()
        ]

    def get_perimeter_folders(self, obj) -> list[dict]:
        role_assignment = obj.role_assignment
        if role_assignment is None:
            return []
        return [
            {"id": str(folder.id), "str": folder.name}
            for folder in role_assignment.perimeter_folders.all()
        ]

    def get_is_recursive(self, obj) -> bool:
        role_assignment = obj.role_assignment
        return role_assignment.is_recursive if role_assignment else False


class ServiceAccountWriteSerializer(serializers.Serializer):
    """
    Serializer for creating/updating a ServiceAccount. Permission and folder
    ids are re-validated server-side in iam.service_accounts helpers.
    """

    name = serializers.CharField(max_length=200)
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    permissions = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    perimeter_folders = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False
    )
    is_recursive = serializers.BooleanField(default=False)


class DisableMFASerializer(serializers.Serializer):
    """
    Serializer for disabling another user's MFA as an administrator.
    """

    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
