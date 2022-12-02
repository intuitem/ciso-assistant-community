from django import template

from asf_rm.settings import VERSION, BUILD, DEBUG

register = template.Library()

@register.simple_tag()
def mira_version():
    return VERSION

@register.simple_tag()
def mira_build():
    return f'{BUILD} (dev)' if DEBUG else BUILD

@register.filter('class')
def _class(obj):
    return obj.__class__.__name__ if obj else ''

@register.filter
def index(List, i):
    return List[int(i)]

@register.filter
def entry_num_array(List):
    return range(len(List))