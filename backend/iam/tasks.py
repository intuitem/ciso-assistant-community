from huey.contrib.djhuey import db_task
import structlog

logger = structlog.get_logger(__name__)


@db_task()
def send_password_reset_email(user_id, subject):
    from iam.models import User

    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return
    try:
        user.mailing(
            email_template_name="registration/password_reset_email.html",
            subject=subject,
        )
    except Exception as e:
        logger.error(
            "Failed to send password reset email", user_id=str(user_id), error=str(e)
        )


@db_task()
def notify_login_throttled(email, client_ip):
    _do_notify_login_throttled(email, client_ip)


def _do_notify_login_throttled(email, client_ip):
    from django.contrib.auth import get_user_model
    from core.tasks import send_notification_email

    User = get_user_model()

    admin_subject = "CISO Assistant: repeated failed login attempts"
    admin_body = f"Repeated failed login attempts for {email} from IP {client_ip}."
    admin_emails = (
        User.objects.filter(is_superuser=True, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    for admin_email in admin_emails:
        send_notification_email(admin_subject, admin_body, admin_email)

    account = User.objects.filter(email__iexact=email, is_active=True).first()
    if account is not None and account.is_local and account.email:
        send_notification_email(
            "CISO Assistant: failed sign-in attempts on your account",
            "We detected repeated failed sign-in attempts on your account. "
            "If this was not you, consider resetting your password.",
            account.email,
        )
