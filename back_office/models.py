from collections import defaultdict
from django.db import models
from django.contrib.auth.models import Group, User, Permission
from asf_rm import settings
from general.models import *
from django.utils.translation import gettext_lazy as _
from general.utils import *


class UserGroup(Group):
    folder = models.ForeignKey("general.Folder", verbose_name=_(
        "Domain"), on_delete=models.CASCADE, default=None)
    builtin = models.BooleanField(default=False)

    def __str__(self) -> str:
        if self.builtin:
            return f"{self.folder.name} - {BUILTIN_USERGROUP_CODENAMES.get(self.name)}"
        return self.name

    def get_user_groups(user):
        l = []
        for user_group in UserGroup.objects.all():
            if user in user_group.user_set.all():
                l.append(user_group)
        return l

    def get_manager_user_groups(manager):
        l = []
        folders = []
        for user_group in UserGroup.get_user_groups(manager):
            for ra in user_group.roleassignment_set.all():
                if ra.role.name == "Domain Manager":
                    for folder in ra.perimeter_folders.all():
                        folders.append(folder)
        for user_group in UserGroup.objects.all():
            if user_group.folder in folders:
                l.append(user_group)
        return l


class Role(Group):
    builtin = models.BooleanField(default=False)

    def __str__(self) -> str:
        if self.builtin:
            return f"{BUILTIN_ROLE_CODENAMES.get(self.name)}"
        return self.name


class RoleAssignment(models.Model):

    perimeter_folders = models.ManyToManyField(
        "general.Folder", verbose_name=_("Domain"), related_name='perimeter_folders')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    user_group = models.ForeignKey(
        UserGroup, null=True, on_delete=models.CASCADE)
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, verbose_name=_("Role"))
    is_recursive = models.BooleanField(
        _('sub folders are visible'), default=False)
    builtin = models.BooleanField(default=False)
    folder = models.ForeignKey("general.Folder", on_delete=models.CASCADE, verbose_name=_("Folder"))

    def __str__(self):
        if not self.user:
            return "id=" + str(self.id) + \
                ", folders: " + str(list(self.perimeter_folders.values_list('name', flat=True))) + \
                ", role: " + str(self.role.name) + \
                ", user group: " + str(self.user_group.name)
        else:
            return "id=" + str(self.id) + \
                ", folders: " + str(list(self.perimeter_folders.values_list('name', flat=True))) + \
                ", role: " + str(self.role.name) + \
                ", user: " + str(self.user.username)

    def is_access_allowed(user, perm, folder=None):
        """Determines if a user has specified permission on a specified folder
           Note: the None value for folder is a kludge for the time being, an existing folder should be specified
        """
        if user.is_superuser:
            return True
        for ra in RoleAssignment.get_role_assignments(user):
            if (not folder or folder in ra.perimeter_folders.all()) and perm in ra.role.permissions.all():
                return True
        return False

    def get_accessible_folders(folder, user, content_type):
        """Gets the list of folders with specified contentType that can be viewed by a user
           Returns the list of the ids of the matching folders"""
        folders_set=set()
        ref_permission = Permission.objects.get(codename = "view_folder")
        # first get all accessible folders, independently of contentType
        for ra in [x for x in RoleAssignment.get_role_assignments(user) if ref_permission in x.role.permissions.all()]:
            for f in ra.folders.all():
                folders_set.add(f)
                folders_set.update(f.sub_folders())
        # return filtered result
        return [x.id for x in folders_set if x.content_type == content_type]

    def get_accessible_objects(folder, user, object_type):
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
            for f in perimeter & set(ra.perimeter_folders.all()):
                for p in [p for p in permissions if p in ra_permissions]:
                    if p == permissions[0]:
                        folders_with_local_view.add(f)
                    target_folders = [f] + \
                        f.sub_folders() if ra.is_recursive else [f]
                    for object in [x for x in all_objects if folder_for_object[x] in target_folders]:
                        print(object)
                        if not (hasattr(object, "builtin") and object.builtin and p != permissions[0]):
                            permissions_per_object_id[object.id].add(p)

        if hasattr(object_type, "is_published"):
            for f in folders_with_local_view:
                parent_folders = f.get_parent_folders()
                for object in [x for x in all_objects if folder_for_object[x] in parent_folders and x.is_published]:
                    permissions_per_object_id[object.id].add(permissions[0])

        return (
            [x for x in permissions_per_object_id if permissions[0]
                in permissions_per_object_id[x]],
            [x for x in permissions_per_object_id if permissions[1]
                in permissions_per_object_id[x]],
            [x for x in permissions_per_object_id if permissions[2]
                in permissions_per_object_id[x]],
        )

    def is_user_assigned(self, user):
        """ Determines if a user is assigned to the role assignment"""
        return user == self.user or (self.user_group and self.user_group in UserGroup.get_user_groups(user))

    def get_role_assignments(user):
        """ get all role assignments attached to a user directly or indirectly"""
        assignments = list(user.roleassignment_set.all())
        for user_group in UserGroup.get_user_groups(user):
            assignments += list(user_group.roleassignment_set.all())
        return assignments


# Creation of a role assignment (only add)
# Update of a role assignment = delete + create
# Delete of a role assignment (only remove)

# Add user to a usergroup (only add)
# Remove user from a usergroup (only remove)
