import re

from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import RequirementAssignment
from core.permissions import FeatureFlagRequired
from core.serializers import ComplianceAssessmentWriteSerializer
from core.views import (
    PERSONAL_FOLDER_SENTINEL,
    BaseModelViewSet,
    get_or_create_personal_folder,
)
from global_settings.utils import general_setting_is_enabled
from iam.models import Folder, RoleAssignment

# The whole feature is opt-in: the API is unreachable unless `custom_portals` is on,
# mirroring the UI flag gating so a flag-off build can't reach it through the API.
FEATURE_FLAG = "custom_portals"


class CustomPortalsViewSet(BaseModelViewSet):
    feature_flag = FEATURE_FLAG

    def get_permissions(self):
        return super().get_permissions() + [FeatureFlagRequired()]


class PublicPortalAPIView(APIView):
    """Base for the unauthenticated trust-center endpoints: token-gated, and only live
    while `custom_portals` is enabled."""

    permission_classes = [FeatureFlagRequired]
    authentication_classes = []
    feature_flag = FEATURE_FLAG


from .models import FrameworkSnapshot, Portal, PortalPreset, PublicDocument
from .serializers import (
    FrameworkSnapshotReadSerializer,
    PortalReadSerializer,
    PortalWriteSerializer,
)
from .snapshots import compute_snapshot


class PortalPresetViewSet(CustomPortalsViewSet):
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


def _resolve_launch_folder(request, target):
    """Resolve the domain for a launched assessment: forced by the author when the tile
    carries one, otherwise the clicker's choice (a reachable domain, or their personal
    'My space'). Returns (folder, error_response) with exactly one non-None."""
    folder_id = target.get("folder") or request.data.get("folder")
    if not folder_id:
        return None, Response(
            {"detail": "Select a domain."}, status=status.HTTP_400_BAD_REQUEST
        )
    if folder_id == PERSONAL_FOLDER_SENTINEL:
        if not general_setting_is_enabled("personal_folders"):
            return None, Response(
                {"detail": "Personal folders are not enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        folder = get_or_create_personal_folder(request.user)
        if folder is None:
            return None, Response(
                {"detail": "Personal folders are not configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return folder, None
    folder = Folder.objects.filter(pk=folder_id).first()
    if folder is None:
        return None, Response(
            {"detail": "Domain not found."}, status=status.HTTP_404_NOT_FOUND
        )
    return folder, None


def _provision_auditee_assignment(assessment, folder, user):
    """Self-service: provision the assignment ready to answer. 'draft' would show the
    respondent "Not started yet" (only a reviewer can start it), and requirements_list
    intersects with this M2M — an empty set shows nothing — so assign the whole in-scope
    assessment."""
    assignment = RequirementAssignment.objects.create(
        compliance_assessment=assessment,
        folder=folder,
        status=RequirementAssignment.Status.IN_PROGRESS,
    )
    assignment.actor.set([user.actor])
    assignment.requirement_assessments.set(
        assessment.get_requirement_assessments(include_non_assessable=True)
    )
    return assignment


class PortalViewSet(CustomPortalsViewSet):
    model = Portal
    serializers_module = "portals.serializers"
    filterset_fields = ["folder", "status", "is_public", "is_default", "enabled"]
    search_fields = ["name", "description"]

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
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="change_portal"),
            folder=portal.folder,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        portal.public_token = secrets.token_urlsafe(32)
        portal.save(update_fields=["public_token"])
        return Response({"public_token": portal.public_token})

    @staticmethod
    def _find_item(portal, item_id):
        for section in (portal.content or {}).get("sections", []):
            for item in section.get("items", []):
                if item.get("id") == item_id:
                    return item
        return None

    @action(detail=True, methods=["post"], url_path="launch-assessment")
    def launch_assessment(self, request, pk=None):
        """Instantiate the audit configured on an 'assessment' tile, then hand back the
        route the clicker should land on. The framework / domain / mode come from the
        author-stored tile config (never the request body) so a clicker can only create
        what the portal author wired up."""
        portal = self._entitled_queryset(request).filter(pk=pk).first()
        if portal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        item = self._find_item(portal, request.data.get("item"))
        if item is None or item.get("kind") != "assessment":
            return Response(
                {"detail": "Tile not found."}, status=status.HTTP_404_NOT_FOUND
            )

        target = item.get("target") or {}
        framework_id = target.get("framework")
        if not framework_id:
            return Response(
                {"detail": "Tile is misconfigured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        folder, err = _resolve_launch_folder(request, target)
        if err is not None:
            return err
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_complianceassessment"),
            folder=folder,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # Name defaults to the tile title; the clicker may override only when the
        # author opted in (user_names).
        name = item.get("title") or ""
        if target.get("user_names") and request.data.get("name"):
            name = request.data.get("name")
        data = {
            "name": name.strip() or "Assessment",
            "framework": framework_id,
            "folder": str(folder.id),
        }
        igs = target.get("implementation_groups") or []
        if igs:
            data["selected_implementation_groups"] = igs
        # Author-configured field visibility; the serializer merges it over the
        # framework defaults, so a partial map is fine.
        field_visibility = target.get("field_visibility")
        if field_visibility:
            data["field_visibility"] = field_visibility
        serializer = ComplianceAssessmentWriteSerializer(
            data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            assessment = serializer.save()
            assessment.create_requirement_assessments()
            if target.get("mode") == "auditee":
                assignment = _provision_auditee_assignment(
                    assessment, folder, request.user
                )
                return Response({"redirect": f"/auditee-assessments/{assignment.id}"})

        return Response({"redirect": f"/compliance-assessments/{assessment.id}"})

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


class PublicDocumentViewSet(CustomPortalsViewSet):
    model = PublicDocument
    serializers_module = "portals.serializers"
    filterset_fields = ["folder"]
    search_fields = ["name", "description"]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


def _apply_snapshot_sync(snapshot):
    """Pull the source audit into the snapshot's captured fields and stamp synced_at."""
    if snapshot.source_audit is None:
        return False
    payload = compute_snapshot(snapshot.source_audit, snapshot.implementation_groups)
    snapshot.framework_name = payload["framework_name"]
    snapshot.framework_ref_id = payload["framework_ref_id"]
    snapshot.framework_version = payload["framework_version"]
    snapshot.summary = payload["summary"]
    snapshot.content = payload["content"]
    snapshot.control_ids = payload["control_ids"]
    snapshot.synced_at = timezone.now()
    snapshot.save()
    return True


class FrameworkSnapshotViewSet(CustomPortalsViewSet):
    model = FrameworkSnapshot
    serializers_module = "portals.serializers"
    filterset_fields = ["folder", "source_audit"]
    search_fields = ["name", "description", "framework_name", "framework_ref_id"]

    def perform_create(self, serializer):
        # Capture the audit posture immediately so a new snapshot is never empty.
        snapshot = serializer.save()
        _apply_snapshot_sync(snapshot)

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """Compute a fresh projection without saving — feeds the pre-sync diff view."""
        from core.models import ComplianceAssessment

        audit = ComplianceAssessment.objects.filter(
            pk=request.data.get("source_audit")
        ).first()
        if audit is None:
            return Response(
                {"detail": "Audit not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="view_complianceassessment"),
            folder=audit.folder,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(
            compute_snapshot(audit, request.data.get("implementation_groups") or [])
        )

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """Manual re-pull: recompute from the (possibly changed) source audit."""
        snapshot = self.get_object()
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="change_frameworksnapshot"),
            folder=snapshot.folder,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not _apply_snapshot_sync(snapshot):
            return Response(
                {"detail": "Snapshot has no source audit to sync from."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(FrameworkSnapshotReadSerializer(snapshot).data)


# --- Trust center: unauthenticated, token-gated public surface ---------------
# These views are AllowAny on purpose and never touch internal models other than
# the explicitly-published Portal / PublicDocument rows.

PUBLIC_SAFE_TILE_KINDS = {
    "certificationDocument",
    "metric",
    "external",
    "framework",
}


def _published_public_portal_contents():
    return Portal.objects.filter(
        is_public=True, enabled=True, status=Portal.Status.PUBLISHED
    ).values_list("content", flat=True)


def _is_publicly_reachable(*, snapshot_id=None, document_token=None):
    """A token-served resource is public only while a published public portal still
    references it — so unpublishing the portal (or removing the tile) revokes access,
    even if the token itself leaked."""
    for content in _published_public_portal_contents():
        for section in (content or {}).get("sections", []):
            for item in section.get("items") or []:
                target = item.get("target") or {}
                if (
                    snapshot_id is not None
                    and item.get("kind") == "framework"
                    and str(target.get("snapshot")) == str(snapshot_id)
                ):
                    return True
                if (
                    document_token is not None
                    and item.get("kind") == "certificationDocument"
                    and target.get("token") == document_token
                ):
                    return True
    return False


def _safe_download_name(name, fallback="download"):
    """Strip characters that could break out of the Content-Disposition header."""
    cleaned = re.sub(r'[\r\n";\\]', "", name or "").strip()
    return cleaned or fallback


def _portal_snapshot_map(portal):
    """Load every FrameworkSnapshot referenced by the portal's framework tiles, keyed by id."""
    ids = set()
    for section in (portal.content or {}).get("sections", []):
        for item in section.get("items") or []:
            if item.get("kind") == "framework":
                sid = (item.get("target") or {}).get("snapshot")
                if sid:
                    ids.add(sid)
    return {str(s.id): s for s in FrameworkSnapshot.objects.filter(id__in=ids)}


def _enrich_framework_tile(item, snapshots):
    """Attach the captured snapshot summary to a framework tile, or None to drop the tile
    when its snapshot is missing."""
    snap = snapshots.get((item.get("target") or {}).get("snapshot"))
    if snap is None:
        return None
    return {
        **item,
        "snapshot": {
            "name": snap.name,
            "framework_name": snap.framework_name,
            "summary": snap.summary,
            "display_mode": snap.display_mode,
            "token": snap.public_token,
        },
    }


def _enrich_metric_tile(item, computed):
    """Fill a computed metric tile's value from the portal-scoped counts."""
    target = item.get("target") or {}
    if target.get("source") not in computed:
        return item
    return {**item, "target": {**target, "value": computed[target["source"]]}}


def _serialize_public_portal(portal):
    """Project a portal down to what's safe to expose anonymously: name, branding, and
    only the public-safe tile kinds. Framework tiles are enriched with their captured
    snapshot summary; computed metric tiles (frameworks_count / controls_count) are filled
    from the portal's own snapshots (scope = this portal)."""
    snapshots = _portal_snapshot_map(portal)
    control_union = set()
    for snap in snapshots.values():
        control_union.update(snap.control_ids or [])
    computed = {
        "frameworks_count": len(snapshots),
        "controls_count": len(control_union),
    }

    sections = []
    for section in (portal.content or {}).get("sections", []):
        items = []
        for item in section.get("items") or []:
            kind = item.get("kind")
            if kind not in PUBLIC_SAFE_TILE_KINDS:
                continue
            if kind == "framework":
                item = _enrich_framework_tile(item, snapshots)
                if item is None:
                    continue
            elif kind == "metric":
                item = _enrich_metric_tile(item, computed)
            items.append(item)
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


class PublicPortalView(PublicPortalAPIView):
    def get(self, request, token):
        portal = Portal.objects.filter(
            is_public=True,
            enabled=True,
            status=Portal.Status.PUBLISHED,
            public_token=token,
        ).first()
        if portal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_public_portal(portal))


class PublicPrimaryPortalView(PublicPortalAPIView):
    """Vanity `/trust` surface: the single portal flagged is_primary."""

    def get(self, request):
        portal = Portal.objects.filter(
            is_public=True,
            is_primary=True,
            enabled=True,
            status=Portal.Status.PUBLISHED,
        ).first()
        if portal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_public_portal(portal))


class PublicDocumentServeView(PublicPortalAPIView):
    def get(self, request, token):
        doc = PublicDocument.objects.filter(token=token).first()
        if (
            doc is None
            or not doc.file
            or not _is_publicly_reachable(document_token=token)
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            doc.file.open("rb"),
            content_type=doc.mime_type or "application/octet-stream",
            as_attachment=True,
            filename=_safe_download_name(doc.name or doc.file.name.rsplit("/", 1)[-1]),
        )


class PublicFrameworkSnapshotView(PublicPortalAPIView):
    """Drill-down for a framework tile: the captured per-requirement rows + summary.
    Serves only the frozen snapshot, never live audit data; control_ids stay private."""

    def get(self, request, token):
        snap = FrameworkSnapshot.objects.filter(public_token=token).first()
        if snap is None or not _is_publicly_reachable(snapshot_id=snap.id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "name": snap.name,
                "framework_name": snap.framework_name,
                "framework_ref_id": snap.framework_ref_id,
                "framework_version": snap.framework_version,
                "synced_at": snap.synced_at,
                "display_mode": snap.display_mode,
                "summary": snap.summary,
                "content": snap.content,
            }
        )


_EXPORT_HEADERS = ["ref_id", "name", "result", "score"]


def _flatten_snapshot(content, depth=0):
    """DFS the requirement tree into flat export rows, indenting names by depth so the
    hierarchy survives a spreadsheet. Tolerates the legacy flat shape (no children)."""
    rows = []
    for node in content or []:
        rows.append(
            {
                "ref_id": node.get("ref_id", ""),
                "name": ("    " * depth) + (node.get("name") or ""),
                "result": node.get("result") or "",
                "score": node.get("score") if node.get("score") is not None else "",
            }
        )
        rows.extend(_flatten_snapshot(node.get("children"), depth + 1))
    return rows


def _snapshot_export_xlsx(rows, slug):
    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append([h.replace("_", " ").title() for h in _EXPORT_HEADERS])
    for r in rows:
        ws.append([r.get(h, "") for h in _EXPORT_HEADERS])
    buf = BytesIO()
    wb.save(buf)
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{slug}.xlsx"'
    return resp


def _snapshot_export_csv(rows, slug):
    import csv
    from io import StringIO

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EXPORT_HEADERS, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({h: r.get(h, "") for h in _EXPORT_HEADERS})
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{slug}.csv"'
    return resp


class PublicFrameworkSnapshotExportView(PublicPortalAPIView):
    def get(self, request, token):
        snap = FrameworkSnapshot.objects.filter(public_token=token).first()
        if snap is None or not _is_publicly_reachable(snapshot_id=snap.id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        rows = _flatten_snapshot(snap.content)
        slug = _safe_download_name(
            (snap.framework_ref_id or snap.name or "framework").replace(" ", "_"),
            fallback="framework",
        )
        if request.query_params.get("format") == "xlsx":
            return _snapshot_export_xlsx(rows, slug)
        return _snapshot_export_csv(rows, slug)
