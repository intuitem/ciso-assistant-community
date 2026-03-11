import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, call
from collections import defaultdict

from core.tasks import (
    check_email_configuration,
    send_notification_email,
    send_task_node_due_soon_notification,
    send_task_node_overdue_notification,
    _get_task_recurrence_interval_days,
)


@pytest.fixture
def mock_global_settings():
    """Mock GlobalSettings for email configuration"""
    with patch("core.tasks.GlobalSettings") as mock_settings:
        mock_obj = MagicMock()
        mock_obj.value.get.return_value = True
        mock_settings.objects.get.return_value = mock_obj
        yield mock_settings


@pytest.fixture
def mock_email_settings():
    """Mock Django email settings"""
    with patch("core.tasks.settings") as mock_settings:
        mock_settings.EMAIL_HOST = "smtp.example.com"
        mock_settings.EMAIL_PORT = 587
        mock_settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
        yield mock_settings


class TestCheckEmailConfiguration:
    """Tests for check_email_configuration function"""

    def test_check_email_configuration_success(self, mock_global_settings, mock_email_settings):
        """Test successful email configuration check"""
        result = check_email_configuration("test@example.com", [])
        assert result is True

    def test_check_email_configuration_disabled(self, mock_global_settings, mock_email_settings):
        """Test when email notifications are disabled"""
        mock_obj = MagicMock()
        mock_obj.value.get.return_value = False
        mock_global_settings.objects.get.return_value = mock_obj

        result = check_email_configuration("test@example.com", [])
        assert result is False

    def test_check_email_configuration_missing_host(self, mock_global_settings):
        """Test when EMAIL_HOST is missing"""
        with patch("core.tasks.settings") as mock_settings:
            mock_settings.EMAIL_HOST = None
            mock_settings.EMAIL_PORT = 587
            mock_settings.DEFAULT_FROM_EMAIL = "noreply@example.com"

            result = check_email_configuration("test@example.com", [])
            assert result is False

    def test_check_email_configuration_missing_port(self, mock_global_settings):
        """Test when EMAIL_PORT is missing"""
        with patch("core.tasks.settings") as mock_settings:
            mock_settings.EMAIL_HOST = "smtp.example.com"
            mock_settings.EMAIL_PORT = None
            mock_settings.DEFAULT_FROM_EMAIL = "noreply@example.com"

            result = check_email_configuration("test@example.com", [])
            assert result is False

    def test_check_email_configuration_missing_from_email(self, mock_global_settings):
        """Test when DEFAULT_FROM_EMAIL is missing"""
        with patch("core.tasks.settings") as mock_settings:
            mock_settings.EMAIL_HOST = "smtp.example.com"
            mock_settings.EMAIL_PORT = 587
            mock_settings.DEFAULT_FROM_EMAIL = None

            result = check_email_configuration("test@example.com", [])
            assert result is False

    def test_check_email_configuration_no_recipient(self, mock_global_settings, mock_email_settings):
        """Test when no recipient email is provided"""
        result = check_email_configuration(None, [])
        assert result is False

    def test_check_email_configuration_empty_recipient(self, mock_global_settings, mock_email_settings):
        """Test when recipient email is empty string"""
        result = check_email_configuration("", [])
        assert result is False


class TestSendNotificationEmail:
    """Tests for send_notification_email function"""

    @patch("core.tasks.send_mail")
    def test_send_notification_email_success(self, mock_send_mail):
        """Test successful email sending"""
        with patch("core.tasks.settings") as mock_settings:
            mock_settings.DEFAULT_FROM_EMAIL = "noreply@example.com"

            send_notification_email("Test Subject", "Test Message", "recipient@example.com")

            mock_send_mail.assert_called_once_with(
                subject="Test Subject",
                message="Test Message",
                from_email="noreply@example.com",
                recipient_list=["recipient@example.com"],
                fail_silently=False
            )

    @patch("core.tasks.send_mail")
    def test_send_notification_email_failure(self, mock_send_mail):
        """Test email sending failure handling"""
        mock_send_mail.side_effect = Exception("SMTP error")

        with patch("core.tasks.settings") as mock_settings:
            mock_settings.DEFAULT_FROM_EMAIL = "noreply@example.com"

            # Should not raise exception, only log error
            send_notification_email("Test Subject", "Test Message", "recipient@example.com")


class TestGetTaskRecurrenceIntervalDays:
    """Tests for _get_task_recurrence_interval_days function"""

    def test_non_recurrent_task(self):
        """Test that non-recurrent tasks return None"""
        task = MagicMock()
        task.is_recurrent = False
        task.schedule = {"frequency": "DAILY", "interval": 1}

        result = _get_task_recurrence_interval_days(task)
        assert result is None

    def test_recurrent_task_no_schedule(self):
        """Test that recurrent tasks without schedule return None"""
        task = MagicMock()
        task.is_recurrent = True
        task.schedule = None

        result = _get_task_recurrence_interval_days(task)
        assert result is None

    def test_daily_recurrence(self):
        """Test daily recurrence interval calculation"""
        task = MagicMock()
        task.is_recurrent = True
        task.schedule = {"frequency": "DAILY", "interval": 2}

        result = _get_task_recurrence_interval_days(task)
        assert result == 2  # 2 days

    def test_weekly_recurrence(self):
        """Test weekly recurrence interval calculation"""
        task = MagicMock()
        task.is_recurrent = True
        task.schedule = {"frequency": "WEEKLY", "interval": 3}

        result = _get_task_recurrence_interval_days(task)
        assert result == 21  # 3 weeks * 7 days

    def test_monthly_recurrence(self):
        """Test monthly recurrence interval calculation"""
        task = MagicMock()
        task.is_recurrent = True
        task.schedule = {"frequency": "MONTHLY", "interval": 2}

        result = _get_task_recurrence_interval_days(task)
        assert result == 60  # 2 months * 30 days (approximate)

    def test_yearly_recurrence(self):
        """Test yearly recurrence interval calculation"""
        task = MagicMock()
        task.is_recurrent = True
        task.schedule = {"frequency": "YEARLY", "interval": 1}

        result = _get_task_recurrence_interval_days(task)
        assert result == 365  # 1 year * 365 days

    def test_unknown_frequency(self):
        """Test unknown frequency defaults to multiplier of 1"""
        task = MagicMock()
        task.is_recurrent = True
        task.schedule = {"frequency": "UNKNOWN", "interval": 5}

        result = _get_task_recurrence_interval_days(task)
        assert result == 5  # 5 * 1 (default multiplier)

    def test_default_interval(self):
        """Test that default interval is 1 when not specified"""
        task = MagicMock()
        task.is_recurrent = True
        task.schedule = {"frequency": "WEEKLY"}  # No interval specified

        result = _get_task_recurrence_interval_days(task)
        assert result == 7  # 1 week * 7 days (default interval=1)


class TestSendTaskNodeDueSoonNotification:
    """Tests for send_task_node_due_soon_notification function"""

    @patch("core.tasks.send_notification_email")
    @patch("core.tasks.render_email_template")
    @patch("core.tasks.check_email_configuration")
    def test_send_task_node_due_soon_success(self, mock_check, mock_render, mock_send):
        """Test successful task node due soon notification"""
        mock_check.return_value = True
        mock_render.return_value = {
            "subject": "Tasks due in 30 days",
            "body": "You have 2 tasks due soon"
        }

        task_nodes = [MagicMock(), MagicMock()]
        send_task_node_due_soon_notification("test@example.com", task_nodes, days=30)

        mock_check.assert_called_once_with("test@example.com", task_nodes)
        assert mock_render.call_args[0][0] == "task_node_due_soon"
        assert mock_render.call_args[0][1]["task_count"] == 2
        assert mock_render.call_args[0][1]["days_remaining"] == 30
        mock_send.assert_called_once()

    @patch("core.tasks.check_email_configuration")
    def test_send_task_node_due_soon_email_config_fails(self, mock_check):
        """Test when email configuration check fails"""
        mock_check.return_value = False

        task_nodes = [MagicMock()]
        send_task_node_due_soon_notification("test@example.com", task_nodes, days=7)

        # Should return early without sending
        mock_check.assert_called_once()

    @patch("core.tasks.send_notification_email")
    @patch("core.tasks.render_email_template")
    @patch("core.tasks.check_email_configuration")
    def test_send_task_node_due_soon_template_render_fails(self, mock_check, mock_render, mock_send):
        """Test when template rendering fails"""
        mock_check.return_value = True
        mock_render.return_value = None

        task_nodes = [MagicMock()]
        send_task_node_due_soon_notification("test@example.com", task_nodes, days=1)

        # Should not send email when template rendering fails
        mock_send.assert_not_called()


class TestSendTaskNodeOverdueNotification:
    """Tests for send_task_node_overdue_notification function"""

    @patch("core.tasks.send_notification_email")
    @patch("core.tasks.render_email_template")
    @patch("core.tasks.check_email_configuration")
    def test_send_task_node_overdue_success(self, mock_check, mock_render, mock_send):
        """Test successful task node overdue notification"""
        mock_check.return_value = True
        mock_render.return_value = {
            "subject": "Overdue tasks",
            "body": "You have 3 overdue tasks"
        }

        task_nodes = [MagicMock(), MagicMock(), MagicMock()]
        send_task_node_overdue_notification("test@example.com", task_nodes)

        mock_check.assert_called_once_with("test@example.com", task_nodes)
        assert mock_render.call_args[0][0] == "task_node_overdue"
        assert mock_render.call_args[0][1]["task_count"] == 3
        mock_send.assert_called_once()

    @patch("core.tasks.check_email_configuration")
    def test_send_task_node_overdue_email_config_fails(self, mock_check):
        """Test when email configuration check fails"""
        mock_check.return_value = False

        task_nodes = [MagicMock()]
        send_task_node_overdue_notification("test@example.com", task_nodes)

        # Should return early without sending
        mock_check.assert_called_once()

    @patch("core.tasks.send_notification_email")
    @patch("core.tasks.render_email_template")
    @patch("core.tasks.check_email_configuration")
    def test_send_task_node_overdue_template_render_fails(self, mock_check, mock_render, mock_send):
        """Test when template rendering fails"""
        mock_check.return_value = True
        mock_render.return_value = None

        task_nodes = [MagicMock()]
        send_task_node_overdue_notification("test@example.com", task_nodes)

        # Should not send email when template rendering fails
        mock_send.assert_not_called()


class TestNotificationEdgeCases:
    """Edge case tests for notification functions"""

    @patch("core.tasks.send_notification_email")
    @patch("core.tasks.render_email_template")
    @patch("core.tasks.check_email_configuration")
    def test_empty_task_node_list(self, mock_check, mock_render, mock_send):
        """Test notification with empty task node list"""
        mock_check.return_value = True
        mock_render.return_value = {
            "subject": "No tasks",
            "body": "Empty list"
        }

        send_task_node_due_soon_notification("test@example.com", [], days=7)

        # Should still attempt to send even with empty list
        assert mock_render.call_args[0][1]["task_count"] == 0

    def test_task_recurrence_edge_cases(self):
        """Test edge cases for task recurrence interval calculation"""
        # Test with missing interval in schedule
        task = MagicMock()
        task.is_recurrent = True
        task.schedule = {"frequency": "DAILY"}  # Missing interval

        result = _get_task_recurrence_interval_days(task)
        assert result == 1  # Should default to interval=1

        # Test with interval of 0 (edge case)
        task.schedule = {"frequency": "WEEKLY", "interval": 0}
        result = _get_task_recurrence_interval_days(task)
        assert result == 0  # 0 weeks * 7 days