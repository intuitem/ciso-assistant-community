"""What an MCP token may do in the backend, whatever the MCP server asks: only
data, and only the actions its connection allows. Checked in the central RBAC
functions, so it holds for every view."""

from core.context import mcp_access_var

ACTION_OF_PREFIX = {
    "view": "read",
    "add": "create",
    "change": "update",
    "delete": "delete",
}

# administration of identity, access, domains, settings and integrations
CONTROL_PLANE = {
    "user",
    "usergroup",
    "role",
    "roleassignment",
    "idpgroup",
    "folder",
    "globalsettings",
    "ssosettings",
    "mailerconfiguration",
    "mailer",
    "integrationprovider",
    "integrationconfiguration",
    "syncmapping",
    "webhookendpoint",
}

# reading them may reveal secrets
SENSITIVE_READS = {
    "ssosettings",
    "mailerconfiguration",
    "mailer",
    "integrationconfiguration",
    "webhookendpoint",
}

# credentials and their management
NON_DELEGABLE = {
    "personalaccesstoken",
    "scimtoken",
    "serviceaccount",
    "connectedappuse",
    "connectionprofile",
    "appgrant",
    "client",
    "token",
    "authtoken",
    "permission",
    "group",
}


# Custom permissions that stand for an action on data. Every other custom
# permission is refused, whatever its name: `view_user_full` shows sign-in and
# administration details, and the audit log permissions are administration.
CUSTOM_ACTIONS = {
    # the auditor view of an audit: without it, an app would read as a respondent
    "view_compliance_assessment_full": "read",
    # documents in force only: less than `view_documentcontainer`
    "view_published_documentcontainer": "read",
}


def allows(codename: str, access) -> bool:
    if codename in CUSTOM_ACTIONS:
        return CUSTOM_ACTIONS[codename] in access.actions
    prefix, _, model = codename.partition("_")
    action = ACTION_OF_PREFIX.get(prefix)
    # a model name has no underscore: `view_user_full` is a custom permission,
    # like `approve_riskacceptance`, and is refused until CUSTOM_ACTIONS maps it
    if action is None or "_" in model:
        return False
    if model in NON_DELEGABLE or model in SENSITIVE_READS:
        return False
    if model in CONTROL_PLANE and action != "read":
        return False
    return action in access.actions


def delegation_allows(codename: str) -> bool:
    access = mcp_access_var.get()
    return access is None or allows(codename, access)


def is_delegated() -> bool:
    return mcp_access_var.get() is not None
