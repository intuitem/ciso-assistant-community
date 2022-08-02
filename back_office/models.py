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
        return self.user.username + self.role

    # @classmethod
    # def create(self):
    #     if self.isUserGroup:
    #         self.userGroup