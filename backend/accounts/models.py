"""
Client Account model for multi-tenant management in DASHVIDER.
Each ClientAccount represents a company/organization that purchases access to the platform.
"""

import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from core.base_models import AbstractBaseModel
from iam.models import Folder, FolderMixin

import structlog

logger = structlog.get_logger(__name__)


class ClientAccount(AbstractBaseModel):
    """
    Represents a client/tenant account in the multi-tenant system.
    Each account is associated with a Folder (domain) for permission management.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")
        EXPIRED = "expired", _("Expired")
        TRIAL = "trial", _("Trial")

    class Plan(models.TextChoices):
        FREE = "free", _("Free")
        BASIC = "basic", _("Basic")
        PRO = "pro", _("Professional")
        ENTERPRISE = "enterprise", _("Enterprise")

    # Basic Information
    name = models.CharField(
        max_length=255,
        verbose_name=_("Company Name"),
        help_text=_("Name of the client company/organization"),
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("Account Slug"),
        help_text=_("Unique identifier for the account (URL-friendly)"),
    )

    email = models.EmailField(
        verbose_name=_("Contact Email"),
        help_text=_("Primary contact email for the account"),
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Phone Number"),
    )

    address = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Address"),
    )

    # Folder association - links to the permission system
    folder = models.OneToOneField(
        Folder,
        on_delete=models.CASCADE,
        related_name="client_account",
        verbose_name=_("Domain Folder"),
        help_text=_("The folder/domain associated with this account"),
        null=True,
        blank=True,
    )

    # Subscription Information
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
        verbose_name=_("Account Status"),
    )

    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.FREE,
        verbose_name=_("Subscription Plan"),
    )

    subscription_start = models.DateField(
        default=timezone.now,
        verbose_name=_("Subscription Start Date"),
    )

    subscription_end = models.DateField(
        verbose_name=_("Subscription End Date"),
        help_text=_("Date when the subscription expires"),
    )

    # Limits
    max_users = models.PositiveIntegerField(
        default=5,
        verbose_name=_("Maximum Users"),
        help_text=_("Maximum number of users allowed for this account"),
    )

    max_domains = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Maximum Domains"),
        help_text=_("Maximum number of sub-domains/projects allowed"),
    )

    # Additional fields
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Notes"),
        help_text=_("Internal notes about this account"),
    )

    logo = models.ImageField(
        upload_to="account_logos/",
        blank=True,
        null=True,
        verbose_name=_("Company Logo"),
    )

    # Admin user reference
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="administered_accounts",
        verbose_name=_("Account Administrator"),
        help_text=_("Primary administrator for this account"),
    )

    class Meta:
        verbose_name = _("Client Account")
        verbose_name_plural = _("Client Accounts")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs):
        # Auto-create folder if not exists
        if not self.folder:
            self.folder = Folder.objects.create(
                name=self.name,
                description=f"Domain folder for {self.name}",
                content_type=Folder.ContentType.DOMAIN,
                parent_folder=Folder.get_root_folder(),
            )
            # Create default user groups and role assignments
            Folder.create_default_ug_and_ra(self.folder)
            logger.info("Created folder for account", account=self.name, folder_id=self.folder.id)

        # Update status based on subscription_end date
        if self.subscription_end and self.subscription_end < timezone.now().date():
            if self.status == self.Status.ACTIVE:
                self.status = self.Status.EXPIRED
                logger.info("Account expired", account=self.name)

        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        """Check if the account is active and not expired."""
        if self.status != self.Status.ACTIVE and self.status != self.Status.TRIAL:
            return False
        if self.subscription_end and self.subscription_end < timezone.now().date():
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if the subscription has expired."""
        if not self.subscription_end:
            return False
        return self.subscription_end < timezone.now().date()

    @property
    def days_until_expiry(self) -> int:
        """Calculate days until subscription expires."""
        if not self.subscription_end:
            return -1
        delta = self.subscription_end - timezone.now().date()
        return delta.days

    @property
    def user_count(self) -> int:
        """Get the current number of users in this account's domain."""
        if not self.folder:
            return 0
        from iam.models import User, UserGroup
        # Count users in user groups belonging to this folder
        user_groups = UserGroup.objects.filter(folder=self.folder)
        return User.objects.filter(user_groups__in=user_groups).distinct().count()

    @property
    def is_user_limit_reached(self) -> bool:
        """Check if the user limit has been reached."""
        return self.user_count >= self.max_users

    def get_users(self):
        """Get all users belonging to this account."""
        if not self.folder:
            return []
        from iam.models import User, UserGroup
        user_groups = UserGroup.objects.filter(folder=self.folder)
        return User.objects.filter(user_groups__in=user_groups).distinct()

    def activate(self):
        """Activate the account."""
        self.status = self.Status.ACTIVE
        self.save(update_fields=["status", "updated_at"])
        logger.info("Account activated", account=self.name)

    def suspend(self):
        """Suspend the account."""
        self.status = self.Status.SUSPENDED
        self.save(update_fields=["status", "updated_at"])
        logger.info("Account suspended", account=self.name)

    def extend_subscription(self, days: int):
        """Extend the subscription by a number of days."""
        from datetime import timedelta
        if self.subscription_end:
            # If expired, start from today
            if self.subscription_end < timezone.now().date():
                self.subscription_end = timezone.now().date() + timedelta(days=days)
            else:
                self.subscription_end = self.subscription_end + timedelta(days=days)
        else:
            self.subscription_end = timezone.now().date() + timedelta(days=days)

        # Reactivate if was expired
        if self.status == self.Status.EXPIRED:
            self.status = self.Status.ACTIVE

        self.save(update_fields=["subscription_end", "status", "updated_at"])
        logger.info("Subscription extended", account=self.name, new_end_date=self.subscription_end)


# Register model with auditlog
from auditlog.registry import auditlog
auditlog.register(ClientAccount)
