from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from .models import GroupExtra
from django.forms import models
from django.utils.translation import gettext_lazy as _


# todo: remove useless constructs or comment them

class MyInline(models.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(MyInline, self).__init__(*args, **kwargs)
        self.can_delete = False


class GroupInline(admin.StackedInline):
    model = GroupExtra
    formset = MyInline

    verbose_name = _('Portal access and Extra settings')
    verbose_name_plural = _('Portal access and Extra settings')
    extra = 1
    max_num = 1
    can_delete = False


class GroupAdmin(BaseGroupAdmin):
    inlines = (GroupInline, )


# Re-register GroupAdmin
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)