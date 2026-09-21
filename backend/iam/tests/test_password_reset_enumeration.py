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
    def test_email_is_enqueued_only_for_existing_local_user(self):
        user = User.objects.create_user(email="real2@example.com", password=PW)
        with patch("iam.views.send_password_reset_email") as enqueue:
            APIClient().post(URL, {"email": "real2@example.com"}, format="json")
            APIClient().post(URL, {"email": "ghost@example.com"}, format="json")
        assert enqueue.call_count == 1
        assert enqueue.call_args[0][0] == user.id
