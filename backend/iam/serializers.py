import structlog
from django.contrib.auth import password_validation
from rest_framework import serializers

from core.serializer_fields import FieldsRelatedField
from core.utils import RoleCodename

from .models import PersonalAccessToken, Role, ServiceAccount, User

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
    folders = serializers.SerializerMethodField()
    is_recursive = serializers.SerializerMethodField()
    is_role_linked = serializers.BooleanField(source="role.builtin", read_only=True)
    is_global_admin = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = ServiceAccount
        fields = [
            "id",
            "name",
            "description",
            "client_id",
            "is_active",
            "expiry_date",
            "created_at",
            "updated_at",
            "created_by",
            "permissions",
            "folders",
            "is_recursive",
            "previous_secret_expires_at",
            "secret_preview",
            "is_role_linked",
            "is_global_admin",
            "role_name",
            "role",
        ]

    def get_is_global_admin(self, obj) -> bool:
        return obj.role.builtin and obj.role.name == RoleCodename.ADMINISTRATOR.value

    def get_role_name(self, obj) -> str | None:
        return str(obj.role) if obj.role.builtin else None

    def get_role(self, obj) -> str | None:
        return str(obj.role_id) if obj.role.builtin else None

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

    def get_folders(self, obj) -> list[dict]:
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

    name = serializers.CharField(max_length=100)
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    permissions = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True, required=False
    )
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.filter(builtin=True), required=False, allow_null=True
    )
    folders = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    is_recursive = serializers.BooleanField(default=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)

    def validate_name(self, value):
        qs = ServiceAccount.objects.filter(name=value)
        instance = self.context.get("instance")
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A service account with this name already exists."
            )
        return value

    def validate(self, attrs):
        has_role = attrs.get("role") is not None
        has_permissions = bool(attrs.get("permissions"))
        if has_role and has_permissions:
            raise serializers.ValidationError(
                "Provide either a role or permissions, not both."
            )
        if "permissions" in attrs and not has_permissions:
            instance = self.context.get("instance")
            currently_role_linked = instance is not None and instance.role.builtin
            if has_role or currently_role_linked:
                attrs.pop("permissions")
        if not self.partial and not has_role and not has_permissions:
            raise serializers.ValidationError("Provide either a role or permissions.")
        return attrs


class DisableMFASerializer(serializers.Serializer):
    """
    Serializer for disabling another user's MFA as an administrator.
    """

    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
