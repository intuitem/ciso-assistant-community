"""
The notification type registry.

This is a layer *above* the email templates, not a replacement for them. An entry
describes a notification -- what it asks of the recipient, whether the system
re-checks it, and which channels carry it -- and points at an email template when
one of those channels is email. `enterprise_core.template_registry` keeps describing
emails, and is untouched by this.

The layering is what makes an in-app-exclusive notification possible: set
`email_template` to None and the type simply has no email rendering. Nothing about
the email path has to change to allow it.

Fields:
  category        inbox filter and matrix grouping, on the axis "what it asks of you":
                  assignments | approvals | deadlines | updates | account
  mode            condition -> re-checked by a nightly sweep, upserted, deleted when it
                  stops being true, and a re-fire does NOT bump a read row back to unread
                  event     -> fired by an action; a re-fire DOES bump it back to unread
  channels        supported channels, all on by default; later layers may only subtract
  email_template  key into EMAIL_TEMPLATE_REGISTRY and the YAML files under
                  core/templates/emails/{en,fr}/, or None for in-app-exclusive types
  context         variables a producer must supply to render this type's title. NOT the
                  email template's variables: a condition type's email is a digest
                  (${control_count}, ${control_list}) while its inbox row is per object
                  (${control_name}). That difference is the point of the layering.

Row titles are not here: they are per-locale, in notifications/titles/{en,fr}.yaml.
"""

NOTIFICATION_REGISTRY = {
    "applied_control_assignment": {
        "category": "assignments",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "applied_control_assignment",
        "context": ["control_name"],
    },
    "applied_control_expiring_soon": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "applied_control_expiring_soon",
        "context": ["control_name", "days_remaining"],
    },
    "assignment_activated": {
        "category": "assignments",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "assignment_activated",
        "context": ["assessment_name"],
    },
    "assignment_reopened": {
        "category": "assignments",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "assignment_reopened",
        "context": ["assessment_name"],
    },
    "assignment_reviewed": {
        "category": "updates",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "assignment_reviewed",
        "context": ["assessment_name", "decision"],
    },
    "assignment_submitted": {
        "category": "approvals",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "assignment_submitted",
        "context": ["assessment_name"],
    },
    "compliance_assessment_assignment": {
        "category": "assignments",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "compliance_assessment_assignment",
        "context": ["assessment_name"],
    },
    "compliance_assessment_due_soon": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "compliance_assessment_due_soon",
        "context": ["assessment_name", "days_remaining"],
    },
    "evidence_expiring_soon": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "evidence_expiring_soon",
        "context": ["days_remaining", "evidence_name"],
    },
    "expired_controls": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "expired_controls",
        "context": ["control_name"],
    },
    "expired_evidences": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "expired_evidences",
        "context": ["evidence_name"],
    },
    "expired_security_exceptions": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "expired_security_exceptions",
        "context": ["exception_name"],
    },
    "password_reset": {
        "category": "account",
        "mode": "event",
        "channels": ["email"],
        "email_template": "password_reset",
        "context": [],
    },
    "questionnaire_assignment": {
        "category": "assignments",
        "mode": "event",
        "channels": ["email"],
        "email_template": "questionnaire_assignment",
        "context": [],
    },
    "quick_form_reopened": {
        "category": "assignments",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "quick_form_reopened",
        "context": ["response_name"],
    },
    "quick_form_started": {
        "category": "assignments",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "quick_form_started",
        "context": ["response_name"],
    },
    "quick_form_submitted": {
        "category": "approvals",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "quick_form_submitted",
        "context": ["response_name"],
    },
    "risk_scenario_assignment": {
        "category": "assignments",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "risk_scenario_assignment",
        "context": ["scenario_name"],
    },
    "security_exception_assignment": {
        "category": "assignments",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "security_exception_assignment",
        "context": ["exception_name"],
    },
    "security_exception_expiring_soon": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "security_exception_expiring_soon",
        "context": ["days_remaining", "exception_name"],
    },
    "security_exception_status_changed": {
        "category": "updates",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "security_exception_status_changed",
        "context": ["exception_name", "new_status"],
    },
    "task_node_due_soon": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "task_node_due_soon",
        "context": ["days_remaining", "task_name"],
    },
    "task_node_overdue": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "task_node_overdue",
        "context": ["task_name"],
    },
    "task_template_assignment": {
        "category": "assignments",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "task_template_assignment",
        "context": ["task_name"],
    },
    "validation_deadline": {
        "category": "deadlines",
        "mode": "condition",
        "channels": ["in_app", "email"],
        "email_template": "validation_deadline",
        "context": ["days", "validation_ref_id"],
    },
    "validation_flow_created": {
        "category": "approvals",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "validation_flow_created",
        "context": ["validation_ref_id"],
    },
    "validation_flow_updated": {
        "category": "updates",
        "mode": "event",
        "channels": ["in_app", "email"],
        "email_template": "validation_flow_updated",
        "context": ["new_status", "validation_ref_id"],
    },
    "welcome": {
        "category": "account",
        "mode": "event",
        "channels": ["email"],
        "email_template": "welcome",
        "context": [],
    },
    "welcome_sso": {
        "category": "account",
        "mode": "event",
        "channels": ["email"],
        "email_template": "welcome_sso",
        "context": [],
    },
}
