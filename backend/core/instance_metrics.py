"""
This module defines metrics for the CISO Assistant backend using the Prometheus client library.
It provides counters and gauges to track various instance statistics for monitoring and observability.
"""

from prometheus_client import Gauge, Info, REGISTRY
from django.conf import settings


# Dictionary to store metric instances to prevent duplicates
_metrics = {}


def get_or_create_gauge(name, description):
    """Get existing gauge or create new one if it doesn't exist."""
    if name not in _metrics:
        _metrics[name] = Gauge(name, description)
    return _metrics[name]


def get_or_create_info(name, description):
    """Get existing info metric or create new one if it doesn't exist."""
    if name not in _metrics:
        _metrics[name] = Info(name, description)
    return _metrics[name]


# Define Prometheus metrics for instance metrics
nb_users_gauge = get_or_create_gauge(
    "ciso_assistant_nb_users",
    "Number of users in the CISO Assistant instance",
)
nb_first_login_gauge = get_or_create_gauge(
    "ciso_assistant_nb_first_login",
    "Number of users who have logged in for the first time",
)
nb_libraries_gauge = get_or_create_gauge(
    "ciso_assistant_nb_libraries",
    "Number of loaded libraries in the CISO Assistant instance",
)
nb_domains_gauge = get_or_create_gauge(
    "ciso_assistant_nb_domains",
    "Number of domains in the CISO Assistant instance",
)
nb_perimeters_gauge = get_or_create_gauge(
    "ciso_assistant_nb_perimeters",
    "Number of perimeters in the CISO Assistant instance",
)
nb_assets_gauge = get_or_create_gauge(
    "ciso_assistant_nb_assets",
    "Number of assets in the CISO Assistant instance",
)
nb_threats_gauge = get_or_create_gauge(
    "ciso_assistant_nb_threats",
    "Number of threats in the CISO Assistant instance",
)
nb_functions_gauge = get_or_create_gauge(
    "ciso_assistant_nb_functions",
    "Number of reference control functions in the CISO Assistant instance",
)
nb_measures_gauge = get_or_create_gauge(
    "ciso_assistant_nb_measures",
    "Number of applied control measures in the CISO Assistant instance",
)
nb_evidences_gauge = get_or_create_gauge(
    "ciso_assistant_nb_evidences",
    "Number of evidences in the CISO Assistant instance",
)
nb_compliance_assessments_gauge = get_or_create_gauge(
    "ciso_assistant_nb_compliance_assessments",
    "Number of compliance assessments in the CISO Assistant instance",
)
nb_risk_assessments_gauge = get_or_create_gauge(
    "ciso_assistant_nb_risk_assessments",
    "Number of risk assessments in the CISO Assistant instance",
)
nb_risk_scenarios_gauge = get_or_create_gauge(
    "ciso_assistant_nb_risk_scenarios",
    "Number of risk scenarios in the CISO Assistant instance",
)
nb_risk_acceptances_gauge = get_or_create_gauge(
    "ciso_assistant_nb_risk_acceptances",
    "Number of risk acceptances in the CISO Assistant instance",
)
nb_seats_gauge = get_or_create_gauge(
    "ciso_assistant_nb_seats",
    "Number of seats in the CISO Assistant instance",
)
nb_editors_gauge = get_or_create_gauge(
    "ciso_assistant_nb_editors",
    "Number of editors in the CISO Assistant instance",
)
expiration_gauge = get_or_create_gauge(
    "ciso_assistant_license_expiration",
    "Expiration date of the CISO Assistant license",
)
created_at_gauge = get_or_create_gauge(
    "ciso_assistant_created_at",
    "Creation date of the CISO Assistant instance",
)
last_login_gauge = get_or_create_gauge(
    "ciso_assistant_last_login",
    "Last login date of the most recent user in the instance",
)

build_info = get_or_create_info(
    "ciso_assistant_build_info",
    "Build information for the CISO Assistant instance",
)

# Only set the info if it hasn't been set before
metric_names = [
    name for names in REGISTRY._collector_to_names.values() for name in names
]
build_info.info(
    {
        "version": settings.VERSION,
        "build": settings.BUILD,
        "schema_version": str(settings.SCHEMA_VERSION),
        "debug": str(settings.DEBUG),
    }
)
