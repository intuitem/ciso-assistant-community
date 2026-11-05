from rest_framework import permissions


class IsRecipient(permissions.BasePermission):
    """Access is "am I the recipient", never folder RBAC. Folder gating was measured to
    fail both ways: recipients locked out of their own notifications in domains where
    they hold no role, and role-holders able to read other people's (docs §5)."""

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.recipient_id == request.user.id
