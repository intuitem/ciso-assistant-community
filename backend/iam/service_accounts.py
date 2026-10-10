"""Provisioning and update helpers for OAuth2 service accounts (see ServiceAccount model)."""

import uuid

import requests
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from allauth.idp.oidc.adapter import get_adapter as get_oidc_adapter
from allauth.idp.oidc.models import Client
from allauth.socialaccount.models import SocialApp

from iam.models import (
    ALLOWED_PERMISSION_APPS,
    IGNORED_PERMISSION_MODELS,
    Folder,
    Role,
    RoleAssignment,
    ServiceAccount,
    User,
)
from core.net_safety import BlockedRequestError, DnsLookupError
from iam.oidc_federation import check_social_app_live

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


def _ensure_federated_identity_available(
    *, social_app: SocialApp, federated_subject: str, exclude_pk=None
) -> None:
    """Raises ValidationError if (social_app, federated_subject) is already
    claimed by another service account, or the provider can't be reached.
    Shared by creation and by re-pointing an existing federated account."""
    qs = ServiceAccount.objects.filter(
        social_app=social_app, federated_subject=federated_subject
    )
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError(
            "A federated service account is already registered for this "
            "identity provider client and subject."
        )
    try:
        check_social_app_live(social_app)
    except (
        requests.RequestException,
        KeyError,
        BlockedRequestError,
        DnsLookupError,
    ) as e:
        raise ValidationError(
            f"Could not verify the registered identity provider: {e}"
        ) from e


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
        raise ValidationError("Invalid domain selection.")

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


def _detach_to_dedicated_role(
    service_account: ServiceAccount, permission_ids: list[int]
) -> None:
    new_role = Role.objects.create(
        name=f"SA-{service_account.client_id}", folder=Folder.get_root_folder()
    )
    new_role.permissions.set(_validated_permissions(permission_ids))
    _switch_role(service_account, new_role)


def provision_federated_service_account(
    *,
    name: str,
    description: str | None,
    permission_ids: list[int] | None,
    role_id=None,
    folder_ids: list,
    is_recursive: bool,
    created_by: User | None,
    social_app: SocialApp,
    federated_subject: str,
    expiry_date=None,
) -> ServiceAccount:
    role = get_selectable_builtin_role(role_id) if role_id is not None else None
    permissions = _validated_permissions(permission_ids) if role is None else None
    folders = list(Folder.objects.filter(id__in=folder_ids))
    if len(folders) != len(set(folder_ids)) or not folders:
        raise ValidationError("Invalid perimeter folder selection.")
    _ensure_federated_identity_available(
        social_app=social_app, federated_subject=federated_subject
    )

    root_folder = Folder.get_root_folder()
    try:
        with transaction.atomic():
            user = User.objects._create_user(
                email=f"sa-{uuid.uuid4().hex}@{SERVICE_ACCOUNT_EMAIL_DOMAIN}",
                password=None,
                mailing=False,
                initial_group=None,
                first_name=name,
            )
            if role is None:
                role = Role.objects.create(name=f"SA-{user.pk}", folder=root_folder)
                role.permissions.set(permissions)
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
                identity_source=ServiceAccount.IdentitySource.FEDERATED,
                social_app=social_app,
                federated_subject=federated_subject,
                user=user,
                role=role,
                created_by=created_by,
                expiry_date=expiry_date,
            )
    except IntegrityError as e:
        # Confirm it's actually the race we expect before blaming it - some other
        # constraint in this block failing shouldn't be reported as a duplicate.
        if ServiceAccount.objects.filter(
            social_app=social_app, federated_subject=federated_subject
        ).exists():
            raise ValidationError(
                "A federated service account is already registered for this "
                "identity provider client and subject."
            ) from e
        raise
    return service_account


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
    social_app: SocialApp | None = UNSET,
    federated_subject: str | None = UNSET,
) -> ServiceAccount:
    try:
        with transaction.atomic():
            if name is not None:
                service_account.name = name
                if (
                    service_account.identity_source
                    == ServiceAccount.IdentitySource.LOCAL
                ):
                    service_account.client.name = name
                    service_account.client.save(update_fields=["name"])
            if description is not UNSET:
                service_account.description = description
            if expiry_date is not UNSET:
                service_account.expiry_date = expiry_date
            if social_app is not UNSET or federated_subject is not UNSET:
                new_social_app = (
                    social_app
                    if social_app is not UNSET
                    else service_account.social_app
                )
                new_subject = (
                    federated_subject
                    if federated_subject is not UNSET
                    else service_account.federated_subject
                )
                if (
                    new_social_app != service_account.social_app
                    or new_subject != service_account.federated_subject
                ):
                    _ensure_federated_identity_available(
                        social_app=new_social_app,
                        federated_subject=new_subject,
                        exclude_pk=service_account.pk,
                    )
                    service_account.social_app = new_social_app
                    service_account.federated_subject = new_subject
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
            role_assignment = service_account.role_assignment
            if role_assignment is not None:
                if folder_ids is not None:
                    folders = list(Folder.objects.filter(id__in=folder_ids))
                    if len(folders) != len(set(folder_ids)) or not folders:
                        raise ValidationError("Invalid domain selection.")
                    role_assignment.perimeter_folders.set(folders)
                if is_recursive is not None:
                    role_assignment.is_recursive = is_recursive
                role_assignment.save()
    except IntegrityError as e:
        # Same double-check as provisioning: concurrent re-points can race
        # past _ensure_federated_identity_available's exists() pre-check, and
        # only that specific collision should read as a duplicate.
        if (
            service_account.social_app_id is not None
            and ServiceAccount.objects.filter(
                social_app_id=service_account.social_app_id,
                federated_subject=service_account.federated_subject,
            )
            .exclude(pk=service_account.pk)
            .exists()
        ):
            raise ValidationError(
                "A federated service account is already registered for this "
                "identity provider client and subject."
            ) from e
        raise
    return service_account
