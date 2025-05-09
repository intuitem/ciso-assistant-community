from django import template
from django.utils.safestring import mark_safe

from ciso_assistant.settings import VERSION, BUILD, DEBUG
from core.utils import COUNTRY_FLAGS, LANGUAGES
from core.models import RequirementAssessment
from core.helpers import color_css_class

register = template.Library()


@register.simple_tag()
def app_version():
    return VERSION


@register.simple_tag()
def app_build():
    return f"{BUILD} (dev)" if DEBUG else BUILD


@register.simple_tag()
def get_requirements(applied_control, compliance_assessment):
    return [
        str(req.requirement.display_short)
        for req in RequirementAssessment.objects.filter(
            compliance_assessment=compliance_assessment,
            applied_controls=applied_control.id,
        )
    ]


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


@register.filter(name="is_list")
def is_list(val):
    return isinstance(val, list)


@register.filter(name="is_string")
def is_string(val):
    return isinstance(val, str)


@register.filter(name="get_answers")
def get_answers(question, answers):
    if not answers:
        return None
    if isinstance(answers, list):
        return [get_answers(question, answer) for answer in answers]
    elif not answers.startswith("urn:"):
        return answers
    for choice in question["choices"]:
        if choice["urn"] == answers:
            return choice["value"]


@register.filter(name="get_item")
def get_item(dictionary, key):
    return dictionary.get(key)


@register.simple_tag
def bar_graph(assessments, ancestors, node=None):
    compliance_assessments_result = []
    candidates = [
        c
        for c in assessments.filter(requirement__assessable=True)
        if not node or c == node or node in ancestors.get(c, set())
    ]
    total = len(candidates)
    if total > 0:
        for st in RequirementAssessment.Result:
            count = len([c for c in candidates if c.result == st])
            compliance_assessments_result.append((st, round(count * 100 / total)))

    content = '<div class="flex bg-gray-300 rounded-full overflow-hidden h-4 w-2/3">'
    for result, percentage in reversed(compliance_assessments_result):
        if percentage > 0:
            color = f"bg-{color_css_class(result)}"
            if color == "bg-black":
                color += " text-white dark:bg-white dark:text-black"
            content += f"""
            <div class="flex flex-col justify-center overflow-hidden text-xs font-semibold text-center {color}" style="width:{percentage}%">
            """
            if result != "to_do":
                content += f"{percentage}%"
            content += "</div>"
    content += "</div>"
    return mark_safe(content)
