from rest_framework import permissions


class IsRecipient(permissions.BasePermission):
    """
    Access to a notification is "am I the recipient", never folder RBAC.

    This replaces RBACPermissions for the inbox. Folder gating was measured to fail
    in both directions here: users could not read notifications addressed to them in
    domains where they hold no role, while users holding a role in a domain could read
    notifications addressed to other people. See docs/notification_center_shaping.md §5.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.recipient_id == request.user.id
