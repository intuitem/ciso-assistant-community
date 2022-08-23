from django.db import models
from django.contrib.auth.models import Group, User
from django.utils.translation import gettext_lazy as _

class UserGroup(Group):
    
    def get_userGroups(user):
        l = []
        for userGroup in UserGroup.objects.all():
                if user in userGroup.user_set.all():
                    l.append(userGroup)
        return l

class Role(Group):
    pass

class RoleAssignment(models.Model):
    
    # isMainFolderVisible = models.BooleanField(_('top folder are visible'), default=True)
    # isSubFolderVisible = models.BooleanField(_('sub folders are visible'), default=False)
    isUserGroup = models.BooleanField(_('is a User Group'), default=False)
    folders = models.ManyToManyField("general.Folder",verbose_name=_("Domain"))
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    userGroup = models.ForeignKey(UserGroup, null=True, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_("Role"))

    def __str__(self):
        if self.isUserGroup:
            return "id=" + str(self.id) + ", folders: " + str(list(self.folders.values_list('name',flat=True))) + ", role: " + str(self.role.name) + ", user group: " + str(self.userGroup.name)
        else:
            return "id=" + str(self.id) + ", folders: " + str(list(self.folders.values_list('name',flat=True))) + ", role: " + str(self.role.name) + ", user: " + str(self.user.username)

    def is_access_allowed(user, perm, folder = None):
        if user.is_superuser:
            return True
        if not folder:
            for ra in user.roleassignment_set.all():
                if perm in ra.role.permissions.all():
                    return True
            for userGroup in UserGroup.get_userGroups(user):
                    for ra in userGroup.roleassignment_set.all():
                        if perm in ra.role.permissions.all():
                            return True
        else:
            for ra in user.roleassignment_set.all():
                if folder in ra.folders.all() and perm in ra.role.permissions.all():
                    return True
            for userGroup in UserGroup.get_userGroups(user):
                    for ra in userGroup.roleassignment_set.all():
                        if folder in ra.folders.all() and perm in ra.role.permissions.all():
                            return True
        return False

# Creation of a role assignment (only add)
# Update of a role assignment = delete + create
# Delete of a role assignment (only remove)

# Add user to a usergroup (only add)
# Remove user from a usergroup (only remove)