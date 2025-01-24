from rest_framework import permissions
from rest_framework.request import Request
from django.contrib.auth import get_user_model
from .utils import RoleCodename

from iam.models import RoleAssignment, Folder, Permission, Role

User = get_user_model()


class RBACPermissions(permissions.DjangoObjectPermissions):
    """this is the DRF custom permission model enforcing our RBAC logic"""

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_permission(self, request: Request, view) -> bool:
        """we don't need this check, as we have queryset for list and serializers for create
        see https://www.django-rest-framework.org/api-guide/permissions/"""
        return True

    def has_object_permission(self, request: Request, view, obj):
        if not request.method:
            return False
        perms = self.get_required_permissions(request.method, type(obj))
        if not perms:
            return False
        _codename = perms[0].split(".")[1]
        if request.method in ["GET", "OPTIONS", "HEAD"] and getattr(
            obj, "is_published", False
        ):
            return True

        # Check for view action permission overrides
        current_action = getattr(view, "action", None)

        if current_action:
            permission_overrides = getattr(view, "permission_overrides", {})
            _codename = permission_overrides.get(current_action, _codename)

        perm = Permission.objects.get(codename=_codename)

        return RoleAssignment.is_access_allowed(
            user=request.user,
            perm=perm,
            folder=Folder.get_folder(obj),
        )


class IsAdministrator(permissions.BasePermission):
    def has_permission(self, request, view):
        return RoleAssignment.has_role(
            user=request.user, role=Role.objects.get(name=RoleCodename.ADMINISTRATOR)
        )
