"""Provisioning and update helpers for OAuth2 service accounts.

A service account bundles an allauth OIDC Client (client_credentials only),
a dedicated internal User, a dedicated Role holding the explicitly selected
permissions, and a RoleAssignment scoping that role to explicitly chosen
perimeter folders.
"""

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


def provision_service_account(
    *,
    name: str,
    description: str | None,
    permission_ids: list[int],
    folder_ids: list,
    is_recursive: bool,
    created_by: User | None,
) -> tuple[ServiceAccount, str]:
    """Create the full service account bundle. Returns (sa, plaintext_secret);
    the secret is hashed at rest and can never be retrieved again."""
    permissions = _validated_permissions(permission_ids)
    folders = list(Folder.objects.filter(id__in=folder_ids))
    if len(folders) != len(set(folder_ids)) or not folders:
        raise ValidationError("Invalid perimeter folder selection.")

    adapter = get_oidc_adapter()
    client_id = adapter.generate_client_id()
    plain_secret = adapter.generate_client_secret()
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
        )
    return service_account, plain_secret


def update_service_account(
    service_account: ServiceAccount,
    *,
    name: str | None = None,
    description: str | None = None,
    permission_ids: list[int] | None = None,
    folder_ids: list | None = None,
    is_recursive: bool | None = None,
) -> ServiceAccount:
    with transaction.atomic():
        if name is not None:
            service_account.name = name
            service_account.client.name = name
            service_account.client.save(update_fields=["name"])
        if description is not None:
            service_account.description = description
        service_account.save()
        if permission_ids is not None:
            service_account.role.permissions.set(_validated_permissions(permission_ids))
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
