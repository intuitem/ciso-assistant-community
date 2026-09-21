from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
import structlog

from iam.adapter import resolve_client_ip

logger = structlog.get_logger(__name__)


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username") or credentials.get("email")
    if not username:
        return
    logger.warning(
        "login_failed",
        username=username,
        client_ip=resolve_client_ip(request),
    )
