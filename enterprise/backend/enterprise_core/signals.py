import re

from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from auditlog.models import LogEntry
import structlog

from enterprise_core.models import LogEntryAction

logger = structlog.get_logger(__name__)
User = get_user_model()


def _strip_port(address):
    if address.startswith("["):
        return address[1:].split("]")[0]
    if address.count(":") == 1:
        return address.split(":")[0]
    return address


def get_client_ip(request):
    if not request:
        return None

    forwarded = request.headers.get("Forwarded")
    if forwarded:
        match = re.search(r'for=(?:"([^"]+)"|([^;,\s]+))', forwarded, re.IGNORECASE)
        if match:
            return _strip_port((match.group(1) or match.group(2)).strip('"'))

    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return _strip_port(xff.split(",")[0].strip())

    return request.META.get("REMOTE_ADDR")


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username", None)
    if username is None:
        return
    remote_addr = get_client_ip(request)

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
