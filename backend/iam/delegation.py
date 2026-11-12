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


def allows(codename: str, access) -> bool:
    prefix, _, model = codename.partition("_")
    # a custom permission (approve_*, ...) is not mapped yet: refused
    action = ACTION_OF_PREFIX.get(prefix)
    if action is None or model in NON_DELEGABLE or model in SENSITIVE_READS:
        return False
    if model in CONTROL_PLANE and action != "read":
        return False
    return action in access.actions


def delegation_allows(codename: str) -> bool:
    access = mcp_access_var.get()
    return access is None or allows(codename, access)


def is_delegated() -> bool:
    return mcp_access_var.get() is not None
