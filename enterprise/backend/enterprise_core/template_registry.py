"""
Registry of overridable templates with their metadata.
Used by the API to document available templates and validate overrides.
"""

WORD_TEMPLATE_REGISTRY = {
    "audit_report": {
        "description": "Compliance assessment Word report",
        "default_languages": ["en", "fr"],
    },
}


EMAIL_TEMPLATE_REGISTRY = {
    "welcome": {
        "description": "Welcome email sent to new internal users",
        "category": "core",
        "variables": [
            "set_password_url",
            "ciso_assistant_url",
        ],
    },
    "welcome_sso": {
        "description": "Welcome email sent to new SSO users",
        "category": "core",
        "variables": [
            "ciso_assistant_url",
        ],
    },
    "password_reset": {
        "description": "Password reset email",
        "category": "core",
        "variables": [
            "reset_password_url",
            "ciso_assistant_url",
        ],
    },
    "questionnaire_assignment": {
        "description": "Sent when a third-party questionnaire is assigned",
        "category": "core",
        "variables": [
            "questionnaire_url",
            "ciso_assistant_url",
        ],
    },
    "applied_control_assignment": {
        "description": "Sent when a control is assigned to a user",
        "category": "notification",
        "variables": [
            "control_name",
            "control_description",
            "control_ref_id",
            "control_status",
            "control_priority",
            "control_eta",
            "folder_name",
            "ciso_assistant_url",
        ],
    },
    "applied_control_expiring_soon": {
        "description": "Sent when controls are about to expire",
        "category": "notification",
        "variables": [
            "control_count",
            "control_list",
            "days_remaining",
            "ciso_assistant_url",
        ],
    },
    "assignment_activated": {
        "description": "Sent when an audit assignment starts",
        "category": "notification",
        "variables": [
            "assessment_name",
            "framework_name",
            "due_date",
            "ciso_assistant_url",
        ],
    },
    "assignment_reviewed": {
        "description": "Sent when an assignment is reviewed",
        "category": "notification",
        "variables": [
            "assessment_name",
            "decision",
            "reviewer_observation",
            "ciso_assistant_url",
        ],
    },
    "assignment_submitted": {
        "description": "Sent when an assignment is submitted",
        "category": "notification",
        "variables": [
            "assessment_name",
            "actor_names",
            "requirement_count",
            "ciso_assistant_url",
        ],
    },
    "compliance_assessment_assignment": {
        "description": "Sent when a compliance assessment is assigned",
        "category": "notification",
        "variables": [
            "assessment_name",
            "assessment_description",
            "framework_name",
            "assessment_status",
            "assessment_due_date",
            "folder_name",
            "ciso_assistant_url",
        ],
    },
    "compliance_assessment_due_soon": {
        "description": "Sent when compliance assessments are due soon",
        "category": "notification",
        "variables": [
            "assessment_count",
            "assessment_list",
            "days_remaining",
            "ciso_assistant_url",
        ],
    },
    "evidence_expiring_soon": {
        "description": "Sent when evidences are about to expire",
        "category": "notification",
        "variables": [
            "evidence_count",
            "evidence_list",
            "days_remaining",
            "ciso_assistant_url",
        ],
    },
    "expired_controls": {
        "description": "Sent when controls have expired",
        "category": "notification",
        "variables": [
            "control_count",
            "control_list",
            "ciso_assistant_url",
        ],
    },
    "expired_evidences": {
        "description": "Sent when evidences have expired",
        "category": "notification",
        "variables": [
            "evidence_count",
            "evidence_list",
            "expired_since",
            "ciso_assistant_url",
        ],
    },
    "risk_scenario_assignment": {
        "description": "Sent when a risk scenario is assigned",
        "category": "notification",
        "variables": [
            "scenario_name",
            "scenario_description",
            "scenario_ref_id",
            "risk_assessment_name",
            "scenario_treatment",
            "folder_name",
            "ciso_assistant_url",
        ],
    },
    "task_node_due_soon": {
        "description": "Sent when tasks are due soon",
        "category": "notification",
        "variables": [
            "task_count",
            "task_list",
            "days_remaining",
            "ciso_assistant_url",
        ],
    },
    "task_node_overdue": {
        "description": "Sent when tasks are overdue",
        "category": "notification",
        "variables": [
            "task_count",
            "task_list",
            "ciso_assistant_url",
        ],
    },
    "task_template_assignment": {
        "description": "Sent when a task is assigned",
        "category": "notification",
        "variables": [
            "task_id",
            "task_name",
            "task_description",
            "task_ref_id",
            "task_date",
            "is_recurrent",
            "folder_name",
            "ciso_assistant_url",
        ],
    },
    "validation_deadline": {
        "description": "Sent when validation deadlines are approaching",
        "category": "notification",
        "variables": [
            "days",
            "validation_list",
            "validation_count",
            "s",
            "are",
            "their",
            "ciso_assistant_url",
        ],
    },
    "validation_flow_created": {
        "description": "Sent when a validation flow is created",
        "category": "notification",
        "variables": [
            "validation_ref_id",
            "requester_name",
            "validation_deadline",
            "folder_name",
            "validation_url",
            "ciso_assistant_url",
        ],
    },
    "validation_flow_updated": {
        "description": "Sent when a validation flow status changes",
        "category": "notification",
        "variables": [
            "validation_ref_id",
            "new_status",
            "actor_name",
            "folder_name",
            "event_notes",
            "validation_url",
            "ciso_assistant_url",
        ],
    },
}
