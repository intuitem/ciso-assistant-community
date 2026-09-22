from huey.contrib.djhuey import db_task
import structlog

logger = structlog.get_logger(__name__)


@db_task()
def send_password_reset_email(email, subject):
    from global_settings.models import GlobalSettings
    from iam.models import User

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        logger.info("Password reset requested for non-existent user", email=email)
        return
    if not user.is_active:
        logger.info(
            "Password reset requested for inactive user",
            email=email,
            user_id=user.id,
        )
        return
    if not user.is_local:
        try:
            sso_settings = GlobalSettings.objects.get(
                name=GlobalSettings.Names.SSO
            ).value
        except GlobalSettings.DoesNotExist:
            sso_settings = {}
        logger.info(
            "Password reset requested for non-local user",
            email=email,
            user_id=user.id,
            keep_local_login=user.keep_local_login,
            sso_enabled=sso_settings.get("is_enabled", False),
            sso_forced=sso_settings.get("force_sso", False),
        )
        return

    try:
        user.mailing(
            email_template_name="registration/password_reset_email.html",
            subject=subject,
        )
    except Exception as e:
        logger.error(
            "Failed to send password reset email", user_id=str(user.id), error=str(e)
        )
