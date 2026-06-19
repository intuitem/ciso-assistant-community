"""IAM model for CISO Assistant
Inspired from Azure IAM model"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Generator, List, Literal, Optional, Tuple, Iterable
from typing import TYPE_CHECKING, cast
import uuid
from allauth.account.models import EmailAddress
from django.utils import timezone
from django.db import models, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AnonymousUser, Permission
from django.utils.translation import gettext_lazy as _, override as translation_override
from django.urls.base import reverse_lazy
from django.db.models import Q, F, QuerySet, Case, When
from knox.models import AuthToken

if TYPE_CHECKING:
    from iam.cache_builders import AssignmentLite
    from core.models import Actor

from core.utils import (
    BUILTIN_USERGROUP_CODENAMES,
    get_translated_builtin_role_name,
)
from core.base_models import (
    AbstractBaseModel,
    ActorSyncManager,
    ActorSyncMixin,
    NameDescriptionMixin,
)
from core.utils import UserGroupCodename, RoleCodename
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import get_connection, EmailMessage
from django.core.validators import validate_email
from django.conf import settings

import structlog

logger = structlog.get_logger(__name__)

from auditlog.registry import auditlog
from allauth.mfa.models import Authenticator
from core.context import focus_folder_id_var
from django.shortcuts import get_object_or_404
from iam.cache_builders import (
    CacheNotReadyError,
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
    "global_settings",
)

IGNORED_PERMISSION_MODELS = (
    "personalaccesstoken",
    "role",
    "roleassignment",
    "usergroup",
    "ssosettings",
    "historicalmetric",
)

type NativePermissionPrefix = Literal["view", "add", "change", "delete"]
"""Default permission prefixes available for all models (django-native)."""

type UniquePermissionPrefix = Literal["approve", "backup", "restore", "transition"]
"""Unique permission prefixes (only used by a single specific custom builtin `Permission`)."""

type PermissionPrefix = NativePermissionPrefix | UniquePermissionPrefix
"""All possible permission prefixes (both the native and special ones)."""


def _get_root_folder() -> Folder | None:
    """helper function outside of class to facilitate serialization
    to be used only in Folder class
    Returns None only before the IAM tables/migrations are ready so Django's
    pre-migration checks can instantiate models without failing.
    """
    try:
        return Folder.objects.only("id", "content_type").get(
            content_type=Folder.ContentType.ROOT
        )
    except Folder.DoesNotExist:
        return None
    except OperationalError, ProgrammingError:
        return None


class Folder(NameDescriptionMixin):
    """A folder is a container for other folders or any object
    Folders are organized in a tree structure, with a single root folder
    Folders are the base perimeter for role assignments
    """

    @staticmethod
    def get_root_folder() -> "Folder":
        """class function for general use"""
        try:
            state = get_folder_state()
        except CacheNotReadyError:
            # During initial migrations the cache cannot hydrate yet; fall back to the
            # direct lookup which may still be None until the schema is ready.
            folder = _get_root_folder()
            return cast("Folder", folder)  # type: ignore[return-value]

        # Cache is ready, so root folder is already existing
        # But if the cache is stale, we call the db
        if state.root_folder_id:
            cached_root = state.folders.get(state.root_folder_id)
            if cached_root is not None:
                return cached_root
        return Folder.objects.only("id", "content_type").get(
            content_type=Folder.ContentType.ROOT
        )

    @staticmethod
    def get_root_folder_id() -> uuid.UUID | None:
        folder = _get_root_folder()
        return getattr(folder, "id", None)

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
    descendants = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="ancestors",
    )
    builtin = models.BooleanField(default=False)
    create_iam_groups = models.BooleanField(
        default=False,
        help_text=_("Automatically provision IAM groups for domain folders."),
    )

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

    def _update_descendants_at_creation(self):
        """Update the `ancestor.descendants` `ManyToManyField` for each `ancestor` of the newly created `self` `Folder` instance."""
        parent_folder = self.parent_folder
        if parent_folder is None:
            return

        ancestors = [parent_folder]
        ancestors.extend(Folder.objects.filter(descendants=parent_folder))

        for ancestor in ancestors:
            ancestor.descendants.add(self)

    def _update_descendants_on_parent_folder_change(self):
        """
        Update the `descendants` of both the old and new ancestors of this `Folder`.

        If `self.parent_folder` didn't change (compared to the current `old_instance` `Folder` stored in the DB), this function does nothing.
        """
        old_instance = Folder.objects.get(pk=self.pk)

        if old_instance.parent_folder_id == self.parent_folder_id:
            return

        old_ancestors = list(Folder.objects.filter(descendants=self))
        old_ancestor_id_set = {ancestor.id for ancestor in old_ancestors}

        new_parent = self.parent_folder

        if new_parent is None:
            new_ancestors = []
        else:
            new_ancestors = list(Folder.objects.filter(descendants=new_parent))
            new_ancestors.append(new_parent)

        new_ancestor_id_set = {ancestor.id for ancestor in new_ancestors}

        descendant_model = Folder.descendants.through
        descendant_ids = self.descendants.all().values_list("id", flat=True)
        descendant_and_self_ids = descendant_ids.union(
            Folder.objects.filter(id=self.id).values_list("id", flat=True)
        )

        added_ancestors = [
            ancestor
            for ancestor in new_ancestors
            if ancestor.id not in old_ancestor_id_set
        ]
        deleted_ancestors = [
            ancestor
            for ancestor in old_ancestors
            if ancestor.id not in new_ancestor_id_set
        ]

        for ancestor in added_ancestors:
            descendant_model.objects.bulk_create(
                (
                    descendant_model(
                        from_folder_id=ancestor.id, to_folder_id=descendant_id
                    )
                    for descendant_id in descendant_and_self_ids
                ),
                batch_size=1000,
                ignore_conflicts=True,
            )

        descendant_model.objects.filter(
            from_folder_id__in=[ancestor.id for ancestor in deleted_ancestors],
            to_folder_id__in=descendant_and_self_ids,
        ).delete()

    def save(self, *args, **kwargs):
        is_create = self._state.adding

        with transaction.atomic():
            if is_create:
                self.is_published = True
                super().save(*args, **kwargs)
                self._update_descendants_at_creation()
            else:
                self._update_descendants_on_parent_folder_change()
                super().save(*args, **kwargs)

            invalidate_folders_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        invalidate_folders_cache()

    def get_sub_folders(self) -> Generator["Folder", None, None]:
        """Return the list of subfolders through the cached tree."""
        yield from get_sub_folders_cached(self.id)

    # Should we update data-model.md now that this method is a generator ?
    def get_parent_folders(self) -> Generator["Folder", None, None]:
        """Return the list of parent folders"""
        yield from get_parent_folders_cached(self.id)

    def get_folder_full_path(self, *, include_root: bool = False) -> list["Folder"]:
        """
        Get the full path of the folder including its parents.
        If include_root is True, the root folder is included in the path.
        """
        return get_folder_path(self.id, include_root=include_root)

    def get_folder_full_path_string(self, *, include_root: bool = False) -> str:
        """
        Return a stringified slash-separated folder path.
        This string is unique per-folder.
        """
        return "/".join(
            f.name for f in self.get_folder_full_path(include_root=include_root)
        )

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
        # NOTE: This list is not complete.
        paths = [
            ["folder"],
            ["parent_folder"],
            ["perimeter", "folder"],
            ["user", "folder"],
            ["team", "folder"],
            ["entity", "folder"],
            ["provider_entity", "folder"],
            ["solution", "provider_entity", "folder"],
            ["processing", "folder"],
            ["journey", "folder"],
            ["questionnaire_run", "folder"],
            ["agent_run", "folder"],
        ]

        # Attempt to traverse each path until a valid folder is found or all paths are exhausted.
        for path in paths:
            folder = Folder._navigate_structure(obj, path)
            if folder is not None:
                return folder

        # If no folder is found after trying all paths, gracefully fall back
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
    def create_default_ug_and_ra(folder: "Folder"):
        if (
            folder.content_type != Folder.ContentType.DOMAIN
            or not folder.create_iam_groups
        ):
            return

        root_folder = Folder.get_root_folder()
        builtin_pairs = [
            (UserGroupCodename.READER, RoleCodename.READER),
            (UserGroupCodename.APPROVER, RoleCodename.APPROVER),
            (UserGroupCodename.ANALYST, RoleCodename.ANALYST),
            (UserGroupCodename.DOMAIN_MANAGER, RoleCodename.DOMAIN_MANAGER),
            (UserGroupCodename.AUDITEE, RoleCodename.AUDITEE),
        ]

        for ug_codename, role_codename in builtin_pairs:
            ug, created = UserGroup.objects.get_or_create(
                name=str(ug_codename),
                folder=folder,
                defaults={"builtin": True},
            )
            if not created or not ug.builtin:
                if not ug.builtin:
                    ug.builtin = True
                ug.save(update_fields=["builtin"])
            role = Role.objects.get(name=str(role_codename))
            ra, _ = RoleAssignment.objects.get_or_create(
                user_group=ug,
                role=role,
                folder=root_folder,
                defaults={"builtin": True, "is_recursive": True},
            )
            Folder._ensure_recursive_assignment(ra)
            ra.perimeter_folders.add(folder)

        with transaction.atomic():
            for role in Role.objects.filter(builtin=False):
                ug, created = UserGroup.objects.get_or_create(
                    name=role.name,
                    folder=folder,
                    defaults={"builtin": True},
                )
                if not created or not ug.builtin:
                    if not ug.builtin:
                        ug.builtin = True
                    ug.save(update_fields=["builtin"])
                ra, _ = RoleAssignment.objects.get_or_create(
                    user_group=ug,
                    role=role,
                    folder=root_folder,
                    defaults={"builtin": False, "is_recursive": True},
                )
                Folder._ensure_recursive_assignment(ra)
                ra.perimeter_folders.add(folder)

    @staticmethod
    def _ensure_recursive_assignment(role_assignment: "RoleAssignment") -> None:
        if not role_assignment.is_recursive:
            role_assignment.is_recursive = True
            role_assignment.save(update_fields=["is_recursive"])


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
        # Root folder children must be published
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
            role_codename = BUILTIN_USERGROUP_CODENAMES.get(self.name, self.name)
            role_name = get_translated_builtin_role_name(role_codename)
        else:
            role_name = self.name
        return f"{self.folder.name} - {role_name}"

    def get_name_display(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        invalidate_groups_cache()
        invalidate_assignments_cache()  # because RoleAssignment points to groups

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        invalidate_groups_cache()
        invalidate_assignments_cache()

    @property
    def permissions(self):
        return RoleAssignment.get_permissions(self)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(
        self,
        email: str,
        password: Optional[str],
        mailing: bool,
        initial_group: Optional[UserGroup],
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
        user = cast(
            "User",
            self.model(
                email=email,
                first_name=extra_fields.get("first_name", ""),
                last_name=extra_fields.get("last_name", ""),
                is_superuser=extra_fields.get("is_superuser", False),
                is_active=extra_fields.get("is_active", True),
                is_third_party=extra_fields.get("is_third_party", False),
                observation=extra_fields.get("observation"),
                folder=_get_root_folder(),
                keep_local_login=extra_fields.get("keep_local_login", False),
                expiry_date=extra_fields.get("expiry_date"),
                is_published=True,
            ),
        )
        if password:
            user.password = make_password(password)
        else:
            user.set_unusable_password()
        # Set default language from general settings
        try:
            from global_settings.models import GlobalSettings

            general = GlobalSettings.objects.filter(name="general").first()
            if general and isinstance(general.value, dict):
                default_lang = general.value.get("default_language", "en")
            else:
                default_lang = "en"
        except Exception:
            default_lang = "en"
        if not isinstance(user.preferences, dict):
            user.preferences = {}
        user.preferences["lang"] = default_lang

        user.save(using=self._db)
        user.user_groups.set(extra_fields.get("user_groups", []))
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
                    subject=_("Welcome to CISO Assistant!"),
                )
            except Exception as exception:
                print(f"sending email to {email} failed")
                raise exception
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        """create a normal user following Django convention"""
        logger.info("creating user", email=email)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(
            email=email,
            password=password,
            mailing=bool(settings.EMAIL_HOST or settings.EMAIL_HOST_RESCUE),
            initial_group=None,
            **extra_fields,
        )

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        """create a superuser following Django convention"""
        logger.info("creating superuser", email=email)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        superuser = self._create_user(
            email=email,
            password=password,
            mailing=bool(
                (not password) and (settings.EMAIL_HOST or settings.EMAIL_HOST_RESCUE)
            ),
            initial_group=UserGroup.objects.get(name="BI-UG-ADM"),
            keep_local_login=True,
            **extra_fields,
        )
        return superuser


class CaseInsensitiveUserManager(UserManager, ActorSyncManager):
    def get_by_natural_key(self, username):
        """
        By default, Django does a case-sensitive check on usernames™.
        Overriding this method fixes it.
        """
        return self.get(**{self.model.USERNAME_FIELD + "__iexact": username})


class User(ActorSyncMixin, AbstractBaseUser, AbstractBaseModel, FolderMixin):
    """a user is a principal corresponding to a human"""

    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    email = models.CharField(max_length=100, unique=True)
    first_login = models.BooleanField(default=True)
    preferences = models.JSONField(default=dict)
    DATE_FORMATS = {"auto", "iso", "ddmmyyyy", "mmddyyyy", "long_dmy", "long_mdy"}
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

    def get_emails(self) -> list[str]:
        return [self.email]

    def get_preferences(self) -> dict:
        """
        Return normalized user preferences, backfilling defaults in memory.
        Ensures the returned dict always has a 'lang' key.
        Does not persist changes — callers that need to save must do so explicitly.
        """
        prefs = self.preferences
        if not isinstance(prefs, dict):
            prefs = {}
            self.preferences = prefs
        valid_langs = {code for code, _ in settings.LANGUAGES}
        if not isinstance(prefs.get("lang"), str) or prefs["lang"] not in valid_langs:
            try:
                from global_settings.models import GlobalSettings

                general = GlobalSettings.objects.filter(name="general").first()
                default_lang = (
                    general.value.get("default_language", "en")
                    if general and isinstance(general.value, dict)
                    else "en"
                )
            except Exception:
                default_lang = "en"
            prefs["lang"] = default_lang
        if prefs.get("date_format") not in self.DATE_FORMATS:
            prefs["date_format"] = "auto"
        ui = prefs.get("ui") if isinstance(prefs.get("ui"), dict) else {}
        if ui.get("theme") not in ("light", "dark", "system"):
            ui["theme"] = "system"
        prefs["ui"] = ui
        return prefs

    # Maps Django HTML template names to YAML template keys
    _TEMPLATE_KEY_MAP = {
        "registration/first_connexion_email.html": "welcome",
        "registration/first_connexion_email_sso.html": "welcome_sso",
        "registration/password_reset_email.html": "password_reset",
        "tprm/third_party_email.html": "questionnaire_assignment",
    }

    def mailing(self, email_template_name, subject, object="", object_id="", pk=False):
        """
        Sending a mail to a user for password resetting or creation.
        Tries the YAML-based template system first (supports custom overrides),
        falls back to the legacy Django HTML templates.
        """
        user_lang = self.get_preferences().get("lang", "en")
        uid = urlsafe_base64_encode(force_bytes(self.pk))
        token = default_token_generator.make_token(self)

        questionnaire_url = (
            f"{settings.CISO_ASSISTANT_URL}/{object}/{object_id}"
            if object
            else settings.CISO_ASSISTANT_URL
        )

        # Build context for the YAML template system
        context = {
            "set_password_url": f"{settings.CISO_ASSISTANT_URL}/first-connexion?uidb64={uid}&token={token}",
            "reset_password_url": f"{settings.CISO_ASSISTANT_URL}/password-reset/confirm?uidb64={uid}&token={token}",
            "questionnaire_url": questionnaire_url
            if object
            else settings.CISO_ASSISTANT_URL,
        }

        # Try YAML template system (supports custom overrides and Markdown)
        template_key = self._TEMPLATE_KEY_MAP.get(email_template_name)
        if template_key:
            try:
                from core.email_utils import render_email_template

                rendered = render_email_template(
                    template_key, context, locale=user_lang
                )
                if rendered:
                    subject = rendered["subject"]
                    body = rendered["body"]
                    html_body = rendered.get("html_body")
                    return self._send_email(subject, body, html_body)
            except Exception as e:
                logger.warning(
                    "YAML template rendering failed, falling back to Django template",
                    template_key=template_key,
                    exc_info=e,
                )

        # Fallback to legacy Django HTML templates
        header = {
            "email": self.email,
            "root_url": settings.CISO_ASSISTANT_URL,
            "uid": uid,
            "user": self,
            "token": token,
            "protocol": "https",
            "pk": str(pk) if pk else None,
            "object": object,
            "object_id": object_id,
            "questionnaire_url": questionnaire_url,
        }
        with translation_override(user_lang):
            email = render_to_string(email_template_name, header)
            subject = str(subject)

        self._send_email(subject, email, email)

    def _send_email(self, subject, body, html_body=None):
        """Send an email with primary/rescue server fallback."""
        try:
            ssl_context = getattr(settings, "EMAIL_SSL_CONTEXT", None)
            with get_connection(ssl_context=ssl_context) as connection:
                msg = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=None,
                    to=[self.email],
                    connection=connection,
                )
                if html_body:
                    msg.content_subtype = "html"
                    msg.body = html_body
                msg.send()
            logger.info(
                "Email sent successfully", recipient=self.email, subject=subject
            )
        except Exception as primary_exception:
            logger.error(
                "Primary mail server failure, trying rescue",
                recipient=self.email,
                subject=subject,
                error=str(primary_exception),
                email_host=settings.EMAIL_HOST,
                email_port=settings.EMAIL_PORT,
                email_host_user=settings.EMAIL_HOST_USER,
                email_use_tls=settings.EMAIL_USE_TLS,
            )
            if settings.EMAIL_HOST_RESCUE:
                try:
                    with get_connection(
                        host=settings.EMAIL_HOST_RESCUE,
                        port=settings.EMAIL_PORT_RESCUE,
                        username=settings.EMAIL_HOST_USER_RESCUE,
                        password=settings.EMAIL_HOST_PASSWORD_RESCUE,
                        use_tls=settings.EMAIL_USE_TLS_RESCUE,
                        use_ssl=settings.EMAIL_USE_SSL_RESCUE,
                        ssl_context=getattr(settings, "EMAIL_SSL_CONTEXT", None),
                    ) as new_connection:
                        msg = EmailMessage(
                            subject=subject,
                            body=body,
                            from_email=None,
                            to=[self.email],
                            connection=new_connection,
                        )
                        if html_body:
                            msg.content_subtype = "html"
                            msg.body = html_body
                        msg.send()
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
                        email_host=settings.EMAIL_HOST_RESCUE,
                        email_port=settings.EMAIL_PORT_RESCUE,
                        email_username=settings.EMAIL_HOST_USER_RESCUE,
                        email_use_tls=settings.EMAIL_USE_TLS_RESCUE,
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
    def is_auditee(self) -> bool:
        """True when the user holds the auditee role on at least one domain."""
        from core.utils import get_respondent_scoped_folder_ids

        return bool(get_respondent_scoped_folder_ids(self))

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
        return str(
            reverse_lazy(f"{self.__class__.__name__.lower()}-update", args=[self.id])
        )

    @property
    def username(self):
        return self.email

    @property
    def permissions(self):
        return RoleAssignment.get_permissions(self)

    @staticmethod
    def get_admin_users() -> QuerySet["User"]:
        return User.objects.filter(user_groups__name="BI-UG-ADM")

    def is_admin(self) -> bool:
        return self.user_groups.filter(name="BI-UG-ADM").exists()

    # Permissions that grant write access but do not consume a license seat
    NON_SEAT_PERMISSIONS = {
        "change_validationflow",
        "add_chatsession",
        "change_chatsession",
        "delete_chatsession",
    }

    @property
    def is_editor(self) -> bool:
        permissions = RoleAssignment.get_permissions(self)
        editor_prefixes = {"add_", "change_", "delete_"}
        return any(
            any(perm.startswith(prefix) for prefix in editor_prefixes)
            for perm in permissions
            if perm not in self.NON_SEAT_PERMISSIONS
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
    def get_editors(cls) -> List["User"]:
        return [
            user
            for user in cls.objects.all()
            if user.is_editor and not user.is_third_party
        ]

    @property
    def is_sso(self) -> bool:
        """
        Indicates whether the user has a linked SSO (social) account.
        """
        from allauth.socialaccount.models import SocialAccount

        return SocialAccount.objects.filter(user=self).exists()

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
        super().save(*args, **kwargs)
        invalidate_roles_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        invalidate_roles_cache()

    def __str__(self) -> str:
        if self.builtin:
            return get_translated_builtin_role_name(self.name)
        return self.name

    fields_to_check = ["name"]


def _iter_assignment_lites_for_user(user: AbstractBaseUser | AnonymousUser):
    """
    Yield AssignmentLite for a user, including via groups, using caches only.
    Returns empty iterator for AnonymousUser / unauthenticated.
    """
    if isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
        return iter(())
    user_id_opt = cast(Optional[uuid.UUID], getattr(user, "id", None))
    if user_id_opt is None:
        return iter(())

    assignments_state = get_assignments_state()
    groups_state = get_groups_state()

    user_id = cast(uuid.UUID, user_id_opt)
    group_ids = groups_state.user_group_ids.get(user_id, frozenset())

    # user direct
    direct = assignments_state.by_user.get(user_id, ())
    # via groups
    via_groups: list["AssignmentLite"] = []
    for gid in group_ids:
        via_groups.extend(assignments_state.by_group.get(gid, ()))

    return iter((*direct, *via_groups))


class RoleAssignment(NameDescriptionMixin, FolderMixin):
    """fundamental class for CISO Assistant RBAC model, similar to Azure IAM model"""

    if TYPE_CHECKING:
        perimeter_folders: Any  # pragma: no cover
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
        super().save(*args, **kwargs)
        invalidate_assignments_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        invalidate_assignments_cache()

    def __str__(self) -> str:
        folder_names = list(self.perimeter_folders.values_list("name", flat=True))
        role_name = self.role.name

        principal_type = "user_group" if self.user_group else "user"
        principal_name = self.user_group.name if self.user_group else self.user

        return f"id={self.id}, folders={folder_names}, is_recursive={self.is_recursive}, role={role_name}, {principal_type}: {principal_name}"

    @staticmethod
    def get_role_assignments_from_user(user: User) -> QuerySet[RoleAssignment]:
        if not getattr(user, "is_authenticated", False):
            return RoleAssignment.objects.none()

        user_role_assignments = RoleAssignment.objects.filter(
            Q(user=user) | Q(user_group__in=user.user_groups.all())
        )

        return user_role_assignments

    @staticmethod
    def get_role_assignments_from_permission(
        user: User,
        perm: PermissionPrefix,
        model: type[models.Model],
    ) -> QuerySet[RoleAssignment]:
        """Return the `RoleAssignment` list (as a `QuerySet`) granting the `perm` permission on the model `model`."""

        role_assignments = RoleAssignment.get_role_assignments_from_user(user)

        if model is User and perm in ("backup", "restore"):
            codename = perm
        else:
            model_name = model.__name__.lower()
            codename = f"{perm}_{model_name}"

        # Using `.order_by()` prevent django from including the "name" column (to avoid problems on queryset unions)
        role_assignments = role_assignments.order_by().filter(
            role__permissions__codename=codename
        )

        return role_assignments

    @staticmethod
    def is_access_allowed(
        user: AbstractBaseUser | AnonymousUser,
        perm: Permission,
        folder: Folder,
    ) -> bool:
        """
        Determines if a user has specified permission on a specified folder.
        Cached path:
        - role permissions: Roles cache
        - assignments: Assignments cache (+ groups cache)
        - folder ancestry: Folder cache
        """

        from core.models import FilteringLabel

        perm_type = perm.codename.split("_")[0]
        model = perm.content_type.model_class()

        if model is Permission:
            # Everyone can view permissions, no one can add/change/delete them.
            return perm_type == "view"

        if model is FilteringLabel:
            return RoleAssignment.get_role_assignments_from_permission(
                user, perm_type, FilteringLabel
            ).exists()

        allowed_folder_ids = RoleAssignment.get_allowed_folder_ids(
            user, perm_type, model
        )
        return (
            Folder.objects.filter(id__in=allowed_folder_ids)
            .filter(id=folder.id)
            .exists()
        )

    @staticmethod
    def _is_actor_accessible(
        user: AbstractBaseUser | AnonymousUser,
        perm: NativePermissionPrefix,
        actor: Actor,
    ) -> bool:
        from core.models import Team, Entity

        specific = actor.specific
        specific_model = type(specific)
        iam_scope_folder = specific.folder

        return iam_scope_folder in RoleAssignment.get_allowed_folder_ids(
            user, perm, specific_model
        )

    @staticmethod
    def is_object_accessible(
        user: AbstractBaseUser | AnonymousUser,
        perm: PermissionPrefix,
        model: type[models.Model],
        id: uuid.UUID,
    ) -> bool:
        from core.models import Actor, FilteringLabel

        if model is Permission:
            return perm == "view"

        obj = model.objects.filter(id=id).first()
        if obj is None:
            return False

        if model is Actor:
            return RoleAssignment._is_actor_accessible(user, perm, obj)

        user_role_assignments = RoleAssignment.get_role_assignments_from_permission(
            user, perm, model
        )

        direct_accessible_folder_id_set = set(
            user_role_assignments.values_list(
                "perimeter_folders__id", flat=True
            ).distinct()
        )

        if model is FilteringLabel:
            return user_role_assignments.exists()

        iam_scope_folder_id = RoleAssignment.get_iam_folder_id(obj)

        if not isinstance(iam_scope_folder_id, uuid.UUID):
            raise ValueError(
                f"IAM scope folder not found for object {obj!r} of type {model.__qualname__!r}!"
            )

        iam_folder = Folder.objects.get(id=iam_scope_folder_id)

        folder_queryset = Folder.objects.filter(id=iam_scope_folder_id)
        folder_chain_queryset = iam_folder.ancestors.all().union(folder_queryset)
        folder_chain_ids_queryset = folder_chain_queryset.values_list("id", flat=True)

        folder_chain_id_set = set(folder_chain_ids_queryset)
        is_accessible = bool(direct_accessible_folder_id_set & folder_chain_id_set)

        if is_accessible:
            return True

        has_is_published_field = any(
            f.name == "is_published" for f in model._meta.get_fields()
        )

        if has_is_published_field and getattr(obj, "is_published"):
            ancestor_folder_ids = (
                Folder.objects.filter(descendants__in=direct_accessible_folder_id_set)
                .values_list("id", flat=True)
                .distinct()
            )

            is_accessible = iam_folder.id in ancestor_folder_ids
            return is_accessible

        return False

    @staticmethod
    def is_object_readable(
        user: AbstractBaseUser | AnonymousUser, model: type[models.Model], id: uuid.UUID
    ) -> bool:
        return RoleAssignment.is_object_accessible(user, "view", model, id)

    @staticmethod
    def _get_focus_accessible_folder_ids(
        focus_folder_id: uuid.UUID, folder_ids: Iterable[uuid.UUID]
    ) -> QuerySet[uuid.UUID]:
        """Filter out folders excluded by the focus mode."""

        folders = Folder.objects.filter(id__in=folder_ids)
        focused_folders = folders.filter(
            Q(ancestors=focus_folder_id) | Q(id=focus_folder_id)
        )
        focused_folder_ids = focused_folders.values_list("id", flat=True)

        return focused_folder_ids

    @staticmethod
    def _filter_accessible_folder_ids_by_focus_folder(
        focused_folder: Folder,
        direct_flat_folder_ids: Iterable[uuid.UUID],
        direct_recursive_folder_ids: Iterable[uuid.UUID],
    ) -> QuerySet[uuid.UUID]:
        """Return the accessible folder IDs rooted from the `focused_folder` `Folder` from the direct flat and direct recursive folder IDs."""

        direct_recursive_folders = Folder.objects.filter(
            id__in=direct_recursive_folder_ids
        )

        # `True` if the user has the `perm_codename` permission on the focus folder itself OR an ancestor `Folder` of the `focused_folder`.
        is_whole_focus_folder_tree_accessible = direct_recursive_folders.filter(
            Q(id=focused_folder.id) | Q(descendants=focused_folder.id)
        ).exists()

        if is_whole_focus_folder_tree_accessible:
            # A non-strict folder supertree of the `focused_folder` tree is accessible
            # Therefore all the focused folder tree can be accessed.
            focused_folder_tree = Folder.objects.filter(id=focused_folder.id).union(
                Folder.objects.filter(ancestors=focused_folder.id)
            )

            accessible_folder_ids = focused_folder_tree.values_list("id", flat=True)
            return accessible_folder_ids

        accessible_direct_flat_folder_ids = (
            RoleAssignment._get_focus_accessible_folder_ids(
                focused_folder.id, direct_flat_folder_ids
            )
        )
        accessible_direct_recursive_folder_ids = (
            RoleAssignment._get_focus_accessible_folder_ids(
                focused_folder.id, direct_recursive_folder_ids
            )
        )
        directly_accessible_folder_ids = accessible_direct_flat_folder_ids.union(
            accessible_direct_recursive_folder_ids
        )

        indirectly_accessible_folders = Folder.objects.filter(
            ancestors__in=accessible_direct_recursive_folder_ids
        )
        indirectly_accessible_folder_ids = indirectly_accessible_folders.values_list(
            "id", flat=True
        )

        accessible_folder_ids = directly_accessible_folder_ids.union(
            indirectly_accessible_folder_ids
        )
        return accessible_folder_ids

    @staticmethod
    def get_allowed_folder_ids(
        user: AbstractBaseUser | AnonymousUser,
        perm: PermissionPrefix,
        model: type[models.Model],
        *,
        base_folder: Optional[Folder] = None,
    ) -> QuerySet[uuid.UUID]:
        """
        Return the `QuerySet` of accessible folder IDs for a specific permission(`perm`) on a specific model(`model`).

        Example:
        ```
        def can_add_applied_control(user: User, applied_control: AppliedControl) -> bool:
            allowed_folder_ids = RoleAssignment.get_allowed_folder_ids(user, ModelPermission("add", AppliedControl))

            allowed_to_add = Folder.objects.filter(
                id=applied_control.folder.id,
                id__in=allowed_folder_ids,
            ).exists()
            return allowed_to_add
        ```

        If `base_folder` is specified, only descendant folder IDs of `base_folder` will be retained.

        If `base_folder` is specified AND the `focus_folder_id_var` context variable is set THEN:

        Both the `base_folder` and the `focused_folder` will compete to be the become the effective base folder (`effective_focused_folder`).

        In such case: `base_folder` will become the effective base folder ONLY IF `base_folder` is a descendant of `focused_folder`.
        Otherwise `focused_folder` will be the effective base folder.
        """

        user_role_assignments = RoleAssignment.get_role_assignments_from_permission(
            user, perm, model
        )

        flat_role_assignments = user_role_assignments.filter(is_recursive=False)
        # A "flat" `RoleAssignment` is a non-recursive `RoleAssignment`.
        recursive_role_assignments = user_role_assignments.filter(is_recursive=True)

        directly_accessible_folder_ids = user_role_assignments.values_list(
            "perimeter_folders__id", flat=True
        ).distinct()
        """
        The "direct folders" are the one stored in the `RoleAssignment.perimeter_folders` field.
        These folders have roles being directly assigned to them.

        In opposition to the indirect (recursive) folders which permission was granted due to permission on an ancestor folder.
        """

        direct_flat_folder_ids = flat_role_assignments.values_list(
            "perimeter_folders__id", flat=True
        ).distinct()
        # A "flat" `folder` (in this context) is a folder linked to a "flat" `RoleAssignment` (non-recursive).
        direct_recursive_folder_ids = recursive_role_assignments.values_list(
            "perimeter_folders__id", flat=True
        ).distinct()
        # A direct recursive folder, is a direct folder of a recursive `RoleAssignment`.

        focused_folder_id = focus_folder_id_var.get()

        focused_folder = (
            Folder.objects.filter(id=focused_folder_id).first()
            if focused_folder_id
            else None
        )

        effective_focused_folder = base_folder

        if focused_folder is not None:
            # We only keep `base_folder` as the `effective_focused_folder` if it's a descendant of `focused_folder`
            if base_folder is None or (focused_folder not in base_folder.ancestors):
                effective_focused_folder = focused_folder

        # Folder ID of the focused folder (when the user is in `Focus mode`)
        if effective_focused_folder is not None:
            return RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                effective_focused_folder,
                direct_flat_folder_ids,
                direct_recursive_folder_ids,
            )

        indirectly_accessible_folders = Folder.objects.filter(
            ancestors__in=direct_recursive_folder_ids
        )
        indirectly_accessible_folder_ids = indirectly_accessible_folders.values_list(
            "id", flat=True
        )

        accessible_folder_ids = directly_accessible_folder_ids.union(
            indirectly_accessible_folder_ids
        )
        return accessible_folder_ids

    @staticmethod
    def _get_actor_accessible_ids_by_perm(
        user: AbstractBaseUser | AnonymousUser, perm: NativePermissionPrefix
    ) -> QuerySet[uuid.UUID]:
        from core.models import Actor, Team
        from tprm.models import Entity

        user_folder_ids = RoleAssignment.get_allowed_folder_ids(user, perm, User)
        team__folder_ids = RoleAssignment.get_allowed_folder_ids(user, perm, Team)
        entity_folder_ids = RoleAssignment.get_allowed_folder_ids(user, perm, Entity)

        allowed_actors = Actor.objects.annotate(
            iam_folder_id=Case(
                When(user__isnull=False, then=F("user__folder_id")),
                When(team__isnull=False, then=F("team__folder_id")),
                default=F("entity__folder_id"),
            ),
        ).filter(
            Q(user__isnull=False, iam_folder_id__in=user_folder_ids)
            | Q(team__isnull=False, iam_folder_id__in=team__folder_ids)
            | Q(entity__isnull=False, iam_folder_id__in=entity_folder_ids)
        )

        allowed_actor_ids = allowed_actors.values_list("id", flat=True)
        return allowed_actor_ids

    @staticmethod
    def _get_actor_accessible_ids(
        user: AbstractBaseUser | AnonymousUser,
    ) -> tuple[QuerySet[uuid.UUID], QuerySet[uuid.UUID], QuerySet[uuid.UUID]]:
        return (
            RoleAssignment._get_actor_accessible_ids_by_perm(user, "view"),
            RoleAssignment._get_actor_accessible_ids_by_perm(user, "change"),
            RoleAssignment._get_actor_accessible_ids_by_perm(user, "delete"),
        )

    @staticmethod
    def _get_filtering_label_ids_by_perm(
        user: AbstractBaseUser | AnonymousUser, perm: NativePermissionPrefix
    ) -> QuerySet[uuid.UUID]:
        from core.models import FilteringLabel

        # If a user has the `perm` permission on any `Folder` for the `FilteringLabel` model.
        # Then we grant this permission over all the `FilteringLabel` of the DB.
        is_allowed = RoleAssignment.get_role_assignments_from_permission(
            user, perm, FilteringLabel
        ).exists()

        if is_allowed:
            return FilteringLabel.objects.values_list("id", flat=True)
        else:
            return FilteringLabel.objects.none()

    @staticmethod
    def _get_filtering_label_accessible_ids(
        user: AbstractBaseUser | AnonymousUser,
    ) -> tuple[QuerySet[uuid.UUID], QuerySet[uuid.UUID], QuerySet[uuid.UUID]]:
        return (
            RoleAssignment._get_filtering_label_ids_by_perm(user, "view"),
            RoleAssignment._get_filtering_label_ids_by_perm(user, "change"),
            RoleAssignment._get_filtering_label_ids_by_perm(user, "delete"),
        )

    @staticmethod
    def _get_permission_accessible_ids() -> tuple[
        QuerySet[uuid.UUID], QuerySet[uuid.UUID], QuerySet[uuid.UUID]
    ]:
        allowed_ids = (
            Permission.objects.filter(
                content_type__app_label__in=ALLOWED_PERMISSION_APPS
            )
            .exclude(content_type__model__in=IGNORED_PERMISSION_MODELS)
            .values_list("id", flat=True)
        )
        # No user (even admin) SHALL be able to change/delete `Permission` objects.
        _none = Permission.objects.none().values_list("id", flat=True)
        return (allowed_ids, _none, _none)

    @staticmethod
    def get_iam_folder_field(model: type[models.Model]) -> str:
        """
        Return the folder ID field with which the IAM perform permission checks on.

        Examples:
        ```
        assert get_iam_folder_field(Folder) == "id"
        assert get_iam_folder_field(AppliedControl) == "folder_id"
        assert get_iam_folder_field(RiskScenario) == "risk_assessment__folder_id"
        ```
        """
        if model is Folder:
            return "id"

        field_names = {f.name for f in model._meta.get_fields()}

        if "folder" in field_names:
            return "folder_id"

        IAM_SCOPE_FIELDS = [
            "risk_assessment",
            "entity",
            "provider_entity",
            "journey",
            "questionnaire_run",
            "agent_run",
        ]

        for field in IAM_SCOPE_FIELDS:
            if field in field_names:
                return f"{field}__folder_id"

        raise NotImplementedError("type not supported")

    @staticmethod
    def get_iam_folder_id(obj: models.Model) -> uuid.UUID:
        model = type(obj)
        iam_folder_field = RoleAssignment.get_iam_folder_field(model)

        if iam_folder_field == "id":
            return obj.id

        if iam_folder_field == "folder_id":
            return obj.folder_id

        scope_field = iam_folder_field.split("__", 1)[0]
        scope_obj = getattr(obj, scope_field)
        return scope_obj.folder_id

    @staticmethod
    def get_accessible_object_ids(
        folder: Folder,
        user: AbstractBaseUser | AnonymousUser,
        object_type: type[models.Model],
    ) -> Tuple[QuerySet[uuid.UUID], QuerySet[uuid.UUID], QuerySet[uuid.UUID]]:
        """
        Gets all objects of a specified type that a user can reach in a given folder
        Only accessible folders are considered
        Returns a triplet: (view_objects_list, change_object_list, delete_object_list)
        Assumes that object type follows Django conventions for permissions
        Also retrieve published objects in view
        """

        from core.models import Actor, FilteringLabel

        model = object_type

        if not getattr(user, "is_authenticated", False):
            _none = Folder.objects.none().values_list("id", flat=True)
            return (_none, _none, _none)

        if model is Permission:
            return RoleAssignment._get_permission_accessible_ids()

        if model is Actor:
            return RoleAssignment._get_actor_accessible_ids(user)

        if model is FilteringLabel:
            return RoleAssignment._get_filtering_label_accessible_ids(user)

        has_is_published_field = any(
            f.name == "is_published" for f in model._meta.get_fields()
        )

        result = []
        for perm in ["view", "change", "delete"]:
            allowed_folder_ids = RoleAssignment.get_allowed_folder_ids(
                user, perm, model, base_folder=folder
            )
            iam_folder_field = RoleAssignment.get_iam_folder_field(model)

            accessible_object_ids_query = Q(
                **{f"{iam_folder_field}__in": allowed_folder_ids}
            )

            if perm == "view" and has_is_published_field:
                ancestor_folder_ids = Folder.objects.filter(
                    descendants__in=allowed_folder_ids
                ).distinct()
                published_objects_query = Q(
                    **{f"{iam_folder_field}__in": ancestor_folder_ids},
                    is_published=True,
                )

                accessible_object_ids_query |= published_objects_query

            accessible_object_ids = model.objects.filter(
                accessible_object_ids_query
            ).values_list("id", flat=True)
            result.append(accessible_object_ids)

        return tuple(result)

    def is_user_assigned(self, user: User) -> bool:
        """Determines if a user is assigned to the role assignment"""
        if user == self.user:
            return True
        if self.user_group is None:
            return False
        return self.user_group in user.user_groups.all()

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

        role_assignments = RoleAssignment.get_role_assignments_from_user(user)
        has_role = role_assignments.filter(role_id=role.id).exists()

        return has_role

    @classmethod
    def get_permissions_per_folder(
        cls,
        principal: AbstractBaseUser | AnonymousUser | UserGroup,
        recursive: bool = False,
    ):
        """
        Get permissions grouped by folder ID, using caches.

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
