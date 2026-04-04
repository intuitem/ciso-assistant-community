"""
DORA Incident Report (IR) export utilities.

Transforms a DoraIncidentReport model instance into a JSON document
compliant with the DORA IR Schema v1.2.1.
"""

import json
from pathlib import Path
from typing import Any

from core.dora import ENTITY_TYPE_EBA_TO_IR


SCHEMA_PATH = Path(__file__).parent / "schemas" / "dora_ir_v1.2.1.json"


def _strip_empty(obj: Any) -> Any:
    """
    Recursively remove None values and empty strings/lists/dicts from a dict.
    The DORA schema uses additionalProperties: false, so we must not include
    keys with null or empty optional values.
    """
    if isinstance(obj, dict):
        return {k: _strip_empty(v) for k, v in obj.items() if _is_present(v)}
    if isinstance(obj, list):
        return [_strip_empty(item) for item in obj]
    return obj


def _is_present(value: Any) -> bool:
    """Check if a value should be included in the export (not None/empty)."""
    if value is None:
        return False
    if isinstance(value, str) and value == "":
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return True


def _format_datetime(dt) -> str | None:
    """Format a datetime to ISO 8601 string, or None if absent."""
    if dt is None:
        return None
    return dt.isoformat(timespec="seconds")


def entity_to_dora_ir(entity, entity_type_str: str) -> dict:
    """
    Map a tprm.Entity instance to the DORA IR Entity schema.

    Args:
        entity: tprm.Entity instance
        entity_type_str: One of SUBMITTING_ENTITY, AFFECTED_ENTITY,
                         ULTIMATE_PARENT_UNDERTAKING_ENTITY
    """
    if entity is None:
        return {}

    result = {
        "entityType": entity_type_str,
        "name": entity.name or "",
    }

    # Extract LEI and code from legal_identifiers JSONField
    legal_ids = entity.legal_identifiers or {}
    lei = legal_ids.get("LEI", "")
    if lei:
        result["LEI"] = lei

    # Use the first available identifier as code
    from tprm.dora_export import get_entity_identifier

    code, _, _ = get_entity_identifier(entity)
    if code:
        result["code"] = code

    # Map dora_entity_type (eba_CT code) to IR affected entity type
    if entity.dora_entity_type:
        ir_type = ENTITY_TYPE_EBA_TO_IR.get(entity.dora_entity_type)
        if ir_type:
            result["affectedEntityType"] = [ir_type]

    return result


def contact_to_dora_ir(name: str, email: str, phone: str) -> dict:
    """Build a DORA IR Contact object from plain field values."""
    result = {}
    if name:
        result["name"] = name
    if email:
        result["email"] = email
    if phone:
        result["phone"] = phone
    return result


def build_dora_ir_json(report) -> dict:
    """
    Assemble a complete DORA IR JSON document from a DoraIncidentReport instance.

    Reads shared lifecycle fields from the linked Incident:
    - incident.occurred_at -> incidentOccurrenceDateTime
    - incident.resolved_at -> incidentResolutionDateTime
    - incident.resolution -> incidentResolutionSummary
    - incident.is_bcp_activated -> isBusinessContinuityActivated
    """
    incident = report.incident

    # -- Top-level --
    data = {
        "incidentSubmission": report.incident_submission,
        "reportCurrency": report.report_currency,
    }

    # -- Entities --
    if report.submitting_entity:
        data["submittingEntity"] = entity_to_dora_ir(
            report.submitting_entity, "SUBMITTING_ENTITY"
        )

    affected = report.affected_entities.all()
    if affected.exists():
        data["affectedEntity"] = [
            entity_to_dora_ir(e, "AFFECTED_ENTITY") for e in affected
        ]

    if report.ultimate_parent_entity:
        data["ultimateParentUndertaking"] = entity_to_dora_ir(
            report.ultimate_parent_entity, "ULTIMATE_PARENT_UNDERTAKING_ENTITY"
        )

    # -- Contacts --
    primary = contact_to_dora_ir(
        report.primary_contact_name,
        report.primary_contact_email,
        report.primary_contact_phone,
    )
    if primary:
        data["primaryContact"] = primary

    secondary = contact_to_dora_ir(
        report.secondary_contact_name,
        report.secondary_contact_email,
        report.secondary_contact_phone,
    )
    if secondary:
        data["secondaryContact"] = secondary

    # -- Incident section --
    incident_data = {
        "financialEntityCode": report.financial_entity_code,
        "detectionDateTime": _format_datetime(report.detection_date_time),
        "classificationDateTime": _format_datetime(report.classification_date_time),
        "incidentDescription": report.incident_description,
        "otherInformation": report.other_information,
        "classificationTypes": report.classification_types,
        "isBusinessContinuityActivated": incident.is_bcp_activated,
        "incidentOccurrenceDateTime": _format_datetime(incident.occurred_at),
        "incidentDuration": report.incident_duration,
        "originatesFromThirdPartyProvider": report.originates_from_third_party_provider,
        "incidentDiscovery": report.incident_discovery,
        "competentAuthorityCode": report.competent_authority_code,
        "incidentType": report.incident_type,
        "rootCauseHLClassification": report.root_cause_hl_classification,
        "rootCausesDetailedClassification": report.root_causes_detailed_classification,
        "rootCausesAdditionalClassification": report.root_causes_additional_classification,
        "rootCausesOther": report.root_causes_other,
        "rootCausesInformation": report.root_causes_information,
        "rootCauseAddressingDateTime": _format_datetime(
            report.root_cause_addressing_date_time
        ),
        "incidentResolutionSummary": incident.resolution,
        "incidentResolutionDateTime": _format_datetime(incident.resolved_at),
        "incidentResolutionVsPlannedImplementation": report.incident_resolution_vs_planned,
        "assessmentOfRiskToCriticalFunctions": report.assessment_of_risk_to_critical_functions,
        "informationRelevantToResolutionAuthorities": report.information_relevant_to_resolution_authorities,
        "financialRecoveriesAmount": float(report.financial_recoveries_amount)
        if report.financial_recoveries_amount is not None
        else None,
        "grossAmountIndirectDirectCosts": float(
            report.gross_amount_indirect_direct_costs
        )
        if report.gross_amount_indirect_direct_costs is not None
        else None,
        "recurringNonMajorIncidentsDescription": report.recurring_non_major_incidents_description,
        "recurringIncidentDate": _format_datetime(report.recurring_incident_date),
    }
    data["incident"] = incident_data

    # -- Impact Assessment --
    if report.impact_assessment:
        data["impactAssessment"] = report.impact_assessment

    # -- Reporting to other authorities --
    if report.reporting_to_other_authorities:
        data["reportingToOtherAuthorities"] = report.reporting_to_other_authorities

    if report.reporting_to_other_authorities_other:
        data["reportingToOtherAuthoritiesOther"] = (
            report.reporting_to_other_authorities_other
        )

    if report.info_duration_service_downtime_actual_or_estimate:
        data["informationDurationServiceDowntimeActualOrEstimate"] = (
            report.info_duration_service_downtime_actual_or_estimate
        )

    # Strip empty/null values to satisfy additionalProperties: false
    return _strip_empty(data)


def validate_dora_ir(data: dict) -> list[str]:
    """
    Validate a DORA IR JSON document against the bundled schema.

    Returns a list of error messages (empty if valid).
    """
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema library not installed — cannot validate"]

    try:
        with open(SCHEMA_PATH) as f:
            schema = json.load(f)
    except FileNotFoundError:
        return [f"Schema file not found at {SCHEMA_PATH}"]

    format_checker = jsonschema.FormatChecker()
    validator = jsonschema.Draft202012Validator(schema, format_checker=format_checker)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return [
        f"{'.'.join(str(p) for p in error.absolute_path) or '(root)'}: {error.message}"
        for error in errors
    ]
