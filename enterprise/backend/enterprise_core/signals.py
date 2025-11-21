from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from auditlog.models import LogEntry
import structlog

from enterprise_core.models import LogEntryAction

logger = structlog.get_logger(__name__)
User = get_user_model()


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username", None)
    if username is None:
        return
    remote_addr = request.META.get("REMOTE_ADDR") if request else None

    logger.info(
        "Failed login attempt",
        remote_addr=remote_addr,
        username=username,
    )

    LogEntry.objects.create(
        action=LogEntryAction.LOGIN_FAILED,
        content_type=ContentType.objects.get_for_model(User),
        object_repr=username,
        remote_addr=remote_addr,
        additional_data={"username": username},
    )
