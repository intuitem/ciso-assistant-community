"""Publish-time config validation for the actions that only checked themselves
at run time. A graph that cannot work should say so while its author is looking
at it, not on the night the schedule first fires.

The coverage test is the point of the exercise: a new action type either
validates its config or declares that it has nothing to validate.
"""

import pytest

from automation.workflows.actions import (
    ACTION_CONFIG_VALIDATORS,
    ACTION_REGISTRY,
    ACTIONS_WITHOUT_CONFIG_VALIDATION,
    validate_action_config,
    validate_group_membership_config,
    validate_http_request_config,
    validate_provision_folder_config,
    validate_provision_user_config,
    validate_send_email_config,
)
from automation.workflows.models import WorkflowNode


def codes(errors):
    return {code for code, _ in errors}


def node(config):
    return WorkflowNode(action_config=config)


class TestCoverage:
    def test_every_action_type_is_accounted_for(self):
        covered = set(ACTION_CONFIG_VALIDATORS) | ACTIONS_WITHOUT_CONFIG_VALIDATION
        assert set(ACTION_REGISTRY) == covered

    def test_the_dispatch_reaches_each_validator(self):
        assert codes(
            validate_action_config(node({"type": "provision_user", "email": ""}))
        ) == {"action_provision_user_missing_email"}

    def test_an_action_with_nothing_to_check_passes(self):
        assert validate_action_config(node({"type": "log", "message": ""})) == []


class TestHttpRequest:
    def test_a_missing_url_is_caught(self):
        assert "action_http_missing_url" in codes(
            validate_http_request_config(node({"type": "http_request"}))
        )

    def test_an_unsupported_method_is_caught(self):
        assert "action_http_bad_method" in codes(
            validate_http_request_config(
                node(
                    {
                        "type": "http_request",
                        "url": "https://example.com",
                        "method": "TRACE",
                    }
                )
            )
        )

    def test_a_timeout_outside_the_clamp_is_caught(self):
        """The action silently clamps, so 120 quietly became 30 and the author
        never learned their timeout was not the one in the box."""
        for timeout in (0, 120, "soon"):
            assert "action_http_bad_timeout" in codes(
                validate_http_request_config(
                    node(
                        {
                            "type": "http_request",
                            "url": "https://example.com",
                            "timeout": timeout,
                        }
                    )
                )
            ), timeout

    def test_a_templated_timeout_is_left_alone(self):
        assert (
            validate_http_request_config(
                node(
                    {
                        "type": "http_request",
                        "url": "https://example.com",
                        "timeout": "{{seconds}}",
                    }
                )
            )
            == []
        )

    def test_a_secret_over_cleartext_is_caught_at_publish(self):
        assert "action_http_credentials_need_https" in codes(
            validate_http_request_config(
                node(
                    {
                        "type": "http_request",
                        "url": "http://example.com/report",
                        "headers": {"X-Api-Key": "{{secrets.token}}"},
                    }
                )
            )
        )

    def test_an_authorization_header_over_cleartext_is_caught(self):
        assert "action_http_credentials_need_https" in codes(
            validate_http_request_config(
                node(
                    {
                        "type": "http_request",
                        "url": "http://example.com/report",
                        "headers": {"Authorization": "Bearer abc"},
                    }
                )
            )
        )

    def test_the_same_call_over_https_passes(self):
        assert (
            validate_http_request_config(
                node(
                    {
                        "type": "http_request",
                        "url": "https://example.com/report",
                        "headers": {"Authorization": "Bearer {{secrets.token}}"},
                        "method": "POST",
                        "timeout": 20,
                    }
                )
            )
            == []
        )

    def test_a_templated_url_carrying_a_secret_waits_for_run_time(self):
        """The scheme is not knowable yet; _assert_credentials_stay_encrypted
        still refuses it on the run."""
        assert (
            validate_http_request_config(
                node(
                    {
                        "type": "http_request",
                        "url": "{{base_url}}/report",
                        "headers": {"Authorization": "Bearer {{secrets.token}}"},
                    }
                )
            )
            == []
        )

    def test_headers_that_are_not_pairs_are_caught(self):
        assert "action_http_bad_headers" in codes(
            validate_http_request_config(
                node(
                    {
                        "type": "http_request",
                        "url": "https://example.com",
                        "headers": "Authorization: Bearer abc",
                    }
                )
            )
        )


class TestSendEmail:
    def test_no_recipients_is_caught(self):
        assert codes(validate_send_email_config(node({"type": "send_email"}))) == {
            "action_email_missing_recipients"
        }

    def test_a_malformed_recipient_is_caught(self):
        assert "action_email_bad_recipient" in codes(
            validate_send_email_config(
                node({"type": "send_email", "recipients": "ops@example.com, not-email"})
            )
        )

    def test_display_names_and_templates_pass(self):
        assert (
            validate_send_email_config(
                node(
                    {
                        "type": "send_email",
                        "recipients": "Jane Doe <jane@example.com>,{{owner_email}}",
                    }
                )
            )
            == []
        )


class TestProvisioning:
    def test_a_folder_needs_a_name(self):
        assert codes(
            validate_provision_folder_config(node({"type": "provision_folder"}))
        ) == {"action_provision_folder_missing_name"}

    def test_a_user_needs_an_email(self):
        assert codes(
            validate_provision_user_config(node({"type": "provision_user"}))
        ) == {"action_provision_user_missing_email"}

    def test_a_malformed_email_is_caught(self):
        assert codes(
            validate_provision_user_config(
                node({"type": "provision_user", "email": "jane.example.com"})
            )
        ) == {"action_provision_user_bad_email"}

    def test_a_templated_email_waits_for_run_time(self):
        assert (
            validate_provision_user_config(
                node({"type": "provision_user", "email": "{{payload.email}}"})
            )
            == []
        )


class TestGroupMembership:
    def test_a_membership_change_needs_a_user_and_a_target(self):
        assert codes(
            validate_group_membership_config(node({"type": "manage_group_membership"}))
        ) == {"action_group_missing_user", "action_group_missing_target"}

    def test_a_folder_without_a_builtin_code_is_not_a_target(self):
        assert "action_group_missing_target" in codes(
            validate_group_membership_config(
                node(
                    {
                        "type": "manage_group_membership",
                        "user": "jane@example.com",
                        "folder": "{{folder_id}}",
                    }
                )
            )
        )

    def test_an_unknown_operation_is_caught(self):
        """It used to fall through to the add branch, so a typo did the
        opposite of what it said."""
        assert "action_group_bad_operation" in codes(
            validate_group_membership_config(
                node(
                    {
                        "type": "manage_group_membership",
                        "user": "jane@example.com",
                        "group": "{{group_id}}",
                        "operation": "delete",
                    }
                )
            )
        )

    def test_a_sound_config_passes(self):
        assert (
            validate_group_membership_config(
                node(
                    {
                        "type": "manage_group_membership",
                        "user": "{{nodes.provision.user_email}}",
                        "folder": "{{nodes.domain.folder_id}}",
                        "builtin_group": "BI-UG-ANA",
                        "operation": "add",
                    }
                )
            )
            == []
        )


@pytest.mark.django_db
class TestItReachesPublish:
    """The dispatch is wired into validate_graph, not just callable."""

    def test_publishing_a_broken_http_node_reports_it(self):
        import uuid

        from iam.models import Folder
        from automation.workflows.graph import save_graph
        from automation.workflows.models import Workflow, WorkflowVersion
        from automation.workflows.validation import validate_graph

        folder = Folder.objects.create(
            name=f"Publish {uuid.uuid4()}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        workflow = Workflow.objects.create(name=f"Broken {uuid.uuid4()}", folder=folder)
        version = WorkflowVersion.objects.create(workflow=workflow)

        def raw(type_, **kwargs):
            return {
                "id": str(uuid.uuid4()),
                "type": type_,
                "position": {"x": 0, "y": 0},
                **kwargs,
            }

        start = raw("trigger", trigger_config={"type": "manual"})
        act = raw(
            "action",
            label="Fetch",
            action_config={"type": "http_request", "method": "TRACE"},
        )
        end = raw("end")
        save_graph(
            version,
            {
                "nodes": [start, act, end],
                "edges": [
                    {
                        "id": str(uuid.uuid4()),
                        "source": start["id"],
                        "target": act["id"],
                    },
                    {"id": str(uuid.uuid4()), "source": act["id"], "target": end["id"]},
                ],
            },
        )
        reported = {error["code"] for error in validate_graph(version)}
        assert {"action_http_missing_url", "action_http_bad_method"} <= reported
