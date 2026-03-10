"""
Email template utilities for CISO Assistant
"""

import yaml
import markdown
from pathlib import Path
from string import Template
from typing import Dict, Optional
from django.conf import settings
from django.utils.html import escape as html_escape
from django.utils.translation import get_language
from global_settings.models import GlobalSettings
from iam.models import User
import structlog

logger = structlog.getLogger(__name__)

TEMPLATE_BASE_PATH = Path(__file__).parent / "templates" / "emails"


def get_locale_for_email(email: str) -> str:
    """
    Resolve the preferred locale for a given email address.
    Looks up the user's preferences, falls back to admin default, then 'en'.
    """
    try:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            return user.get_preferences().get("lang", "en")
    except Exception as e:
        logger.warning("Failed to resolve user locale for email lookup: %s", e)

    try:
        general = GlobalSettings.objects.filter(name="general").first()
        if general and isinstance(general.value, dict):
            return general.value.get("default_language", "en")
    except Exception as e:
        logger.warning("Failed to resolve default language from global settings: %s", e)

    return "en"


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
        if not override and locale != "en":
            override = CustomEmailTemplate.objects.filter(
                template_key=template_name,
                language="en",
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
    template_name: str, locale: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """
    Load email template, checking for custom overrides first, then falling
    back to the built-in YAML file.

    Args:
        template_name: Name of the template (e.g., 'expired_controls')
        locale: Language code (e.g., 'en', 'fr'). If None, uses current Django language

    Returns:
        Dictionary with 'subject' and 'body' keys, or None if not found
    """
    if locale is None:
        locale = get_language() or "en"
    # Normalize locale: 'fr-FR' -> 'fr', '' -> 'en'
    locale = locale.split("-")[0].lower() or "en"

    # Check for custom override first
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
            template_data = yaml.safe_load(f)

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
    """
    return markdown.markdown(
        text,
        extensions=["nl2br", "sane_lists"],
    )


def render_email_template(
    template_name: str,
    context: Dict,
    locale: Optional[str] = None,
    recipient_email: Optional[str] = None,
) -> Dict[str, str]:
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
        Dictionary with 'subject', 'body', and 'html_body' keys, or empty dict if template not found
    """
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

        # Escape context values for safe HTML embedding
        html_context = {k: html_escape(str(v)) for k, v in full_context.items()}

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


def format_task_node_list(task_nodes) -> str:
    """
    Format a list of task nodes for email templates

    Args:
        task_nodes: List of TaskNode objects

    Returns:
        Formatted string with task node information
    """
    task_lines = []
    for node in task_nodes:
        name = node.task_template.name if node.task_template else "Unknown"
        due_date = node.due_date.strftime("%Y-%m-%d") if node.due_date else "Not set"
        task_lines.append(f"- {name} (Due: {due_date}, Status: {node.status})")

    return "\n".join(task_lines)


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
