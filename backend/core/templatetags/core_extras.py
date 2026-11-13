import os
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from django.conf import settings
from core.utils import COUNTRY_FLAGS, LANGUAGES
from core.models import RequirementAssessment
from core.markdown_utils import render_safe_markdown

register = template.Library()


@register.filter(name="render_markdown")
def render_markdown(text: str | None) -> str:
    # render_safe_markdown escapes raw HTML and keeps only http(s) links
    return mark_safe(render_safe_markdown(text))  # nosec B308 B703


@register.simple_tag()
def app_version():
    return settings.VERSION


@register.simple_tag()
def app_build():
    return f"{settings.BUILD} (dev)" if settings.DEBUG else settings.BUILD


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
    for choice in question.get("choices", []):
        if choice["urn"] == answers:
            return choice["value"]


@register.filter(name="get_item")
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter(name="basename")
def basename_filter(file_path):
    """Extract the basename from a file path."""
    if not file_path:
        return ""
    return os.path.basename(str(file_path))


RESULT_BAR_ORDER = (
    RequirementAssessment.Result.COMPLIANT,
    RequirementAssessment.Result.PARTIALLY_COMPLIANT,
    RequirementAssessment.Result.NON_COMPLIANT,
    RequirementAssessment.Result.NOT_ASSESSED,
    RequirementAssessment.Result.NOT_APPLICABLE,
)


@register.simple_tag
def bar_graph(assessments, ancestors, node=None, legend=False):
    candidates = [
        c
        for c in assessments.filter(requirement__assessable=True)
        if not node or c == node or node in ancestors.get(c, set())
    ]
    total = len(candidates)
    segments = []
    if total > 0:
        for result in RESULT_BAR_ORDER:
            count = len([c for c in candidates if c.result == result])
            if count > 0:
                width = count * 100 / total
                percentage = f"{round(width)}%" if width >= 0.5 else "<1%"
                segments.append(
                    (result, escape(result.label), f"{width:.2f}", escape(percentage))
                )

    content = '<div class="result-bar">'
    for result, label, width, percentage in segments:
        content += f"""
            <div class="result-bar__segment result--{result}" style="width:{width}%" title="{label}: {percentage}">
            {percentage}</div>"""
    content += "</div>"
    if legend and segments:
        content += '<ul class="result-legend">'
        for result, label, _, percentage in segments:
            content += f'<li><span class="result-legend__swatch result--{result}"></span>{label} ({percentage})</li>'
        content += "</ul>"
    return mark_safe(content)
