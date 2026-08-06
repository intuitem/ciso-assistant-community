"""Provisioning and update helpers for OAuth2 service accounts (see ServiceAccount model)."""

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import transaction

from allauth.idp.oidc.adapter import get_adapter as get_oidc_adapter
from allauth.idp.oidc.models import Client

from iam.cache_builders import invalidate_roles_cache
from iam.models import (
    ALLOWED_PERMISSION_APPS,
    IGNORED_PERMISSION_MODELS,
    Folder,
    Role,
    RoleAssignment,
    ServiceAccount,
    User,
)

SERVICE_ACCOUNT_EMAIL_DOMAIN = "service-accounts.local"

# Marks "field omitted" so it's distinguishable from "field sent as null".
UNSET = object()


def get_selectable_permissions():
    """Permissions a service account may be granted — same catalog RBAC uses."""
    return (
        Permission.objects.filter(content_type__app_label__in=ALLOWED_PERMISSION_APPS)
        .exclude(content_type__model__in=IGNORED_PERMISSION_MODELS)
        .select_related("content_type")
        .order_by("content_type__app_label", "content_type__model", "codename")
    )


def _validated_permissions(permission_ids):
    permissions = list(get_selectable_permissions().filter(id__in=permission_ids))
    if len(permissions) != len(set(permission_ids)):
        raise ValidationError("Invalid permission selection.")
    return permissions


def get_selectable_builtin_role(role_id) -> Role:
    role = Role.objects.filter(id=role_id, builtin=True).first()
    if role is None:
        raise ValidationError("Invalid role selection.")
    return role


def provision_service_account(
    *,
    name: str,
    description: str | None,
    permission_ids: list[int] | None,
    role_id=None,
    folder_ids: list,
    is_recursive: bool,
    created_by: User | None,
    expiry_date=None,
) -> tuple[ServiceAccount, str]:
    """Returns (sa, plaintext_secret); exactly one of permission_ids/role_id is expected."""
    role = get_selectable_builtin_role(role_id) if role_id is not None else None
    permissions = _validated_permissions(permission_ids) if role is None else None
    folders = list(Folder.objects.filter(id__in=folder_ids))
    if len(folders) != len(set(folder_ids)) or not folders:
        raise ValidationError("Invalid perimeter folder selection.")

    adapter = get_oidc_adapter()
    client_id = adapter.generate_client_id()
    plain_secret = ServiceAccount.generate_secret()
    root_folder = Folder.get_root_folder()

    with transaction.atomic():
        user = User.objects._create_user(
            email=f"sa-{client_id}@{SERVICE_ACCOUNT_EMAIL_DOMAIN}",
            password=None,
            mailing=False,
            initial_group=None,
            first_name=name,
        )
        client = Client(
            id=client_id,
            name=name,
            type=Client.Type.CONFIDENTIAL,
            grant_types=Client.GrantType.CLIENT_CREDENTIALS,
            scopes="",
            response_types="",
            owner=user,
        )
        client.set_secret(plain_secret)
        client.save()
        if role is None:
            role = Role.objects.create(name=f"SA-{client_id}", folder=root_folder)
            role.permissions.set(permissions)
            invalidate_roles_cache()
        role_assignment = RoleAssignment.objects.create(
            user=user,
            role=role,
            is_recursive=is_recursive,
            folder=root_folder,
        )
        role_assignment.perimeter_folders.set(folders)
        service_account = ServiceAccount.objects.create(
            name=name,
            description=description,
            client=client,
            user=user,
            role=role,
            created_by=created_by,
            expiry_date=expiry_date,
            secret_preview=ServiceAccount.secret_preview_for(plain_secret),
        )
    return service_account, plain_secret


def _switch_role(service_account: ServiceAccount, new_role: Role) -> None:
    old_role = service_account.role
    role_assignment = RoleAssignment.objects.filter(user=service_account.user).first()
    service_account.role = new_role
    service_account.save(update_fields=["role", "updated_at"])
    if role_assignment is not None:
        role_assignment.role = new_role
        role_assignment.save()
    if not old_role.builtin:
        old_role.delete()
    invalidate_roles_cache()


def _detach_to_dedicated_role(
    service_account: ServiceAccount, permission_ids: list[int]
) -> None:
    new_role = Role.objects.create(
        name=f"SA-{service_account.client_id}", folder=Folder.get_root_folder()
    )
    new_role.permissions.set(_validated_permissions(permission_ids))
    _switch_role(service_account, new_role)


def update_service_account(
    service_account: ServiceAccount,
    *,
    name: str | None = None,
    description=UNSET,
    permission_ids: list[int] | None = None,
    role_id=None,
    folder_ids: list | None = None,
    is_recursive: bool | None = None,
    expiry_date=UNSET,
) -> ServiceAccount:
    with transaction.atomic():
        if name is not None:
            service_account.name = name
            service_account.client.name = name
            service_account.client.save(update_fields=["name"])
        if description is not UNSET:
            service_account.description = description
        if expiry_date is not UNSET:
            service_account.expiry_date = expiry_date
        service_account.save()
        if role_id is not None:
            new_role = get_selectable_builtin_role(role_id)
            if new_role.id != service_account.role_id:
                _switch_role(service_account, new_role)
        elif permission_ids is not None:
            if service_account.role.builtin:
                current_ids = set(
                    service_account.role.permissions.values_list("id", flat=True)
                )
                if set(permission_ids) != current_ids:
                    _detach_to_dedicated_role(service_account, permission_ids)
            else:
                service_account.role.permissions.set(
                    _validated_permissions(permission_ids)
                )
                invalidate_roles_cache()
        role_assignment = service_account.role_assignment
        if role_assignment is not None:
            if folder_ids is not None:
                folders = list(Folder.objects.filter(id__in=folder_ids))
                if len(folders) != len(set(folder_ids)) or not folders:
                    raise ValidationError("Invalid perimeter folder selection.")
                role_assignment.perimeter_folders.set(folders)
            if is_recursive is not None:
                role_assignment.is_recursive = is_recursive
            role_assignment.save()  # invalidates the assignments cache
    return service_account
