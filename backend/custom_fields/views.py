"""CRUD API for FieldDefinition + FieldChoice. Install-global; not folder-scoped."""

from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS, BasePermission

from custom_fields.models import (
    FieldChoice,
    FieldDefinition,
    FieldValue,
)
from custom_fields.serializers import (
    FieldChoiceReadSerializer,
    FieldChoiceWriteSerializer,
    FieldDefinitionReadSerializer,
    FieldDefinitionWriteSerializer,
)


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"


class CanManageFieldDefinitions(BasePermission):
    """Reads: any authenticated user. Writes: custom_fields.change_fielddefinition."""

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.has_perm("custom_fields.change_fielddefinition")


class FieldDefinitionViewSet(viewsets.ModelViewSet):
    queryset = (
        FieldDefinition.objects.all()
        .select_related("target_content_type")
        .prefetch_related("choices")
    )
    permission_classes = [IsAuthenticated, CanManageFieldDefinitions]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "target_content_type",
        "target_content_type__model",
        "type",
        "is_visible",
        "filterable",
        "builtin",
    ]
    search_fields = ["name", "label", "description"]
    ordering_fields = ["target_content_type__model", "order", "name", "created_at"]
    # Order by model slug (stable across installs, unlike ContentType PK).
    ordering = ["target_content_type__model", "order", "name"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return FieldDefinitionReadSerializer
        return FieldDefinitionWriteSerializer

    def perform_destroy(self, instance: FieldDefinition) -> None:
        if instance.builtin:
            raise PermissionDenied("Builtin field definitions cannot be deleted.")
        try:
            super().perform_destroy(instance)
        except ProtectedError as exc:
            count = FieldValue.objects.filter(definition=instance).count()
            raise Conflict(
                f"Cannot delete: {count} value(s) reference this field. "
                "Clear values first."
            ) from exc


class FieldChoiceViewSet(viewsets.ModelViewSet):
    queryset = FieldChoice.objects.all().select_related("definition")
    permission_classes = [IsAuthenticated, CanManageFieldDefinitions]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["definition", "is_visible"]
    search_fields = ["value", "label"]
    ordering_fields = ["definition", "order", "value"]
    ordering = ["definition", "order", "value"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return FieldChoiceReadSerializer
        return FieldChoiceWriteSerializer

    def perform_destroy(self, instance: FieldChoice) -> None:
        try:
            super().perform_destroy(instance)
        except ProtectedError as exc:
            count = FieldValue.objects.filter(value_choice=instance).count()
            raise Conflict(
                f"Cannot delete: {count} value(s) reference this choice. "
                "Reassign or clear them first."
            ) from exc
