"""What a connection may do. The host puts the level in the access token's
claims; a token without one falls back to its scopes."""

READ = "read"
CREATE = "create"
UPDATE = "update"
APPROVE = "approve"

LEVELS = (READ, CREATE, UPDATE, APPROVE)

WRITE_SCOPE = "mcp:write"

_REFUSED_ACTION = {
    CREATE: "creating data",
    UPDATE: "changing or deleting data",
    APPROVE: "approving or moving items through a workflow",
}

_SUMMARY = {
    READ: "read data in CISO Assistant",
    CREATE: "read and create data in CISO Assistant",
    UPDATE: "read, create, change and delete data in CISO Assistant",
    APPROVE: (
        "read, create, change and delete data in CISO Assistant, and approve "
        "or move items through a workflow"
    ),
}


def allows(granted: str, needed: str) -> bool:
    return LEVELS.index(granted) >= LEVELS.index(needed)


def granted_level(access) -> str:
    level = (access.claims or {}).get("level") if access else None
    if level in LEVELS:
        return level
    if access is not None and WRITE_SCOPE in access.scopes:
        return UPDATE
    return READ


def profile_name(access) -> str | None:
    return (access.claims or {}).get("profile") if access else None


def refusal(access, needed: str) -> str:
    action = _REFUSED_ACTION[needed]
    profile = profile_name(access)
    if profile:
        return (
            f'Error: this connection uses the "{profile}" profile, which does not '
            f"allow {action}. Ask your administrator for a profile that does."
        )
    return (
        f"Error: this connection does not allow {action}. "
        "Reconnect and grant write access to use it."
    )


def summary(access) -> str:
    level = granted_level(access)
    profile = profile_name(access)
    text = f"This connection can {_SUMMARY[level]}."
    missing = [_REFUSED_ACTION[lvl] for lvl in LEVELS if not allows(level, lvl)]
    if missing:
        text += " It does not allow " + ", ".join(missing) + "."
    if profile:
        text = f'Profile "{profile}" ({level}). ' + text
    return text
