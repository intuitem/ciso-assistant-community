""" IAM model for MIRA
    Inspired from Azure IAM model """

from collections import defaultdict
from typing import Any, Tuple
import uuid
from django.utils import timezone
from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _
from django.urls.base import reverse_lazy
from asf_rm import settings
from core.utils import BUILTIN_USERGROUP_CODENAMES, BUILTIN_ROLE_CODENAMES
from core.base_models import AbstractBaseModel
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail
from asf_rm.settings import MIRA_URL

class UserGroup(models.Model):
    """ UserGroup objects contain users and can be used as principals in role assignments """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    folder = models.ForeignKey("Folder", verbose_name=_(
        "Domain"), on_delete=models.CASCADE, default=None)
    name = models.CharField(_('name'), max_length=150, unique=False)
    builtin = models.BooleanField(default=False)

    class Meta:
        """ for Model """
        verbose_name = _('user group')
        verbose_name_plural = _('user groups')

    def __str__(self) -> str:
        if self.builtin:
            return f"{self.folder.name} - {BUILTIN_USERGROUP_CODENAMES.get(self.name)}"
        return self.name

    @staticmethod
    def get_user_groups(user):
        # pragma pylint: disable=no-member
        """ get the list of user groups containing the user given in parameter """
        user_group_list = []
        for user_group in UserGroup.objects.all():
            if user in user_group.user_set.all():
                user_group_list.append(user_group)
        return user_group_list


class Role(models.Model):
    """ A role is a list of permissions """
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('permissions'),
        blank=True,
    )
    name = models.CharField(_('name'), max_length=150, unique=False)
    builtin = models.BooleanField(default=False)

    def __str__(self) -> str:
        if self.builtin:
            return f"{BUILTIN_ROLE_CODENAMES.get(self.name)}"
        return self.name


class Folder(AbstractBaseModel):
    """ A folder is a container for other folders or any object
        Folders are organized in a tree structure, with a single root folder
        Folders are the base perimeter for role assignments
        """
    class ContentType(models.TextChoices):
        """ content type for a folder """
        ROOT = "GL", _("GLOBAL")
        DOMAIN = "DO", _("DOMAIN")
    content_type = models.CharField(
        max_length=2, choices=ContentType.choices, default=ContentType.DOMAIN)
    parent_folder = models.ForeignKey(
        "self", null=True, on_delete=models.CASCADE, verbose_name=_("parent folder"))
    builtin = models.BooleanField(default=False)
    hide_public_asset = models.BooleanField(default=False)
    hide_public_matrix = models.BooleanField(default=False)
    hide_public_threat = models.BooleanField(default=False)
    hide_public_security_function = models.BooleanField(default=False)

    class Meta:
        """ for Model """
        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")

    def __str__(self) -> str:
        return self.name.__str__()

    def sub_folders(self) -> 'Self':  # type annotation Self to come in Python 3.11
        """Return the list of subfolders"""
        def sub_folders_in(f, sub_folder_list):
            for sub_folder in f.folder_set.all():
                sub_folder_list.append(sub_folder)
                sub_folders_in(sub_folder, sub_folder_list)
            return sub_folder_list
        return sub_folders_in(self, [])

    # type annotation Self to come in Python 3.11
    def get_parent_folders(self) -> 'Self':
        """Return the list of parent folders"""
        return [self.parent_folder] + Folder.get_parent_folders(self.parent_folder) if self.parent_folder else []

    @staticmethod
    def get_folder(obj: Any) -> 'Self':  # type annotation Self to come in Python 3.11
        """Return the folder of an object"""
        # todo: add a folder attribute to all objects to avoid introspection
        if hasattr(obj, 'folder'):
            return obj.folder
        if hasattr(obj, 'parent_folder'):
            return obj.parent_folder
        if hasattr(obj, 'project'):
            return obj.project.folder
        if hasattr(obj, 'analysis'):
            return obj.analysis.project.folder
        if hasattr(obj, 'risk_scenario'):
            return obj.risk_scenario.analysis.project.folder


class FolderMixin(models.Model):
    """
    Add foreign key to Folder
    """
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='%(class)s_folder')

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """

        if not email:
            raise ValueError("The email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.password = make_password(password)
        else:
            user.password = make_password(str(uuid.uuid4()))
            try:
                user.mailing(email_template_name="registration/first_connexion_email.txt", subject=_("First Connexion"))
            except Exception as exception:
                user.save(using=self._db)
                raise exception
        user.save(using=self._db)
        return user
 
    def create_user(self, email, password=None, **extra_fields):
        print("Creating user for", email)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        print("Creating superuser for", email)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    """ a user is a principal corresponding to a human """
    try:
        id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
        last_name = models.CharField(_('last name'), max_length=150, blank=True)
        first_name = models.CharField(_('first name'), max_length=150, blank=True)
        email = models.CharField(max_length=100, unique=True)
        last_five_logins = models.JSONField(default=list) # NOTE: think about this functionnality because now it's only used to know the first connection
        is_active = models.BooleanField(
            _('active'),
            default=True,
            help_text=_(
                'Designates whether this user should be treated as active. '
                'Unselect this instead of deleting accounts.'
            ),
        )
        date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
        is_superuser = models.BooleanField(
            _('superuser status'),
            default=False,
            help_text=_(
                'Designates that this user has all permissions without explicitly assigning them.'
            ),
        )
        user_groups = models.ManyToManyField(
            UserGroup,
            verbose_name=_('user groups'),
            blank=True,
            help_text=_(
                'The user groups this user belongs to. A user will get all permissions '
                'granted to each of their user groups.'
            ),
            related_name="user_set",
            related_query_name="user",
        )
        objects = UserManager()
    except:
        print("Exception kludge")

    # USERNAME_FIELD is used as the unique identifier for the user
    # and is required by Django to be set to a non-empty value.
    # See https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#django.contrib.auth.models.CustomUser.USERNAME_FIELD
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        """ for Model """
        verbose_name = _('user')
        verbose_name_plural = _('users')
#        swappable = 'AUTH_USER_MODEL'

    def get_full_name(self) -> str:
        """get user's full name (i.e. first_name + last_name)"""
        try:
            full_name = f'{self.first_name} {self.last_name}'
            return full_name.strip()
        except:
            return ""
        
    def get_short_name(self) -> str:
        """get user's short name (i.e. first_name or email before @))"""
        try:
            return self.first_name if self.first_name else self.email.split('@')[0]
        except:
            return ""
        
    def update_last_login_list(self): # NOTE: think about this functionnality because now it's only used to know the first connection
        """
        Adds the date and time of the user's last login to the list
        last_five_logins and keeps only the last 5 items.
        """
        self.last_five_logins.append(str(self.last_login))
        self.last_five_logins = self.last_five_logins[-5:]
        self.save()
    
    def mailing(self, email_template_name, subject, pk=False):
        """
        Sending a mail to a user for password resetting or creation
        """
        header = {
                    "email": self.email,
                    'root_url': MIRA_URL,
                    "uid": urlsafe_base64_encode(force_bytes(self.pk)),
                    "user": self,
                    'token': default_token_generator.make_token(self),
                    'protocol': 'https',
                    'pk': str(pk) if pk else None
                }
        email = render_to_string(email_template_name, header)
        send_mail(subject, email, None, [self.email], fail_silently=False)

    @property
    def edit_url(self) -> str:
        """get the edit url of the user"""
        return reverse_lazy(f"{self.__class__.__name__.lower()}-update", args=[self.id])

    @property
    def username(self):
        return self.email
    
    @username.setter
    def set_username(self, username):
        self.email = username


class RoleAssignment(models.Model):
    """ fundamental class for MIRA RBAC model, similar to Azure IAM model """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    perimeter_folders = models.ManyToManyField(
        "Folder", verbose_name=_("Domain"), related_name='perimeter_folders')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True, on_delete=models.CASCADE)
    user_group = models.ForeignKey(
        UserGroup, null=True, on_delete=models.CASCADE)
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, verbose_name=_("Role"))
    is_recursive = models.BooleanField(
        _('sub folders are visible'), default=False)
    builtin = models.BooleanField(default=False)
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, verbose_name=_("Folder"))

    def __str__(self) -> str:
        # pragma pylint: disable=no-member
        return "id=" + str(self.id) + \
            ", folders: " + str(list(self.perimeter_folders.values_list('name', flat=True))) + \
            ", role: " + str(self.role.name) + \
            ", user: " + (str(self.user.email) if self.user else "/") + \
            ", user group: " + (str(self.user_group.name)
                                if self.user_group else "/")

    @staticmethod
    def is_access_allowed(user: User, perm: Permission, folder: Folder = None) -> bool:
        """Determines if a user has specified permission on a specified folder
           Note: the None value for folder is a kludge for the time being, an existing folder should be specified
        """
        for ra in RoleAssignment.get_role_assignments(user):
            if (not folder or folder in ra.perimeter_folders.all() or folder.parent_folder in ra.perimeter_folders.all()) and perm in ra.role.permissions.all():
                return True
        return False

    @staticmethod
    def get_accessible_folders(folder: Folder, user: User, content_type: Folder.ContentType, codename: str="view_folder") -> 'list[Folder]':
        """Gets the list of folders with specified contentType that can be viewed by a user from a given folder
           Returns the list of the ids of the matching folders
           If permission is specified, returns accessible folders which can be altered with this specific permission"""
        folders_set = set()
        ref_permission = Permission.objects.get(codename=codename)
        # first get all accessible folders, independently of contentType
        for ra in [x for x in RoleAssignment.get_role_assignments(user) if ((Permission.objects.get(codename="view_folder") in x.role.permissions.all()) and (ref_permission in x.role.permissions.all()))]:
            for f in ra.perimeter_folders.all():
                folders_set.add(f)
                folders_set.update(f.sub_folders())
        # calculate perimeter
        perimeter = set()
        perimeter.add(folder)
        perimeter.update(folder.sub_folders())
        # return filtered result
        return [x.id for x in folders_set if x.content_type == content_type and x in perimeter]

    @staticmethod
    def get_accessible_object_ids(folder: Folder, user: User, object_type: Any) -> Tuple['list[Any]', 'list[Any]', 'list[Any]']:
        """ Gets all objects of a specified type that a user can reach in a given folder
            Only accessible folders are considered
            Returns a triplet: (view_objects_list, change_object_list, delete_object_list)
            Assumes that object type follows Django conventions for permissions
            Also retrieve published objects in view
        """
        class_name = object_type.__name__.lower()
        permissions = [
            Permission.objects.get(codename="view_" + class_name),
            Permission.objects.get(codename="change_" + class_name),
            Permission.objects.get(codename="delete_" + class_name)
        ]

        folders_with_local_view = set()
        permissions_per_object_id = defaultdict(set)
        ref_permission = Permission.objects.get(codename="view_folder")
        all_objects = object_type.objects.all()
        folder_for_object = {x: Folder.get_folder(x) for x in all_objects}
        perimeter = set()
        perimeter.add(folder)
        perimeter.update(folder.sub_folders())
        for ra in [x for x in RoleAssignment.get_role_assignments(user) if ref_permission in x.role.permissions.all()]:
            ra_permissions = ra.role.permissions.all()
            for my_folder in perimeter & set(ra.perimeter_folders.all()):
                target_folders = [my_folder] + \
                    my_folder.sub_folders() if ra.is_recursive else [my_folder]
                for p in [p for p in permissions if p in ra_permissions]:
                    if p == permissions[0]:
                        folders_with_local_view.add(my_folder)
                    for object in [x for x in all_objects if folder_for_object[x] in target_folders]:
                        # builtins objects cannot be edited or deleted
                        if not (hasattr(object, "builtin") and object.builtin and p != permissions[0]):
                            permissions_per_object_id[object.id].add(p)

        if hasattr(object_type, "is_published"):
            for my_folder in folders_with_local_view:
                target_folders = []
                my_folder2 = my_folder
                while my_folder2 and not getattr(my_folder2, f"block_published_{class_name}", False):
                    if my_folder2 != my_folder:
                        target_folders.append(my_folder2)
                    my_folder2 = my_folder2.parent_folder
                for object in [x for x in all_objects if folder_for_object[x] in target_folders and x.is_published]:
                    permissions_per_object_id[object.id].add(permissions[0])

        return (
            [x for x in permissions_per_object_id if permissions[0]
                in permissions_per_object_id[x]],
            [x for x in permissions_per_object_id if permissions[1]
                in permissions_per_object_id[x]],
            [x for x in permissions_per_object_id if permissions[2]
                in permissions_per_object_id[x]],
        )

    def is_user_assigned(self, user) -> bool:
        """ Determines if a user is assigned to the role assignment"""
        return user == self.user or (self.user_group and self.user_group in UserGroup.get_user_groups(user))

    @staticmethod
    def get_role_assignments(user):
        """ get all role assignments attached to a user directly or indirectly"""
        assignments = list(user.roleassignment_set.all())
        for user_group in UserGroup.get_user_groups(user):
            assignments += list(user_group.roleassignment_set.all())
        return assignments
    
    def has_permission(user, codename):
        """ Determines if a user has a specific permission """
        for ra in RoleAssignment.get_role_assignments(user):
            for perm in ra.role.permissions.all():
                if perm.codename == codename:
                    return True
        return False
