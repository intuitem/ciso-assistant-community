from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _


from general.utils import *


class User(AbstractBaseUser):
    pass


class AbstractGroup(models.Model):
    name = models.CharField(_('name'), max_length=150, unique=False)
    builtin = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name


class Group(AbstractGroup):
    folder = models.ForeignKey("general.Folder", verbose_name=_(
        "Domain"), on_delete=models.CASCADE, default=None)

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    def __str__(self) -> str:
        if self.builtin:
            return f"{self.folder.name} - {BUILTIN_USERGROUP_CODENAMES.get(self.name)}"
        return self.name

    def get_user_groups(user):
        l = []
        for user_group in Group.objects.all():
            if user in user_group.user_set.all():
                l.append(user_group)
        return l

    def get_manager_user_groups(manager):
        l = []
        folders = []
        for user_group in Group.get_user_groups(manager):
            for ra in user_group.roleassignment_set.all():
                if ra.role.name == "BI-RL-DMA":
                    for folder in ra.perimeter_folders.all():
                        folders.append(folder)
        for user_group in Group.objects.all():
            if user_group.folder in folders:
                l.append(user_group)
        return l


class Role(AbstractGroup):
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('permissions'),
        blank=True,
    )

    def __str__(self) -> str:
        if self.builtin:
            return f"{BUILTIN_ROLE_CODENAMES.get(self.name)}"
        return self.name
        