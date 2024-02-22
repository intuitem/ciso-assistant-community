from rest_framework import permissions
from rest_framework.request import Request
from django.contrib.auth import get_user_model
from .utils import RoleCodename

from iam.models import RoleAssignment, Folder, Permission, Role

User = get_user_model()


class RBACPermissions(permissions.DjangoObjectPermissions):
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
        if not request.user or (
            not request.user.is_authenticated and self.authenticated_users_only
        ):
            return False
        if not request.method:
            return False
        # Read access is filtered at the queryset level
        if request.method in permissions.SAFE_METHODS:
            return True
        # Workaround to ensure DjangoModelPermissions are not applied
        # to the root view when using DefaultRouter.
        if getattr(view, "_ignore_model_permissions", False):
            return True

        queryset = self._queryset(view)
        perms = self.get_required_permissions(request.method, queryset.model)
        if not perms:
            return False
        _codename = perms[0].split(".")[1]
        return RoleAssignment.has_permission(user=request.user, codename=_codename)

    def has_object_permission(self, request: Request, view, obj):
        if not request.method:
            return False
        queryset = self._queryset(view)
        perms = self.get_required_permissions(request.method, queryset.model)
        if not perms:
            return False
        _codename = perms[0].split(".")[1]
        if queryset.model == User:
            return RoleAssignment.has_permission(user=request.user, codename=_codename)
        return RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename=_codename),
            folder=Folder.get_folder(obj),
        )


class IsAdministrator(permissions.BasePermission):
    def has_permission(self, request, view):
        return RoleAssignment.has_role(
            user=request.user, role=Role.objects.get(name=RoleCodename.ADMINISTRATOR)
        )
