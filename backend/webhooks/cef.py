"""CEF / LEEF text builders for legacy SIEMs (ArcSight, QRadar).

Flat key=value formats — the nested field-level diff is JSON-encoded into a
single custom field (CEF cs1 / LEEF changes); who/what/when keep full fidelity.
"""

import json

from .ocsf import _ACTION_VERB, _model_name

_VENDOR = "intuitem"
_PRODUCT = "CISO Assistant"
_VERSION = "1"
_SEVERITY = 3


def _changes_json(log_entry) -> str:
    return json.dumps(log_entry.changes or {}, separators=(",", ":"))


def _cef_escape_header(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|")


def _cef_escape_ext(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("=", "\\=").replace("\n", " ")


def log_entry_to_cef(log_entry) -> str:
    model = _model_name(log_entry)
    verb = _ACTION_VERB.get(log_entry.action, "unknown")
    folder_id = (log_entry.additional_data or {}).get("folder_id")
    ext = {
        "rt": int(log_entry.timestamp.timestamp() * 1000),
        "act": verb,
        "suser": log_entry.actor_email or "",
        "src": log_entry.remote_addr or "",
        "externalId": str(log_entry.object_pk),
        "cs1Label": "object",
        "cs1": log_entry.object_repr or "",
        "cs2Label": "folder",
        "cs2": folder_id or "",
        "cs3Label": "changes",
        "cs3": _changes_json(log_entry),
    }
    extension = " ".join(f"{k}={_cef_escape_ext(v)}" for k, v in ext.items() if v != "")
    header = "|".join(
        _cef_escape_header(p)
        for p in [
            "CEF:0",
            _VENDOR,
            _PRODUCT,
            _VERSION,
            f"{model}.{verb}",
            f"{verb} {model}",
            str(_SEVERITY),
        ]
    )
    return f"{header}|{extension}"


def _leef_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("^", "\\^")


def log_entry_to_leef(log_entry) -> str:
    model = _model_name(log_entry)
    verb = _ACTION_VERB.get(log_entry.action, "unknown")
    folder_id = (log_entry.additional_data or {}).get("folder_id")
    header = f"LEEF:2.0|{_VENDOR}|{_PRODUCT}|{_VERSION}|{model}.{verb}|^|"
    attrs = {
        "devTime": int(log_entry.timestamp.timestamp() * 1000),
        "cat": model,
        "act": verb,
        "usrName": log_entry.actor_email or "",
        "src": log_entry.remote_addr or "",
        "externalId": str(log_entry.object_pk),
        "object": log_entry.object_repr or "",
        "folder": folder_id or "",
        "changes": _changes_json(log_entry),
    }
    body = "^".join(f"{k}={_leef_escape(v)}" for k, v in attrs.items() if v != "")
    return header + body
