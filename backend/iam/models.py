"""IAM model for CISO Assistant
Inspired from Azure IAM model"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Self
import uuid
from allauth.account.models import EmailAddress
from django.utils import timezone
from django.db import models, transaction
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AnonymousUser, Permission
from django.utils.translation import gettext_lazy as _
from django.urls.base import reverse_lazy
from django.db.models import Q, F, Prefetch
from knox.models import AuthToken
from core.utils import (
    BUILTIN_USERGROUP_CODENAMES,
    BUILTIN_ROLE_CODENAMES,
)
from core.base_models import AbstractBaseModel, NameDescriptionMixin
from core.utils import UserGroupCodename, RoleCodename
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail, get_connection, EmailMessage
from django.core.validators import validate_email
from ciso_assistant.settings import (
    CISO_ASSISTANT_URL,
    EMAIL_HOST,
    EMAIL_HOST_USER,
    EMAIL_HOST_USER_RESCUE,
    EMAIL_HOST_PASSWORD_RESCUE,
    EMAIL_HOST_RESCUE,
    EMAIL_PORT,
    EMAIL_PORT_RESCUE,
    EMAIL_USE_TLS,
    EMAIL_USE_TLS_RESCUE,
)
from django.conf import settings

import structlog

logger = structlog.get_logger(__name__)

from auditlog.registry import auditlog
from allauth.mfa.models import Authenticator
from iam.cache_builders import (
    get_folder_state,
    get_roles_state,
    get_groups_state,
    get_assignments_state,
    get_sub_folders_cached,
    get_parent_folders_cached,
    get_folder_path,
    invalidate_folders_cache,
    invalidate_roles_cache,
    invalidate_groups_cache,
    invalidate_assignments_cache,
    iter_descendant_ids,
)


ALLOWED_PERMISSION_APPS = (
    "core",
    "ebios_rm",
    "tprm",
    "privacy",
    "resilience",
    "crq",
    "pmbok",
    "iam",
)

IGNORED_PERMISSION_MODELS = (
    "personalaccesstoken",
    "role",
    "roleassignment",
    "usergroup",
    "ssosettings",
    "historicalmetric",
)


def _get_root_folder():
    """helper function outside of class to facilitate serialization
    to be used only in Folder class"""
    try:
        return Folder.objects.get(content_type=Folder.ContentType.ROOT)
    except:
        return None


class Folder(NameDescriptionMixin):
    """A folder is a container for other folders or any object
    Folders are organized in a tree structure, with a single root folder
    Folders are the base perimeter for role assignments
    """

    @staticmethod
    def get_root_folder() -> Self | None:
        """class function for general use"""
        if apps.ready:
            try:
                state = get_folder_state()
                root_id = getattr(state, "root_folder_id", None)
                if root_id:
                    return state.folders.get(root_id)
            except Exception:
                pass
        return _get_root_folder()

    @staticmethod
    def get_root_folder_id() -> uuid.UUID | None:
        return getattr(Folder.get_root_folder(), "id", None)

    class ContentType(models.TextChoices):
        """content type for a folder"""

        ROOT = "GL", _("GLOBAL")
        DOMAIN = "DO", _("DOMAIN")
        ENCLAVE = "EN", _("ENCLAVE")

    content_type = models.CharField(
        max_length=2, choices=ContentType.choices, default=ContentType.DOMAIN
    )

    parent_folder = models.ForeignKey(
        "self",
        null=True,
        on_delete=models.CASCADE,
        verbose_name=_("parent folder"),
        default=_get_root_folder,
    )
    builtin = models.BooleanField(default=False)

    filtering_labels = models.ManyToManyField(
        "core.FilteringLabel",
        blank=True,
        verbose_name=_("Labels"),
        related_name="folders",
    )

    fields_to_check = ["name"]

    class Meta:
        """for Model"""

        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")

    def __str__(self) -> str:
        return self.name.__str__()

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        invalidate_folders_cache()
        return result

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        invalidate_folders_cache()
        return result

    def get_sub_folders(self) -> Generator[Self, None, None]:
        """Return the list of subfolders through the cached tree."""
        yield from get_sub_folders_cached(self.id)

    # Should we update data-model.md now that this method is a generator ?
    def get_parent_folders(self) -> Generator[Self, None, None]:
        """Return the list of parent folders"""
        yield from get_parent_folders_cached(self.id)

    def get_folder_full_path(self, *, include_root: bool = False) -> list[Self]:
        """
        Get the full path of the folder including its parents.
        If include_root is True, the root folder is included in the path.
        """
        return get_folder_path(self.id, include_root=include_root)

    @staticmethod
    def _navigate_structure(start, path):
        """
        Navigate through a mixed structure of objects and dictionaries.

        :param start: The initial object or dictionary from which to start navigating.
        :param path: A list of strings representing the path to navigate, with each element
                     being an attribute name (for objects) or a key (for dictionaries).
        :return: The value found at the end of the path, or None if any part of the path is invalid.
        """
        current = start
        for p in path:
            if isinstance(current, dict):
                # For dictionaries
                current = current.get(p, None)
            else:
                # For objects
                try:
                    current = getattr(current, p, None)
                except AttributeError:
                    # If the attribute doesn't exist and current is not a dictionary
                    return None
            if current is None:
                return None
        return current

    @staticmethod
    def get_folder(obj: Any):
        """
        Return the folder of an object using navigation through mixed structures.
        For a folder, it is the object itself
        """
        if isinstance(obj, Folder):
            return obj
        # Define paths to try in order. Each path is a list representing the traversal path.
        # NOTE: There are probably better ways to represent these, but it works.
        paths = [
            ["folder"],
            ["parent_folder"],
            ["perimeter", "folder"],
            ["entity", "folder"],
            ["provider_entity", "folder"],
            ["solution", "provider_entity", "folder"],
            ["risk_assessment", "perimeter", "folder"],
            ["risk_scenario", "risk_assessment", "perimeter", "folder"],
            ["compliance_assessment", "perimeter", "folder"],
        ]

        # Attempt to traverse each path until a valid folder is found or all paths are exhausted.
        for path in paths:
            folder = Folder._navigate_structure(obj, path)
            if folder is not None:
                return folder

        # If no folder is found after trying all paths, handle this case (e.g., return None or raise an error).
        return None

    def get_user_roles(self) -> dict[str, list[str]]:
        """
        For a given folder, retrieves all users with roles on it
        and returns a dictionary mapping each user's email to a list of their
        role codenames.

        This function correctly handles roles that are:
        - Assigned directly to a user.
        - Assigned to a user group the user belongs to.
        - Inherited from parent folders via recursive role assignments.
        """
        folder_path_ids = [self.id] + [f.id for f in self.get_parent_folders()]

        role_assignment_filter = Q(is_recursive=False, perimeter_folders=self) | Q(
            is_recursive=True, perimeter_folders__id__in=folder_path_ids
        )

        direct_perms_qs = (
            RoleAssignment.objects.filter(role_assignment_filter, user__isnull=False)
            .annotate(user_pk=F("user__id"))
            .order_by()
        )

        # Query for roles granted to users via groups.
        # The ORM traverses the UserGroup -> User relationship.
        group_perms_qs = (
            RoleAssignment.objects.filter(
                role_assignment_filter, user_group__isnull=False
            )
            .annotate(user_pk=F("user_group__user__id"))
            .order_by()
        )

        # Combine both querysets into a single one.
        all_roles_qs = direct_perms_qs.union(group_perms_qs)

        user_roles = defaultdict(list)
        for item in all_roles_qs:
            # Filter out nulls that can occur if a role has no roles
            # or a group has no users.
            if item.user_pk and item.role:
                user_roles[item.user_pk].append(item.role)

        return dict(user_roles)

    @staticmethod
    def create_default_ug_and_ra(folder: Self):
        if folder.content_type == Folder.ContentType.DOMAIN:
            readers = UserGroup.objects.create(
                name=UserGroupCodename.READER, folder=folder, builtin=True
            )
            approvers = UserGroup.objects.create(
                name=UserGroupCodename.APPROVER, folder=folder, builtin=True
            )
            analysts = UserGroup.objects.create(
                name=UserGroupCodename.ANALYST, folder=folder, builtin=True
            )
            managers = UserGroup.objects.create(
                name=UserGroupCodename.DOMAIN_MANAGER, folder=folder, builtin=True
            )
            ra1 = RoleAssignment.objects.create(
                user_group=readers,
                role=Role.objects.get(name=RoleCodename.READER),
                builtin=True,
                folder=Folder.get_root_folder(),
                is_recursive=True,
            )
            ra1.perimeter_folders.add(folder)
            ra2 = RoleAssignment.objects.create(
                user_group=approvers,
                role=Role.objects.get(name=RoleCodename.APPROVER),
                builtin=True,
                folder=Folder.get_root_folder(),
                is_recursive=True,
            )
            ra2.perimeter_folders.add(folder)
            ra3 = RoleAssignment.objects.create(
                user_group=analysts,
                role=Role.objects.get(name=RoleCodename.ANALYST),
                builtin=True,
                folder=Folder.get_root_folder(),
                is_recursive=True,
            )
            ra3.perimeter_folders.add(folder)
            ra4 = RoleAssignment.objects.create(
                user_group=managers,
                role=Role.objects.get(name=RoleCodename.DOMAIN_MANAGER),
                builtin=True,
                folder=Folder.get_root_folder(),
                is_recursive=True,
            )
            ra4.perimeter_folders.add(folder)
            # Clear the cache after a new folder is created - purposely clearing everything

            # Create a UG and RA for each non-builtin role (idempotent)
            with transaction.atomic():
                for role in Role.objects.filter(builtin=False):
                    ug, _ = UserGroup.objects.get_or_create(
                        name=role.name, folder=folder, defaults={"builtin": False}
                    )
                    ra, created = RoleAssignment.objects.get_or_create(
                        user_group=ug,
                        role=role,
                        folder=Folder.get_root_folder(),
                        defaults={"builtin": False, "is_recursive": True},
                    )
                    # Ensure perimeter folder link exists
                    ra.perimeter_folders.add(folder)


class FolderMixin(models.Model):
    """
    Add foreign key to Folder, defaults to root folder
    """

    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name="%(class)s_folder",
        default=Folder.get_root_folder_id,
    )

    def get_folder_full_path(self, *, include_root: bool = False) -> list[Folder]:
        folders = ([self.folder] + [f for f in self.folder.get_parent_folders()])[::-1]
        if include_root:
            return folders
        return folders[1:] if len(folders) > 1 else folders

    class Meta:
        abstract = True


class PublishInRootFolderMixin(models.Model):
    """
    Set is_published to True if object is attached to the root folder
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if (
            getattr(self, "folder") == Folder.get_root_folder()
            and hasattr(self, "is_published")
            and not self.is_published
        ):
            self.is_published = True
        super().save(*args, **kwargs)


class UserGroup(NameDescriptionMixin, FolderMixin):
    """UserGroup objects contain users and can be used as principals in role assignments"""

    builtin = models.BooleanField(default=False)

    class Meta:
        """for Model"""

        verbose_name = _("user group")
        verbose_name_plural = _("user groups")

    def __str__(self) -> str:
        if self.builtin:
            return f"{self.folder.name} - {BUILTIN_USERGROUP_CODENAMES.get(self.name)}"
        return f"{self.folder.name} - {self.name}"

    def get_name_display(self) -> str:
        return self.name

    def get_localization_dict(self) -> dict:
        return {
            "folder": self.folder.name,
            "role": BUILTIN_USERGROUP_CODENAMES.get(self.name)
            if self.builtin
            else self.name,
        }

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        invalidate_groups_cache()
        invalidate_assignments_cache()  # because RoleAssignment points to groups
        return result

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        invalidate_groups_cache()
        invalidate_assignments_cache()
        return result

    @property
    def permissions(self):
        return RoleAssignment.get_permissions(self)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(
        self,
        email: str,
        password: str,
        mailing: bool,
        initial_group: UserGroup,
        **extra_fields,
    ):
        """
        Create and save a user with the given email, and password.
        If mailing is set, send a welcome mail
        If initial_group is given, put the new user in this group
        On mail error, raise a corresponding exception, but the user is properly created
        TODO: find a better way to manage mailing error
        """
        validate_email(email)
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=extra_fields.get("first_name", ""),
            last_name=extra_fields.get("last_name", ""),
            is_superuser=extra_fields.get("is_superuser", False),
            is_active=extra_fields.get("is_active", True),
            observation=extra_fields.get("observation"),
            folder=_get_root_folder(),
            keep_local_login=extra_fields.get("keep_local_login", False),
            expiry_date=extra_fields.get("expiry_date"),
        )
        user.user_groups.set(extra_fields.get("user_groups", []))
        if password:
            user.password = make_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        if initial_group:
            initial_group.user_set.add(user)

        # create an EmailAddress object for the newly created user
        # this is required by allauth
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True,
        )

        logger.info("user created sucessfully", user=user)

        if mailing:
            template_name = (
                "registration/first_connexion_email.html"
                if user.is_local
                else "registration/first_connexion_email_sso.html"
            )
            try:
                user.mailing(
                    email_template_name=template_name,
                    subject=_("Welcome to Ciso Assistant!"),
                )
            except Exception as exception:
                print(f"sending email to {email} failed")
                raise exception
        return user

    def create_user(self, email: str, password: str = None, **extra_fields):
        """create a normal user following Django convention"""
        logger.info("creating user", email=email)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(
            email=email,
            password=password,
            mailing=(EMAIL_HOST or EMAIL_HOST_RESCUE),
            initial_group=None,
            **extra_fields,
        )

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        """create a superuser following Django convention"""
        logger.info("creating superuser", email=email)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        superuser = self._create_user(
            email=email,
            password=password,
            mailing=not (password) and (EMAIL_HOST or EMAIL_HOST_RESCUE),
            initial_group=UserGroup.objects.get(name="BI-UG-ADM"),
            keep_local_login=True,
            **extra_fields,
        )
        return superuser


class CaseInsensitiveUserManager(UserManager):
    def get_by_natural_key(self, username):
        """
        By default, Django does a case-sensitive check on usernames™.
        Overriding this method fixes it.
        """
        return self.get(**{self.model.USERNAME_FIELD + "__iexact": username})


class User(AbstractBaseUser, AbstractBaseModel, FolderMixin):
    """a user is a principal corresponding to a human"""

    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    email = models.CharField(max_length=100, unique=True)
    first_login = models.BooleanField(default=True)
    preferences = models.JSONField(default=dict)
    keep_local_login = models.BooleanField(
        default=False,
        help_text=_(
            "If True allow the user to log in using the normal login form even with SSO forced."
        ),
    )
    is_third_party = models.BooleanField(default=False)
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    is_superuser = models.BooleanField(
        _("superuser status"),
        default=False,
        help_text=_(
            "Designates that this user has all permissions without explicitly assigning them."
        ),
    )
    user_groups = models.ManyToManyField(
        UserGroup,
        verbose_name=_("user groups"),
        blank=True,
        help_text=_(
            "The user groups this user belongs to. A user will get all permissions "
            "granted to each of their user groups."
        ),
    )
    observation = models.TextField(
        null=True, blank=True, verbose_name="Notes about a user"
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Expiry date"),
    )
    objects = CaseInsensitiveUserManager()

    # USERNAME_FIELD is used as the unique identifier for the user
    # and is required by Django to be set to a non-empty value.
    # See https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#django.contrib.auth.models.CustomUser.USERNAME_FIELD
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        """for Model"""

        verbose_name = _("user")
        verbose_name_plural = _("users")
        #        swappable = 'AUTH_USER_MODEL'
        permissions = (("backup", "backup"), ("restore", "restore"))

    @classmethod
    def visible_users(
        cls, for_user: AbstractBaseUser | AnonymousUser, view_all_users: bool
    ):
        """
        Return a queryset of users visible to `for_user`, always including `for_user`.
        Mirrors the logic used in UserViewSet.get_queryset().
        """
        if not getattr(for_user, "is_authenticated", False):
            return User.objects.none()

        (viewable_user_group_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), for_user, UserGroup
        )

        if view_all_users:
            base_qs = User.objects.all()

        else:
            (visible_users_ids, _, _) = RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), for_user, User
            )
            base_qs = (
                User.objects.filter(id__in=visible_users_ids)
                | User.objects.filter(pk=for_user.pk)
            ).distinct()

        # 🔒 Filtered prefetch for serializer
        return base_qs.prefetch_related(
            Prefetch(
                "user_groups",
                queryset=UserGroup.objects.filter(id__in=viewable_user_group_ids).only(
                    "id", "builtin"
                ),  # minimal
            )
        )

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        logger.info("user deleted", user=self)

    def save(self, *args, **kwargs):
        if self.is_superuser and not self.is_active:
            # avoid deactivation of superuser
            self.is_active = True
        if not self.is_local:
            self.set_unusable_password()
        super().save(*args, **kwargs)
        logger.info("user saved", user=self)

    def __str__(self):
        return (
            f"{self.first_name} {self.last_name}"
            if self.first_name and self.last_name
            else self.email
        )

    def get_full_name(self) -> str:
        """get user's full name (i.e. first_name + last_name)"""
        try:
            full_name = f"{self.first_name} {self.last_name}"
            return full_name
        except:
            return ""

    def get_short_name(self) -> str:
        """get user's short name (i.e. first_name or email before @))"""
        return self.first_name if self.first_name else self.email.split("@")[0]

    def mailing(self, email_template_name, subject, object="", object_id="", pk=False):
        """
        Sending a mail to a user for password resetting or creation
        """
        header = {
            "email": self.email,
            "root_url": CISO_ASSISTANT_URL,
            "uid": urlsafe_base64_encode(force_bytes(self.pk)),
            "user": self,
            "token": default_token_generator.make_token(self),
            "protocol": "https",
            "pk": str(pk) if pk else None,
            "object": object,
            "object_id": object_id,
        }
        email = render_to_string(email_template_name, header)
        try:
            send_mail(
                subject,
                email,
                None,
                [self.email],
                fail_silently=False,
                html_message=email,
            )
            logger.info(
                "Email sent successfully", recipient=self.email, subject=subject
            )
        except Exception as primary_exception:
            logger.error(
                "Primary mail server failure, trying rescue",
                recipient=self.email,
                subject=subject,
                error=str(primary_exception),
                email_host=EMAIL_HOST,
                email_port=EMAIL_PORT,
                email_host_user=EMAIL_HOST_USER,
                email_use_tls=EMAIL_USE_TLS,
            )
            if EMAIL_HOST_RESCUE:
                try:
                    with get_connection(
                        host=EMAIL_HOST_RESCUE,
                        port=EMAIL_PORT_RESCUE,
                        username=EMAIL_HOST_USER_RESCUE,
                        password=EMAIL_HOST_PASSWORD_RESCUE,
                        use_tls=EMAIL_USE_TLS_RESCUE if EMAIL_USE_TLS_RESCUE else False,
                    ) as new_connection:
                        EmailMessage(
                            subject,
                            email,
                            None,
                            [self.email],
                            connection=new_connection,
                        ).send()
                    logger.info(
                        "Email sent via rescue server",
                        recipient=self.email,
                        subject=subject,
                    )
                except Exception as rescue_exception:
                    logger.error(
                        "Rescue mail server failure",
                        recipient=self.email,
                        subject=subject,
                        error=str(rescue_exception),
                        email_host=EMAIL_HOST_RESCUE,
                        email_port=EMAIL_PORT_RESCUE,
                        email_username=EMAIL_HOST_USER_RESCUE,
                        email_use_tls=EMAIL_USE_TLS_RESCUE,
                    )
                    raise rescue_exception
            else:
                raise primary_exception

    def get_user_groups(self):
        """get the list of user groups containing the user in the form (group_name, builtin)"""
        return [(x.__str__(), x.builtin) for x in self.user_groups.all()]

    def get_roles(self):
        """get the list of roles attached to the user"""
        return list(
            self.user_groups.all()
            .values_list("roleassignment__role__name", flat=True)
            .distinct()
        )

    @property
    def has_backup_permission(self) -> bool:
        return RoleAssignment.is_access_allowed(
            user=self,
            perm=Permission.objects.get(codename="backup"),
            folder=Folder.get_root_folder(),
        )

    @property
    def edit_url(self) -> str:
        """get the edit url of the user"""
        return reverse_lazy(f"{self.__class__.__name__.lower()}-update", args=[self.id])

    @property
    def username(self):
        return self.email

    @property
    def permissions(self):
        return RoleAssignment.get_permissions(self)

    @username.setter
    def set_username(self, username):
        self.email = username

    @staticmethod
    def get_admin_users() -> List[Self]:
        return User.objects.filter(user_groups__name="BI-UG-ADM")

    def is_admin(self) -> bool:
        return self.user_groups.filter(name="BI-UG-ADM").exists()

    @property
    def is_editor(self) -> bool:
        permissions = RoleAssignment.get_permissions(self)
        editor_prefixes = {"add_", "change_", "delete_"}
        return any(
            any(perm.startswith(prefix) for prefix in editor_prefixes)
            for perm in permissions
        )

    @property
    def is_local(self) -> bool:
        """
        Indicates whether the user can log in using a local password
        """
        from global_settings.models import GlobalSettings

        try:
            sso_settings = GlobalSettings.objects.get(
                name=GlobalSettings.Names.SSO
            ).value
        except GlobalSettings.DoesNotExist:
            sso_settings = {}

        return self.is_active and (
            self.keep_local_login
            or not sso_settings.get("is_enabled", False)
            or not sso_settings.get("force_sso", False)
        )

    @classmethod
    def get_editors(cls) -> List[Self]:
        return [
            user
            for user in cls.objects.all()
            if user.is_editor and not user.is_third_party
        ]

    def has_mfa_enabled(self) -> bool:
        """
        Check if the user has Multi-Factor Authentication (MFA) enabled.
        Returns True if the user has any active MFA authenticators (TOTP, WebAuthn, etc.).
        """
        return Authenticator.objects.filter(user=self).exists()


class Role(NameDescriptionMixin, FolderMixin):
    """A role is a list of permissions"""

    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("permissions"),
        blank=True,
    )
    builtin = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        invalidate_roles_cache()
        return result

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        invalidate_roles_cache()
        return result

    def __str__(self) -> str:
        if self.builtin:
            return f"{BUILTIN_ROLE_CODENAMES.get(self.name)}"
        return self.name

    fields_to_check = ["name"]


def _iter_assignment_lites_for_user(user: AbstractBaseUser | AnonymousUser):
    """
    Yield AssignmentLite for a user, including via groups, using caches only.
    Returns empty iterator for AnonymousUser / unauthenticated.
    """
    if not getattr(user, "is_authenticated", False) or not getattr(user, "id", None):
        return iter(())

    assignments_state = get_assignments_state()
    groups_state = get_groups_state()

    user_id = user.id
    group_ids = groups_state.user_group_ids.get(user_id, frozenset())

    # user direct
    direct = assignments_state.by_user.get(user_id, ())
    # via groups
    via_groups = []
    for gid in group_ids:
        via_groups.extend(assignments_state.by_group.get(gid, ()))

    return iter((*direct, *via_groups))


class RoleAssignment(NameDescriptionMixin, FolderMixin):
    """fundamental class for CISO Assistant RBAC model, similar to Azure IAM model"""

    perimeter_folders = models.ManyToManyField(
        "Folder", verbose_name=_("Domain"), related_name="perimeter_folders"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
    )
    user_group = models.ForeignKey(UserGroup, null=True, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_("Role"))
    is_recursive = models.BooleanField(_("sub folders are visible"), default=False)
    builtin = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        invalidate_assignments_cache()
        return result

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        invalidate_assignments_cache()
        return result

    def __str__(self) -> str:
        # pragma pylint: disable=no-member
        return (
            "id="
            + str(self.id)
            + ", folders: "
            + str(list(self.perimeter_folders.values_list("name", flat=True)))
            + ", role: "
            + str(self.role.name)
            + ", user: "
            + (str(self.user.email) if self.user else "/")
            + ", user group: "
            + (str(self.user_group.name) if self.user_group else "/")
        )

    @staticmethod
    def is_access_allowed(
        user: AbstractBaseUser | AnonymousUser, perm: Permission, folder: Folder
    ) -> bool:
        """
        Determines if a user has specified permission on a specified folder.
        Cached path:
        - role permissions: Roles cache
        - assignments: Assignments cache (+ groups cache)
        - folder ancestry: Folder cache
        """
        if not getattr(user, "is_authenticated", False):
            return False

        perm_codename = perm.codename
        if not perm_codename:
            return False

        state = get_folder_state()
        roles_state = get_roles_state()

        # Special-case preserved from your code (but now codename based)
        add_tag_codename = "add_filteringlabel"

        for a in _iter_assignment_lites_for_user(user):
            role_perms = roles_state.role_permissions.get(a.role_id, frozenset())

            if perm_codename not in role_perms:
                continue

            # allow any folder if user has add_filteringlabel in role (your old behavior)
            if perm_codename == add_tag_codename:
                return True

            perimeter_ids = set(a.perimeter_folder_ids)

            # walk up folder parents via cached parent_map
            current_id = folder.id
            while current_id is not None:
                if current_id in perimeter_ids:
                    return True
                current_id = state.parent_map.get(current_id)

        return False

    @staticmethod
    def is_object_readable(
        user: AbstractBaseUser | AnonymousUser, object_type: Any, id: uuid
    ) -> bool:
        """
        Determines if a user has read on an object by id
        """
        obj = object_type.objects.filter(id=id).first()
        if not obj:
            return False
        class_name = object_type.__name__.lower()
        permission = Permission.objects.get(codename="view_" + class_name)
        return RoleAssignment.is_access_allowed(
            user, permission, Folder.get_folder(obj)
        )

    @staticmethod
    def get_accessible_folder_ids(
        folder: Folder,
        user: User,
        content_type: Folder.ContentType,
        codename: str = "view_folder",
    ) -> list[uuid.UUID]:
        """Return folder IDs in the scoped perimeter that the user can access."""
        state = get_folder_state()
        roles_state = get_roles_state()

        perimeter_ids = set(iter_descendant_ids(state, folder.id, include_start=True))

        accessible_ids: Set[uuid.UUID] = set()

        for a in _iter_assignment_lites_for_user(user):
            role_perms = roles_state.role_permissions.get(a.role_id, frozenset())
            # Must be able to see folders + have requested permission
            if "view_folder" not in role_perms or codename not in role_perms:
                continue

            ra_perimeter_ids = set(a.perimeter_folder_ids)
            if a.is_recursive:
                # Expand assignment perimeter downward
                expanded = set()
                for pf_id in ra_perimeter_ids:
                    expanded.update(
                        iter_descendant_ids(state, pf_id, include_start=True)
                    )
                ra_perimeter_ids = expanded

            accessible_ids.update(perimeter_ids & ra_perimeter_ids)

        # Filter by content_type and keep only within perimeter_ids
        result: list[uuid.UUID] = []
        for folder_id in accessible_ids:
            folder_obj = state.folders[folder_id]
            if content_type and folder_obj.content_type != content_type:
                continue
            if folder_id in perimeter_ids:
                result.append(folder_id)

        return result

    @staticmethod
    def get_accessible_object_ids(
        folder: Folder, user: AbstractBaseUser | AnonymousUser, object_type: Any
    ) -> Tuple["list[Any]", "list[Any]", "list[Any]"]:
        """Gets all objects of a specified type that a user can reach in a given folder
        Only accessible folders are considered
        Returns a triplet: (view_objects_list, change_object_list, delete_object_list)
        Assumes that object type follows Django conventions for permissions
        Also retrieve published objects in view
        """
        if not getattr(user, "is_authenticated", False):
            return ([], [], [])

        class_name = object_type.__name__.lower()

        # We still need Permission rows for:
        # - returning ids when object_type is Permission
        # - (optionally) ensuring the codenames exist in DB
        needed_codenames = [
            f"view_{class_name}",
            f"change_{class_name}",
            f"delete_{class_name}",
        ]
        permissions_map = {
            p.codename: p
            for p in Permission.objects.filter(codename__in=needed_codenames)
        }

        view_code = f"view_{class_name}"
        change_code = f"change_{class_name}"
        delete_code = f"delete_{class_name}"

        # If a permission doesn't exist for this model, behave safely.
        if (
            view_code not in permissions_map
            or change_code not in permissions_map
            or delete_code not in permissions_map
        ):
            return ([], [], [])

        # Cached state
        state = get_folder_state()
        roles_state = get_roles_state()

        perimeter_ids = set(iter_descendant_ids(state, folder.id, include_start=True))

        # folder_id -> set of granted permission codenames ("view_x", "change_x", "delete_x")
        folder_perm_codes: dict[uuid.UUID, set[str]] = defaultdict(set)

        # Compute folder permissions using caches only
        for a in _iter_assignment_lites_for_user(user):
            role_perm_codenames = roles_state.role_permissions.get(
                a.role_id, frozenset()
            )

            # Must be able to see folders at all
            if "view_folder" not in role_perm_codenames:
                continue

            ra_perimeter = set(a.perimeter_folder_ids)
            if a.is_recursive:
                expanded: set[uuid.UUID] = set()
                for pf_id in ra_perimeter:
                    expanded.update(
                        iter_descendant_ids(state, pf_id, include_start=True)
                    )
                ra_perimeter = expanded

            target_folders = perimeter_ids & ra_perimeter
            if not target_folders:
                continue

            can_view = view_code in role_perm_codenames
            can_change = change_code in role_perm_codenames
            can_delete = delete_code in role_perm_codenames

            if not (can_view or can_change or can_delete):
                continue

            for f_id in target_folders:
                if can_view:
                    folder_perm_codes[f_id].add(view_code)
                if can_change:
                    folder_perm_codes[f_id].add(change_code)
                if can_delete:
                    folder_perm_codes[f_id].add(delete_code)

        result_view: set[Any] = set()
        result_change: set[Any] = set()
        result_delete: set[Any] = set()

        # Fetch object ids per folder (DB work only here)
        for f_id, perms in folder_perm_codes.items():
            if hasattr(object_type, "folder"):
                objects_ids = object_type.objects.filter(folder_id=f_id).values_list(
                    "id", flat=True
                )
            elif object_type is Folder:
                objects_ids = [f_id]
            elif hasattr(object_type, "risk_assessment"):
                objects_ids = object_type.objects.filter(
                    risk_assessment__folder_id=f_id
                ).values_list("id", flat=True)
            elif hasattr(object_type, "entity"):
                objects_ids = object_type.objects.filter(
                    entity__folder_id=f_id
                ).values_list("id", flat=True)
            elif hasattr(object_type, "provider_entity"):
                objects_ids = object_type.objects.filter(
                    provider_entity__folder_id=f_id
                ).values_list("id", flat=True)
            else:
                raise NotImplementedError("type not supported")

            if view_code in perms:
                result_view.update(objects_ids)
            if change_code in perms:
                result_change.update(objects_ids)
            if delete_code in perms:
                result_delete.update(objects_ids)

        # Published inheritance: published parents for local-view folders
        # PERF: collect all ancestor folder_ids first, then do ONE query.
        if hasattr(object_type, "is_published") and hasattr(object_type, "folder"):
            ancestor_ids: set[uuid.UUID] = set()

            for folder_id, perms in folder_perm_codes.items():
                if view_code not in perms:
                    continue

                folder_obj = state.folders[folder_id]
                if folder_obj.content_type == Folder.ContentType.ENCLAVE:
                    continue

                parent_id = state.parent_map.get(folder_id)
                while parent_id:
                    ancestor_ids.add(parent_id)
                    parent_id = state.parent_map.get(parent_id)

            if ancestor_ids:
                result_view.update(
                    object_type.objects.filter(
                        folder_id__in=ancestor_ids, is_published=True
                    ).values_list("id", flat=True)
                )

        return (list(result_view), list(result_change), list(result_delete))

    def is_user_assigned(self, user) -> bool:
        """Determines if a user is assigned to the role assignment"""
        return user == self.user or (
            self.user_group and self.user_group in user.user_groups.all()
        )

    @staticmethod
    def get_permissions(principal: AbstractBaseUser | AnonymousUser | UserGroup):
        """Get all permissions attached to a user/group (direct or indirect), using caches.

        Returns: {codename: {"str": Permission.name}}
        """
        if isinstance(principal, AnonymousUser) or not getattr(
            principal, "is_authenticated", True
        ):
            return {}

        roles_state = get_roles_state()
        permissions_codes: set[str] = set()

        # --- UserGroup principal: assignments come from "by_group" cache only
        if isinstance(principal, UserGroup):
            assignments_state = get_assignments_state()
            for a in assignments_state.by_group.get(principal.id, ()):
                permissions_codes.update(
                    roles_state.role_permissions.get(a.role_id, frozenset())
                )

        # --- User principal: assignments come from helper (user + via groups)
        else:
            for a in _iter_assignment_lites_for_user(principal):
                permissions_codes.update(
                    roles_state.role_permissions.get(a.role_id, frozenset())
                )

        if not permissions_codes:
            return {}

        # Preserve old output: codename -> {"str": permission name}
        # (single DB hit, but IAM logic is cached)
        rows = Permission.objects.filter(codename__in=permissions_codes).values_list(
            "codename", "name"
        )

        out: dict[str, dict[str, str]] = {}
        for codename, name in rows:
            if codename:
                out[codename] = {"str": name}

        return out

    @staticmethod
    def has_role(user: AbstractBaseUser | AnonymousUser, role: Role) -> bool:
        """
        Determines if a user has a specific role, using caches only.
        Checks both direct assignments and assignments via groups.
        """
        if not getattr(user, "is_authenticated", False) or not getattr(
            user, "id", None
        ):
            return False

        role_id = getattr(role, "id", None)
        if not role_id:
            return False

        for a in _iter_assignment_lites_for_user(user):
            if a.role_id == role_id:
                return True
        return False

    @classmethod
    def get_permissions_per_folder(
        cls,
        principal: AbstractBaseUser | AnonymousUser | UserGroup,
        recursive: bool = False,
    ):
        """Get permissions grouped by folder id, using caches.

        - Always adds permissions on the explicit perimeter folders in assignments.
        - If `recursive=True` AND assignment.is_recursive=True, propagates to descendants.
        Returns: dict[str(folder_id)] -> set[codename]
        """
        if isinstance(principal, AnonymousUser) or not getattr(
            principal, "is_authenticated", True
        ):
            return {}

        state = get_folder_state()
        roles_state = get_roles_state()
        perms_by_folder: dict[str, set[str]] = defaultdict(set)

        def apply_assignment(a):
            role_perm_codenames = roles_state.role_permissions.get(
                a.role_id, frozenset()
            )
            if not role_perm_codenames:
                return

            for folder_id in a.perimeter_folder_ids:
                perms_by_folder[str(folder_id)].update(role_perm_codenames)

                if recursive and a.is_recursive:
                    for descendant_id in iter_descendant_ids(
                        state, folder_id, include_start=False
                    ):
                        perms_by_folder[str(descendant_id)].update(role_perm_codenames)

        # --- UserGroup principal
        if isinstance(principal, UserGroup):
            assignments_state = get_assignments_state()
            for a in assignments_state.by_group.get(principal.id, ()):
                apply_assignment(a)
            return perms_by_folder

        # --- User principal (user + via groups)
        for a in _iter_assignment_lites_for_user(principal):
            apply_assignment(a)

        return perms_by_folder


@dataclass(frozen=True, slots=True)
class FolderDisplayContext:
    """Information needed to render a folder path in the UI."""

    folder: Folder
    absolute_path: tuple[str, ...]
    relative_path: tuple[str, ...]
    minimal_context: tuple[str, ...]
    depth: int


# -----------------------------
# Personal Access Token
# -----------------------------


class PersonalAccessToken(models.Model):
    """
    Personal Access Token model.
    """

    name = models.CharField(max_length=255)
    auth_token = models.ForeignKey(AuthToken, on_delete=models.CASCADE)

    @property
    def created(self):
        return self.auth_token.created

    @property
    def expiry(self):
        return self.auth_token.expiry

    @property
    def digest(self):
        return self.auth_token.digest

    def __str__(self):
        return f"{self.auth_token.user.email} : {self.name} : {self.auth_token.digest}"


common_exclude = ["created_at", "updated_at"]
auditlog.register(
    User,
    m2m_fields={"user_groups"},
    exclude_fields=common_exclude,
)
auditlog.register(
    Folder,
    exclude_fields=common_exclude,
)
