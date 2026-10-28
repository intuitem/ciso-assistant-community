"""Published-only read access: `view_published_documentcontainer` lets a role
read the revision in force of the documents in its folders, and nothing else
(no drafts, pending revisions, edit history or diffs)."""

from django.contrib.auth.models import Permission
from django.db.models import F, Q
from rest_framework.permissions import SAFE_METHODS

from core.permissions import RBACPermissions
from iam.models import RoleAssignment

from .models import (
    DocumentAttachment,
    DocumentContainer,
    DocumentRevision,
    ManagedDocument,
)

PUBLISHED_ONLY_CODENAME = "view_published_documentcontainer"

# Detail actions a published-only reader may call on an object in scope.
PUBLISHED_READ_ACTIONS = {"retrieve", "file", "export_pdf", "references"}

_PUBLISHED = DocumentRevision.Status.PUBLISHED
PUBLISHED_FILTERS = {
    DocumentContainer: Q(documents__revisions__status=_PUBLISHED),
    ManagedDocument: Q(revisions__status=_PUBLISHED),
    DocumentRevision: Q(status=_PUBLISHED),
    # One Q, so both conditions hit the same revision row: images uploaded after the
    # publication belong to a later draft.
    DocumentAttachment: Q(
        document__revisions__status=_PUBLISHED,
        created_at__lte=F("document__revisions__published_at"),
    ),
}


def published_only_ids(user, model):
    """IDs of `model` objects readable through the published-only permission."""
    permission = Permission.objects.get(codename=PUBLISHED_ONLY_CODENAME)
    folder_ids = RoleAssignment.get_allowed_folder_ids(user, permission)
    return model.objects.filter(
        PUBLISHED_FILTERS[model], folder__in=folder_ids
    ).values_list("id", flat=True)


def readable_ids(user, model) -> set:
    """Full view plus published-only view."""
    return set(RoleAssignment.get_viewable_object_ids(user, model)) | set(
        published_only_ids(user, model)
    )


def full_view_ids(request, model):
    """IDs the requester fully sees, or None when they see every object; computed
    once per request."""
    cache = request.__dict__.setdefault("_doc_full_view_ids", {})
    if model not in cache:
        view = (getattr(request, "parser_context", None) or {}).get("view")
        if hasattr(view, "_user_can_view_all") and view._user_can_view_all(model):
            cache[model] = None
        else:
            cache[model] = set(
                RoleAssignment.get_viewable_object_ids(request.user, model)
            )
    return cache[model]


def has_full_view(request, model, obj_id) -> bool:
    """Whether the requester sees `obj_id` beyond its revision in force."""
    ids = full_view_ids(request, model)
    return ids is None or obj_id in ids


class PublishedReadMixin:
    """Widens the read queryset of a document viewset to the published-only scope."""

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.method not in SAFE_METHODS or self._user_can_view_all(
            self.model
        ):
            return qs
        return qs | self.model.objects.filter(
            id__in=published_only_ids(self.request.user, self.model)
        )

    def _get_accessible_ids_map(self, related_models):
        # Otherwise list/retrieve mask e.g. `current_revision` as an unreadable relation.
        allowed = super()._get_accessible_ids_map(related_models)
        for model, ids in allowed.items():
            if ids is not None and model in PUBLISHED_FILTERS:
                ids |= {str(i) for i in published_only_ids(self.request.user, model)}
        return allowed


class DocumentRBACPermissions(RBACPermissions):
    def has_object_permission(self, request, view, obj):
        if super().has_object_permission(request, view, obj):
            return True
        return (
            request.method in SAFE_METHODS
            and getattr(view, "action", None) in PUBLISHED_READ_ACTIONS
            and published_only_ids(request.user, type(obj)).filter(id=obj.id).exists()
        )
