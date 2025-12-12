from datetime import date, timedelta
from huey import crontab
from huey.contrib.djhuey import periodic_task, task, db_periodic_task, db_task
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    ValidationFlow,
    FlowEvent,
)
from tprm.models import EntityAssessment
from iam.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
import logging
from global_settings.models import GlobalSettings

import logging.config
import structlog


from django.core.management import call_command

logging.config.dictConfig(settings.LOGGING)
logger = structlog.getLogger(__name__)


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="0"))
def check_controls_with_expired_eta():
    expired_controls = (
        AppliedControl.objects.exclude(status__in=["active", "deprecated"])
        .filter(eta__lt=date.today(), eta__isnull=False)
        .prefetch_related("owner")
    )
    # Group by individual owner
    owner_controls = {}
    for control in expired_controls:
        for owner in control.owner.all():
            if owner.email not in owner_controls:
                owner_controls[owner.email] = []
            owner_controls[owner.email].append(control)
    # Send personalized email to each owner
    for owner_email, controls in owner_controls.items():
        send_notification_email_expired_eta(owner_email, controls)


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="10"))
def check_compliance_assessments_due_in_week():
    """Check for ComplianceAssessments due in 7 days"""
    target_date = date.today() + timedelta(days=7)
    assessments_due_soon = (
        ComplianceAssessment.objects.filter(due_date=target_date)
        .exclude(status__in=["done", "deprecated"])
        .prefetch_related("authors")
    )

    # Group by individual author
    author_assessments = {}
    for assessment in assessments_due_soon:
        for author in assessment.authors.all():
            if author.email not in author_assessments:
                author_assessments[author.email] = []
            author_assessments[author.email].append(assessment)

    # Send personalized email to each author
    for author_email, assessments in author_assessments.items():
        send_compliance_assessment_due_soon_notification(
            author_email, assessments, days=7
        )


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="15"))
def check_compliance_assessments_due_tomorrow():
    """Check for ComplianceAssessments due in 1 day"""
    target_date = date.today() + timedelta(days=1)
    assessments_due_tomorrow = (
        ComplianceAssessment.objects.filter(due_date=target_date)
        .exclude(status__in=["done", "deprecated"])
        .prefetch_related("authors")
    )

    # Group by individual author
    author_assessments = {}
    for assessment in assessments_due_tomorrow:
        for author in assessment.authors.all():
            if author.email not in author_assessments:
                author_assessments[author.email] = []
            author_assessments[author.email].append(assessment)

    # Send personalized email to each author
    for author_email, assessments in author_assessments.items():
        send_compliance_assessment_due_soon_notification(
            author_email, assessments, days=1
        )


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="20"))
def check_applied_controls_expiring_in_week():
    """Check for AppliedControls due in 7 days"""
    target_date = date.today() + timedelta(days=7)
    controls_due_soon = (
        AppliedControl.objects.filter(expiry_date=target_date)
        .exclude(status__in=["deprecated"])
        .prefetch_related("owner")
    )

    # Group by individual owner
    owner_controls = {}
    for control in controls_due_soon:
        for owner in control.owner.all():
            if owner.email not in owner_controls:
                owner_controls[owner.email] = []
            owner_controls[owner.email].append(control)

    # Send personalized email to each owner
    for owner_email, controls in owner_controls.items():
        send_applied_control_expiring_soon_notification(owner_email, controls, days=7)


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="25"))
def check_applied_controls_expiring_tomorrow():
    """Check for AppliedControls due in 1 day"""
    target_date = date.today() + timedelta(days=1)
    controls_due_tomorrow = (
        AppliedControl.objects.filter(expiry_date=target_date)
        .exclude(status__in=["deprecated"])
        .prefetch_related("owner")
    )

    # Group by individual owner
    owner_controls = {}
    for control in controls_due_tomorrow:
        for owner in control.owner.all():
            if owner.email not in owner_controls:
                owner_controls[owner.email] = []
            owner_controls[owner.email].append(control)

    # Send personalized email to each owner
    for owner_email, controls in owner_controls.items():
        send_applied_control_expiring_soon_notification(owner_email, controls, days=1)


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="30"))
def check_evidences_expiring_in_week():
    """Check for Evidences expiring in 7 days"""
    target_date = date.today() + timedelta(days=7)
    evidences_expiring_soon = (
        Evidence.objects.filter(expiry_date=target_date)
        .exclude(status__in=["expired"])
        .prefetch_related("owner")
    )

    # Group by individual owner
    owner_evidences = {}
    for evidence in evidences_expiring_soon:
        for owner in evidence.owner.all():
            if owner.email not in owner_evidences:
                owner_evidences[owner.email] = []
            owner_evidences[owner.email].append(evidence)

    # Send personalized email to each owner
    for owner_email, evidences in owner_evidences.items():
        send_evidence_expiring_soon_notification(owner_email, evidences, days=7)


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="35"))
def check_evidences_expiring_tomorrow():
    """Check for Evidences expiring in 1 day"""
    target_date = date.today() + timedelta(days=1)
    evidences_expiring_tomorrow = (
        Evidence.objects.filter(expiry_date=target_date)
        .exclude(status__in=["expired"])
        .prefetch_related("owner")
    )

    # Group by individual owner
    owner_evidences = {}
    for evidence in evidences_expiring_tomorrow:
        for owner in evidence.owner.all():
            if owner.email not in owner_evidences:
                owner_evidences[owner.email] = []
            owner_evidences[owner.email].append(evidence)

    # Send personalized email to each owner
    for owner_email, evidences in owner_evidences.items():
        send_evidence_expiring_soon_notification(owner_email, evidences, days=1)


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="40"))
def check_validation_flows_deadline_in_week():
    """Check for ValidationFlows with deadline in 7 days (only submitted status)"""
    target_date = date.today() + timedelta(days=7)
    validations_due_soon = ValidationFlow.objects.filter(
        validation_deadline=target_date, status=ValidationFlow.Status.SUBMITTED
    )

    # Group by individual approver
    approver_validations = {}
    for validation in validations_due_soon:
        if validation.approver and validation.approver.email:
            approver_email = validation.approver.email
            if approver_email not in approver_validations:
                approver_validations[approver_email] = []
            approver_validations[approver_email].append(validation)

    # Send personalized email to each approver
    for approver_email, validations in approver_validations.items():
        send_validation_deadline_notification(approver_email, validations, days=7)


# @db_periodic_task(crontab(minute="*/1"))  # for testing
@db_periodic_task(crontab(hour="6", minute="45"))
def check_validation_flows_deadline_tomorrow():
    """Check for ValidationFlows with deadline in 1 day (only submitted status)"""
    target_date = date.today() + timedelta(days=1)
    validations_due_tomorrow = ValidationFlow.objects.filter(
        validation_deadline=target_date, status=ValidationFlow.Status.SUBMITTED
    )

    # Group by individual approver
    approver_validations = {}
    for validation in validations_due_tomorrow:
        if validation.approver and validation.approver.email:
            approver_email = validation.approver.email
            if approver_email not in approver_validations:
                approver_validations[approver_email] = []
            approver_validations[approver_email].append(validation)

    # Send personalized email to each approver
    for approver_email, validations in approver_validations.items():
        send_validation_deadline_notification(approver_email, validations, days=1)


@task()
def send_notification_email_expired_eta(owner_email, controls):
    if not check_email_configuration(owner_email, controls):
        return

    from .email_utils import render_email_template, format_control_list

    context = {
        "control_count": len(controls),
        "control_list": format_control_list(controls),
    }

    rendered = render_email_template("expired_controls", context)
    if rendered:
        send_notification_email(rendered["subject"], rendered["body"], owner_email)
    else:
        logger.error(
            f"Failed to render expired_controls email template for {owner_email}"
        )


@task()
def send_notification_email(subject, message, owner_email):
    try:
        logger.debug(
            "Sending notification email",
            subject=subject,
            message=message,
            recipient=owner_email,
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner_email],
            fail_silently=False,
        )
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


@task()
def check_email_configuration(owner_email, controls):
    notifications_enable_mailing = GlobalSettings.objects.get(name="general").value.get(
        "notifications_enable_mailing", False
    )
    if not notifications_enable_mailing:
        logger.warning(
            "Email notification is disabled. You can enable it under Extra/Settings. Skipping for now."
        )
        return False

    # Check required email settings
    required_settings = ["EMAIL_HOST", "EMAIL_PORT", "DEFAULT_FROM_EMAIL"]
    missing_settings = [
        setting
        for setting in required_settings
        if not hasattr(settings, setting) or not getattr(settings, setting)
    ]

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


@periodic_task(crontab(hour="*/3"))
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

    for email in assigned_user_emails:
        if email and check_email_configuration(email, [control]):
            rendered = render_email_template("applied_control_assignment", context)
            if rendered:
                send_notification_email(rendered["subject"], rendered["body"], email)


@task()
def send_task_template_assignment_notification(task_template_id, assigned_user_emails):
    """Send notification when TaskTemplate is assigned to users"""
    if not assigned_user_emails:
        return

    try:
        from core.models import TaskTemplate

        task_template = TaskTemplate.objects.get(id=task_template_id)
    except TaskTemplate.DoesNotExist:
        logger.error(f"TaskTemplate with id {task_template_id} not found")
        return

    from .email_utils import render_email_template

    context = {
        "task_name": task_template.name,
        "task_description": task_template.description or "No description provided",
        "task_ref_id": task_template.ref_id or "N/A",
        "task_date": task_template.task_date.strftime("%Y-%m-%d")
        if task_template.task_date
        else "Not set",
        "is_recurrent": "Yes" if task_template.is_recurrent else "No",
        "folder_name": task_template.folder.name if task_template.folder else "Default",
    }

    for email in assigned_user_emails:
        if email and check_email_configuration(email, [task_template]):
            rendered = render_email_template("task_template_assignment", context)
            if rendered:
                send_notification_email(rendered["subject"], rendered["body"], email)


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

    context = {
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

    for email in assigned_user_emails:
        if email and check_email_configuration(email, [assessment]):
            rendered = render_email_template(
                "compliance_assessment_assignment", context
            )
            if rendered:
                send_notification_email(rendered["subject"], rendered["body"], email)


@task()
def send_compliance_assessment_due_soon_notification(author_email, assessments, days):
    """Send notification when ComplianceAssessment is due soon"""
    if not check_email_configuration(author_email, assessments):
        return

    from .email_utils import render_email_template, format_assessment_list

    context = {
        "assessment_count": len(assessments),
        "assessment_list": format_assessment_list(assessments),
        "days_remaining": days,
        "days_text": "day" if days == 1 else "days",
    }

    template_name = "compliance_assessment_due_soon"
    rendered = render_email_template(template_name, context)
    if rendered:
        send_notification_email(rendered["subject"], rendered["body"], author_email)
    else:
        logger.error(
            f"Failed to render {template_name} email template for {author_email}"
        )


@task()
def send_applied_control_expiring_soon_notification(owner_email, controls, days):
    """Send notification when AppliedControl is due soon"""
    if not check_email_configuration(owner_email, controls):
        return

    from .email_utils import render_email_template, format_control_list

    context = {
        "control_count": len(controls),
        "control_list": format_control_list(controls),
        "days_remaining": days,
        "days_text": "day" if days == 1 else "days",
    }

    template_name = "applied_control_expiring_soon"
    rendered = render_email_template(template_name, context)
    if rendered:
        send_notification_email(rendered["subject"], rendered["body"], owner_email)
    else:
        logger.error(
            f"Failed to render {template_name} email template for {owner_email}"
        )


@task()
def send_evidence_expiring_soon_notification(owner_email, evidences, days):
    """Send notification when Evidence is expiring soon"""
    if not check_email_configuration(owner_email, evidences):
        return

    from .email_utils import render_email_template, format_evidence_list

    context = {
        "evidence_count": len(evidences),
        "evidence_list": format_evidence_list(evidences),
        "days_remaining": days,
        "days_text": "day" if days == 1 else "days",
    }

    template_name = "evidence_expiring_soon"
    rendered = render_email_template(template_name, context)
    if rendered:
        send_notification_email(rendered["subject"], rendered["body"], owner_email)
    else:
        logger.error(
            f"Failed to render {template_name} email template for {owner_email}"
        )


@task()
def send_validation_flow_created_notification(validation_flow):
    """Send notification to approver when validation flow is created"""
    if not validation_flow.approver or not validation_flow.approver.email:
        logger.warning(
            f"No approver email for validation flow {validation_flow.ref_id}"
        )
        return

    approver_email = validation_flow.approver.email
    if not check_email_configuration(approver_email, [validation_flow]):
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

    rendered = render_email_template("validation_flow_created", context)
    if rendered:
        send_notification_email(rendered["subject"], rendered["body"], approver_email)
        logger.info(
            f"Sent validation flow creation notification to {approver_email} for {validation_flow.ref_id}"
        )
    else:
        logger.error(
            f"Failed to render validation_flow_created email template for {approver_email}"
        )


@task()
def send_validation_deadline_notification(approver_email, validations, days):
    """Send notification about validation deadlines approaching"""
    if not check_email_configuration(approver_email, validations):
        return

    from .email_utils import render_email_template, format_validation_list

    template_name = f"validation_deadline_d{days}"
    s = "s" if len(validations) > 1 else ""
    are = "are" if len(validations) > 1 else "is"
    their = "their" if len(validations) > 1 else "its"

    context = {
        "days": days,
        "validation_list": format_validation_list(validations),
        "validation_count": len(validations),
        "s": s,
        "are": are,
        "their": their,
    }

    rendered = render_email_template(template_name, context)
    if rendered:
        send_notification_email(rendered["subject"], rendered["body"], approver_email)
    else:
        logger.error(
            f"Failed to render {template_name} email template for {approver_email}"
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
