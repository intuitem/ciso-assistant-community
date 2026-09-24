from django.contrib.auth.signals import user_login_failed
from django.test import RequestFactory
from structlog.testing import capture_logs


def test_failed_login_is_logged_from_email_credential():
    req = RequestFactory().post("/login", REMOTE_ADDR="203.0.113.7")
    with capture_logs() as logs:
        user_login_failed.send(
            sender=None,
            credentials={"email": "attacker@example.invalid", "password": "x"},
            request=req,
        )
    events = [entry for entry in logs if entry.get("event") == "login_failed"]
    assert len(events) == 1
    assert events[0]["username"] == "attacker@example.invalid"
    assert events[0]["client_ip"] == "203.0.113.7"


def test_missing_identifier_is_not_logged():
    with capture_logs() as logs:
        user_login_failed.send(sender=None, credentials={"password": "x"}, request=None)
    assert not [entry for entry in logs if entry.get("event") == "login_failed"]
