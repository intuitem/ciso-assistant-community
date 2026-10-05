"""
Email template utilities for CISO Assistant
"""

import re
import markdown
from pathlib import Path
from string import Template
from typing import Dict, Optional
from django.conf import settings
from django.utils.formats import date_format as django_date_format
from django.utils.html import escape as html_escape
from django.utils.translation import get_language, override
from core.utils import yaml_safe_load
from global_settings.models import GlobalSettings
from iam.models import User
import structlog

logger = structlog.getLogger(__name__)


class MarkdownSafe(str):
    """
    A string subclass that signals to render_email_template() that
    this value already contains Markdown formatting (e.g. links) and
    should NOT be HTML-escaped before Markdown conversion.
    """

    pass


TEMPLATE_BASE_PATH = Path(__file__).parent / "templates" / "emails"

_DAY_UNITS = {
    "de": ("Tag", "Tagen"),
    "en": ("day", "days"),
    "fr": ("jour", "jours"),
}

_ASSIGNMENT_DECISIONS = {
    "de": {
        "closed": "geschlossen",
        "reopened": "erneut geöffnet",
        "changes_requested": "zur Überarbeitung zurückgegeben",
    },
    "en": {
        "closed": "closed",
        "reopened": "reopened",
        "changes_requested": "returned with changes requested",
    },
    "fr": {
        "closed": "clôturée",
        "reopened": "rouverte",
        "changes_requested": "renvoyée avec des modifications demandées",
    },
}

_TASK_LIST_LABELS = {
    "de": {
        "due": "Fällig",
        "status": "Status",
        "not_set": "Nicht festgelegt",
        "unknown": "Unbekannt",
    },
    "en": {
        "due": "Due",
        "status": "Status",
        "not_set": "Not set",
        "unknown": "Unknown",
    },
    "fr": {
        "due": "Échéance",
        "status": "Statut",
        "not_set": "Non définie",
        "unknown": "Inconnue",
    },
}

_TASK_STATUSES = {
    "de": {
        "pending": "Ausstehend",
        "in_progress": "In Bearbeitung",
        "completed": "Abgeschlossen",
        "cancelled": "Abgebrochen",
    },
    "en": {
        "pending": "Pending",
        "in_progress": "In progress",
        "completed": "Completed",
        "cancelled": "Cancelled",
    },
    "fr": {
        "pending": "En attente",
        "in_progress": "En cours",
        "completed": "Terminé",
        "cancelled": "Annulé",
    },
}


def _language_code(locale: Optional[str]) -> str:
    """Normalize a locale such as ``de-DE`` to a supported language code."""
    language = (locale or "en").split("-")[0].lower()
    return language if language in _DAY_UNITS else "en"


def localize_day_unit(days: int, locale: Optional[str]) -> str:
    """Return the language-specific day unit for a numeric duration."""
    singular, plural = _DAY_UNITS[_language_code(locale)]
    return singular if days == 1 else plural


def localize_assignment_decision(decision: str, locale: Optional[str]) -> str:
    """Return an assignment decision phrased for the recipient's language."""
    language = _language_code(locale)
    return _ASSIGNMENT_DECISIONS[language].get(
        decision, decision.replace("_", " ").lower()
    )


def get_email_preferences(email: str) -> tuple[str, str]:
    """
    Resolve the recipient's language and date format preferences.

    User preferences take precedence over the instance defaults. External email
    recipients, who have no user record, receive the instance defaults.
    """
    try:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            preferences = user.get_preferences()
            return (
                preferences.get("lang", "en"),
                preferences.get("date_format", "auto"),
            )
    except Exception as e:
        logger.warning("Failed to resolve user preferences for email lookup: %s", e)

    try:
        general = GlobalSettings.objects.filter(name="general").first()
        if general and isinstance(general.value, dict):
            locale = general.value.get("default_language", "en")
            date_format = general.value.get("default_date_format", "auto")
            if date_format not in User.DATE_FORMATS:
                date_format = "auto"
            return locale, date_format
    except Exception as e:
        logger.warning("Failed to resolve defaults from global settings: %s", e)

    return "en", "auto"


def get_locale_for_email(email: str) -> str:
    """Resolve the preferred locale for a given email address."""
    locale, _ = get_email_preferences(email)
    return locale


def format_email_date(value, locale: Optional[str], preference: str = "auto") -> str:
    """Format a date for an email using the recipient's UI preference."""
    if preference not in User.DATE_FORMATS:
        preference = "auto"

    if preference == "iso":
        return value.strftime("%Y-%m-%d")
    if preference == "ddmmyyyy":
        return value.strftime("%d/%m/%Y")
    if preference == "mmddyyyy":
        return value.strftime("%m/%d/%Y")

    language = (locale or "en").split("-")[0].lower()
    configured_languages = {code for code, _ in settings.LANGUAGES}
    if language not in configured_languages:
        language = "en"
    with override(language):
        if preference == "long_dmy":
            return django_date_format(value, "j F Y")
        if preference == "long_mdy":
            return django_date_format(value, "F j, Y")
        return django_date_format(value, "SHORT_DATE_FORMAT")


def get_disabled_email_templates() -> set:
    """
    Return the set of template keys disabled by the administrator.
    Stored in GlobalSettings(name="general").value["disabled_email_templates"].
    An absent or malformed entry means every template is enabled.
    """
    try:
        general = GlobalSettings.objects.filter(name="general").first()
        if general and isinstance(general.value, dict):
            disabled = general.value.get("disabled_email_templates", [])
            if isinstance(disabled, list):
                return {key for key in disabled if isinstance(key, str)}
    except Exception as e:
        logger.warning("Failed to resolve disabled email templates: %s", e)
    return set()


def is_email_template_enabled(template_name: str) -> bool:
    """Whether emails using this template may be sent (enabled by default)."""
    return template_name not in get_disabled_email_templates()


def _load_custom_email_template(
    template_name: str, locale: str
) -> Optional[Dict[str, str]]:
    """
    Try to load a custom email template override from the database.
    Returns None if no active override exists.
    """
    try:
        from core.models import CustomEmailTemplate

        override = CustomEmailTemplate.objects.filter(
            template_key=template_name,
            language=locale,
            is_active=True,
        ).first()
        if override:
            return {"subject": override.subject, "body": override.body}
    except Exception as e:
        logger.warning(
            "Failed to load custom email template override",
            template=template_name,
            locale=locale,
            exc_info=e,
        )
    return None


def load_email_template(
    template_name: str,
    locale: Optional[str] = None,
    builtin_only: bool = False,
) -> Optional[Dict[str, str]]:
    """
    Load email template, checking for custom overrides first, then falling
    back to the built-in YAML file.

    Args:
        template_name: Name of the template (e.g., 'expired_controls')
        locale: Language code (e.g., 'en', 'fr'). If None, uses current Django language
        builtin_only: If True, skip custom overrides and load only the built-in YAML file

    Returns:
        Dictionary with 'subject' and 'body' keys, or None if not found
    """
    if locale is None:
        locale = get_language() or "en"
    # Normalize locale: 'fr-FR' -> 'fr', '' -> 'en'
    locale = locale.split("-")[0].lower() or "en"

    # Check for custom override first
    if not builtin_only:
        custom = _load_custom_email_template(template_name, locale)
        if custom:
            return custom

    # Construct file path
    template_file = TEMPLATE_BASE_PATH / locale / f"{template_name}.yaml"

    # If locale-specific template doesn't exist, fall back to English
    if not template_file.exists():
        if locale != "en":
            logger.warning(
                f"Template {template_file} not found, falling back to English"
            )
            template_file = TEMPLATE_BASE_PATH / "en" / f"{template_name}.yaml"

        if not template_file.exists():
            logger.error(f"Template {template_file} not found")
            return None

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            template_data = yaml_safe_load(f)

        # Validate template structure
        if (
            not isinstance(template_data, dict)
            or "subject" not in template_data
            or "body" not in template_data
        ):
            logger.error(f"Invalid template structure in {template_file}")
            return None

        return template_data
    except Exception as e:
        logger.error(f"Error loading template {template_file}: {str(e)}")
        return None


def markdown_to_html(text: str) -> str:
    """
    Convert Markdown text to HTML for email bodies.

    Context variables should already be HTML-escaped before substitution
    into the template. The template body itself is authored by admins
    (who have change_globalsettings permission), so raw HTML in the
    template is an accepted trust boundary.

    All <a> links get target="_blank" so they open in a new tab
    (important for webmail clients, email previews, and embedded iframes).
    """
    html = markdown.markdown(
        text,
        extensions=["nl2br", "sane_lists"],
    )
    # Add target="_blank" with rel="noopener noreferrer" to all <a> tags
    # - noopener: prevents the opened page from accessing window.opener
    # - noreferrer: prevents sending the Referer header to the linked page
    html = re.sub(
        r"<a(?![^>]*\btarget=)",
        '<a target="_blank" rel="noopener noreferrer"',
        html,
    )
    return html


def render_email_template(
    template_name: str,
    context: Dict,
    locale: Optional[str] = None,
    recipient_email: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """
    Render email template with context variables.

    Template bodies support Markdown syntax. The returned dict contains:
    - 'subject': plain text subject line
    - 'body': plain text body (for email clients that don't support HTML)
    - 'html_body': HTML body converted from Markdown

    Args:
        template_name: Name of the template (e.g., 'expired_controls')
        context: Dictionary of variables to substitute in template
        locale: Language code. If None, resolves from recipient_email or uses current Django language
        recipient_email: Email address of recipient, used to resolve locale from user preferences

    Returns:
        Dictionary with 'subject', 'body', and 'html_body' keys.
        Returns None if the template is disabled in settings (intentional skip),
        or an empty dict if the template could not be loaded or rendered (failure).
    """
    if not is_email_template_enabled(template_name):
        logger.info(
            "Email template is disabled in settings, skipping send",
            template=template_name,
        )
        return None

    if locale is None and recipient_email:
        locale = get_locale_for_email(recipient_email)
    template_data = load_email_template(template_name, locale)
    if not template_data:
        logger.error(f"Failed to load template {template_name}")
        return {}

    try:
        # Add default context variables
        full_context = get_default_context()
        full_context.update(context)

        # Escape context values for safe HTML embedding.
        # MarkdownSafe values are already formatted Markdown (e.g. links)
        # and must NOT be escaped, so the Markdown->HTML pass can convert them.
        html_context = {
            k: str(v) if isinstance(v, MarkdownSafe) else html_escape(str(v))
            for k, v in full_context.items()
        }

        # Use string.Template for safe substitution
        subject = Template(template_data["subject"]).safe_substitute(full_context)
        body = Template(template_data["body"]).safe_substitute(full_context)
        html_body_raw = Template(template_data["body"]).safe_substitute(html_context)
        html_body = markdown_to_html(html_body_raw)

        return {"subject": subject, "body": body, "html_body": html_body}
    except Exception as e:
        logger.error(f"Error rendering template {template_name}: {str(e)}")
        return {}


def format_control_list(controls) -> str:
    """
    Format a list of controls for email templates

    Args:
        controls: List of AppliedControl objects

    Returns:
        Formatted string with control information
    """
    control_lines = []
    for control in controls:
        if hasattr(control, "eta") and control.eta:
            control_lines.append(f"- {control.name} (ETA: {control.eta})")
        else:
            control_lines.append(f"- {control.name}")

    return "\n".join(control_lines)


def format_assessment_list(assessments) -> str:
    """
    Format a list of assessments for email templates

    Args:
        assessments: List of ComplianceAssessment objects

    Returns:
        Formatted string with assessment information
    """
    assessment_lines = []
    for assessment in assessments:
        framework_name = (
            assessment.framework.name if assessment.framework else "No framework"
        )
        due_date = (
            assessment.due_date.strftime("%Y-%m-%d")
            if assessment.due_date
            else "Not set"
        )
        assessment_lines.append(
            f"- {assessment.name} (Framework: {framework_name}, Due: {due_date})"
        )

    return "\n".join(assessment_lines)


def format_evidence_list(evidences) -> str:
    """
    Format a list of evidences for email templates

    Args:
        evidences: List of Evidence objects

    Returns:
        Formatted string with evidence information
    """
    evidence_lines = []
    for evidence in evidences:
        expiry_date = (
            evidence.expiry_date.strftime("%Y-%m-%d")
            if evidence.expiry_date
            else "Not set"
        )
        status = (
            evidence.get_status_display()
            if hasattr(evidence, "get_status_display")
            else evidence.status
        )
        evidence_lines.append(
            f"- {evidence.name} (Status: {status}, Expiry: {expiry_date})"
        )

    return "\n".join(evidence_lines)


def format_security_exception_list(security_exceptions) -> str:
    """
    Format a list of security exceptions for email templates

    Args:
        security_exceptions: List of SecurityException objects

    Returns:
        Formatted string with security exception information
    """
    exception_lines = []
    for exception in security_exceptions:
        expiration_date = (
            exception.expiration_date.strftime("%Y-%m-%d")
            if exception.expiration_date
            else "Not set"
        )
        status = (
            exception.get_status_display()
            if hasattr(exception, "get_status_display")
            else exception.status
        )
        ref_id = f"{exception.ref_id} - " if exception.ref_id else ""
        exception_lines.append(
            f"- {ref_id}{exception.name} (Status: {status}, Expiration: {expiration_date})"
        )

    return "\n".join(exception_lines)


def format_validation_list(validations) -> str:
    """
    Format a list of validation flows for email templates

    Args:
        validations: List of ValidationFlow objects

    Returns:
        Formatted string with validation flow information
    """
    validation_lines = []
    for validation in validations:
        deadline = (
            validation.validation_deadline.strftime("%Y-%m-%d")
            if validation.validation_deadline
            else "Not set"
        )
        requester_name = (
            f"{validation.requester.first_name} {validation.requester.last_name}".strip()
            if validation.requester
            and (validation.requester.first_name or validation.requester.last_name)
            else validation.requester.email
            if validation.requester
            else "Unknown"
        )
        validation_lines.append(
            f"- {validation.ref_id} (Requester: {requester_name}, Deadline: {deadline})"
        )

    return "\n".join(validation_lines)


def format_task_node_list(
    task_nodes,
    include_description: bool = False,
    *,
    locale: Optional[str] = "en",
    date_format: str = "auto",
) -> MarkdownSafe:
    """
    Format a list of task nodes for email templates.

    Each task node is rendered as a Markdown link pointing to its detail page,
    so recipients can click through directly.

    Args:
        task_nodes: List of TaskNode objects
        include_description: If True, include the task template description
            below each task entry
        locale: Recipient language used for labels and status values
        date_format: Recipient date format preference

    Returns:
        MarkdownSafe string with task node information (contains Markdown links)
    """
    base_url = getattr(settings, "CISO_ASSISTANT_URL", "http://localhost:5173")
    language = _language_code(locale)
    labels = _TASK_LIST_LABELS[language]
    items = []
    for node in task_nodes:
        name = (
            html_escape(node.task_template.name)
            if node.task_template
            else labels["unknown"]
        )
        due_date = (
            format_email_date(node.due_date, locale, date_format)
            if node.due_date
            else labels["not_set"]
        )
        status = _TASK_STATUSES[language].get(
            node.status, node.status.replace("_", " ")
        )
        # Recurrent tasks link to the task node (each occurrence is distinct),
        # non-recurrent tasks link to the task template (the main object).
        if node.task_template and node.task_template.is_recurrent:
            node_url = f"{base_url}/task-nodes/{node.id}"
        else:
            template_id = node.task_template.id if node.task_template else node.id
            node_url = f"{base_url}/task-templates/{template_id}"
        link = (
            f'<a target="_blank" rel="noopener noreferrer" href="{node_url}">{name}</a>'
        )
        item = (
            f"<li>{link}<br>{labels['due']}: {html_escape(due_date)}"
            f"<br>{labels['status']}: {html_escape(status)}"
        )
        if (
            include_description
            and node.task_template
            and node.task_template.description
        ):
            # Escape HTML first to prevent injection, then convert Markdown.
            desc_escaped = html_escape(node.task_template.description.strip())
            desc_html = markdown_to_html(desc_escaped)
            item += f"<br>{desc_html}"
        item += "</li>"
        items.append(item)

    return MarkdownSafe("<ul>" + "".join(items) + "</ul>")


def get_default_context() -> Dict[str, str]:
    """
    Get default context variables for email templates

    Returns:
        Dictionary with default context variables
    """
    return {
        "ciso_assistant_url": getattr(
            settings, "CISO_ASSISTANT_URL", "http://localhost:5173"
        ),
    }


def send_templated_notification(
    template_name: str,
    context: Dict,
    recipient_email: str,
    locale: Optional[str] = None,
) -> bool:
    """
    Helper function to send a notification using a template

    Args:
        template_name: Name of the email template
        context: Context variables for the template
        recipient_email: Email address to send to
        locale: Language code for the template

    Returns:
        True if email was queued successfully, False otherwise
    """
    from .tasks import check_email_configuration, send_notification_email

    if not check_email_configuration(recipient_email, []):
        return False

    rendered = render_email_template(
        template_name, context, locale=locale, recipient_email=recipient_email
    )
    if not rendered:
        return False

    send_notification_email(
        rendered["subject"],
        rendered["body"],
        recipient_email,
        rendered.get("html_body"),
    )
    return True
