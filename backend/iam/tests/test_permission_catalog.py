"""The permissions offered when building a custom role."""

import pytest
from django.contrib.auth.models import Permission

from core.startup import (
    ADMINISTRATOR_PERMISSIONS_LIST,
    ANALYST_PERMISSIONS_LIST,
    APPROVER_PERMISSIONS_LIST,
    AUDITEE_PERMISSIONS_LIST,
    BASELINE_READER_PERMISSIONS_LIST,
    DOMAIN_MANAGER_PERMISSIONS_LIST,
    READER_PERMISSIONS_LIST,
    TECHNICAL_TESTER_PERMISSIONS_LIST,
    THIRD_PARTY_RESPONDENT_PERMISSIONS_LIST,
    USER_CREATOR_PERMISSIONS_LIST,
)
from iam.models import get_permission_catalog

BUILTIN_ROLE_PERMISSIONS = {
    *ADMINISTRATOR_PERMISSIONS_LIST,
    *ANALYST_PERMISSIONS_LIST,
    *APPROVER_PERMISSIONS_LIST,
    *AUDITEE_PERMISSIONS_LIST,
    *BASELINE_READER_PERMISSIONS_LIST,
    *DOMAIN_MANAGER_PERMISSIONS_LIST,
    *READER_PERMISSIONS_LIST,
    *TECHNICAL_TESTER_PERMISSIONS_LIST,
    *THIRD_PARTY_RESPONDENT_PERMISSIONS_LIST,
    *USER_CREATOR_PERMISSIONS_LIST,
}


# Granted to built-in roles, but kept out of the catalog on purpose
EXCLUDED_BUILTIN_PERMISSIONS = {
    ("auth", "view_permission"),
    # Role and identity management stays with the built-in roles
    ("iam", "add_role"),
    ("iam", "change_role"),
    ("iam", "delete_role"),
    ("iam", "view_role"),
    ("iam", "view_roleassignment"),
    ("iam", "change_usergroup"),
    ("iam", "delete_usergroup"),
    ("iam", "view_usergroup"),
    ("iam", "add_idpgroup"),
    ("iam", "change_idpgroup"),
    ("iam", "delete_idpgroup"),
    ("iam", "view_idpgroup"),
    ("iam", "change_ssosettings"),
    ("iam", "view_ssosettings"),
    # Never checked: mail settings are gated by *_mailerconfiguration
    ("global_settings", "add_mailer"),
    ("global_settings", "change_mailer"),
    ("global_settings", "delete_mailer"),
    ("global_settings", "view_mailer"),
    ("global_settings", "view_mailerhealth"),
    # Administrator-only
    ("cal", "add_event"),
    ("cal", "change_event"),
    ("cal", "delete_event"),
    ("cal", "view_event"),
    ("chat", "change_indexeddocument"),
    ("integrations", "add_integrationconfiguration"),
    ("integrations", "change_integrationconfiguration"),
    ("integrations", "delete_integrationconfiguration"),
    ("webhooks", "add_webhookendpoint"),
    ("webhooks", "change_webhookendpoint"),
    ("webhooks", "delete_webhookendpoint"),
    ("webhooks", "view_webhookendpoint"),
    ("webhooks", "view_webhookeventtype"),
    # Metric previews aggregate objects without checking they can be read
    ("metrology", "add_custommetricsample"),
    ("metrology", "change_custommetricsample"),
    ("metrology", "delete_custommetricsample"),
    ("metrology", "view_custommetricsample"),
    ("metrology", "add_dashboard"),
    ("metrology", "change_dashboard"),
    ("metrology", "delete_dashboard"),
    ("metrology", "view_dashboard"),
    ("metrology", "add_dashboardwidget"),
    ("metrology", "change_dashboardwidget"),
    ("metrology", "delete_dashboardwidget"),
    ("metrology", "view_dashboardwidget"),
    ("metrology", "add_metricdefinition"),
    ("metrology", "change_metricdefinition"),
    ("metrology", "delete_metricdefinition"),
    ("metrology", "view_metricdefinition"),
    ("metrology", "add_metricinstance"),
    ("metrology", "change_metricinstance"),
    ("metrology", "delete_metricinstance"),
    ("metrology", "view_metricinstance"),
    # Served read-only
    ("core", "add_quickformpage"),
    ("core", "change_quickformpage"),
    ("core", "delete_quickformpage"),
    ("pmbok", "add_responsibilityassignment"),
    ("pmbok", "change_responsibilityassignment"),
    ("pmbok", "delete_responsibilityassignment"),
    ("pmbok", "add_responsibilityrole"),
    ("pmbok", "change_responsibilityrole"),
    ("pmbok", "delete_responsibilityrole"),
}


@pytest.mark.django_db
def test_every_permission_of_a_builtin_role_can_be_given_to_a_custom_role() -> None:
    missing = set(
        Permission.objects.filter(codename__in=BUILTIN_ROLE_PERMISSIONS)
        .exclude(id__in=get_permission_catalog())
        .values_list("content_type__app_label", "codename")
    )

    assert missing == EXCLUDED_BUILTIN_PERMISSIONS


@pytest.mark.django_db
@pytest.mark.parametrize(
    "codename",
    [
        "view_conditionbranch",
        "view_customfieldchoice",
        "view_customfieldvalue",
        "view_documentreference",
        "view_integrationprovider",
        "view_integrationschemacache",
        "view_posturerun",
        "view_syncevent",
        "add_chatmessage",
        "add_documentedit",
        "add_workflowinstancelog",
        "add_notification",
        "add_workflowtoken",
        "delete_workflowtoken",
        "add_workflowtrigger",
        "delete_workflowtrigger",
    ],
)
def test_internal_or_system_written_permissions_are_not_offered(
    codename: str,
) -> None:
    assert not get_permission_catalog().filter(codename=codename).exists()
