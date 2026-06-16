from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework.filters import SearchFilter

from core.constants import CURRENCY_CHOICES
from core.views import BaseModelViewSet
from custom_fields.filters import CustomFieldFilterBackend, CustomFieldSearchFilter
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
from pmbok.serializers import ResponsibilityMatrixActivityReadSerializer

LONG_CACHE_TTL = 60  # mn


class GenericCollectionViewSet(BaseModelViewSet):
    model = GenericCollection
    serializers_module = "pmbok.serializers"
    filterset_fields = [
        "folder",
        "compliance_assessments",
        "risk_assessments",
        "crq_studies",
        "ebios_studies",
        "entity_assessments",
        "findings_assessments",
        "documents",
        "security_exceptions",
        "policies",
        "filtering_labels",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["created_at"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Generic Collection status choices")
    def status(self, request):
        return Response({})


class AccreditationViewSet(BaseModelViewSet):
    model = Accreditation
    serializers_module = "pmbok.serializers"
    filterset_fields = [
        "folder",
        "status",
        "category",
        "author",
        "authority",
        "linked_collection",
        "checklist",
        "filtering_labels",
    ]
    search_fields = ["name", "description", "ref_id", "authority", "authority_name"]
    ordering = ["created_at"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Accreditation status choices")
    def status(self, request):
        return Response(dict(Accreditation.STATUS_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Accreditation category choices")
    def category(self, request):
        return Response(dict(Accreditation.CATEGORY_CHOICES))


class ProjectViewSet(BaseModelViewSet):
    model = Project
    serializers_module = "pmbok.serializers"
    filter_backends = [
        CustomFieldSearchFilter if backend is SearchFilter else backend
        for backend in BaseModelViewSet.filter_backends
    ] + [CustomFieldFilterBackend]
    filterset_fields = [
        "folder",
        "kind",
        "status",
        "priority",
        "health",
        "owner",
        "sponsor",
        "parent_project",
        "linked_collection",
        "filtering_labels",
    ]
    search_fields = ["name", "description", "ref_id", "purpose", "objectives"]
    ordering = ["created_at"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Project priority choices")
    def priority(self, request):
        return Response(
            [{"value": v, "label": str(label)} for v, label in Project.PRIORITY]
        )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Project kind choices")
    def kind(self, request):
        return Response(
            [{"value": v, "label": str(label)} for v, label in Project.Kind.choices]
        )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get supported currency choices")
    def currencies(self, request):
        return Response(
            [
                {"value": code, "label": f"{code} – {name}"}
                for code, name in CURRENCY_CHOICES
            ]
        )


class ResponsibilityRoleViewSet(BaseModelViewSet):
    # Read-only: roles are seeded via ResponsibilityRole.create_default_roles().
    model = ResponsibilityRole
    serializers_module = "pmbok.serializers"
    filterset_fields = ["folder", "taxonomy", "builtin", "is_visible"]
    search_fields = ["code", "name", "description"]
    ordering = ["taxonomy", "order", "code"]
    http_method_names = ["get", "head", "options"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Responsibility Role taxonomy choices")
    def taxonomy(self, request):
        return Response(dict(ResponsibilityRole.Taxonomy.choices))


class ResponsibilityMatrixViewSet(BaseModelViewSet):
    model = ResponsibilityMatrix
    serializers_module = "pmbok.serializers"
    filterset_fields = ["folder", "preset", "roles", "filtering_labels"]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["created_at"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Responsibility Matrix preset choices")
    def preset(self, request):
        return Response(dict(ResponsibilityMatrix.Preset.choices))

    @action(detail=True, methods=["post"], url_path="cycle-cell")
    def cycle_cell(self, request, pk=None):
        # Body: {activity, actor, direction: "forward"|"backward"}.
        # Returns: {role: {id, code, name, color} | null, assignment_id: uuid | null}.
        # Cycles empty -> roles[0] -> ... -> roles[-1] -> empty.
        matrix = self.get_object()
        activity_id = request.data.get("activity")
        actor_id = request.data.get("actor")
        direction = request.data.get("direction", "forward")
        if not activity_id or not actor_id:
            return Response(
                {"detail": "activity and actor are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            activity = matrix.activities.get(id=activity_id)
        except ResponsibilityMatrixActivity.DoesNotExist:
            return Response(
                {"detail": "activity does not belong to this matrix"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Off-matrix actor assignments would persist in the DB even if the UI hides them.
        if not matrix.matrix_actors.filter(actor_id=actor_id).exists():
            return Response(
                {"detail": "actor is not a member of this matrix"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        roles = list(matrix.roles.all().order_by("order", "code"))
        if not roles:
            return Response(
                {"detail": "this matrix has no roles attached"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            existing = ResponsibilityAssignment.objects.filter(
                activity=activity, actor_id=actor_id
            ).first()
            if existing is None:
                next_role = roles[0] if direction == "forward" else roles[-1]
            else:
                current_idx = next(
                    (i for i, r in enumerate(roles) if r.id == existing.role_id), -1
                )
                if direction == "forward":
                    next_idx = current_idx + 1
                    next_role = roles[next_idx] if next_idx < len(roles) else None
                else:
                    next_idx = current_idx - 1
                    next_role = roles[next_idx] if next_idx >= 0 else None

            if next_role is None:
                if existing:
                    existing.delete()
                payload = {"role": None, "assignment_id": None}
            else:
                if existing:
                    existing.role = next_role
                    existing.save(update_fields=["role", "updated_at"])
                    assignment = existing
                else:
                    # Concurrent cycle-cells race here; loser hits the unique constraint, then patches the winner's row.
                    try:
                        assignment = ResponsibilityAssignment.objects.create(
                            activity=activity, actor_id=actor_id, role=next_role
                        )
                    except IntegrityError:
                        assignment = ResponsibilityAssignment.objects.get(
                            activity=activity, actor_id=actor_id
                        )
                        assignment.role = next_role
                        assignment.save(update_fields=["role", "updated_at"])
                payload = {
                    "role": {
                        "id": str(next_role.id),
                        "code": next_role.code,
                        "name": next_role.name,
                        "color": next_role.color,
                    },
                    "assignment_id": str(assignment.id),
                }

        return Response(payload)

    @action(detail=True, methods=["post"], url_path="reorder-activities")
    def reorder_activities(self, request, pk=None):
        # Body: {ids: [activity_uuid, ...]} in the desired display order.
        matrix = self.get_object()
        ids = request.data.get("ids") or []
        with transaction.atomic():
            for idx, aid in enumerate(ids):
                ResponsibilityMatrixActivity.objects.filter(
                    id=aid, matrix=matrix
                ).update(order=idx)
        return Response({"updated": len(ids)})

    @action(detail=True, methods=["post"], url_path="reorder-actors")
    def reorder_actors(self, request, pk=None):
        # Body: {ids: [matrix_actor_uuid, ...]} in the desired column order.
        matrix = self.get_object()
        ids = request.data.get("ids") or []
        with transaction.atomic():
            for idx, mid in enumerate(ids):
                ResponsibilityMatrixActor.objects.filter(id=mid, matrix=matrix).update(
                    order=idx
                )
        return Response({"updated": len(ids)})


class ResponsibilityMatrixActorViewSet(BaseModelViewSet):
    model = ResponsibilityMatrixActor
    serializers_module = "pmbok.serializers"
    filterset_fields = ["matrix", "actor"]
    ordering = ["order", "id"]

    def perform_destroy(self, instance):
        # Remove the actor's assignments in this matrix as part of the same transaction.
        with transaction.atomic():
            ResponsibilityAssignment.objects.filter(
                activity__matrix=instance.matrix, actor=instance.actor
            ).delete()
            instance.delete()


class ResponsibilityMatrixActivityViewSet(BaseModelViewSet):
    model = ResponsibilityMatrixActivity
    serializers_module = "pmbok.serializers"
    filterset_fields = ["matrix"]
    search_fields = ["name", "description"]
    ordering = ["matrix", "order"]

    def update(self, request, *args, **kwargs):
        # Return the Read shape so the frontend can rehydrate M2M links without
        # re-fetching lookup pools (~7 fetches per matrix detail mount).
        response = super().update(request, *args, **kwargs)
        instance = self.get_object()
        response.data = ResponsibilityMatrixActivityReadSerializer(instance).data
        return response


class ResponsibilityAssignmentViewSet(BaseModelViewSet):
    # Read-only: writes route through ResponsibilityMatrixViewSet.cycle_cell, which
    # validates actor-in-matrix and role-in-taxonomy. Direct writes would bypass both.
    model = ResponsibilityAssignment
    serializers_module = "pmbok.serializers"
    filterset_fields = ["activity", "actor", "role", "activity__matrix"]
    ordering = ["activity", "role", "actor"]
    http_method_names = ["get", "head", "options"]
