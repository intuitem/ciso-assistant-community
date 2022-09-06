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
    
    isMainFolderVisible = models.BooleanField(_('top folder are visible'), default=True)
    isSubFolderVisible = models.BooleanField(_('sub folders are visible'), default=False)
    isUserGroup = models.BooleanField(_('is a User Group'), default=False)
    folders = models.ManyToManyField("general.Folder",verbose_name=_("Domain"))
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    user_group = models.ForeignKey(UserGroup, null=True, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_("Role"))

    def __str__(self):
        if self.isUserGroup:
            return "id=" + str(self.id) + ", folders: " + str(list(self.folders.values_list('name',flat=True))) + ", role: " + str(self.role.name) + ", user group: " + str(self.user_group.name)
        else:
            return "id=" + str(self.id) + ", folders: " + str(list(self.folders.values_list('name',flat=True))) + ", role: " + str(self.role.name) + ", user: " + str(self.user.username)

    def is_access_allowed(user, perm, folder = None):
        if user.is_superuser:
            return True
        if not folder:
            for ra in user.roleassignment_set.all():
                if perm in ra.role.permissions.all():
                    return True
            for user_group in UserGroup.get_user_groups(user):
                    for ra in user_group.roleassignment_set.all():
                        if perm in ra.role.permissions.all():
                            return True
        else:
            for ra in user.roleassignment_set.all():
                if folder in ra.folders.all() and perm in ra.role.permissions.all():
                    return True
            for user_group in UserGroup.get_user_groups(user):
                    for ra in user_group.roleassignment_set.all():
                        if folder in ra.folders.all() and perm in ra.role.permissions.all():
                            return True
        return False

    def get_accessible_folders(folder, user, contentType):
        folders_list= list()
        for ra in user.roleassignment_set.all():
            for scope in ra.folders.all():
                if scope.content_type == contentType and scope.parent_folder == folder and Permission.objects.get(codename = "view_folder") in ra.role.permissions.all():
                    folders_list.append(scope)
                elif scope.content_type == Folder.ContentType.ROOT and Permission.objects.get(codename = "view_folder"):
                    return True
        for user_group in UserGroup.get_user_groups(user):
            for ra in user_group.roleassignment_set.all():
                for scope in ra.folders.all():
                    if scope.content_type == contentType and scope.parent_folder == folder and Permission.objects.get(codename = "view_folder") in ra.role.permissions.all():
                        folders_list.append(scope)
                    elif scope.content_type == Folder.ContentType.ROOT and Permission.objects.get(codename = "view_folder"):
                        return True
        return folders_list

    def get_accessible_objects(folder, user, object_type):     
        permissions_per_type = {
            Project: {
                Permission.objects.get(codename="view_project"), 
                Permission.objects.get(codename="change_project"), 
                Permission.objects.get(codename="delete_project")
            }
        }

        def helper_main(folder, permissions_per_object):
            for ra in [x for x in folder.roleassignment_set.all() if x.is_user_assigned(user) and x.isMainFolderVisible]:
                all_permissions = ra.role.permissions.all()
                for object in [x for x in object_type.objects.all() if x.folder == folder]:
                    for p in permissions_per_type[object_type] & set(all_permissions):
                        permissions_per_object[object].add(p)

        permissions_per_object = defaultdict(set)
        helper_main(folder, permissions_per_object)
        for x in folder.sub_folders():
            helper_main(x, permissions_per_object)
        print(permissions_per_object)
        # for sub_folder in folder.folder_set.all():

    def is_user_assigned(self, user):
        return user == self.user or ( self.user_group and self.user_group in UserGroup.get_user_groups(user)) 

# Creation of a role assignment (only add)
# Update of a role assignment = delete + create
# Delete of a role assignment (only remove)

# Add user to a usergroup (only add)
# Remove user from a usergroup (only remove)