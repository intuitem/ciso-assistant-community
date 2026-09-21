from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from iam.tasks import _do_notify_login_throttled

User = get_user_model()
PW = "correct-horse-battery-staple-9"


def _superuser(email):
    admin = User.objects.create_user(email=email, password=PW)
    admin.is_superuser = True
    admin.save()
    return admin


@pytest.mark.django_db
def test_notify_reaches_superusers_and_account_owner():
    _superuser("admin@example.com")
    User.objects.create_user(email="victim@example.com", password=PW)
    with patch("core.tasks.send_notification_email") as send:
        _do_notify_login_throttled("victim@example.com", "203.0.113.1")
    recipients = [call.args[2] for call in send.call_args_list]
    assert "admin@example.com" in recipients
    assert "victim@example.com" in recipients


@pytest.mark.django_db
def test_notify_unknown_email_alerts_admin_only():
    _superuser("admin@example.com")
    with patch("core.tasks.send_notification_email") as send:
        _do_notify_login_throttled("ghost@example.com", "203.0.113.1")
    recipients = [call.args[2] for call in send.call_args_list]
    assert recipients == ["admin@example.com"]
