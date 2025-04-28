from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import authenticate
from knox.models import AuthToken
from rest_framework import serializers
from .models import User
from django.contrib.auth import password_validation
from core.serializer_fields import FieldsRelatedField


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


class AuthTokenReadSerializer(serializers.ModelSerializer):
    """
    Serializer for AuthToken model.
    """

    user = FieldsRelatedField(["email", "id"])

    class Meta:
        model = AuthToken
        fields = ["user", "created", "expiry", "digest"]


class AuthTokenCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating AuthToken.
    """

    def create(self, validated_data):
        user = self.context["request"].user
        auth_token = AuthToken.objects.create(user=user, **validated_data)
        return auth_token

    def validate_expiry(self, expiry):
        if expiry is not None:
            if expiry <= timezone.now():
                raise serializers.ValidationError("Expiry must be in the future.")
            if timedelta(days=366) < expiry - timezone.now():
                raise serializers.ValidationError(
                    "Expiry must be less than a year away."
                )

    class Meta:
        model = AuthToken
        fields = ["created", "expiry"]
