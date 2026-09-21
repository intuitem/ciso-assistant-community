from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from auditlog.models import LogEntry

from enterprise_core.models import LogEntryAction
from iam.adapter import resolve_client_ip

User = get_user_model()


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username") or credentials.get("email")
    if username is None:
        return
    remote_addr = resolve_client_ip(request)

    LogEntry.objects.create(
        action=LogEntryAction.LOGIN_FAILED,
        content_type=ContentType.objects.get_for_model(User),
        object_repr=username,
        remote_addr=remote_addr,
        additional_data={"username": username},
    )
