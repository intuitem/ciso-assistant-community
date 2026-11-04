"""What a connection may do. Read is always allowed; create and update are
granted separately. The host puts the actions in the access token's claims; a
token without them may only read."""

READ = "read"
CREATE = "create"
UPDATE = "update"

ACTIONS = (READ, CREATE, UPDATE)

_REFUSED_ACTION = {
    CREATE: "creating data",
    UPDATE: "changing or deleting data",
}

_ALLOWED_VERBS = {
    READ: ["read"],
    CREATE: ["create"],
    UPDATE: ["change", "delete"],
}


def granted_actions(access) -> set[str]:
    claimed = (access.claims or {}).get("actions") if access else None
    if isinstance(claimed, list):
        return {READ} | {action for action in claimed if action in ACTIONS}
    return {READ}


def allows(access, needed: str) -> bool:
    return needed in granted_actions(access)


def profile_name(access) -> str | None:
    return (access.claims or {}).get("profile") if access else None


def refusal(access, needed: str) -> str:
    profile = profile_name(access)
    who = "this connection"
    if profile:
        who += f' uses the "{profile}" profile, which'
    return (
        f"Error: {who} does not allow {_REFUSED_ACTION[needed]}. "
        "Reconnect the app and pick a profile that does."
    )


def _join(words: list[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def summary(access) -> str:
    granted = granted_actions(access)
    allowed = [verb for a in ACTIONS if a in granted for verb in _ALLOWED_VERBS[a]]
    text = f"This connection can {_join(allowed)} data in CISO Assistant."
    missing = [_REFUSED_ACTION[a] for a in ACTIONS if a != READ and a not in granted]
    if missing:
        text += " It does not allow " + " or ".join(missing) + "."
    profile = profile_name(access)
    if profile:
        text = f'Profile "{profile}". ' + text
    return text
