"""
Registry of overridable templates with their metadata.
Used by the API to document available templates and validate overrides.
"""

WORD_TEMPLATE_REGISTRY = {
    "audit_report": {
        "description": "Compliance assessment Word report",
        "default_languages": ["en", "fr"],
        "variables": [
            {
                "name": "audit",
                "type": "object",
                "description": "The compliance assessment object (audit.name, audit.description, audit.framework, etc.)",
            },
            {
                "name": "date",
                "type": "string",
                "description": "Current date formatted as DD/MM/YYYY",
            },
            {
                "name": "contributors",
                "type": "string",
                "description": "Authors and reviewers email addresses",
            },
            {
                "name": "req",
                "type": "object",
                "description": "Aggregated result counts: req.compliant, req.non_compliant, req.partially_compliant, req.not_applicable, req.not_assessed, req.total",
            },
            {
                "name": "compliance_donut",
                "type": "image",
                "description": "Donut chart of compliance results distribution",
            },
            {
                "name": "completion_bar",
                "type": "image",
                "description": "Bar chart of completion percentage per category",
            },
            {
                "name": "compliance_radar",
                "type": "image",
                "description": "Spider/radar chart of compliance percentage per category",
            },
            {
                "name": "category_radar",
                "type": "image",
                "description": "Radar chart of average scores per category",
            },
            {
                "name": "chart_controls",
                "type": "image",
                "description": "Horizontal bar chart of applied control status distribution",
            },
            {
                "name": "drifts_per_domain",
                "type": "list",
                "description": "List of {name, drift_count} per top-level domain",
            },
            {
                "name": "p1_controls",
                "type": "list",
                "description": "P1 priority controls: {name, description, status, category, coverage}",
            },
            {
                "name": "full_controls",
                "type": "list",
                "description": "All applied controls: {name, description, prio, status, eta, category, coverage}",
            },
            {
                "name": "ac_count",
                "type": "number",
                "description": "Total number of applied controls",
            },
            {
                "name": "igs",
                "type": "string",
                "description": "Selected implementation groups (comma-separated)",
            },
            {
                "name": "category_scores",
                "type": "object",
                "description": "Per-category score details: {name, total_score, item_count, scored_count, average_score}",
            },
            {
                "name": "requirement_assessments",
                "type": "list",
                "description": "All assessable requirement assessments: {ref_id, name, description, status, result, extended_result, score, max_score, observation, applied_controls}",
            },
            {
                "name": "ra_count",
                "type": "number",
                "description": "Total number of assessable requirement assessments",
            },
        ],
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
