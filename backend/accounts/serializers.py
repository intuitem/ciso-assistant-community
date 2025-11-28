"""
Serializers for ClientAccount model.
"""

from rest_framework import serializers
from django.utils.text import slugify
from django.utils import timezone

from .models import ClientAccount
from iam.models import Folder, User


class ClientAccountSerializer(serializers.ModelSerializer):
    """Serializer for ClientAccount model with full details."""

    user_count = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_user_limit_reached = serializers.BooleanField(read_only=True)
    folder_name = serializers.CharField(source="folder.name", read_only=True)
    folder_id = serializers.UUIDField(source="folder.id", read_only=True)
    admin_user_email = serializers.CharField(source="admin_user.email", read_only=True)

    class Meta:
        model = ClientAccount
        fields = [
            "id",
            "name",
            "slug",
            "email",
            "phone",
            "address",
            "folder",
            "folder_id",
            "folder_name",
            "status",
            "plan",
            "subscription_start",
            "subscription_end",
            "max_users",
            "max_domains",
            "notes",
            "logo",
            "admin_user",
            "admin_user_email",
            "user_count",
            "is_active",
            "is_expired",
            "days_until_expiry",
            "is_user_limit_reached",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "folder",
            "folder_id",
            "folder_name",
            "created_at",
            "updated_at",
        ]

    def validate_slug(self, value):
        """Ensure slug is unique and properly formatted."""
        value = slugify(value)
        instance = self.instance
        if instance:
            # Exclude current instance when checking uniqueness
            if ClientAccount.objects.filter(slug=value).exclude(pk=instance.pk).exists():
                raise serializers.ValidationError("A client account with this slug already exists.")
        else:
            if ClientAccount.objects.filter(slug=value).exists():
                raise serializers.ValidationError("A client account with this slug already exists.")
        return value

    def validate_subscription_end(self, value):
        """Ensure subscription end date is not in the past for new accounts."""
        if not self.instance and value < timezone.now().date():
            raise serializers.ValidationError("Subscription end date cannot be in the past.")
        return value

    def validate_max_users(self, value):
        """Ensure max_users is at least 1."""
        if value < 1:
            raise serializers.ValidationError("Maximum users must be at least 1.")
        return value


class ClientAccountCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new ClientAccount."""

    admin_email = serializers.EmailField(write_only=True, required=False)
    admin_first_name = serializers.CharField(write_only=True, required=False)
    admin_last_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = ClientAccount
        fields = [
            "name",
            "slug",
            "email",
            "phone",
            "address",
            "status",
            "plan",
            "subscription_start",
            "subscription_end",
            "max_users",
            "max_domains",
            "notes",
            "admin_email",
            "admin_first_name",
            "admin_last_name",
        ]

    def validate_slug(self, value):
        """Auto-generate slug if not provided, ensure uniqueness."""
        if not value:
            value = slugify(self.initial_data.get("name", ""))
        value = slugify(value)
        if ClientAccount.objects.filter(slug=value).exists():
            # Append a unique suffix
            import uuid
            value = f"{value}-{str(uuid.uuid4())[:8]}"
        return value

    def create(self, validated_data):
        # Extract admin user data
        admin_email = validated_data.pop("admin_email", None)
        admin_first_name = validated_data.pop("admin_first_name", "")
        admin_last_name = validated_data.pop("admin_last_name", "")

        # Create the account (this will auto-create the folder)
        account = ClientAccount.objects.create(**validated_data)

        # Create admin user if email provided
        if admin_email:
            from iam.models import UserGroup

            # Create user
            user = User.objects.create_user(
                email=admin_email,
                first_name=admin_first_name,
                last_name=admin_last_name,
            )

            # Add user to Domain Manager group
            try:
                manager_group = UserGroup.objects.get(
                    folder=account.folder,
                    name="BI-UG-DOM"
                )
                manager_group.user_set.add(user)
            except UserGroup.DoesNotExist:
                # Fallback: add to first available group in the folder
                first_group = UserGroup.objects.filter(folder=account.folder).first()
                if first_group:
                    first_group.user_set.add(user)

            account.admin_user = user
            account.save(update_fields=["admin_user"])

        return account


class ClientAccountListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing accounts."""

    user_count = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClientAccount
        fields = [
            "id",
            "name",
            "slug",
            "email",
            "status",
            "plan",
            "subscription_start",
            "subscription_end",
            "max_users",
            "user_count",
            "is_active",
            "days_until_expiry",
            "created_at",
        ]


class ClientAccountStatsSerializer(serializers.Serializer):
    """Serializer for account statistics."""

    total_accounts = serializers.IntegerField()
    active_accounts = serializers.IntegerField()
    expired_accounts = serializers.IntegerField()
    suspended_accounts = serializers.IntegerField()
    trial_accounts = serializers.IntegerField()
    total_users = serializers.IntegerField()
    expiring_soon = serializers.IntegerField()  # Accounts expiring in next 30 days
    plan_distribution = serializers.DictField()


class ExtendSubscriptionSerializer(serializers.Serializer):
    """Serializer for extending subscription."""

    days = serializers.IntegerField(min_value=1, max_value=3650)  # Max 10 years


class ChangeStatusSerializer(serializers.Serializer):
    """Serializer for changing account status."""

    status = serializers.ChoiceField(choices=ClientAccount.Status.choices)
