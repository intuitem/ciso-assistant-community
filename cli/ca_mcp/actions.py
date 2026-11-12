"""What a connection may do. Read is always allowed; create, update and delete
are granted separately. The host puts the actions in the access token's claims; a
token without them may only read."""

READ = "read"
CREATE = "create"
UPDATE = "update"
DELETE = "delete"

ACTIONS = (READ, CREATE, UPDATE, DELETE)

_REFUSED_ACTION = {
    CREATE: "creating",
    UPDATE: "changing",
    DELETE: "deleting",
}

_ALLOWED_VERBS = {
    READ: ["read"],
    CREATE: ["create"],
    UPDATE: ["change"],
    DELETE: ["delete"],
}


def granted_actions(access) -> set[str]:
    claimed = (access.claims or {}).get("actions") if access else None
    if isinstance(claimed, list):
        return {READ} | {action for action in claimed if action in ACTIONS}
    return {READ}


def profile_name(access) -> str | None:
    return (access.claims or {}).get("profile") if access else None


def refusal(access, needed: str) -> str:
    profile = profile_name(access)
    who = "this connection"
    if profile:
        who += f' uses the "{profile}" profile, which'
    return (
        f"Error: {who} does not allow {_REFUSED_ACTION[needed]} data. "
        "The user can reconnect the app and allow it, if their administrator "
        "lets AI apps change data."
    )


def _join(words: list[str], last: str = "and") -> str:
    if len(words) == 1:
        return words[0]
    return ", ".join(words[:-1]) + f" {last} " + words[-1]


def summary(access) -> str:
    granted = granted_actions(access)
    allowed = [verb for a in ACTIONS if a in granted for verb in _ALLOWED_VERBS[a]]
    text = f"This connection can {_join(allowed)} data in CISO Assistant."
    missing = [_REFUSED_ACTION[a] for a in ACTIONS if a != READ and a not in granted]
    if missing:
        text += f" It does not allow {_join(missing, 'or')} data."
    profile = profile_name(access)
    if profile:
        text = f'Profile "{profile}". ' + text
    return text
