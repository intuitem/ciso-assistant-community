from collections import defaultdict
from django.db import models
from django.contrib.auth.models import Group, User, Permission
from general.models import *
from django.utils.translation import gettext_lazy as _

class UserGroup(Group):
    
    folder = models.ForeignKey("general.Folder",verbose_name=_("Domain"), on_delete=models.CASCADE, default=None)
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
                if  ra.role.name == "Domain Manager":
                    for folder in ra.folders.all():
                        folders.append(folder)
        for user_group in UserGroup.objects.all():
            if user_group.folder in folders:
                l.append(user_group)
        return l

class Role(Group):
    pass

class RoleAssignment(models.Model):
    
    folders = models.ManyToManyField("general.Folder",verbose_name=_("Domain"))
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    user_group = models.ForeignKey(UserGroup, null=True, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_("Role"))
    is_recursive = models.BooleanField(_('sub folders are visible'), default=False)
    # todo: add folder like any object, rename folders to perimeter_folders

    def __str__(self):
        if not self.user: 
            return "id=" + str(self.id) + \
                ", folders: " + str(list(self.folders.values_list('name',flat=True))) + \
                ", role: " + str(self.role.name) + \
                ", user group: " + str(self.user_group.name)
        else:
            return "id=" + str(self.id) + \
                ", folders: " + str(list(self.folders.values_list('name',flat=True))) + \
                ", role: " + str(self.role.name) + \
                ", user: " + str(self.user.username)

    def is_access_allowed(user, perm, folder = None):
        """Determines if a user has specified permission on a specified folder
           Note: the None value for folder is a kludge for the time being, an existing folder should be specified
        """
        if user.is_superuser:
            return True
        for ra in RoleAssignment.get_role_assignments(user):
            if (not folder or folder in ra.folders.all()) and perm in ra.role.permissions.all():
                return True
        return False

    def get_accessible_folders(folder, user, content_type):
        """Gets the list of folders with specified contentType that can be viewed by a user"""
        folders_set=set()
        ref_permission = Permission.objects.get(codename = "view_folder")
        # first get all accessible folders, independently of contentType
        for ra in [x for x in RoleAssignment.get_role_assignments(user) if ref_permission in x.role.permissions.all()]:
            for f in ra.folders.all():
                folders_set.add(f)
                folders_set.update(f.sub_folders())
        # return filtered result
        return [x for x in folders_set if x.content_type == content_type]


    def get_accessible_objects(folder, user, object_type):
        """ Gets all objects of a specified type that a user can reach in a given folder
            Only accessible folders are considered
            Returns a list containing following elements: (object, is_view, is_change, is_delete)
            Assumes that ojbect type follows Dhango conventions for permissions
        """
        class_name = object_type.__name__.lower()
        permissions = [
                Permission.objects.get(codename="view_" + class_name), 
                Permission.objects.get(codename="change_" + class_name), 
                Permission.objects.get(codename="delete_" + class_name)
        ]

        permissions_per_object = defaultdict(set)
        ref_permission = Permission.objects.get(codename = "view_folder")
        all_objects = object_type.objects.all()
        perimeter = set()
        perimeter.add(folder)
        perimeter.update(folder.sub_folders())
        for ra in [x for x in RoleAssignment.get_role_assignments(user) if ref_permission in x.role.permissions.all()]:
            ra_permissions = ra.role.permissions.all()
            for f in perimeter & set(ra.folders.all()):
                for p in [p for p in permissions if p in ra_permissions]:
                    target_folders = [f] + f.sub_folders() if ra.is_recursive else [f]
                    for object in [x for x in all_objects if Folder.get_folder(x) in target_folders]:
                        permissions_per_object[object].add(p)
        return [(x, permissions[0] in permissions_per_object[x], permissions[1] in permissions_per_object[x],  permissions[2] in permissions_per_object[x]) for x in permissions_per_object]


    def is_user_assigned(self, user):
        """ Determines if a user is assigned to the role assignment"""
        return user == self.user or ( self.user_group and self.user_group in UserGroup.get_user_groups(user)) 

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