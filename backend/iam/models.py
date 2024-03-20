""" IAM model for CISO Assistant
    Inspired from Azure IAM model """

from collections import defaultdict
from typing import Any, List, Self, Tuple
import uuid
from django.utils import timezone
from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AnonymousUser, Permission
from django.utils.translation import gettext_lazy as _
from django.urls.base import reverse_lazy
from ciso_assistant import settings
from core.utils import (
    BUILTIN_USERGROUP_CODENAMES,
    BUILTIN_ROLE_CODENAMES,
)
from core.base_models import AbstractBaseModel, NameDescriptionMixin
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail, get_connection, EmailMessage
from django.core.validators import validate_email
from core.utils import RoleCodename, UserGroupCodename
from django.db.models.signals import post_save
from django.dispatch import receiver
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
from django.core.exceptions import ObjectDoesNotExist

import structlog

logger = structlog.get_logger(__name__)


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
    def get_root_folder() -> Self:
        """class function for general use"""
        return _get_root_folder()

    class ContentType(models.TextChoices):
        """content type for a folder"""

        ROOT = "GL", _("GLOBAL")
        DOMAIN = "DO", _("DOMAIN")

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

    fields_to_check = ["name"]

    class Meta:
        """for Model"""

        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")

    def __str__(self) -> str:
        return self.name.__str__()

    def sub_folders(self) -> List[Self]:
        """Return the list of subfolders"""

        def sub_folders_in(f, sub_folder_list):
            for sub_folder in f.folder_set.all():
                sub_folder_list.append(sub_folder)
                sub_folders_in(sub_folder, sub_folder_list)
            return sub_folder_list

        return sub_folders_in(self, [])

    def get_parent_folders(self) -> List[Self]:
        """Return the list of parent folders"""
        return (
            [self.parent_folder] + Folder.get_parent_folders(self.parent_folder)
            if self.parent_folder
            else []
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
        paths = [
            ["folder"],
            ["parent_folder"],
            ["project", "folder"],
            ["risk_assessment", "project", "folder"],
            ["risk_scenario", "risk_assessment", "project", "folder"],
        ]

        # Attempt to traverse each path until a valid folder is found or all paths are exhausted.
        for path in paths:
            folder = Folder._navigate_structure(obj, path)
            if folder is not None:
                return folder

        # If no folder is found after trying all paths, handle this case (e.g., return None or raise an error).
        return None


class FolderMixin(models.Model):
    """
    Add foreign key to Folder, defaults to root folder
    """

    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name="%(class)s_folder",
        default=Folder.get_root_folder,
    )

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
        return self.name

    def get_name_display(self) -> str:
        return self.name

    def get_localization_dict(self) -> dict:
        return {
            "folder": self.folder.name,
            "role": BUILTIN_USERGROUP_CODENAMES.get(self.name),
        }

    @staticmethod
    def get_user_groups(user):
        # pragma pylint: disable=no-member
        """get the list of user groups containing the user given in parameter"""
        user_group_list = []
        for user_group in UserGroup.objects.all():
            if user in user_group.user_set.all():
                user_group_list.append(user_group)
        return user_group_list


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, mailing=True, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """

        validate_email(email)
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=extra_fields.get("first_name", ""),
            last_name=extra_fields.get("last_name", ""),
            is_superuser=extra_fields.get("is_superuser", False),
            is_active=extra_fields.get("is_active", True),
            folder=_get_root_folder(),
        )
        user.user_groups.set(extra_fields.get("user_groups", []))
        user.password = make_password(password if password else str(uuid.uuid4()))
        user.save(using=self._db)

        logger.info("user created sucessfully", user=user)

        if mailing:
            try:
                user.mailing(
                    email_template_name="registration/first_connexion_email.html",
                    subject=_("Welcome to Ciso Assistant!"),
                )
            except Exception as exception:
                print(f"sending email to {email} failed")
                raise exception
        return user

    def create_user(self, email, password=None, **extra_fields):
        logger.info("creating user", email=email)
        extra_fields.setdefault("is_superuser", False)
        if not (EMAIL_HOST or EMAIL_HOST_RESCUE):
            extra_fields.setdefault("mailing", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        logger.info("creating superuser", email=email)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        extra_fields.setdefault(
            "mailing", not (password) and (EMAIL_HOST or EMAIL_HOST_RESCUE)
        )
        superuser = self._create_user(email, password, **extra_fields)
        UserGroup.objects.get(name="BI-UG-ADM").user_set.add(superuser)
        return superuser


class User(AbstractBaseUser, AbstractBaseModel, FolderMixin):
    """a user is a principal corresponding to a human"""

    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    email = models.CharField(max_length=100, unique=True)
    first_login = models.BooleanField(default=True)
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
    objects = UserManager()

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
        try:
            return self.first_name if self.first_name else self.email.split("@")[0]
        except:
            return ""

    def mailing(self, email_template_name, subject, pk=False):
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
            logger.info("email sent", recipient=self.email, subject=subject)
        except Exception as primary_exception:
            logger.error(
                "primary mailer failure, trying rescue",
                recipient=self.email,
                subject=subject,
                error=primary_exception,
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
                    logger.info("email sent", recipient=self.email, subject=subject)
                except Exception as rescue_exception:
                    logger.error(
                        "rescue mailer failure",
                        recipient=self.email,
                        subject=subject,
                        error=rescue_exception,
                        email_host=EMAIL_HOST_RESCUE,
                        email_port=EMAIL_PORT_RESCUE,
                        email_username=EMAIL_HOST_USER_RESCUE,
                        email_use_tls=EMAIL_USE_TLS_RESCUE,
                    )
                    raise rescue_exception
            else:
                raise primary_exception

    def get_user_groups(self):
        # pragma pylint: disable=no-member
        """get the list of user groups containing the user"""
        user_group_list = []
        for user_group in UserGroup.objects.all():
            if self in user_group.user_set.all():
                user_group_list.append((user_group.__str__(), user_group.builtin))
        return user_group_list

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


class Role(NameDescriptionMixin, FolderMixin):
    """A role is a list of permissions"""

    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("permissions"),
        blank=True,
    )
    builtin = models.BooleanField(default=False)

    def __str__(self) -> str:
        if self.builtin:
            return f"{BUILTIN_ROLE_CODENAMES.get(self.name)}"
        return self.name


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
        Determines if a user has specified permission on a specified folder
        """
        for ra in RoleAssignment.get_role_assignments(user):
            f = folder
            while f is not None:
                if (
                    f in ra.perimeter_folders.all()
                    and perm in ra.role.permissions.all()
                ):
                    return True
                f = f.parent_folder
        return False

    @staticmethod
    def get_accessible_folders(
        folder: Folder,
        user: User,
        content_type: Folder.ContentType,
        codename: str = "view_folder",
    ) -> list[Folder]:
        """Gets the list of folders with specified contentType that can be viewed by a user from a given folder
        If the contentType is not specified, returns all accessible folders
        Returns the list of the ids of the matching folders
        If permission is specified, returns accessible folders which can be altered with this specific permission
        """
        folders_set = set()
        ref_permission = Permission.objects.get(codename=codename)
        # first get all accessible folders, independently of contentType
        for ra in [
            x
            for x in RoleAssignment.get_role_assignments(user)
            if (
                (
                    Permission.objects.get(codename="view_folder")
                    in x.role.permissions.all()
                )
                and (ref_permission in x.role.permissions.all())
            )
        ]:
            for f in ra.perimeter_folders.all():
                folders_set.add(f)
                folders_set.update(f.sub_folders())
        # calculate perimeter
        perimeter = set()
        perimeter.add(folder)
        perimeter.update(folder.sub_folders())
        # return filtered result
        return [
            x.id
            for x in folders_set
            if (x.content_type == content_type if content_type else True)
            and x in perimeter
        ]

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
        class_name = object_type.__name__.lower()
        permissions = [
            Permission.objects.get(codename="view_" + class_name),
            Permission.objects.get(codename="change_" + class_name),
            Permission.objects.get(codename="delete_" + class_name),
        ]

        folders_with_local_view = set()
        permissions_per_object_id = defaultdict(set)
        ref_permission = Permission.objects.get(codename="view_folder")
        all_objects = (
            object_type.objects.select_related("folder")
            if hasattr(object_type, "folder")
            else object_type.objects.all()
        )
        folder_for_object = {x: Folder.get_folder(x) for x in all_objects}
        perimeter = set()
        perimeter.add(folder)
        perimeter.update(folder.sub_folders())
        for ra in [
            x
            for x in RoleAssignment.get_role_assignments(user)
            if ref_permission in x.role.permissions.all()
        ]:
            ra_permissions = ra.role.permissions.all()
            for my_folder in perimeter & set(ra.perimeter_folders.all()):
                target_folders = (
                    [my_folder] + my_folder.sub_folders()
                    if ra.is_recursive
                    else [my_folder]
                )
                for p in [p for p in permissions if p in ra_permissions]:
                    if p == permissions[0]:
                        folders_with_local_view.add(my_folder)
                    for object in [
                        x for x in all_objects if folder_for_object[x] in target_folders
                    ]:
                        # builtins objects cannot be edited or deleted
                        if not (
                            hasattr(object, "builtin")
                            and object.builtin
                            and p != permissions[0]
                        ):
                            permissions_per_object_id[object.id].add(p)

        if hasattr(object_type, "is_published"):
            for my_folder in folders_with_local_view:
                target_folders = []
                my_folder2 = my_folder
                while my_folder2:
                    if my_folder2 != my_folder:
                        target_folders.append(my_folder2)
                    my_folder2 = my_folder2.parent_folder
                for object in [
                    x
                    for x in all_objects
                    if folder_for_object[x] in target_folders and x.is_published
                ]:
                    permissions_per_object_id[object.id].add(permissions[0])

        return (
            [
                x
                for x in permissions_per_object_id
                if permissions[0] in permissions_per_object_id[x]
            ],
            [
                x
                for x in permissions_per_object_id
                if permissions[1] in permissions_per_object_id[x]
            ],
            [
                x
                for x in permissions_per_object_id
                if permissions[2] in permissions_per_object_id[x]
            ],
        )

    def is_user_assigned(self, user) -> bool:
        """Determines if a user is assigned to the role assignment"""
        return user == self.user or (
            self.user_group and self.user_group in UserGroup.get_user_groups(user)
        )

    @staticmethod
    def get_role_assignments(user):
        """get all role assignments attached to a user directly or indirectly"""
        assignments = list(user.roleassignment_set.all())
        for user_group in UserGroup.get_user_groups(user):
            assignments += list(user_group.roleassignment_set.all())
        return assignments

    @staticmethod
    def get_permissions(user: AbstractBaseUser | AnonymousUser):
        """get all permissions attached to a user directly or indirectly"""
        permissions = {}
        for ra in RoleAssignment.get_role_assignments(user):
            for p in ra.role.permissions.all():
                permission_dict = {p.codename: {"str": str(p)}}
                permissions.update(permission_dict)

        return permissions

    @staticmethod
    def has_role(user: AbstractBaseUser | AnonymousUser, role: Role):
        """
        Determines if a user has a specific role.
        """
        for ra in RoleAssignment.get_role_assignments(user):
            if ra.role == role:
                return True
        return False
