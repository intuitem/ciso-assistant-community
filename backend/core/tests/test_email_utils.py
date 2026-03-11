import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import yaml

from core.email_utils import (
    load_email_template,
    render_email_template,
    format_control_list,
    format_assessment_list,
    format_evidence_list,
    format_validation_list,
    format_task_node_list,
    get_default_context,
    send_templated_notification,
    TEMPLATE_BASE_PATH,
)


@pytest.fixture
def mock_template_data():
    return {
        "subject": "Test Subject: $control_name",
        "body": "Hello $user_name, this is a test body with $control_name"
    }


@pytest.fixture
def mock_control():
    control = MagicMock()
    control.name = "Test Control"
    control.eta = None
    return control


@pytest.fixture
def mock_control_with_eta():
    from datetime import date
    control = MagicMock()
    control.name = "Test Control with ETA"
    control.eta = date(2026, 12, 31)
    return control


@pytest.fixture
def mock_assessment():
    assessment = MagicMock()
    assessment.name = "Test Assessment"
    assessment.framework = MagicMock()
    assessment.framework.name = "ISO 27001"
    assessment.due_date = None
    return assessment


@pytest.fixture
def mock_evidence():
    from datetime import date
    evidence = MagicMock()
    evidence.name = "Test Evidence"
    evidence.expiry_date = date(2026, 6, 30)
    evidence.status = "valid"
    evidence.get_status_display = MagicMock(return_value="Valid")
    return evidence


@pytest.fixture
def mock_validation_flow():
    from datetime import date
    validation = MagicMock()
    validation.ref_id = "VAL-001"
    validation.validation_deadline = date(2026, 5, 15)
    validation.requester = MagicMock()
    validation.requester.first_name = "John"
    validation.requester.last_name = "Doe"
    validation.requester.email = "john.doe@example.com"
    return validation


@pytest.fixture
def mock_task_node():
    from datetime import date
    node = MagicMock()
    node.task_template = MagicMock()
    node.task_template.name = "Test Task"
    node.due_date = date(2026, 7, 1)
    node.status = "pending"
    return node


class TestLoadEmailTemplate:
    """Tests for load_email_template function"""

    def test_load_template_success_default_locale(self, mock_template_data):
        """Test loading template with default locale (English)"""
        template_path = TEMPLATE_BASE_PATH / "en" / "test_template.yaml"

        with patch("builtins.open", mock_open(read_data=yaml.dump(mock_template_data))):
            with patch.object(Path, "exists", return_value=True):
                result = load_email_template("test_template", locale="en")

        assert result == mock_template_data
        assert "subject" in result
        assert "body" in result

    def test_load_template_with_explicit_locale(self, mock_template_data):
        """Test loading template with explicit French locale"""
        with patch("builtins.open", mock_open(read_data=yaml.dump(mock_template_data))):
            with patch.object(Path, "exists", return_value=True):
                result = load_email_template("test_template", locale="fr")

        assert result == mock_template_data

    def test_load_template_fallback_to_english(self, mock_template_data):
        """Test fallback to English when locale-specific template doesn't exist"""
        def exists_side_effect(path):
            # Simulate that French template doesn't exist but English does
            return "en" in str(path)

        with patch("builtins.open", mock_open(read_data=yaml.dump(mock_template_data))):
            with patch.object(Path, "exists", side_effect=exists_side_effect):
                result = load_email_template("test_template", locale="fr")

        assert result == mock_template_data

    def test_load_template_not_found(self):
        """Test when template file doesn't exist"""
        with patch.object(Path, "exists", return_value=False):
            result = load_email_template("nonexistent_template", locale="en")

        assert result is None

    def test_load_template_invalid_structure(self):
        """Test loading template with invalid structure (missing required keys)"""
        invalid_data = {"subject": "Only subject"}

        with patch("builtins.open", mock_open(read_data=yaml.dump(invalid_data))):
            with patch.object(Path, "exists", return_value=True):
                result = load_email_template("test_template", locale="en")

        assert result is None

    def test_load_template_yaml_parse_error(self):
        """Test handling of YAML parsing errors"""
        with patch("builtins.open", mock_open(read_data="invalid: yaml: content:")):
            with patch.object(Path, "exists", return_value=True):
                result = load_email_template("test_template", locale="en")

        # Should return None on parse error
        assert result is None

    def test_load_template_locale_with_hyphen(self, mock_template_data):
        """Test locale extraction from 'en-us' format to 'en'"""
        with patch("builtins.open", mock_open(read_data=yaml.dump(mock_template_data))):
            with patch.object(Path, "exists", return_value=True):
                with patch("core.email_utils.get_language", return_value="en-us"):
                    result = load_email_template("test_template", locale=None)

        assert result == mock_template_data


class TestRenderEmailTemplate:
    """Tests for render_email_template function"""

    def test_render_template_success(self, mock_template_data):
        """Test successful template rendering with context variables"""
        context = {
            "control_name": "Access Control",
            "user_name": "Alice"
        }

        with patch("core.email_utils.load_email_template", return_value=mock_template_data):
            result = render_email_template("test_template", context, locale="en")

        assert result["subject"] == "Test Subject: Access Control"
        assert "Access Control" in result["body"]
        assert "Alice" in result["body"]

    def test_render_template_with_default_context(self, mock_template_data):
        """Test that default context variables (like CISO URL) are included"""
        template_data = {
            "subject": "Test",
            "body": "Visit $ciso_assistant_url"
        }

        with patch("core.email_utils.load_email_template", return_value=template_data):
            result = render_email_template("test_template", {}, locale="en")

        # Should contain the default CISO assistant URL
        assert "http://" in result["body"] or "https://" in result["body"]

    def test_render_template_not_found(self):
        """Test rendering when template is not found"""
        with patch("core.email_utils.load_email_template", return_value=None):
            result = render_email_template("nonexistent", {}, locale="en")

        assert result == {}

    def test_render_template_safe_substitute(self):
        """Test that safe_substitute doesn't error on missing variables"""
        template_data = {
            "subject": "Test $missing_var",
            "body": "Hello $existing_var and $another_missing"
        }
        context = {"existing_var": "World"}

        with patch("core.email_utils.load_email_template", return_value=template_data):
            result = render_email_template("test_template", context, locale="en")

        # safe_substitute should leave missing variables as-is
        assert result["subject"] == "Test $missing_var"
        assert "World" in result["body"]

    def test_render_template_rendering_exception(self):
        """Test error handling during template rendering"""
        with patch("core.email_utils.load_email_template", side_effect=Exception("Render error")):
            result = render_email_template("test_template", {}, locale="en")

        assert result == {}


class TestFormatControlList:
    """Tests for format_control_list function"""

    def test_format_control_list_with_eta(self, mock_control_with_eta):
        """Test formatting controls with ETA"""
        controls = [mock_control_with_eta]
        result = format_control_list(controls)

        assert "Test Control with ETA" in result
        assert "2026-12-31" in result
        assert "ETA:" in result

    def test_format_control_list_without_eta(self, mock_control):
        """Test formatting controls without ETA"""
        controls = [mock_control]
        result = format_control_list(controls)

        assert "Test Control" in result
        assert "ETA:" not in result

    def test_format_control_list_multiple(self, mock_control, mock_control_with_eta):
        """Test formatting multiple controls"""
        controls = [mock_control, mock_control_with_eta]
        result = format_control_list(controls)

        lines = result.split("\n")
        assert len(lines) == 2
        assert all(line.startswith("- ") for line in lines)

    def test_format_control_list_empty(self):
        """Test formatting empty control list"""
        result = format_control_list([])
        assert result == ""


class TestFormatAssessmentList:
    """Tests for format_assessment_list function"""

    def test_format_assessment_list_with_due_date(self, mock_assessment):
        """Test formatting assessment with due date"""
        from datetime import date
        mock_assessment.due_date = date(2026, 12, 31)

        assessments = [mock_assessment]
        result = format_assessment_list(assessments)

        assert "Test Assessment" in result
        assert "ISO 27001" in result
        assert "2026-12-31" in result

    def test_format_assessment_list_without_due_date(self, mock_assessment):
        """Test formatting assessment without due date"""
        assessments = [mock_assessment]
        result = format_assessment_list(assessments)

        assert "Test Assessment" in result
        assert "Not set" in result

    def test_format_assessment_list_no_framework(self, mock_assessment):
        """Test formatting assessment without framework"""
        mock_assessment.framework = None
        assessments = [mock_assessment]
        result = format_assessment_list(assessments)

        assert "No framework" in result

    def test_format_assessment_list_empty(self):
        """Test formatting empty assessment list"""
        result = format_assessment_list([])
        assert result == ""


class TestFormatEvidenceList:
    """Tests for format_evidence_list function"""

    def test_format_evidence_list_with_expiry(self, mock_evidence):
        """Test formatting evidence with expiry date"""
        evidences = [mock_evidence]
        result = format_evidence_list(evidences)

        assert "Test Evidence" in result
        assert "Valid" in result
        assert "2026-06-30" in result

    def test_format_evidence_list_without_display_method(self, mock_evidence):
        """Test formatting evidence without get_status_display method"""
        mock_evidence.get_status_display = None
        mock_evidence.status = "active"
        evidences = [mock_evidence]
        result = format_evidence_list(evidences)

        assert "active" in result

    def test_format_evidence_list_empty(self):
        """Test formatting empty evidence list"""
        result = format_evidence_list([])
        assert result == ""


class TestFormatValidationList:
    """Tests for format_validation_list function"""

    def test_format_validation_list_with_full_name(self, mock_validation_flow):
        """Test formatting validation with requester full name"""
        validations = [mock_validation_flow]
        result = format_validation_list(validations)

        assert "VAL-001" in result
        assert "John Doe" in result
        assert "2026-05-15" in result

    def test_format_validation_list_email_fallback(self, mock_validation_flow):
        """Test formatting validation when requester has no name (falls back to email)"""
        mock_validation_flow.requester.first_name = ""
        mock_validation_flow.requester.last_name = ""
        validations = [mock_validation_flow]
        result = format_validation_list(validations)

        assert "john.doe@example.com" in result

    def test_format_validation_list_no_requester(self, mock_validation_flow):
        """Test formatting validation with no requester"""
        mock_validation_flow.requester = None
        validations = [mock_validation_flow]
        result = format_validation_list(validations)

        assert "Unknown" in result

    def test_format_validation_list_empty(self):
        """Test formatting empty validation list"""
        result = format_validation_list([])
        assert result == ""


class TestFormatTaskNodeList:
    """Tests for format_task_node_list function"""

    def test_format_task_node_list_standard(self, mock_task_node):
        """Test formatting task nodes with standard information"""
        nodes = [mock_task_node]
        result = format_task_node_list(nodes)

        assert "Test Task" in result
        assert "2026-07-01" in result
        assert "pending" in result

    def test_format_task_node_list_no_template(self, mock_task_node):
        """Test formatting task nodes when template is None"""
        mock_task_node.task_template = None
        nodes = [mock_task_node]
        result = format_task_node_list(nodes)

        assert "Unknown" in result

    def test_format_task_node_list_no_due_date(self, mock_task_node):
        """Test formatting task nodes without due date"""
        mock_task_node.due_date = None
        nodes = [mock_task_node]
        result = format_task_node_list(nodes)

        assert "Not set" in result

    def test_format_task_node_list_empty(self):
        """Test formatting empty task node list"""
        result = format_task_node_list([])
        assert result == ""


class TestGetDefaultContext:
    """Tests for get_default_context function"""

    def test_get_default_context_with_setting(self):
        """Test that default context includes CISO assistant URL from settings"""
        with patch("django.conf.settings.CISO_ASSISTANT_URL", "https://custom.ciso.url"):
            result = get_default_context()

        assert "ciso_assistant_url" in result
        assert result["ciso_assistant_url"] == "https://custom.ciso.url"

    def test_get_default_context_fallback(self):
        """Test default context fallback when setting is not present"""
        with patch("django.conf.settings.CISO_ASSISTANT_URL", "http://localhost:5173"):
            result = get_default_context()

        assert result["ciso_assistant_url"] == "http://localhost:5173"


class TestSendTemplatedNotification:
    """Tests for send_templated_notification function"""

    @patch("core.email_utils.send_notification_email")
    @patch("core.email_utils.check_email_configuration")
    @patch("core.email_utils.render_email_template")
    def test_send_templated_notification_success(self, mock_render, mock_check, mock_send):
        """Test successful sending of templated notification"""
        mock_check.return_value = True
        mock_render.return_value = {
            "subject": "Test Subject",
            "body": "Test Body"
        }

        result = send_templated_notification(
            "test_template",
            {"key": "value"},
            "test@example.com",
            locale="en"
        )

        assert result is True
        mock_check.assert_called_once()
        mock_render.assert_called_once_with("test_template", {"key": "value"}, "en")
        mock_send.assert_called_once_with("Test Subject", "Test Body", "test@example.com")

    @patch("core.email_utils.check_email_configuration")
    def test_send_templated_notification_email_config_fails(self, mock_check):
        """Test notification sending when email configuration check fails"""
        mock_check.return_value = False

        result = send_templated_notification(
            "test_template",
            {},
            "test@example.com"
        )

        assert result is False

    @patch("core.email_utils.check_email_configuration")
    @patch("core.email_utils.render_email_template")
    def test_send_templated_notification_template_render_fails(self, mock_render, mock_check):
        """Test notification sending when template rendering fails"""
        mock_check.return_value = True
        mock_render.return_value = None

        result = send_templated_notification(
            "test_template",
            {},
            "test@example.com"
        )

        assert result is False

    @patch("core.email_utils.check_email_configuration")
    @patch("core.email_utils.render_email_template")
    def test_send_templated_notification_empty_rendered(self, mock_render, mock_check):
        """Test notification sending when rendered template is empty dict"""
        mock_check.return_value = True
        mock_render.return_value = {}

        result = send_templated_notification(
            "test_template",
            {},
            "test@example.com"
        )

        assert result is False