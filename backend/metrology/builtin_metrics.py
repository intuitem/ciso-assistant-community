"""
Builtin Metrics Registry

This module defines the available builtin metrics for each model type.
These metrics are computed from existing data and stored in BuiltinMetricSample.
"""

from django.utils.translation import gettext_lazy as _

# Metric types for frontend display
METRIC_TYPE_NUMBER = "number"  # Single numeric value
METRIC_TYPE_PERCENTAGE = "percentage"  # 0-100 percentage
METRIC_TYPE_BREAKDOWN = "breakdown"  # Dictionary of category -> count
METRIC_TYPE_STATUS = "status"  # Single status value (string)

# Chart types allowed per metric type
# Maps metric_type -> list of allowed chart_type values
METRIC_TYPE_CHART_TYPES = {
    METRIC_TYPE_NUMBER: ["kpi_card", "gauge", "sparkline", "line", "area"],
    METRIC_TYPE_PERCENTAGE: ["gauge", "kpi_card", "sparkline", "line", "area"],
    METRIC_TYPE_BREAKDOWN: ["donut", "pie", "bar", "table"],
    METRIC_TYPE_STATUS: ["kpi_card"],
}


# Registry of available builtin metrics per model
# Format: model_name -> {metric_key: {label, type, description}}
BUILTIN_METRICS = {
    "ComplianceAssessment": {
        "progress": {
            "label": _("Progress"),
            "type": METRIC_TYPE_PERCENTAGE,
            "description": _("Completion percentage of the assessment"),
        },
        "score": {
            "label": _("Score"),
            "type": METRIC_TYPE_NUMBER,
            "description": _("Global compliance score"),
        },
        "total_requirements": {
            "label": _("Total Requirements"),
            "type": METRIC_TYPE_NUMBER,
            "description": _("Total number of requirements"),
        },
        "status_breakdown": {
            "label": _("Status Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Requirements count per status"),
        },
        "result_breakdown": {
            "label": _("Result Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Requirements count per result"),
        },
    },
    "RiskAssessment": {
        "total_scenarios": {
            "label": _("Total Scenarios"),
            "type": METRIC_TYPE_NUMBER,
            "description": _("Total number of risk scenarios"),
        },
        "treatment_breakdown": {
            "label": _("Treatment Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Scenarios count per treatment option"),
        },
        "current_level_breakdown": {
            "label": _("Current Risk Level Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Scenarios count per current risk level"),
        },
        "residual_level_breakdown": {
            "label": _("Residual Risk Level Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Scenarios count per residual risk level"),
        },
    },
    "FindingsAssessment": {
        "total_findings": {
            "label": _("Total Findings"),
            "type": METRIC_TYPE_NUMBER,
            "description": _("Total number of findings"),
        },
        "severity_breakdown": {
            "label": _("Severity Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Findings count per severity level"),
        },
        "status_breakdown": {
            "label": _("Status Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Findings count per status"),
        },
    },
    "Folder": {
        # Applied Controls metrics
        "controls_status_breakdown": {
            "label": _("Controls Status Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Applied controls count per status in this domain"),
        },
        "controls_category_breakdown": {
            "label": _("Controls Category Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Applied controls count per category in this domain"),
        },
        # Incidents metrics
        "incidents_severity_breakdown": {
            "label": _("Incidents Severity Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Incidents count per severity in this domain"),
        },
        "incidents_status_breakdown": {
            "label": _("Incidents Status Breakdown"),
            "type": METRIC_TYPE_BREAKDOWN,
            "description": _("Incidents count per status in this domain"),
        },
        "total_controls": {
            "label": _("Total Controls"),
            "type": METRIC_TYPE_NUMBER,
            "description": _("Total applied controls in this domain"),
        },
        "total_incidents": {
            "label": _("Total Incidents"),
            "type": METRIC_TYPE_NUMBER,
            "description": _("Total incidents in this domain"),
        },
    },
}


def get_available_metrics_for_model(model_name: str) -> dict:
    """
    Returns the available builtin metrics for a given model.

    Args:
        model_name: The Django model class name (e.g., 'ComplianceAssessment')

    Returns:
        Dictionary of metric definitions or empty dict if model not supported
    """
    return BUILTIN_METRICS.get(model_name, {})


def get_supported_models() -> list[str]:
    """Returns list of model names that support builtin metrics."""
    return list(BUILTIN_METRICS.keys())


def get_metric_choices_for_model(model_name: str) -> list[tuple[str, str]]:
    """
    Returns metric choices suitable for a Django form field.

    Args:
        model_name: The Django model class name

    Returns:
        List of (metric_key, label) tuples
    """
    metrics = get_available_metrics_for_model(model_name)
    return [(key, str(meta["label"])) for key, meta in metrics.items()]


def get_chart_types_for_metric(model_name: str, metric_key: str) -> list[str]:
    """
    Returns the allowed chart types for a specific metric.

    Args:
        model_name: The Django model class name
        metric_key: The metric key

    Returns:
        List of allowed chart type values
    """
    metrics = get_available_metrics_for_model(model_name)
    if metric_key not in metrics:
        return []
    metric_type = metrics[metric_key].get("type", METRIC_TYPE_NUMBER)
    return METRIC_TYPE_CHART_TYPES.get(metric_type, [])
