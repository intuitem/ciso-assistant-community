from django import template

from ciso_assistant.settings import VERSION, BUILD, DEBUG
from core.utils import COUNTRY_FLAGS, LANGUAGES
from core.models import RequirementAssessment

register = template.Library()


@register.simple_tag()
def app_version():
    return VERSION


@register.simple_tag()
def app_build():
    return f"{BUILD} (dev)" if DEBUG else BUILD

@register.simple_tag()
def get_requirements_count(applied_control, compliance_assessment):
    return RequirementAssessment.objects.filter(
                        compliance_assessment=compliance_assessment
                    ).filter(applied_controls=applied_control).count()


@register.filter("class")
def _class(obj):
    return obj.__class__.__name__ if obj else ""


@register.filter
def index(List, i):
    return List[int(i)]


@register.filter
def entry_num_array(List):
    return range(len(List))


@register.filter("country_flag")
def country_flag(country_code):
    return COUNTRY_FLAGS.get(country_code, "🌐")


@register.filter("language_name")
def country_name(country_code):
    return LANGUAGES.get(country_code, "Unknown")


@register.filter(name="isinstance")
def isinstance_filter(val, instance_type):
    return isinstance(val, eval(instance_type))
