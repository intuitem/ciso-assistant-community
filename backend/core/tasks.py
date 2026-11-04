from collections import defaultdict
from datetime import date, timedelta
from huey import crontab
from huey.contrib.djhuey import periodic_task, task, db_periodic_task
from core.models import (
    QuickFormResponse,
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    Incident,
    RiskAcceptance,
    OrganisationIssue,
    RequirementAssignment,
    RiskAssessment,
    RiskScenario,
    SecurityException,
    TaskNode,
    TaskTemplate,
    ValidationFlow,
    Vulnerability,
)
from iam.models import ServiceAccount, User
from core import mailer
from django.conf import settings
from django.db import models, transaction
import logging
from global_settings.models import GlobalSettings

import logging.config
import structlog


from django.core.management import call_command
from notifications.service import clear_stale, notify, notify_many

logging.config.dictConfig(settings.LOGGING)
logger = structlog.getLogger(__name__)

# Days before a deadline on which email escalates. Descending: the first is also the
# width of the window the inbox tracks continuously (see check_evidences_expiring_soon).
EXPIRY_NOTICE_DAYS = (30, 7, 1)


def _localized_day_unit(email: str, days: int) -> tuple[str, str]:
    from .email_utils import get_locale_for_email, localize_day_unit

    locale = get_locale_for_email(email)
    return locale, localize_day_unit(days, locale)


def _localized_assignment_decision(email: str, decision: str) -> tuple[str, str]:
    from .email_utils import get_locale_for_email, localize_assignment_decision

    locale = get_locale_for_email(email)
    return locale, localize_assignment_decision(decision, locale)


def _sweep_deadline(
    notification_type: str,
    objects,
    *,
    due_date,
    recipients,
    context,
    send,
    skip=None,
) -> None:
    """One sweep per deadline type, replacing the in_month / in_week / tomorrow trio.

    Both channels escalate on the same days; the inbox additionally keeps the row in
    between, which is why it needs the whole window and email only needs today. Only a
    sweep seeing the whole window can say which rows are stale -- any one of the three
    would have cleared the others' rows.

    `objects` must cover the whole window. `skip(obj, days_remaining)` drops an object
    from both channels.
    """
    today = date.today()
    steady, escalating = [], []
    by_horizon = {days: defaultdict(list) for days in EXPIRY_NOTICE_DAYS}

    for obj in objects:
        due = due_date(obj)
        if due is None:
            continue
        days_remaining = (due - today).days
        if skip and skip(obj, days_remaining):
            continue
        emails = recipients(obj)
        if not emails:
            continue

        item = (emails, obj, context(obj, days_remaining))
        # The same test decides both channels: today is an escalation day, or it is not.
        if days_remaining in by_horizon:
            escalating.append(item)
            for email in emails:
                by_horizon[days_remaining][email].append(obj)
        else:
            steady.append(item)

    written = notify_many(notification_type, steady) + notify_many(
        notification_type, escalating, renotify=True
    )
    clear_stale(notification_type, _written(written))

    for days, per_recipient in by_horizon.items():
        for email, batch in per_recipient.items():
            # Keyword: these senders' signatures are (recipient, objects, days) and
            # the tests read kwargs.
            send(email, batch, days=days)


def _written(rows) -> set:
    """The pairs a sweep just wrote, in the shape clear_stale takes."""
    return {(row.recipient_id, row.object_id) for row in rows}


def _actor_emails(actors) -> set:
    """Flatten actors to addresses; an actor with no internal user gets email only."""
    return {email for actor in actors for email in actor.get_emails() if email}


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="0"))
def check_controls_with_expired_eta():
    expired_controls = (
        AppliedControl.objects.exclude(status__in=["active", "deprecated"])
        .filter(eta__lt=date.today(), eta__isnull=False)
        .prefetch_related("owner")
    )
    # Group by individual owner
    owner_controls = defaultdict(list)
    for control in expired_controls:
        for owner in control.owner.all():
            for email in owner.get_emails():
                owner_controls[email].append(control)
    rows = notify_many(
        "expired_controls",
        (
            (
                _actor_emails(control.owner.all()),
                control,
                {"control_name": str(control)},
            )
            for control in expired_controls
        ),
    )
    clear_stale("expired_controls", _written(rows))

    # Send personalized email to each owner
    for owner_email, controls in owner_controls.items():
        send_notification_email_expired_eta(owner_email, controls)


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="5"))
def check_compliance_assessments_due_soon():
    """Audits approaching their due date. Replaces the in_month/in_week/tomorrow trio."""
    today = date.today()
    _sweep_deadline(
        "compliance_assessment_due_soon",
        ComplianceAssessment.objects.filter(
            due_date__gt=today,
            due_date__lte=today + timedelta(days=EXPIRY_NOTICE_DAYS[0]),
        )
        .exclude(status__in=["done", "deprecated"])
        .prefetch_related("authors"),
        due_date=lambda assessment: assessment.due_date,
        recipients=lambda assessment: _actor_emails(assessment.authors.all()),
        context=lambda assessment, days: {
            "assessment_name": str(assessment),
            "days_remaining": days,
        },
        send=send_compliance_assessment_due_soon_notification,
    )


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="17"))
def check_applied_controls_expiring_soon():
    """Controls approaching expiry. Replaces the in_month / in_week / tomorrow trio."""
    today = date.today()
    _sweep_deadline(
        "applied_control_expiring_soon",
        AppliedControl.objects.filter(
            expiry_date__gt=today,
            expiry_date__lte=today + timedelta(days=EXPIRY_NOTICE_DAYS[0]),
        )
        .exclude(status__in=["deprecated"])
        .prefetch_related("owner"),
        due_date=lambda control: control.expiry_date,
        recipients=lambda control: _actor_emails(control.owner.all()),
        context=lambda control, days: {
            "control_name": str(control),
            "days_remaining": days,
        },
        send=send_applied_control_expiring_soon_notification,
    )


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="27"))
def check_evidences_expiring_soon():
    """Evidences approaching expiry. Replaces the in_month / in_week / tomorrow trio."""
    today = date.today()
    _sweep_deadline(
        "evidence_expiring_soon",
        Evidence.objects.filter(
            expiry_date__gt=today,
            expiry_date__lte=today + timedelta(days=EXPIRY_NOTICE_DAYS[0]),
        )
        .exclude(status__in=["expired"])
        .prefetch_related("owner"),
        due_date=lambda evidence: evidence.expiry_date,
        recipients=lambda evidence: _actor_emails(evidence.owner.all()),
        context=lambda evidence, days: {
            "evidence_name": str(evidence),
            "days_remaining": days,
        },
        send=send_evidence_expiring_soon_notification,
    )


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="40"))
def check_evidences_expired():
    """Check for expired Evidences"""
    expired_evidences = Evidence.objects.filter(
        expiry_date__lt=date.today()
    ).prefetch_related("owner")

    # Group by individual owner
    owner_evidences = defaultdict(list)
    for evidence in expired_evidences:
        for owner in evidence.owner.all():
            for email in owner.get_emails():
                owner_evidences[email].append(evidence)

    rows = notify_many(
        "expired_evidences",
        (
            (
                _actor_emails(evidence.owner.all()),
                evidence,
                {"evidence_name": str(evidence)},
            )
            for evidence in expired_evidences
        ),
    )
    clear_stale("expired_evidences", _written(rows))

    # Send personalized email to each owner
    for owner_email, evidences in owner_evidences.items():
        days = 0
        days_list = [(date.today() - ev.expiry_date).days for ev in evidences]
        if days_list:
            days = max(days_list)

        send_notification_email_expired_evidence(owner_email, evidences, days=days)


# Security exceptions in a terminal state should not trigger expiry reminders.
SECURITY_EXCEPTION_TERMINAL_STATUSES = [
    SecurityException.Status.REJECTED,
    SecurityException.Status.RESOLVED,
    SecurityException.Status.EXPIRED,
    SecurityException.Status.DEPRECATED,
]


def _group_security_exceptions_by_owner(security_exceptions):
    """Group security exceptions by each owner's email address.

    Several owners can resolve to the same email, so dedupe per recipient to
    avoid duplicate rows and an inflated count in the reminder email.
    """
    owner_exceptions = defaultdict(dict)
    for exception in security_exceptions:
        for owner in exception.owners.all():
            for email in owner.get_emails():
                if email:
                    owner_exceptions[email][exception.id] = exception
    return {
        email: list(exceptions.values())
        for email, exceptions in owner_exceptions.items()
    }


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="7", minute="15"))
def check_security_exceptions_expiring_soon():
    """Exceptions approaching expiry. Replaces the in_month/in_week/tomorrow trio."""
    today = date.today()
    _sweep_deadline(
        "security_exception_expiring_soon",
        SecurityException.objects.filter(
            expiration_date__gt=today,
            expiration_date__lte=today + timedelta(days=EXPIRY_NOTICE_DAYS[0]),
        )
        .exclude(status__in=SECURITY_EXCEPTION_TERMINAL_STATUSES)
        .prefetch_related("owners"),
        due_date=lambda exception: exception.expiration_date,
        recipients=lambda exception: _actor_emails(exception.owners.all()),
        context=lambda exception, days: {
            "exception_name": str(exception),
            "days_remaining": days,
        },
        send=send_security_exception_expiring_soon_notification,
    )


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="7", minute="30"))
def check_security_exceptions_expired():
    """Check for expired SecurityExceptions"""
    expired_exceptions = (
        SecurityException.objects.filter(expiration_date__lt=date.today())
        .exclude(status__in=SECURITY_EXCEPTION_TERMINAL_STATUSES)
        .prefetch_related("owners")
    )

    rows = notify_many(
        "expired_security_exceptions",
        (
            (
                _actor_emails(exception.owners.all()),
                exception,
                {"exception_name": str(exception)},
            )
            for exception in expired_exceptions
        ),
    )
    clear_stale("expired_security_exceptions", _written(rows))

    for owner_email, exceptions in _group_security_exceptions_by_owner(
        expired_exceptions
    ).items():
        days_list = [(date.today() - exc.expiration_date).days for exc in exceptions]
        days = max(days_list) if days_list else 0
        send_notification_email_expired_security_exception(
            owner_email, exceptions, days=days
        )


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="37"))
def check_validation_flows_deadline_soon():
    """Validations approaching their deadline. Replaces the in_month/in_week/tomorrow trio."""
    today = date.today()
    _sweep_deadline(
        "validation_deadline",
        ValidationFlow.objects.filter(
            validation_deadline__gt=today,
            validation_deadline__lte=today + timedelta(days=EXPIRY_NOTICE_DAYS[0]),
            status=ValidationFlow.Status.SUBMITTED,
        ).select_related("approver"),
        due_date=lambda flow: flow.validation_deadline,
        recipients=lambda flow: (
            {flow.approver.email} if flow.approver and flow.approver.email else set()
        ),
        context=lambda flow, days: {
            "validation_ref_id": flow.ref_id,
            "days": days,
        },
        send=send_validation_deadline_notification,
    )


def _get_task_recurrence_interval_days(task_template):
    """Return the approximate recurrence interval in days, or None if not recurrent."""
    if not task_template.is_recurrent or not task_template.schedule:
        return None
    schedule = task_template.schedule
    interval = schedule.get("interval", 1)
    frequency = schedule.get("frequency", "DAILY")
    multipliers = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30, "YEARLY": 365}
    return interval * multipliers.get(frequency, 1)


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="55"))
def check_task_nodes_due_soon():
    """Tasks approaching their due date. Replaces the in_month/in_week/tomorrow trio.

    A task that recurs more often than the horizon is not announced that far out --
    a weekly task has no business appearing a month ahead, in either channel.
    """
    today = date.today()

    def recurs_sooner_than(node, days_remaining):
        interval = _get_task_recurrence_interval_days(node.task_template)
        return interval is not None and interval < days_remaining

    _sweep_deadline(
        "task_node_due_soon",
        TaskNode.objects.filter(
            due_date__gt=today,
            due_date__lte=today + timedelta(days=EXPIRY_NOTICE_DAYS[0]),
            status__in=["pending", "in_progress"],
        )
        .select_related("task_template")
        .filter(task_template__enabled=True)
        .prefetch_related("task_template__assigned_to"),
        due_date=lambda node: node.due_date,
        recipients=lambda node: _actor_emails(node.task_template.assigned_to.all()),
        context=lambda node, days: {"task_name": str(node), "days_remaining": days},
        send=send_task_node_due_soon_notification,
        skip=recurs_sooner_than,
    )


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="7", minute="10"))
def check_task_nodes_overdue():
    """Check for TaskNodes that are past due and still open."""
    overdue_nodes = (
        TaskNode.objects.filter(
            due_date__lt=date.today(), status__in=TaskNode.OPEN_STATUSES
        )
        .select_related("task_template")
        .filter(task_template__enabled=True)
        .prefetch_related("task_template__assigned_to")
    )

    actor_nodes = defaultdict(list)
    for node in overdue_nodes:
        for actor in node.task_template.assigned_to.all():
            for email in actor.get_emails():
                actor_nodes[email].append(node)

    rows = notify_many(
        "task_node_overdue",
        (
            (
                _actor_emails(node.task_template.assigned_to.all()),
                node,
                {"task_name": str(node)},
            )
            for node in overdue_nodes
        ),
    )
    clear_stale("task_node_overdue", _written(rows))

    for email, nodes in actor_nodes.items():
        send_task_node_overdue_notification(email, nodes)


@task()
def send_task_node_due_soon_notification(actor_email, task_nodes, days):
    """Send notification when TaskNodes are due soon."""
    if not check_email_configuration(actor_email):
        return

    from .email_utils import (
        format_task_node_list,
        get_email_preferences,
        localize_day_unit,
        render_email_template,
    )

    locale, date_format = get_email_preferences(actor_email)
    days_unit = localize_day_unit(days, locale)

    context = {
        "task_count": len(task_nodes),
        "task_list": format_task_node_list(
            task_nodes, locale=locale, date_format=date_format
        ),
        "task_list_detailed": format_task_node_list(
            task_nodes,
            include_description=True,
            locale=locale,
            date_format=date_format,
        ),
        "days_remaining": days,
        "days_remaining_unit": days_unit,
    }

    rendered = render_email_template(
        "task_node_due_soon", context, locale=locale, recipient_email=actor_email
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            actor_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render task_node_due_soon email template for {actor_email}"
        )


@task()
def send_task_node_overdue_notification(actor_email, task_nodes):
    """Send notification for overdue TaskNodes."""
    if not check_email_configuration(actor_email):
        return

    from .email_utils import (
        format_task_node_list,
        get_email_preferences,
        render_email_template,
    )

    locale, date_format = get_email_preferences(actor_email)

    context = {
        "task_count": len(task_nodes),
        "task_list": format_task_node_list(
            task_nodes, locale=locale, date_format=date_format
        ),
        "task_list_detailed": format_task_node_list(
            task_nodes,
            include_description=True,
            locale=locale,
            date_format=date_format,
        ),
    }

    rendered = render_email_template(
        "task_node_overdue",
        context,
        locale=locale,
        recipient_email=actor_email,
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            actor_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render task_node_overdue email template for {actor_email}"
        )


@db_periodic_task(crontab(hour="6", minute="50"))
def check_expired_organisation_issues():
    expired_issues_query = OrganisationIssue.objects.filter(
        expiration_date__lt=date.today(), status=OrganisationIssue.Status.ACTIVE
    )
    expired_issues = list(expired_issues_query)

    for issue in expired_issues:
        issue.status = OrganisationIssue.Status.INACTIVE

    OrganisationIssue.objects.bulk_update(
        expired_issues,
        ["status"],
        batch_size=100,
    )


@task()
def send_notification_email_expired_eta(owner_email, controls):
    if not check_email_configuration(owner_email):
        return

    from .email_utils import (
        format_control_list,
        get_email_preferences,
        render_email_template,
    )

    locale, date_format = get_email_preferences(owner_email)

    context = {
        "control_count": len(controls),
        "control_list": format_control_list(
            controls, locale=locale, date_format=date_format
        ),
    }

    rendered = render_email_template(
        "expired_controls",
        context,
        locale=locale,
        recipient_email=owner_email,
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            owner_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render expired_controls email template for {owner_email}"
        )


def send_email_now(
    subject: str,
    message: str,
    recipient: str,
    html_message: str | None = None,
    connection=None,
) -> None:
    """Synchronous send through core.mailer; failures propagate to the caller.
    Pass `connection` (from core.mailer.open_connection) to batch several
    sends over one session; the caller owns its lifecycle."""
    mailer.send(
        subject, message, recipient, html_body=html_message, connection=connection
    )


@task()
def send_notification_email(subject, message, owner_email, html_message=None):
    try:
        logger.debug(
            "Sending notification email",
            recipient=owner_email,
            has_html=html_message is not None,
        )
        send_email_now(subject, message, owner_email, html_message)
        logger.info(
            "Notification email sent successfully",
            recipient=owner_email,
            subject=subject,
        )
    except Exception as e:
        logger.error(
            "Failed to send notification email",
            recipient=owner_email,
            subject=subject,
            error=str(e),
        )


def check_email_configuration(owner_email):
    """Return True if an email can be sent: mailing is enabled in the general
    settings, the SMTP settings are complete, and a recipient is given.
    """
    notifications_enable_mailing = GlobalSettings.objects.get(name="general").value.get(
        "notifications_enable_mailing", False
    )
    if not notifications_enable_mailing:
        logger.info(
            "Email notification is disabled. You can enable it under Extra/Settings. Skipping for now."
        )
        return False

    missing_settings = mailer.missing_configuration()

    if missing_settings:
        error_msg = f"Cannot send email notification: Missing email settings: {', '.join(missing_settings)}"
        logger.error(error_msg)
        return False

    if not owner_email:
        logger.error("Cannot send email notification: No recipient email provided")
        return False

    return True


@periodic_task(crontab(hour="22", minute="30"))
def auditlog_retention_cleanup():
    retention_days = getattr(settings, "AUDITLOG_RETENTION_DAYS", 90)
    before_date = date.today() - timedelta(days=retention_days)

    try:
        call_command("auditlogflush", "--before-date", before_date.isoformat(), "--yes")
        logger.info(f"Successfully cleaned up audit logs before {before_date}")
    except Exception as e:
        logger.error(f"Failed to clean up audit logs: {str(e)}")


@periodic_task(crontab(minute="0", hour="*/3"))
def auditlog_prune():
    try:
        call_command("prune_auditlog")
        logger.debug("Successfully pruned audit logs")
    except Exception as e:
        logger.error(f"Failed to prune the audit logs: {str(e)}")


# Assignment notification functions


@task()
def send_applied_control_assignment_notification(control_id, assigned_user_emails):
    """Send notification when AppliedControl is assigned to users"""
    if not assigned_user_emails:
        return

    try:
        control = AppliedControl.objects.get(id=control_id)
    except AppliedControl.DoesNotExist:
        logger.error(f"AppliedControl with id {control_id} not found")
        return

    from .email_utils import render_email_template

    context = {
        "control_name": control.name,
        "control_description": control.description or "No description provided",
        "control_ref_id": control.ref_id or "N/A",
        "control_status": control.get_status_display(),
        "control_priority": control.get_priority_display()
        if control.priority
        else "Not set",
        "control_eta": control.eta.strftime("%Y-%m-%d") if control.eta else "Not set",
        "folder_name": control.folder.name if control.folder else "Default",
    }

    notify("applied_control_assignment", assigned_user_emails, control, context)

    for email in assigned_user_emails:
        if email and check_email_configuration(email):
            rendered = render_email_template(
                "applied_control_assignment", context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


@task()
def send_task_template_assignment_notification(task_template_id, emails):
    """Send notification when TaskTemplate is assigned to users"""
    if not emails:
        return

    try:
        from core.models import TaskTemplate

        task_template = TaskTemplate.objects.get(id=task_template_id)
    except TaskTemplate.DoesNotExist:
        logger.error(f"TaskTemplate with id {task_template_id} not found")
        return

    from .email_utils import render_email_template

    context = {
        "task_id": task_template.id,
        "task_name": task_template.name,
        "task_description": task_template.description or "No description provided",
        "task_ref_id": task_template.ref_id or "N/A",
        "task_date": task_template.task_date.strftime("%Y-%m-%d")
        if task_template.task_date
        else "Not set",
        "is_recurrent": "Yes" if task_template.is_recurrent else "No",
        "folder_name": task_template.folder.name if task_template.folder else "Default",
    }

    notify("task_template_assignment", emails, task_template, context)

    for email in emails:
        if email and check_email_configuration(email):
            rendered = render_email_template(
                "task_template_assignment", context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


def _compliance_assessment_context(assessment):
    return {
        "assessment_name": assessment.name,
        "assessment_description": assessment.description or "No description provided",
        "assessment_ref_id": assessment.ref_id or "N/A",
        "framework_name": assessment.framework.name
        if assessment.framework
        else "No framework",
        "assessment_status": assessment.get_status_display(),
        "assessment_version": assessment.version or "1.0",
        "assessment_due_date": assessment.due_date.strftime("%Y-%m-%d")
        if assessment.due_date
        else "Not set",
        "folder_name": assessment.folder.name if assessment.folder else "Default",
    }


@task()
def send_compliance_assessment_reviewer_assignment_notification(
    assessment_id, reviewer_ids
):
    """Tell actors added as reviewers of an audit. Recipients are resolved from the
    audit's current reviewers, so one removed before the task runs is skipped."""
    assessment = ComplianceAssessment.objects.filter(id=assessment_id).first()
    if not assessment:
        return

    emails = sorted(_actor_emails(assessment.reviewers.filter(id__in=reviewer_ids)))
    if not emails:
        return

    context = _compliance_assessment_context(assessment)
    notify("compliance_assessment_reviewer_assignment", emails, assessment, context)

    for email in emails:
        if check_email_configuration(email):
            _send_rendered("compliance_assessment_reviewer_assignment", context, email)


@task()
def send_compliance_assessment_assignment_notification(
    assessment_id, assigned_user_emails
):
    """Send notification when ComplianceAssessment is assigned to users"""
    if not assigned_user_emails:
        return

    try:
        from core.models import ComplianceAssessment

        assessment = ComplianceAssessment.objects.get(id=assessment_id)
    except ComplianceAssessment.DoesNotExist:
        logger.error(f"ComplianceAssessment with id {assessment_id} not found")
        return

    from .email_utils import render_email_template

    context = _compliance_assessment_context(assessment)

    notify(
        "compliance_assessment_assignment", assigned_user_emails, assessment, context
    )

    for email in assigned_user_emails:
        if email and check_email_configuration(email):
            rendered = render_email_template(
                "compliance_assessment_assignment", context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


@task()
def send_risk_scenario_assignment_notification(scenario_id, assigned_user_emails):
    """Send notification when RiskScenario is assigned to users"""
    if not assigned_user_emails:
        return

    try:
        scenario = RiskScenario.objects.get(id=scenario_id)
    except RiskScenario.DoesNotExist:
        logger.error(f"RiskScenario with id {scenario_id} not found")
        return

    from .email_utils import render_email_template

    context = {
        "scenario_name": scenario.name,
        "scenario_description": scenario.description or "No description provided",
        "scenario_ref_id": scenario.ref_id or "N/A",
        "risk_assessment_name": scenario.risk_assessment.name
        if scenario.risk_assessment
        else "N/A",
        "scenario_treatment": scenario.get_treatment_display(),
        "folder_name": scenario.folder.name if scenario.folder else "Default",
    }

    notify("risk_scenario_assignment", assigned_user_emails, scenario, context)

    for email in assigned_user_emails:
        if email and check_email_configuration(email):
            rendered = render_email_template(
                "risk_scenario_assignment", context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


@task()
def send_incident_assignment_notification(incident_id, owner_ids):
    """Send notification when an Incident is assigned to owners.

    Takes owner IDs, not addresses: an owner removed before this task runs must not
    be notified, so recipients are resolved here from the incident's current owners.
    """
    if not owner_ids:
        return

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        logger.error(f"Incident with id {incident_id} not found")
        return

    assigned_user_emails = sorted(
        _actor_emails(incident.owners.filter(id__in=owner_ids))
    )
    if not assigned_user_emails:
        return

    from .email_utils import render_email_template

    context = {
        "incident_name": incident.name,
        "incident_ref_id": incident.ref_id or "N/A",
        "incident_severity": incident.get_severity_display(),
        "incident_status": incident.get_status_display(),
        "folder_name": incident.folder.name if incident.folder else "Default",
    }

    notify("incident_assignment", assigned_user_emails, incident, context)

    for email in assigned_user_emails:
        if email and check_email_configuration(email):
            rendered = render_email_template(
                "incident_assignment", context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


def _risk_acceptance_context(acceptance, actor_name):
    return {
        "acceptance_name": acceptance.name,
        "actor_name": actor_name,
        "risk_scenarios": ", ".join(str(s) for s in acceptance.risk_scenarios.all()),
        "folder_name": acceptance.folder.name if acceptance.folder else "Default",
    }


def _send_rendered(template_name, context, email, locale=None):
    from .email_utils import render_email_template

    rendered = render_email_template(
        template_name, context, locale=locale, recipient_email=email
    )
    if rendered:
        send_notification_email(
            rendered["subject"], rendered["body"], email, rendered.get("html_body")
        )


@task()
def send_risk_acceptance_submitted_notification(acceptance_id, actor_name):
    """Ask the approver to decide on a submitted risk acceptance."""
    acceptance = (
        RiskAcceptance.objects.select_related("approver", "folder")
        .filter(id=acceptance_id)
        .first()
    )
    # Re-checked at run time: a draft-back or approver change since submit cancels it.
    if not acceptance or acceptance.state != "submitted" or not acceptance.approver:
        return

    email = acceptance.approver.email
    context = {
        **_risk_acceptance_context(acceptance, actor_name),
        "expiry_date": acceptance.expiry_date.strftime("%Y-%m-%d")
        if acceptance.expiry_date
        else "-",
    }
    notify("risk_acceptance_submitted", [email], acceptance, context)

    if check_email_configuration(email):
        _send_rendered("risk_acceptance_submitted", context, email)


@task()
def send_risk_acceptance_decided_notification(acceptance_id, decision, actor_name):
    """Tell the owners of the covered risk scenarios that the approver decided."""
    acceptance = (
        RiskAcceptance.objects.select_related("folder")
        .prefetch_related("risk_scenarios__owner", "risk_scenarios__risk_assessment")
        .filter(id=acceptance_id)
        .first()
    )
    if not acceptance or acceptance.state != decision:
        return

    owners = {o for s in acceptance.risk_scenarios.all() for o in s.owner.all()}
    emails = sorted(_actor_emails(owners))
    if not emails:
        return

    context = {
        **_risk_acceptance_context(acceptance, actor_name),
        "justification": acceptance.justification or "-",
    }
    notify(
        "risk_acceptance_decided",
        emails,
        acceptance,
        {"acceptance_name": acceptance.name, "decision_key": decision},
    )

    from django.contrib.auth.models import Permission

    from iam.models import RoleAssignment

    from .email_utils import get_locale_for_email, localize_state

    view_perm = Permission.objects.get(codename="view_riskscenario")
    users = {u.email: u for u in User.objects.filter(email__in=emails)}
    for email in emails:
        if check_email_configuration(email):
            user = users.get(email)
            visible = [
                str(s)
                for s in acceptance.risk_scenarios.all()
                if user
                and RoleAssignment.is_access_allowed(
                    user, view_perm, s.risk_assessment.folder
                )
            ]
            locale = get_locale_for_email(email)
            _send_rendered(
                "risk_acceptance_decided",
                {
                    **context,
                    "risk_scenarios": ", ".join(visible) or "-",
                    "decision": localize_state(decision, locale),
                },
                email,
                locale,
            )


@task()
def send_evidence_reviewed_notification(evidence_id, decision, actor_name):
    """Tell an evidence's owners it was approved or rejected, one notice per evidence."""
    evidence = Evidence.objects.select_related("folder").filter(id=evidence_id).first()
    # Re-checked at run time: a later status change supersedes this one.
    if not evidence or evidence.status != decision:
        return

    emails = sorted(_actor_emails(evidence.owner.all()))
    if not emails:
        return

    notify(
        "evidence_reviewed",
        emails,
        evidence,
        {"evidence_name": evidence.name, "decision_key": decision},
    )

    from .email_utils import get_locale_for_email, localize_state

    context = {
        "evidence_name": evidence.name,
        "actor_name": actor_name,
        "folder_name": evidence.folder.name if evidence.folder else "Default",
    }
    for email in emails:
        if check_email_configuration(email):
            locale = get_locale_for_email(email)
            _send_rendered(
                "evidence_reviewed",
                {**context, "decision": localize_state(decision, locale)},
                email,
                locale,
            )


@task()
def send_object_assignment_notification(
    notification_type, model_label, object_id, field, actor_ids
):
    """Generic "assigned to you" for models without a dedicated type (see
    AssignmentNotificationMixin). Recipients are resolved from the field's current
    members, so an actor removed before the task runs is skipped."""
    from django.apps import apps

    from .email_utils import (
        get_locale_for_email,
        localize_model_name,
        paraglide_model_key,
    )

    model = apps.get_model(model_label)
    obj = model.objects.filter(pk=object_id).first()
    if not obj:
        return

    emails = sorted(_actor_emails(getattr(obj, field).filter(id__in=actor_ids)))
    if not emails:
        return

    object_name = getattr(obj, "name", None) or str(obj)
    type_key = paraglide_model_key(model)
    notify(
        notification_type,
        emails,
        obj,
        {"object_name": object_name, "object_type_key": type_key},
    )

    folder = getattr(obj, "folder", None)
    context = {
        "object_name": object_name,
        "folder_name": folder.name if folder else "Default",
    }
    for email in emails:
        if check_email_configuration(email):
            locale = get_locale_for_email(email)
            _send_rendered(
                notification_type,
                {**context, "object_type": localize_model_name(type_key, locale)},
                email,
                locale,
            )


def _document_revision(revision_id):
    from doc_management.models import DocumentRevision

    return (
        DocumentRevision.objects.select_related("author", "document__container__folder")
        .filter(id=revision_id)
        .first()
    )


def _document_context(revision, actor_name):
    container = revision.document.container
    return {
        "document_name": str(container),
        "version_number": revision.version_number,
        "actor_name": actor_name,
        "folder_name": container.folder.name if container.folder else "Default",
    }


@task()
def send_document_review_requested_notification(
    revision_id, actor_name, submitter_email
):
    """Ask the container's reviewers to review a submitted revision."""
    revision = _document_revision(revision_id)
    # Re-checked at run time: a decision taken since then supersedes the request.
    if not revision or revision.status != "in_review":
        return

    container = revision.document.container
    emails = sorted(_actor_emails(container.reviewers.all()) - {submitter_email})
    if not emails:
        return

    context = {
        **_document_context(revision, actor_name),
        "change_summary": revision.change_summary or "-",
    }
    notify(
        "document_review_requested",
        emails,
        container,
        {"document_name": context["document_name"]},
    )
    for email in emails:
        if check_email_configuration(email):
            _send_rendered("document_review_requested", context, email)


@task()
def send_document_revision_reviewed_notification(revision_id, state, actor_name):
    """Tell a revision's author it was validated, sent back, or published."""
    revision = _document_revision(revision_id)
    if not revision or revision.status != state or not revision.author:
        return

    email = revision.author.email
    context = {
        **_document_context(revision, actor_name),
        "reviewer_comments": revision.reviewer_comments or "-",
    }
    notify(
        "document_revision_reviewed",
        [email],
        revision.document.container,
        {"document_name": context["document_name"], "decision_key": state},
    )
    if check_email_configuration(email):
        from .email_utils import get_locale_for_email, localize_state

        locale = get_locale_for_email(email)
        _send_rendered(
            "document_revision_reviewed",
            {**context, "decision": localize_state(state, locale)},
            email,
            locale,
        )


@task()
def send_compliance_assessment_due_soon_notification(author_email, assessments, days):
    """Send notification when ComplianceAssessment is due soon"""
    if not check_email_configuration(author_email):
        return

    from .email_utils import format_assessment_list, render_email_template

    locale, days_unit = _localized_day_unit(author_email, days)

    context = {
        "assessment_count": len(assessments),
        "assessment_list": format_assessment_list(assessments),
        "days_remaining": days,
        "days_remaining_unit": days_unit,
    }

    template_name = "compliance_assessment_due_soon"
    rendered = render_email_template(
        template_name, context, locale=locale, recipient_email=author_email
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            author_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render {template_name} email template for {author_email}"
        )


@task()
def send_applied_control_expiring_soon_notification(owner_email, controls, days):
    """Send notification when AppliedControl is due soon"""
    if not check_email_configuration(owner_email):
        return

    from .email_utils import (
        format_control_list,
        get_email_preferences,
        localize_day_unit,
        render_email_template,
    )

    locale, date_format = get_email_preferences(owner_email)
    days_unit = localize_day_unit(days, locale)

    context = {
        "control_count": len(controls),
        "control_list": format_control_list(
            controls, locale=locale, date_format=date_format
        ),
        "days_remaining": days,
        "days_remaining_unit": days_unit,
    }

    template_name = "applied_control_expiring_soon"
    rendered = render_email_template(
        template_name, context, locale=locale, recipient_email=owner_email
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            owner_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render {template_name} email template for {owner_email}"
        )


@task()
def send_notification_email_expired_evidence(owner_email, evidences, days=0):
    if not check_email_configuration(owner_email):
        return

    from .email_utils import format_evidence_list, render_email_template

    locale, days_unit = _localized_day_unit(owner_email, days)

    context = {
        "evidence_count": len(evidences),
        "evidence_list": format_evidence_list(evidences),
        "expired_since": days,
        "expired_since_unit": days_unit,
    }

    rendered = render_email_template(
        "expired_evidences", context, locale=locale, recipient_email=owner_email
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            owner_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render expired_evidences email template for {owner_email}"
        )


@task()
def send_evidence_expiring_soon_notification(owner_email, evidences, days):
    """Send notification when Evidence is expiring soon"""
    if not check_email_configuration(owner_email):
        return

    from .email_utils import format_evidence_list, render_email_template

    locale, days_unit = _localized_day_unit(owner_email, days)

    context = {
        "evidence_count": len(evidences),
        "evidence_list": format_evidence_list(evidences),
        "days_remaining": days,
        "days_remaining_unit": days_unit,
    }

    template_name = "evidence_expiring_soon"
    rendered = render_email_template(
        template_name, context, locale=locale, recipient_email=owner_email
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            owner_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render {template_name} email template for {owner_email}"
        )


@task()
def send_security_exception_expiring_soon_notification(
    owner_email, security_exceptions, days
):
    """Send notification when SecurityException is expiring soon"""
    if not check_email_configuration(owner_email):
        return

    from .email_utils import format_security_exception_list, render_email_template

    locale, days_unit = _localized_day_unit(owner_email, days)

    context = {
        "exception_count": len(security_exceptions),
        "exception_list": format_security_exception_list(security_exceptions),
        "days_remaining": days,
        "days_remaining_unit": days_unit,
    }

    template_name = "security_exception_expiring_soon"
    rendered = render_email_template(
        template_name, context, locale=locale, recipient_email=owner_email
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            owner_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render {template_name} email template for {owner_email}"
        )


@task()
def send_notification_email_expired_security_exception(
    owner_email, security_exceptions, days=0
):
    """Send notification for expired SecurityExceptions"""
    if not check_email_configuration(owner_email):
        return

    from .email_utils import format_security_exception_list, render_email_template

    locale, days_unit = _localized_day_unit(owner_email, days)

    context = {
        "exception_count": len(security_exceptions),
        "exception_list": format_security_exception_list(security_exceptions),
        "expired_since": days,
        "expired_since_unit": days_unit,
    }

    template_name = "expired_security_exceptions"
    rendered = render_email_template(
        template_name, context, locale=locale, recipient_email=owner_email
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            owner_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render {template_name} email template for {owner_email}"
        )


@task()
def send_security_exception_assignment_notification(exception_id, assigned_user_emails):
    """Send notification when a SecurityException is assigned to owners"""
    if not assigned_user_emails:
        return

    try:
        security_exception = SecurityException.objects.get(id=exception_id)
    except SecurityException.DoesNotExist:
        logger.error(f"SecurityException with id {exception_id} not found")
        return

    from .email_utils import render_email_template

    context = {
        "exception_name": security_exception.name,
        "exception_description": security_exception.description
        or "No description provided",
        "exception_ref_id": security_exception.ref_id or "N/A",
        "exception_severity": security_exception.get_severity_display(),
        "exception_status": security_exception.get_status_display(),
        "expiration_date": security_exception.expiration_date.strftime("%Y-%m-%d")
        if security_exception.expiration_date
        else "Not set",
        "folder_name": security_exception.folder.name
        if security_exception.folder
        else "Default",
    }

    notify(
        "security_exception_assignment",
        assigned_user_emails,
        security_exception,
        context,
    )

    for email in assigned_user_emails:
        if email and check_email_configuration(email):
            rendered = render_email_template(
                "security_exception_assignment", context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


@task()
def send_vulnerability_assignment_notification(vulnerability_id, assigned_user_emails):
    """Send notification when a Vulnerability is assigned to owners"""
    if not assigned_user_emails:
        return

    try:
        vulnerability = Vulnerability.objects.get(id=vulnerability_id)
    except Vulnerability.DoesNotExist:
        logger.error(f"Vulnerability with id {vulnerability_id} not found")
        return

    from .email_utils import render_email_template

    context = {
        "vulnerability_name": vulnerability.name,
        "vulnerability_description": vulnerability.description
        or "No description provided",
        "vulnerability_ref_id": vulnerability.ref_id or "N/A",
        "vulnerability_severity": vulnerability.get_severity_display(),
        "vulnerability_status": vulnerability.get_status_display(),
        "due_date": vulnerability.due_date.strftime("%Y-%m-%d")
        if vulnerability.due_date
        else "Not set",
        "folder_name": vulnerability.folder.name if vulnerability.folder else "Default",
    }

    notify("vulnerability_assignment", assigned_user_emails, vulnerability, context)

    for email in assigned_user_emails:
        if email and check_email_configuration(email):
            rendered = render_email_template(
                "vulnerability_assignment", context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


@task()
def send_security_exception_status_notification(
    exception_id, new_status, actor_name, recipient_emails
):
    """Send notification when a SecurityException's status changes"""
    if not recipient_emails:
        return

    try:
        security_exception = SecurityException.objects.get(id=exception_id)
    except SecurityException.DoesNotExist:
        logger.error(f"SecurityException with id {exception_id} not found")
        return

    from .email_utils import render_email_template

    context = {
        "exception_name": security_exception.name,
        "exception_ref_id": security_exception.ref_id or "N/A",
        "new_status": new_status,
        "actor_name": actor_name,
        "folder_name": security_exception.folder.name
        if security_exception.folder
        else "Default",
    }

    notify(
        "security_exception_status_changed",
        recipient_emails,
        security_exception,
        context,
    )

    for email in set(recipient_emails):
        if email and check_email_configuration(email):
            rendered = render_email_template(
                "security_exception_status_changed", context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


@task()
def send_validation_flow_created_notification(validation_flow):
    """Send notification to approver when validation flow is created"""
    # The instance was pickled at enqueue; the approver may have changed since.
    try:
        validation_flow.refresh_from_db()
    except ValidationFlow.DoesNotExist:
        return
    if validation_flow.status != ValidationFlow.Status.SUBMITTED:
        return
    if not validation_flow.approver or not validation_flow.approver.email:
        logger.warning(
            f"No approver email for validation flow {validation_flow.ref_id}"
        )
        return

    approver_email = validation_flow.approver.email

    notify(
        "validation_flow_created",
        [approver_email],
        validation_flow,
        {"validation_ref_id": validation_flow.ref_id},
    )

    # Below is the email channel only: it may be unusable while the inbox above still
    # works, so the guard must not come before the notify() call.
    if not check_email_configuration(approver_email):
        return

    from .email_utils import render_email_template

    requester_name = (
        f"{validation_flow.requester.first_name} {validation_flow.requester.last_name}".strip()
        if validation_flow.requester
        and (
            validation_flow.requester.first_name or validation_flow.requester.last_name
        )
        else validation_flow.requester.email
        if validation_flow.requester
        else "Unknown"
    )

    context = {
        "validation_ref_id": validation_flow.ref_id,
        "requester_name": requester_name,
        "validation_deadline": (
            validation_flow.validation_deadline.strftime("%Y-%m-%d")
            if validation_flow.validation_deadline
            else "Not set"
        ),
        "folder_name": validation_flow.folder.name
        if validation_flow.folder
        else "Unknown",
        "validation_url": f"{getattr(settings, 'CISO_ASSISTANT_URL', 'http://localhost:5173')}/validation-flows/{validation_flow.id}",
    }

    rendered = render_email_template(
        "validation_flow_created", context, recipient_email=approver_email
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            approver_email,
            rendered.get("html_body"),
        )
        logger.info(
            f"Sent validation flow creation notification to {approver_email} for {validation_flow.ref_id}"
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render validation_flow_created email template for {approver_email}"
        )


@task()
def send_validation_flow_updated_notification(
    validation_flow_id, recipient_email, new_status, actor_name, event_notes
):
    """Send notification when a validation flow status changes."""
    try:
        validation_flow = ValidationFlow.objects.get(id=validation_flow_id)
    except ValidationFlow.DoesNotExist:
        logger.error(f"ValidationFlow with id {validation_flow_id} not found")
        return

    notify(
        "validation_flow_updated",
        [recipient_email],
        validation_flow,
        {"validation_ref_id": validation_flow.ref_id, "new_status": new_status},
    )

    # Email channel only, hence after the inbox write (see above).
    if not check_email_configuration(recipient_email):
        return

    from .email_utils import render_email_template

    context = {
        "validation_ref_id": validation_flow.ref_id,
        "new_status": new_status,
        "actor_name": actor_name,
        "folder_name": validation_flow.folder.name
        if validation_flow.folder
        else "Unknown",
        "event_notes": event_notes or "",
        "validation_url": f"{getattr(settings, 'CISO_ASSISTANT_URL', 'http://localhost:5173')}/validation-flows/{validation_flow.id}",
    }

    rendered = render_email_template(
        "validation_flow_updated", context, recipient_email=recipient_email
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            recipient_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render validation_flow_updated email template for {recipient_email}"
        )


@task()
def send_validation_deadline_notification(approver_email, validations, days):
    """Send notification about validation deadlines approaching"""
    if not check_email_configuration(approver_email):
        return

    from .email_utils import format_validation_list, render_email_template

    locale, days_unit = _localized_day_unit(approver_email, days)

    s = "s" if len(validations) > 1 else ""
    are = "are" if len(validations) > 1 else "is"
    their = "their" if len(validations) > 1 else "its"

    context = {
        "days": days,
        "validation_list": format_validation_list(validations),
        "validation_count": len(validations),
        "days_unit": days_unit,
        "s": s,
        "are": are,
        "their": their,
    }

    rendered = render_email_template(
        "validation_deadline",
        context,
        locale=locale,
        recipient_email=approver_email,
    )
    if rendered:
        send_notification_email(
            rendered["subject"],
            rendered["body"],
            approver_email,
            rendered.get("html_body"),
        )
    elif rendered is not None:
        logger.error(
            f"Failed to render validation_deadline email template for {approver_email}"
        )


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="2", minute="30"))
def lock_overdue_compliance_assessments():
    """Lock ComplianceAssessments that have exceeded their due_date and move status to in_review"""
    overdue_assessments = (
        ComplianceAssessment.objects.filter(
            due_date__lt=date.today(), due_date__isnull=False, is_locked=False
        )
        .exclude(status__in=["done", "deprecated"])
        .filter(
            models.Q(campaign__isnull=False)  # Associated with a campaign
            | models.Q(
                entityassessment__isnull=False
            )  # Or associated with an entity assessment
        )
        .distinct()
    )

    count = 0
    for assessment in overdue_assessments:
        assessment.is_locked = True
        assessment.status = "in_review"
        assessment.save()
        count += 1
        logger.info(
            f"Locked overdue compliance assessment: {assessment.name} (ID: {assessment.id})"
        )

    if count > 0:
        logger.info(f"Successfully locked {count} overdue compliance assessments")
    else:
        logger.debug("No overdue compliance assessments found to lock")


# @db_periodic_task(crontab(minute="*/5"))  # for testing
@db_periodic_task(crontab(hour="2", minute="45"))
def auto_sync_assessments():
    """Automatically sync to actions for assessments with auto_sync enabled, skipping locked ones"""
    risk_assessments = RiskAssessment.objects.filter(
        auto_sync=True, is_locked=False
    ).exclude(status__in=["done", "deprecated"])

    ra_count = 0
    for assessment in risk_assessments:
        try:
            changes = assessment.sync_to_applied_controls(
                reset_residual=False, dry_run=False
            )
            if changes:
                ra_count += 1
                logger.info(
                    "Auto-synced risk assessment",
                    assessment_id=str(assessment.id),
                    assessment_name=assessment.name,
                    changes_count=len(changes),
                )
        except Exception as e:
            logger.error(
                "Failed to auto-sync risk assessment",
                assessment_id=str(assessment.id),
                assessment_name=assessment.name,
                error=str(e),
            )

    compliance_assessments = ComplianceAssessment.objects.filter(
        auto_sync=True, is_locked=False
    ).exclude(status__in=["done", "deprecated"])

    ca_count = 0
    for assessment in compliance_assessments:
        try:
            changes = assessment.sync_to_applied_controls(dry_run=False)
            if changes:
                ca_count += 1
                logger.info(
                    "Auto-synced compliance assessment",
                    assessment_id=str(assessment.id),
                    assessment_name=assessment.name,
                    changes_count=len(changes),
                )
        except Exception as e:
            logger.error(
                "Failed to auto-sync compliance assessment",
                assessment_id=str(assessment.id),
                assessment_name=assessment.name,
                error=str(e),
            )

    if ra_count > 0 or ca_count > 0:
        logger.info(
            f"Auto-sync completed: {ra_count} risk assessments, {ca_count} compliance assessments synced"
        )
    else:
        logger.debug("Auto-sync completed: no assessments needed syncing")


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="3", minute="0"))
def deactivate_expired_users():
    """Deactivate users whose expiry_date has passed, except superusers"""
    today = date.today()
    expired_users = User.objects.filter(
        expiry_date__lt=today,
        expiry_date__isnull=False,
        is_active=True,
        is_superuser=False,  # Exclude superusers from auto-deactivation
    )

    count = 0
    for user in expired_users:
        # Never expire the deployment out of administration: keep the last
        # active directly-managed admin, mirroring the API-side guard
        # (UserWriteSerializer._enforce_last_active_admin) for expiry dates
        # that predate it.
        if (
            user.user_groups.filter(name="BI-UG-ADM").exists()
            and not User.objects.filter(user_groups__name="BI-UG-ADM", is_active=True)
            .exclude(pk=user.pk)
            .exists()
        ):
            logger.warning(
                f"Skipping expiry deactivation of the last active admin: {user.email} (ID: {user.id})"
            )
            continue
        user.is_active = False
        user.save()
        count += 1
        logger.info(
            f"Deactivated expired user: {user.email} (ID: {user.id}), expiry date: {user.expiry_date}"
        )

    if count > 0:
        logger.info(f"Successfully deactivated {count} expired users")
    else:
        logger.debug("No expired users found to deactivate")


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="3", minute="5"))
def deactivate_expired_service_accounts():
    """Deactivate service accounts whose expiry_date has passed.

    Uses ServiceAccount.deactivate(), not a plain is_active flip — it also
    revokes the OIDC client's grant types and deletes outstanding tokens, so
    an expired account can't keep authenticating on tokens minted earlier.
    """
    today = date.today()
    expired_service_accounts = ServiceAccount.objects.filter(
        expiry_date__lt=today,
        expiry_date__isnull=False,
        is_active=True,
    )

    count = 0
    for service_account in expired_service_accounts:
        try:
            with transaction.atomic():
                service_account.deactivate()
        except Exception as e:
            logger.error(
                f"Failed to deactivate expired service account: {service_account.name} (ID: {service_account.id})",
                error=str(e),
            )
            continue
        count += 1
        logger.info(
            f"Deactivated expired service account: {service_account.name} (ID: {service_account.id}), expiry date: {service_account.expiry_date}"
        )

    if count > 0:
        logger.info(f"Successfully deactivated {count} expired service accounts")
    else:
        logger.debug("No expired service accounts found to deactivate")


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="3", minute="35"))
def mark_expired_evidences():
    """Mark evidences as expired when their expiry_date has passed"""
    today = date.today()
    expired_evidences = Evidence.objects.filter(
        expiry_date__lt=today,
        expiry_date__isnull=False,
    ).exclude(status="expired")

    count = 0
    for evidence in expired_evidences:
        evidence.status = "expired"
        evidence.save()
        count += 1
        logger.info(
            f"Marked evidence as expired: {evidence.name} (ID: {evidence.id}), expiry date: {evidence.expiry_date}"
        )

    if count > 0:
        logger.info(f"Successfully marked {count} evidences as expired")
    else:
        logger.debug("No expired evidences found to mark")


@task()
def send_assignment_activated_notification(assignment_id):
    """Send notification when a RequirementAssignment is started (draft -> in_progress)."""
    try:
        assignment = RequirementAssignment.objects.select_related(
            "compliance_assessment",
            "compliance_assessment__framework",
        ).get(id=assignment_id)
    except RequirementAssignment.DoesNotExist:
        logger.error(f"RequirementAssignment with id {assignment_id} not found")
        return

    from .email_utils import render_email_template

    ca = assignment.compliance_assessment
    context = {
        "assessment_name": ca.name,
        "framework_name": ca.framework.name if ca.framework else "N/A",
        "due_date": ca.due_date.strftime("%Y-%m-%d") if ca.due_date else "Not set",
    }

    notify("assignment_activated", _actor_emails(assignment.actor.all()), ca, context)

    for actor in assignment.actor.all():
        for email in actor.get_emails():
            if email and check_email_configuration(email):
                rendered = render_email_template(
                    "assignment_activated", context, recipient_email=email
                )
                if rendered:
                    send_notification_email(
                        rendered["subject"],
                        rendered["body"],
                        email,
                        rendered.get("html_body"),
                    )


@task()
def send_assignment_submitted_notification(assignment_id):
    """Send notification when a RequirementAssignment is submitted for review."""
    try:
        assignment = RequirementAssignment.objects.select_related(
            "compliance_assessment",
        ).get(id=assignment_id)
    except RequirementAssignment.DoesNotExist:
        logger.error(f"RequirementAssignment with id {assignment_id} not found")
        return

    from .email_utils import render_email_template

    ca = assignment.compliance_assessment
    actor_names = ", ".join(str(a) for a in assignment.actor.all())
    requirement_count = assignment.requirement_assessments.count()

    context = {
        "assessment_name": ca.name,
        "actor_names": actor_names,
        "requirement_count": str(requirement_count),
    }

    # Notify reviewers, fallback to authors
    reviewers = ca.reviewers.all()
    if not reviewers or not reviewers.exists():
        reviewers = ca.authors.all()

    recipient_emails = set()
    for reviewer in reviewers:
        for email in reviewer.get_emails():
            if email:
                recipient_emails.add(email)

    notify("assignment_submitted", recipient_emails, ca, context)

    for email in recipient_emails:
        if check_email_configuration(email):
            rendered = render_email_template(
                "assignment_submitted", context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


@task()
def send_assignment_reopened_notification(assignment_id, observation=""):
    """Send notification when a RequirementAssignment is reset back to draft for editing."""
    try:
        assignment = RequirementAssignment.objects.select_related(
            "compliance_assessment",
        ).get(id=assignment_id)
    except RequirementAssignment.DoesNotExist:
        logger.error(f"RequirementAssignment with id {assignment_id} not found")
        return

    from .email_utils import render_email_template

    ca = assignment.compliance_assessment
    context = {
        "assessment_name": ca.name,
        "reviewer_observation": observation,
    }

    notify("assignment_reopened", _actor_emails(assignment.actor.all()), ca, context)

    for actor in assignment.actor.all():
        for email in actor.get_emails():
            if email and check_email_configuration(email):
                rendered = render_email_template(
                    "assignment_reopened", context, recipient_email=email
                )
                if rendered:
                    send_notification_email(
                        rendered["subject"],
                        rendered["body"],
                        email,
                        rendered.get("html_body"),
                    )


@task()
def send_assignment_reviewed_notification(
    assignment_id, decision, reviewer_observation=""
):
    """Send notification when a RequirementAssignment is reviewed (closed, reopened, or changes_requested)."""
    try:
        assignment = RequirementAssignment.objects.select_related(
            "compliance_assessment",
        ).get(id=assignment_id)
    except RequirementAssignment.DoesNotExist:
        logger.error(f"RequirementAssignment with id {assignment_id} not found")
        return

    from .email_utils import render_email_template

    ca = assignment.compliance_assessment
    context = {
        "assessment_name": ca.name,
        "decision": decision.replace("_", " ").title(),
        "reviewer_observation": reviewer_observation,
    }

    notify("assignment_reviewed", _actor_emails(assignment.actor.all()), ca, context)

    for actor in assignment.actor.all():
        for email in actor.get_emails():
            if email and check_email_configuration(email):
                locale, localized_decision = _localized_assignment_decision(
                    email, decision
                )
                email_context = {
                    **context,
                    "decision": localized_decision,
                }
                rendered = render_email_template(
                    "assignment_reviewed",
                    email_context,
                    locale=locale,
                    recipient_email=email,
                )
                if rendered:
                    send_notification_email(
                        rendered["subject"],
                        rendered["body"],
                        email,
                        rendered.get("html_body"),
                    )


def notify_audit_assignees(audit) -> list:
    """Email everyone holding an assignment on *audit*. Returns the actors that failed."""
    from django.utils.translation import gettext_lazy as _

    failed = []
    # Driven by the assignments, not by `authors`: an actor can be pointed at an
    # assignment without being an author, and iterating authors skips them silently.
    for assignment in audit.requirement_assignments.prefetch_related("actor"):
        for actor in assignment.actor.all():
            try:
                specific = actor.specific
                if not hasattr(specific, "mailing"):
                    logger.warning(
                        "Actor has no mailing method, skipping email",
                        actor=actor,
                        actor_type=type(specific).__name__,
                    )
                    continue
                specific.mailing(
                    email_template_name="tprm/third_party_email.html",
                    subject=_(
                        "CISO Assistant: A questionnaire has been assigned to you"
                    ),
                    object="auditee-assessments",
                    object_id=assignment.id,
                )
            except Exception as e:
                logger.error("Failed to send email", actor=actor, error=e)
                failed.append(str(actor))
    return failed


@task()
def notify_campaign_assignees(campaign_id):
    """Send a campaign's notifications off the request thread: a fan-out is one SMTP round trip per audit."""
    audits = ComplianceAssessment.objects.filter(campaign_id=campaign_id)
    notified = failed = 0
    for audit in audits:
        errors = notify_audit_assignees(audit)
        failed += len(errors)
        notified += 1
    logger.info(
        "campaign notifications sent",
        campaign_id=str(campaign_id),
        audits=notified,
        failed_actors=failed,
    )


# ---------------------------------------------------------------------------
# Quick form notifications
# ---------------------------------------------------------------------------


def _quick_form_context(response) -> dict:
    return {
        "response_name": response.name,
        "quick_form_name": response.quick_form.name,
        "due_date": response.due_date.strftime("%Y-%m-%d")
        if response.due_date
        else "Not set",
        "response_id": str(response.id),
        "observation": response.observation or "",
    }


def _notify_actors(actors, template_name, context, response) -> None:
    from .email_utils import render_email_template

    recipient_emails = _actor_emails(actors)
    notify(template_name, recipient_emails, response, context)

    for email in sorted(recipient_emails):
        if check_email_configuration(email):
            rendered = render_email_template(
                template_name, context, recipient_email=email
            )
            if rendered:
                send_notification_email(
                    rendered["subject"],
                    rendered["body"],
                    email,
                    rendered.get("html_body"),
                )


def _load_quick_form_response(response_id):
    try:
        return QuickFormResponse.objects.select_related("quick_form").get(
            id=response_id
        )
    except QuickFormResponse.DoesNotExist:
        logger.error(f"QuickFormResponse with id {response_id} not found")
        return None


@task()
def send_quick_form_started_notification(response_id):
    """Respondents are told a quick form response is ready for their input."""
    response = _load_quick_form_response(response_id)
    if response is None:
        return
    _notify_actors(
        response.respondents.all(),
        "quick_form_started",
        _quick_form_context(response),
        response,
    )


@task()
def send_quick_form_submitted_notification(response_id):
    """Reviewers are told a quick form response was submitted."""
    response = _load_quick_form_response(response_id)
    if response is None:
        return
    _notify_actors(
        response.reviewers.all(),
        "quick_form_submitted",
        _quick_form_context(response),
        response,
    )


@task()
def send_quick_form_reopened_notification(response_id):
    """Respondents are told a submitted response was sent back to them."""
    response = _load_quick_form_response(response_id)
    if response is None:
        return
    _notify_actors(
        response.respondents.all(),
        "quick_form_reopened",
        _quick_form_context(response),
        response,
    )
