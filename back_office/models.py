from django.db import models
from django.contrib.auth.models import Group, User
from django.utils.translation import gettext_lazy as _

from general.models import ProjectsGroup

class UserGroup(Group):
    pass

class Role(Group):
    pass

class RoleAssignment(models.Model):
    
    isUserGroup = models.BooleanField(_('is a User Group'), default=False,)
    domains = models.ManyToManyField(ProjectsGroup,verbose_name=_("Domain"))
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    userGroup = models.ForeignKey(UserGroup, null=True, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_("Role"))

    def __str__(self):
        if self.isUserGroup:
            return "id=" + str(self.id) + ", domains: " + str(list(self.domains.values_list('name',flat=True))) + ", role: " + str(self.role.name) + ", user group: " + str(self.userGroup.name)
        else:
            return "id=" + str(self.id) + ", domains: " + str(list(self.domains.values_list('name',flat=True))) + ", role: " + str(self.role.name) + ", user: " + str(self.user.username)

    def is_access_allowed(user, perm, domain = None):
        if user.is_superuser:
            return True
        else:
            if not domain:
                for ra in user.roleassignment_set.all():
                    if perm in ra.role.permissions.all():
                        return True
                for userGroup in UserGroup.objects.all():
                    if user in userGroup.user_set.all():
                        for ra in userGroup.roleassignment_set.all():
                            if perm in ra.role.permissions.all():
                                return True
            else:
                for ra in user.roleassignment_set.all():
                    if domain in ra.domains.all() and perm in ra.role.permissions.all():
                        return True
                for userGroup in UserGroup.objects.all():
                    if user in userGroup.user_set.all():
                        for ra in userGroup.roleassignment_set.all():
                            if domain in ra.domains.all() and perm in ra.role.permissions.all():
                                return True
        return False

# Creation of a role assignment (only add)
# Update of a role assignment = delete + create
# Delete of a role assignment (only remove)

# Add user to a usergroup (only add)
# Remove user from a usergroup (only remove)