from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

User = get_user_model()
PW = "correct-horse-battery-staple-9"
URL = "/api/iam/password-reset/"


@pytest.mark.django_db
class TestPasswordResetEnumeration:
    @override_settings(EMAIL_HOST="smtp.example.com")
    def test_existing_and_missing_return_identical_response(self):
        User.objects.create_user(email="real@example.com", password=PW)
        client = APIClient()
        with patch("iam.views.send_password_reset_email"):
            hit = client.post(URL, {"email": "real@example.com"}, format="json")
            miss = client.post(URL, {"email": "nobody@example.com"}, format="json")
        assert hit.status_code == miss.status_code == 202
        assert hit.content == miss.content

    @override_settings(EMAIL_HOST="smtp.example.com")
    def test_email_is_always_enqueued_regardless_of_match(self):
        # The view must not branch on whether the email matches an account:
        # a request-side queue write present only for matches is itself a
        # timing oracle. Eligibility is resolved inside the task instead.
        User.objects.create_user(email="real2@example.com", password=PW)
        with patch("iam.views.send_password_reset_email") as enqueue:
            APIClient().post(URL, {"email": "real2@example.com"}, format="json")
            APIClient().post(URL, {"email": "ghost@example.com"}, format="json")
        assert enqueue.call_count == 2
        enqueued_emails = {call.args[0] for call in enqueue.call_args_list}
        assert enqueued_emails == {"real2@example.com", "ghost@example.com"}


@pytest.mark.django_db
class TestSendPasswordResetEmailTask:
    def test_skips_nonexistent_user(self):
        from iam.tasks import send_password_reset_email

        # .call_local() runs the huey task body synchronously in tests.
        send_password_reset_email.call_local("ghost@example.com", "subject")

    def test_sends_for_existing_local_user(self):
        from iam.tasks import send_password_reset_email

        User.objects.create_user(email="real3@example.com", password=PW)
        with patch("iam.models.User.mailing") as mailing:
            send_password_reset_email.call_local("real3@example.com", "subject")
        assert mailing.call_count == 1
        assert mailing.call_args.kwargs["subject"] == "subject"


@pytest.mark.django_db
class TestPasswordResetThrottle:
    """The endpoint is unauthenticated and queues a task per call, so without a
    cap anyone can enqueue unbounded work with random addresses."""

    @override_settings(
        EMAIL_HOST="smtp.example.com", PASSWORD_RESET_THROTTLE_RATE="3/h"
    )
    def test_requests_past_the_rate_are_refused(self):
        client = APIClient()
        with patch("iam.views.send_password_reset_email") as enqueue:
            codes = [
                client.post(
                    URL,
                    {"email": f"spray{i}@example.com"},
                    format="json",
                    HTTP_X_REAL_IP="203.0.113.50",
                ).status_code
                for i in range(4)
            ]
        assert codes == [202, 202, 202, 429], codes
        # The refused request must not have reached the queue.
        assert enqueue.call_count == 3

    @override_settings(
        EMAIL_HOST="smtp.example.com", PASSWORD_RESET_THROTTLE_RATE="3/h"
    )
    def test_each_source_address_gets_its_own_budget(self):
        client = APIClient()
        with patch("iam.views.send_password_reset_email"):
            for i in range(3):
                client.post(
                    URL,
                    {"email": f"a{i}@example.com"},
                    format="json",
                    HTTP_X_REAL_IP="203.0.113.50",
                )
            blocked = client.post(
                URL,
                {"email": "a3@example.com"},
                format="json",
                HTTP_X_REAL_IP="203.0.113.50",
            )
            other = client.post(
                URL,
                {"email": "b0@example.com"},
                format="json",
                HTTP_X_REAL_IP="198.51.100.77",
            )
        assert blocked.status_code == 429
        assert other.status_code == 202
