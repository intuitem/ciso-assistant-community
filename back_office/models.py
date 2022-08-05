from django.db import models
from django.contrib.auth.models import Group, User
from django.utils.translation import gettext_lazy as _

from general.models import ProjectsGroup

class UserGroup(Group):
    pass

class Role(Group):
    pass

class RoleAssignment(models.Model):

    isUserGroup = models.BooleanField(_('is a User Group'),
        default=False,)
    domains = models.ManyToManyField(ProjectsGroup,verbose_name=_("Domain"))
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    userGroup = models.ForeignKey(UserGroup, null=True, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_("Role"))

    def __str__(self):
        return str(self.id)

    def has_domain_perm(self, perms, domain):
        if domain in self.domains.all() and perms in self.role.permissions.all():
            return True
        else:
            return False
    
    def has_perm(self, perms):
        if perms in self.role.permissions.all():
            return True
        else:
            return False
    
    def gabarit_perm(self):
        return True

# Creation of a role assignment (only add)
# Update of a role assignment = delete + create
# Delete of a role assignment (only remove)

# Add user to a usergroup (only add)
# Remove user from a usergroup (only remove)