from django import template

from asf_rm.settings import VERSION

register = template.Library()

@register.tag
def mira_version():
    return VERSION