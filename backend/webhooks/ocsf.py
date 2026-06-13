"""Audit LogEntry → external-SIEM body builders.

Default schema is OCSF (Open Cybersecurity Schema Framework), API Activity class
(class_uid 6003), which the OCSF spec documents as general CRUD API activities —
a direct fit for our create/update/delete audit records. A canonical body removes
per-SIEM field mapping; per-destination auth/wrapper still lives in the transport.
"""

from auditlog.models import LogEntry

OCSF_VERSION = "1.8.0"
_PRODUCT = {"name": "CISO Assistant", "vendor_name": "intuitem"}
_API_ACTIVITY_CLASS_UID = 6003
_APPLICATION_ACTIVITY_CATEGORY_UID = 6

# auditlog.Action → OCSF API Activity activity_id (1=Create, 2=Read, 3=Update, 4=Delete).
# Note the remap: auditlog uses 0=CREATE, 1=UPDATE, 2=DELETE, 3=ACCESS.
_OCSF_ACTIVITY_BY_ACTION = {
    LogEntry.Action.CREATE: 1,
    LogEntry.Action.UPDATE: 3,
    LogEntry.Action.DELETE: 4,
    LogEntry.Action.ACCESS: 2,
}
_ACTION_VERB = {
    LogEntry.Action.CREATE: "create",
    LogEntry.Action.UPDATE: "update",
    LogEntry.Action.DELETE: "delete",
    LogEntry.Action.ACCESS: "read",
}


def _model_name(log_entry) -> str:
    return log_entry.content_type.model if log_entry.content_type_id else "unknown"


def _actor(log_entry) -> dict:
    if not (log_entry.actor_id or log_entry.actor_email):
        return {}
    return {
        "user": {
            "uid": str(log_entry.actor_id) if log_entry.actor_id else None,
            "email_addr": log_entry.actor_email or None,
        }
    }


def log_entry_to_ocsf(log_entry) -> dict:
    """Map a django-auditlog LogEntry to an OCSF API Activity (6003) event."""
    activity_id = _OCSF_ACTIVITY_BY_ACTION.get(log_entry.action, 0)
    model_name = _model_name(log_entry)
    additional = log_entry.additional_data or {}
    src_endpoint = {"ip": log_entry.remote_addr} if log_entry.remote_addr else {}
    # auditlog stamps every entry in a request with the same correlation id;
    # surfacing it lets a SIEM group all events from one request.
    metadata = {"version": OCSF_VERSION, "product": _PRODUCT}
    if log_entry.cid:
        metadata["correlation_uid"] = log_entry.cid
    return {
        "activity_id": activity_id,
        "category_uid": _APPLICATION_ACTIVITY_CATEGORY_UID,
        "class_uid": _API_ACTIVITY_CLASS_UID,
        "type_uid": _API_ACTIVITY_CLASS_UID * 100 + activity_id,
        "severity_id": 1,  # Informational
        "status_id": 1,  # Success
        "time": int(log_entry.timestamp.timestamp() * 1000),
        "metadata": metadata,
        "actor": _actor(log_entry),
        "api": {
            "operation": _ACTION_VERB.get(log_entry.action, "unknown"),
            "service": {"name": model_name},
        },
        "src_endpoint": src_endpoint,
        "resources": [
            {
                "type": model_name,
                "uid": str(log_entry.object_pk),
                "name": log_entry.object_repr,
            }
        ],
        "unmapped": {
            "changes": log_entry.changes,
            "folder_id": additional.get("folder_id"),
        },
    }


def log_entry_to_raw(log_entry) -> dict:
    """Pass-through of the LogEntry fields, for sinks that prefer our native shape."""
    return {
        "action": _ACTION_VERB.get(log_entry.action, "unknown"),
        "model": _model_name(log_entry),
        "object_id": str(log_entry.object_pk),
        "object_repr": log_entry.object_repr,
        "changes": log_entry.changes,
        "actor": _actor(log_entry).get("user", {}),
        "remote_addr": log_entry.remote_addr,
        "folder_id": (log_entry.additional_data or {}).get("folder_id"),
        "correlation_id": log_entry.cid,
        "timestamp": log_entry.timestamp.isoformat(),
    }


def build_audit_body(log_entry, body_format):
    # Returns a dict for JSON formats (ocsf/raw) or a str for text formats (cef/leef).
    if body_format == "raw":
        return log_entry_to_raw(log_entry)
    if body_format in ("cef", "leef"):
        from .cef import log_entry_to_cef, log_entry_to_leef

        return (log_entry_to_cef if body_format == "cef" else log_entry_to_leef)(
            log_entry
        )
    return log_entry_to_ocsf(log_entry)
