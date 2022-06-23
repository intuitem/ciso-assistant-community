from django import template

register = template.Library()

@register.filter('class')
def _class(obj):
    return obj.__class__.__name__ if obj else ''
