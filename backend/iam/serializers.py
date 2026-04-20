import re

import structlog
from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers

from core.serializer_fields import FieldsRelatedField

from .models import (
    PersonalAccessToken,
    SA_EMAIL_DOMAIN,
    User,
)

logger = structlog.get_logger(__name__)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(
        # This will be used when the DRF browsable API is enabled
        style={"input_type": "password"},
        trim_whitespace=False,
        write_only=True,
    )

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(
                request=self.context.get("request"),
                username=username,
                password=password,
            )
            if not user:
                msg = "Unable to log in with provided credentials."
                raise serializers.ValidationError(msg, code="authorization")
        else:
            msg = 'Must include "username" and "password".'
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs


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


_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,62}[a-z0-9]$|^[a-z0-9]$")


class ServiceAccountCreateSerializer(serializers.Serializer):
    """Create a new service account. The email is built from the slug."""

    slug = serializers.CharField(max_length=64)
    description = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )
    expiry_date = serializers.DateField(required=False, allow_null=True, default=None)

    def validate_slug(self, value):
        value = value.lower().strip()
        if not _SLUG_RE.match(value):
            raise serializers.ValidationError(
                "Slug must be lowercase alphanumeric with hyphens, no leading/trailing hyphens."
            )
        email = f"{value}@{SA_EMAIL_DOMAIN}"
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "A service account with this name already exists."
            )
        return value

    def create(self, validated_data):
        slug = validated_data["slug"]
        email = f"{slug}@{SA_EMAIL_DOMAIN}"
        from iam.models import Folder

        user = User(
            email=email,
            first_name="",
            last_name="",
            is_active=True,
            is_service_account=True,
            is_superuser=False,
            first_login=False,
            keep_local_login=False,
            observation=validated_data.get("description", ""),
            expiry_date=validated_data.get("expiry_date"),
            folder=Folder.get_root_folder(),
        )
        user.set_unusable_password()
        user.save()
        return user


class ServiceAccountReadSerializer(serializers.ModelSerializer):
    """Read serializer for a service account user."""

    slug = serializers.SerializerMethodField()
    description = serializers.CharField(source="observation")
    active_key_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "slug",
            "email",
            "description",
            "is_active",
            "expiry_date",
            "date_joined",
            "active_key_count",
        ]

    def get_slug(self, obj):
        return obj.email.split("@")[0]

    def get_active_key_count(self, obj):
        if hasattr(obj, "active_key_count"):
            return obj.active_key_count
        return PersonalAccessToken.objects.filter(
            auth_token__user=obj, is_active=True
        ).count()


class ServiceAccountUpdateSerializer(serializers.ModelSerializer):
    """Partial update for a service account."""

    description = serializers.CharField(
        source="observation", required=False, allow_blank=True
    )

    class Meta:
        model = User
        fields = ["is_active", "expiry_date", "description"]


SA_KEY_LIMIT = 5


class ServiceAccountKeyReadSerializer(serializers.ModelSerializer):
    """Read serializer for a service account key (reuses PersonalAccessToken)."""

    created_at = serializers.SerializerMethodField()
    expiry_date = serializers.SerializerMethodField()

    class Meta:
        model = PersonalAccessToken
        fields = ["id", "name", "is_active", "created_at", "expiry_date"]

    def get_created_at(self, obj):
        return obj.auth_token.created

    def get_expiry_date(self, obj):
        return obj.auth_token.expiry


class ServiceAccountKeyCreateSerializer(serializers.Serializer):
    """Create a new API key for a service account."""

    service_account = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_service_account=True)
    )
    name = serializers.CharField(max_length=64)
    expiry_days = serializers.IntegerField(min_value=1, max_value=365, default=365)

    def validate(self, attrs):
        from datetime import date

        sa = attrs["service_account"]
        if not sa.is_active:
            raise serializers.ValidationError(
                {
                    "service_account": "Cannot create a key for a disabled service account."
                }
            )
        if sa.expiry_date and sa.expiry_date < date.today():
            raise serializers.ValidationError(
                {
                    "service_account": "Cannot create a key for an expired service account."
                }
            )
        if PersonalAccessToken.objects.filter(
            auth_token__user=sa, name=attrs["name"]
        ).exists():
            raise serializers.ValidationError(
                {
                    "name": "A key with this name already exists for this service account."
                }
            )
        if (
            PersonalAccessToken.objects.filter(auth_token__user=sa).count()
            >= SA_KEY_LIMIT
        ):
            raise serializers.ValidationError(
                f"Service account already has {SA_KEY_LIMIT} keys. Revoke one first."
            )
        return attrs
