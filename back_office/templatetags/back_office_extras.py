from django import template

from asf_rm.settings import VERSION

register = template.Library()

@register.simple_tag()
def mira_version():
    return VERSION

@register.filter('class')
def _class(obj):
    return obj.__class__.__name__ if obj else ''
