"""Failed logins are recorded: a log line, and a LOGIN_FAILED audit entry."""

import structlog
from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_login_failed
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver

from core.custom_middleware import resolve_client_ip

logger = structlog.get_logger(__name__)

# Audit log action of a failed login, after django-auditlog's own (0 to 3).
LOGIN_FAILED_ACTION = 4


@receiver(user_login_failed)
def record_failed_login(sender, credentials, request=None, **kwargs):
    # allauth passes the email as "email", other callers of authenticate() as
    # "username".
    username = credentials.get("email") or credentials.get("username")
    if username is None:
        return
    remote_addr = resolve_client_ip(request)

    logger.info("Failed login attempt", remote_addr=remote_addr, username=username)

    LogEntry.objects.create(
        action=LOGIN_FAILED_ACTION,
        content_type=ContentType.objects.get_for_model(get_user_model()),
        object_repr=username,
        remote_addr=remote_addr,
        additional_data={"username": username},
    )
