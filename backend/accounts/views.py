"""
Views for ClientAccount management.
Only superusers can access these views.
"""

from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

import structlog

from .models import ClientAccount
from .serializers import (
    ClientAccountSerializer,
    ClientAccountCreateSerializer,
    ClientAccountListSerializer,
    ClientAccountStatsSerializer,
    ExtendSubscriptionSerializer,
    ChangeStatusSerializer,
)

logger = structlog.get_logger(__name__)


class IsSuperUser(permissions.BasePermission):
    """
    Custom permission to only allow superusers to access.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class ClientAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing client accounts.
    Only superusers can access this endpoint.
    """

    queryset = ClientAccount.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "create":
            return ClientAccountCreateSerializer
        elif self.action == "list":
            return ClientAccountListSerializer
        return ClientAccountSerializer

    def get_queryset(self):
        """Filter and annotate queryset."""
        queryset = ClientAccount.objects.all()

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by plan
        plan_filter = self.request.query_params.get("plan")
        if plan_filter:
            queryset = queryset.filter(plan=plan_filter)

        # Filter by expiring soon (next 30 days)
        expiring_soon = self.request.query_params.get("expiring_soon")
        if expiring_soon and expiring_soon.lower() == "true":
            today = timezone.now().date()
            thirty_days = today + timedelta(days=30)
            queryset = queryset.filter(
                subscription_end__gte=today,
                subscription_end__lte=thirty_days
            )

        # Filter by expired
        expired = self.request.query_params.get("expired")
        if expired and expired.lower() == "true":
            today = timezone.now().date()
            queryset = queryset.filter(subscription_end__lt=today)

        # Search by name or email
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(email__icontains=search)
            )

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        """Create a new account."""
        account = serializer.save()
        logger.info(
            "Client account created",
            account_id=str(account.id),
            account_name=account.name,
            created_by=self.request.user.email,
        )

    def perform_update(self, serializer):
        """Update an account."""
        account = serializer.save()
        logger.info(
            "Client account updated",
            account_id=str(account.id),
            account_name=account.name,
            updated_by=self.request.user.email,
        )

    def perform_destroy(self, instance):
        """Delete an account and its associated folder."""
        account_name = instance.name
        account_id = str(instance.id)

        # Delete the folder (cascade will handle user groups, etc.)
        if instance.folder:
            folder_id = str(instance.folder.id)
            instance.folder.delete()
            logger.info(
                "Folder deleted for account",
                folder_id=folder_id,
                account_name=account_name,
            )

        instance.delete()
        logger.info(
            "Client account deleted",
            account_id=account_id,
            account_name=account_name,
            deleted_by=self.request.user.email,
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get statistics about all client accounts.
        """
        today = timezone.now().date()
        thirty_days = today + timedelta(days=30)

        # Count by status
        total = ClientAccount.objects.count()
        active = ClientAccount.objects.filter(status=ClientAccount.Status.ACTIVE).count()
        expired = ClientAccount.objects.filter(status=ClientAccount.Status.EXPIRED).count()
        suspended = ClientAccount.objects.filter(status=ClientAccount.Status.SUSPENDED).count()
        trial = ClientAccount.objects.filter(status=ClientAccount.Status.TRIAL).count()

        # Expiring soon (active accounts expiring in next 30 days)
        expiring_soon = ClientAccount.objects.filter(
            status__in=[ClientAccount.Status.ACTIVE, ClientAccount.Status.TRIAL],
            subscription_end__gte=today,
            subscription_end__lte=thirty_days
        ).count()

        # Count total users across all accounts
        total_users = sum(account.user_count for account in ClientAccount.objects.all())

        # Plan distribution
        plan_dist = {}
        for plan_choice in ClientAccount.Plan.choices:
            plan_code = plan_choice[0]
            plan_dist[plan_code] = ClientAccount.objects.filter(plan=plan_code).count()

        stats_data = {
            "total_accounts": total,
            "active_accounts": active,
            "expired_accounts": expired,
            "suspended_accounts": suspended,
            "trial_accounts": trial,
            "total_users": total_users,
            "expiring_soon": expiring_soon,
            "plan_distribution": plan_dist,
        }

        serializer = ClientAccountStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def extend_subscription(self, request, id=None):
        """
        Extend the subscription for an account by a number of days.
        """
        account = self.get_object()
        serializer = ExtendSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        days = serializer.validated_data["days"]
        old_end_date = account.subscription_end
        account.extend_subscription(days)

        logger.info(
            "Subscription extended",
            account_id=str(account.id),
            account_name=account.name,
            old_end_date=str(old_end_date),
            new_end_date=str(account.subscription_end),
            extended_by=request.user.email,
        )

        return Response({
            "message": f"Subscription extended by {days} days",
            "new_subscription_end": account.subscription_end,
            "status": account.status,
        })

    @action(detail=True, methods=["post"])
    def change_status(self, request, id=None):
        """
        Change the status of an account (activate, suspend, etc.).
        """
        account = self.get_object()
        serializer = ChangeStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = account.status
        new_status = serializer.validated_data["status"]
        account.status = new_status
        account.save(update_fields=["status", "updated_at"])

        logger.info(
            "Account status changed",
            account_id=str(account.id),
            account_name=account.name,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user.email,
        )

        return Response({
            "message": f"Account status changed from {old_status} to {new_status}",
            "status": account.status,
        })

    @action(detail=True, methods=["get"])
    def users(self, request, id=None):
        """
        Get list of users belonging to this account.
        """
        account = self.get_object()
        users = account.get_users()

        user_data = [
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "date_joined": user.date_joined,
                "last_login": user.last_login,
            }
            for user in users
        ]

        return Response({
            "count": len(user_data),
            "max_users": account.max_users,
            "users": user_data,
        })

    @action(detail=True, methods=["post"])
    def activate(self, request, id=None):
        """Quick action to activate an account."""
        account = self.get_object()
        account.activate()
        return Response({"message": "Account activated", "status": account.status})

    @action(detail=True, methods=["post"])
    def suspend(self, request, id=None):
        """Quick action to suspend an account."""
        account = self.get_object()
        account.suspend()
        return Response({"message": "Account suspended", "status": account.status})
