from django.contrib.auth.models import Permission
from django.db.models import Q
from django.http import FileResponse
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.views import BaseModelViewSet
from iam.models import RoleAssignment

from .models import Portal, PortalPreset, PublicDocument
from .serializers import PortalReadSerializer, PortalWriteSerializer


class PortalPresetViewSet(BaseModelViewSet):
    model = PortalPreset
    serializers_module = "portals.serializers"
    filterset_fields = ["folder", "provider"]
    search_fields = ["name", "description", "ref_id", "urn"]

    def _reject_if_library_backed(self):
        if self.get_object().urn is not None:
            return Response(
                {"detail": "Library-backed presets are read-only. Duplicate first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def update(self, request, *args, **kwargs):
        return self._reject_if_library_backed() or super().update(
            request, *args, **kwargs
        )

    def partial_update(self, request, *args, **kwargs):
        return self._reject_if_library_backed() or super().partial_update(
            request, *args, **kwargs
        )

    def destroy(self, request, *args, **kwargs):
        return self._reject_if_library_backed() or super().destroy(
            request, *args, **kwargs
        )


class PortalViewSet(BaseModelViewSet):
    model = Portal
    serializers_module = "portals.serializers"
    filterset_fields = ["folder", "status", "is_public", "is_default", "enabled"]
    search_fields = ["name", "description", "slug"]

    def _entitled_queryset(self, request):
        """Portals the current user may see: enabled, and either targeted at one of
        the user's groups, untargeted (visible to all), public, or the default.
        Audience entitlement is the access control here, so this intentionally
        bypasses IAM folder scoping (like the dashboard endpoints)."""
        groups = request.user.user_groups.all()
        return (
            Portal.objects.filter(enabled=True, status=Portal.Status.PUBLISHED)
            .filter(
                Q(audience_groups__in=groups)
                | Q(audience_groups__isnull=True)
                | Q(is_public=True)
                | Q(is_default=True)
            )
            .distinct()
            .order_by("order", "name")
        )

    @action(detail=False, methods=["get"])
    def mine(self, request):
        portals = self._entitled_queryset(request)
        return Response(
            [
                {"id": str(p.id), "name": p.name, "is_default": p.is_default}
                for p in portals
            ]
        )

    @action(detail=True, methods=["get"])
    def content(self, request, pk=None):
        portal = self._entitled_queryset(request).filter(pk=pk).first()
        if portal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": str(portal.id),
                "name": portal.name,
                "branding": portal.branding,
                "sections": (portal.content or {}).get("sections", []),
            }
        )

    @action(detail=False, methods=["post"], url_path="from-preset")
    def from_preset(self, request):
        """Clone a preset's design into a new editable portal (cord cut, no sync)."""
        preset = PortalPreset.objects.filter(pk=request.data.get("preset")).first()
        if preset is None:
            return Response(
                {"detail": "Preset not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="view_portalpreset"),
            folder=preset.folder,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        data = {
            "name": request.data.get("name") or preset.name,
            "folder": str(preset.folder_id),
            "content": preset.content,
            "source_ref": preset.urn or preset.ref_id or str(preset.id),
        }
        serializer = PortalWriteSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        portal = serializer.save()
        return Response(
            PortalReadSerializer(portal).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="regenerate-public-token")
    def regenerate_public_token(self, request, pk=None):
        """Mint a fresh public token, instantly revoking any link built on the old one."""
        import secrets

        portal = self.get_object()
        portal.public_token = secrets.token_urlsafe(32)
        portal.save(update_fields=["public_token"])
        return Response({"public_token": portal.public_token})

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        portal = self.get_object()
        data = {
            "name": f"{portal.name} (copy)",
            "folder": str(portal.folder_id),
            "content": portal.content,
            "branding": portal.branding,
            "source_ref": portal.source_ref,
        }
        serializer = PortalWriteSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        clone = serializer.save()
        return Response(
            PortalReadSerializer(clone).data, status=status.HTTP_201_CREATED
        )


class PublicDocumentViewSet(BaseModelViewSet):
    model = PublicDocument
    serializers_module = "portals.serializers"
    filterset_fields = ["folder"]
    search_fields = ["name", "description"]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


# --- Trust center: unauthenticated, token-gated public surface ---------------
# These views are AllowAny on purpose and never touch internal models other than
# the explicitly-published Portal / PublicDocument rows.

PUBLIC_SAFE_TILE_KINDS = {"badge", "metric", "document", "external", "status"}


def _serialize_public_portal(portal):
    """Project a portal down to what's safe to expose anonymously: name, branding, and
    only the public-safe tile kinds."""
    sections = []
    for section in (portal.content or {}).get("sections", []):
        items = [
            item
            for item in (section.get("items") or [])
            if item.get("kind") in PUBLIC_SAFE_TILE_KINDS
        ]
        sections.append(
            {
                "title": section.get("title", ""),
                "description": section.get("description", ""),
                "items": items,
            }
        )
    return {
        "name": portal.name,
        "branding": portal.branding,
        "sections": sections,
    }


class PublicPortalView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, token):
        portal = Portal.objects.filter(is_public=True, public_token=token).first()
        if portal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_public_portal(portal))


class PublicPrimaryPortalView(APIView):
    """Vanity `/trust` surface: the single portal flagged is_primary."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        portal = Portal.objects.filter(is_public=True, is_primary=True).first()
        if portal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_public_portal(portal))


class PublicDocumentServeView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, token):
        doc = PublicDocument.objects.filter(token=token).first()
        if doc is None or not doc.file:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            doc.file.open("rb"),
            content_type=doc.mime_type or "application/octet-stream",
            as_attachment=True,
            filename=doc.name or doc.file.name.rsplit("/", 1)[-1],
        )
