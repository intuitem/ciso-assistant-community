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
