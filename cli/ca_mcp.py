from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import requests
import json
from rich import print as rprint
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .mcp.env file
load_dotenv(".mcp.env")

# Initialize FastMCP server
mcp = FastMCP("ciso-assistant")

cli_cfg = dict()
auth_data = dict()
GLOBAL_FOLDER_ID = None

# Read TOKEN and VERIFY_CERTIFICATE from environment variables
API_URL = os.getenv("API_URL", "")
TOKEN = os.getenv("TOKEN", "")
VERIFY_CERTIFICATE = os.getenv("VERIFY_CERTIFICATE", "true").lower() in (
    "true",
    "1",
    "yes",
    "on",
)
HTTP_TIMEOUT = 30  # seconds


@mcp.tool()
async def get_risk_scenarios():
    """Get risks scenarios
    Query CISO Assistant Risk Registry
    """
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    # Get evidence ID by name
    url = f"{API_URL}/risk-scenarios/"
    res = requests.get(
        url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
    )
    data = res.json()
    if res.status_code != 200:
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No risk scenarios found", file=sys.stderr)
        return
    scenarios = [
        f"|{rs.get('name')}|{rs.get('description') or ''}|{rs.get('current_level')}|{rs.get('residual_level')}|{(rs.get('folder') or {}).get('str', 'N/A')}|"
        for rs in data["results"]
    ]
    return (
        "|name|description|current_level|residual_level|domain|"
        + "\n|---|---|---|---|---|\n"
        + "\n".join(scenarios)
    )


@mcp.tool()
async def get_applied_controls():
    """Get applied controls
    Query CISO Assistant combined action plan
    """
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    # Get evidence ID by name
    url = f"{API_URL}/applied-controls/"
    res = requests.get(
        url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
    )
    data = res.json()
    if res.status_code != 200:
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No applied controls found", file=sys.stderr)
        return
    items = [
        f"|{item.get('name')}|{item.get('description') or ''}|{item.get('status')}|{item.get('eta') or ''}|{(item.get('folder') or {}).get('str', 'N/A')}|"
        for item in data["results"]
    ]
    return (
        "|name|description|status|eta|domain|"
        + "\n|---|---|---|---|---|\n"
        + "\n".join(items)
    )


@mcp.tool()
async def get_business_impact_analyses():
    """Get all Business Impact Analyses (BIAs) in CISO Assistant
    Returns a list of BIAs with their status and basic information
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        res = requests.get(
            f"{API_URL}/resilience/business-impact-analysis/",
            headers=headers,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            bias = data["results"]
        elif isinstance(data, list):
            bias = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not bias:
            return "No Business Impact Analyses found"

        result = "# Business Impact Analyses\n\n"
        result += f"Total: {len(bias)}\n\n"
        result += "|ID|Name|Status|Version|Risk Matrix|Perimeter|Folder|\n"
        result += "|---|---|---|---|---|---|---|\n"

        for bia in bias:
            bia_id = bia.get("id", "N/A")
            name = bia.get("name", "N/A")
            status = bia.get("status", "N/A")
            version = bia.get("version", "N/A")
            risk_matrix = (bia.get("risk_matrix") or {}).get("str", "N/A")
            perimeter = (bia.get("perimeter") or {}).get("str", "N/A")
            folder = (bia.get("folder") or {}).get("str", "N/A")

            result += f"|{bia_id}|{name}|{status}|{version}|{risk_matrix}|{perimeter}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_business_impact_analyses: {str(e)}"


@mcp.tool()
async def get_audits_progress():
    """Get the audits progress
    Query CISO Assistant compliance engine for audits progress
    """
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    # Get evidence ID by name
    url = f"{API_URL}/compliance-assessments/"
    res = requests.get(
        url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
    )
    data = res.json()
    if res.status_code != 200:
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No audits found", file=sys.stderr)
        return
    items = [
        f"|{item.get('name')}|{(item.get('framework') or {}).get('str', 'N/A')}|{item.get('status')}|{item.get('progress')}|{(item.get('folder') or {}).get('str', 'N/A')}|"
        for item in data["results"]
    ]
    return (
        "|name|framework|status|progress|domain|"
        + "\n|---|---|---|---|---|\n"
        + "\n".join(items)
    )


@mcp.tool()
async def get_all_audits_with_metrics():
    """Get all compliance assessments (audits) with detailed compliance metrics
    Returns a comprehensive summary of all audits including requirement breakdown by compliance result

    Note: This uses 'result' field which represents the actual compliance outcome
    (compliant, non_compliant, partially_compliant, not_applicable, not_assessed).
    The 'status' field (not used here) represents the auditor's review workflow state.
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        # Get all compliance assessments
        url = f"{API_URL}/compliance-assessments/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )
        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            audits = data["results"]
        elif isinstance(data, list):
            audits = data
        else:
            return f"Error: Unexpected response format for audits: {type(data)}"

        if not audits:
            return "No audits found"

        # Fetch requirement assessments for all audits
        url = f"{API_URL}/requirement-assessments/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )
        if res.status_code != 200:
            return f"Error fetching requirements: HTTP {res.status_code} - {res.text}"

        req_data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(req_data, dict) and "results" in req_data:
            all_requirements = req_data["results"]
        elif isinstance(req_data, list):
            all_requirements = req_data
        else:
            all_requirements = []

        # Group requirements by compliance assessment
        req_by_audit = {}
        for req in all_requirements:
            # compliance_assessment is returned as an object with id, name, etc.
            compliance_assessment = req.get("compliance_assessment")
            if compliance_assessment:
                # Extract the ID from the compliance_assessment object
                audit_id = (
                    compliance_assessment.get("id")
                    if isinstance(compliance_assessment, dict)
                    else compliance_assessment
                )
                if audit_id:
                    if audit_id not in req_by_audit:
                        req_by_audit[audit_id] = []
                    req_by_audit[audit_id].append(req)

        # Build summary for each audit
        result = "# All Compliance Assessments - Summary\n\n"
        result += f"Total Audits: {len(audits)}\n\n"

        for audit in audits:
            audit_id = audit.get("id")
            audit_name = audit.get("name", "N/A")
            framework = (audit.get("framework") or {}).get("str", "N/A")
            status = audit.get("status", "N/A")
            progress = audit.get("progress", "N/A")
            domain = (audit.get("folder") or {}).get("str", "N/A")

            requirements = req_by_audit.get(audit_id, [])
            total = len(requirements)

            # Count by compliance result (not status)
            # result = actual compliance outcome
            compliant = sum(
                1 for r in requirements if r.get("result", "").lower() == "compliant"
            )
            non_compliant = sum(
                1
                for r in requirements
                if r.get("result", "").lower() == "non_compliant"
            )
            partially_compliant = sum(
                1
                for r in requirements
                if r.get("result", "").lower() == "partially_compliant"
            )
            not_applicable = sum(
                1
                for r in requirements
                if r.get("result", "").lower() == "not_applicable"
            )
            not_assessed = sum(
                1 for r in requirements if r.get("result", "").lower() == "not_assessed"
            )

            result += f"## {audit_name}\n"
            result += f"- **Framework:** {framework}\n"
            result += f"- **Domain:** {domain}\n"
            result += f"- **Audit Status:** {status}\n"
            result += f"- **Progress:** {progress}%\n"
            result += f"- **Total Requirements:** {total}\n"

            if total > 0:
                result += f"\n**Compliance Results:**\n"
                result += f"  - Compliant: {compliant} ({compliant * 100 // total}%)\n"
                result += f"  - Partially Compliant: {partially_compliant} ({partially_compliant * 100 // total}%)\n"
                result += f"  - Non-Compliant: {non_compliant} ({non_compliant * 100 // total}%)\n"
                result += f"  - Not Assessed: {not_assessed} ({not_assessed * 100 // total}%)\n"
                result += f"  - Not Applicable: {not_applicable} ({not_applicable * 100 // total}%)\n"

                # Add gap indicator
                gaps = non_compliant + not_assessed
                if gaps > 0:
                    result += f"  - **⚠️ Gaps:** {gaps} requirements need attention\n"
                else:
                    result += f"  - **✅ No gaps**\n"
            else:
                result += f"  - No requirements found\n"

            result += "\n"

        return result
    except Exception as e:
        return f"Error in get_all_audits_with_metrics: {str(e)}"


@mcp.tool()
async def get_audit_gap_analysis(audit_name: str):
    """Perform gap analysis on a specific audit (compliance assessment)
    Get detailed compliance status and identify gaps (non-compliant requirements)

    Note: This uses 'result' field which represents the actual compliance outcome
    (compliant, non_compliant, partially_compliant, not_applicable, not_assessed).
    The 'status' field represents the auditor's review workflow state (todo, in_progress, in_review, done).

    Args:
        audit_name: Name of the audit/compliance assessment to analyze
    """
    headers = {
        "Authorization": f"Token {TOKEN}",
    }

    # First, find the compliance assessment by name
    url = f"{API_URL}/compliance-assessments/"
    res = requests.get(
        url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
    )
    if res.status_code != 200:
        rprint(f"Error: check credentials.", file=sys.stderr)
        return "Error: Unable to fetch audits"

    data = res.json()
    audit = None
    for item in data.get("results", []):
        if item.get("name") == audit_name:
            audit = item
            break

    if not audit:
        return f"Error: Audit '{audit_name}' not found"

    # Get requirement assessments for this compliance assessment
    url = f"{API_URL}/requirement-assessments/"
    params = {"compliance_assessment": audit["id"]}
    res = requests.get(
        url,
        headers=headers,
        params=params,
        verify=VERIFY_CERTIFICATE,
        timeout=HTTP_TIMEOUT,
    )

    if res.status_code != 200:
        rprint(f"Error: Unable to fetch requirement assessments.", file=sys.stderr)
        return "Error: Unable to fetch requirements"

    req_data = res.json()
    requirements = req_data.get("results", [])

    if not requirements:
        return f"No requirements found for audit '{audit_name}'"

    # Categorize requirements by compliance result (not status)
    # result = compliance outcome, status = auditor review workflow
    compliant = []
    non_compliant = []
    partially_compliant = []
    not_assessed = []
    not_applicable = []

    for req in requirements:
        result = (req.get("result") or "").lower()  # Compliance result
        review_status = (req.get("status") or "").lower()  # Auditor review status
        name = req.get("name", "N/A")
        description = (req.get("description") or "")[:100]  # Truncate long descriptions

        req_summary = f"{name} [Review: {review_status}]: {description}"

        if result == "compliant":
            compliant.append(req_summary)
        elif result == "non_compliant":
            non_compliant.append(req_summary)
        elif result == "partially_compliant":
            partially_compliant.append(req_summary)
        elif result == "not_applicable":
            not_applicable.append(req_summary)
        else:
            not_assessed.append(req_summary)

    # Build gap analysis report
    total = len(requirements)
    result = f"# Gap Analysis: {audit_name}\n\n"
    result += f"**Framework:** {(audit.get('framework') or {}).get('str', 'N/A')}\n"
    result += f"**Overall Progress:** {audit.get('progress', 'N/A')}\n"
    result += f"**Audit Status:** {audit.get('status', 'N/A')}\n\n"
    result += f"## Compliance Results Summary\n"
    result += f"- Total Requirements: {total}\n"
    result += f"- Compliant: {len(compliant)} ({len(compliant) * 100 // total if total > 0 else 0}%)\n"
    result += f"- Partially Compliant: {len(partially_compliant)} ({len(partially_compliant) * 100 // total if total > 0 else 0}%)\n"
    result += f"- Non-Compliant: {len(non_compliant)} ({len(non_compliant) * 100 // total if total > 0 else 0}%)\n"
    result += f"- Not Assessed: {len(not_assessed)} ({len(not_assessed) * 100 // total if total > 0 else 0}%)\n"
    result += f"- Not Applicable: {len(not_applicable)} ({len(not_applicable) * 100 // total if total > 0 else 0}%)\n\n"

    # Show gaps (non-compliant + not assessed)
    if non_compliant or not_assessed:
        result += f"## Gaps Requiring Attention\n\n"

        if non_compliant:
            result += f"### Non-Compliant ({len(non_compliant)})\n"
            for req in non_compliant[:10]:  # Limit to first 10
                result += f"- {req}\n"
            if len(non_compliant) > 10:
                result += f"- ... and {len(non_compliant) - 10} more\n"
            result += "\n"

        if not_assessed:
            result += f"### Not Yet Assessed ({len(not_assessed)})\n"
            for req in not_assessed[:10]:  # Limit to first 10
                result += f"- {req}\n"
            if len(not_assessed) > 10:
                result += f"- ... and {len(not_assessed) - 10} more\n"
            result += "\n"
    else:
        result += f"## ✅ No Gaps Found\n\nAll requirements are either compliant or not applicable.\n"

    return result


def resolve_folder_id(folder_name_or_id: str) -> str:
    """Helper function to resolve folder name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID (contains hyphens in UUID format)
    if "-" in folder_name_or_id and len(folder_name_or_id) == 36:
        return folder_name_or_id

    # Otherwise, look up by name
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    res = requests.get(
        f"{API_URL}/folders/",
        headers=headers,
        params={"name": folder_name_or_id},
        verify=VERIFY_CERTIFICATE,
        timeout=HTTP_TIMEOUT,
    )

    if res.status_code != 200:
        raise ValueError(
            f"Failed to look up folder '{folder_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    folders = data.get("results", []) if isinstance(data, dict) else data

    if not folders:
        raise ValueError(f"Folder '{folder_name_or_id}' not found")

    if len(folders) > 1:
        raise ValueError(
            f"Multiple folders found with name '{folder_name_or_id}'. Please use UUID instead."
        )

    return folders[0]["id"]


def resolve_perimeter_id(perimeter_name_or_id: str) -> str:
    """Helper function to resolve perimeter name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in perimeter_name_or_id and len(perimeter_name_or_id) == 36:
        return perimeter_name_or_id

    # Otherwise, look up by name
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    res = requests.get(
        f"{API_URL}/perimeters/",
        headers=headers,
        params={"name": perimeter_name_or_id},
        verify=VERIFY_CERTIFICATE,
        timeout=HTTP_TIMEOUT,
    )

    if res.status_code != 200:
        raise ValueError(
            f"Failed to look up perimeter '{perimeter_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    perimeters = data.get("results", []) if isinstance(data, dict) else data

    if not perimeters:
        raise ValueError(f"Perimeter '{perimeter_name_or_id}' not found")

    if len(perimeters) > 1:
        raise ValueError(
            f"Multiple perimeters found with name '{perimeter_name_or_id}'. Please use UUID instead."
        )

    return perimeters[0]["id"]


def resolve_risk_matrix_id(matrix_name_or_id: str) -> str:
    """Helper function to resolve risk matrix name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in matrix_name_or_id and len(matrix_name_or_id) == 36:
        return matrix_name_or_id

    # Otherwise, look up by name
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    res = requests.get(
        f"{API_URL}/risk-matrices/",
        headers=headers,
        params={"name": matrix_name_or_id},
        verify=VERIFY_CERTIFICATE,
        timeout=HTTP_TIMEOUT,
    )

    if res.status_code != 200:
        raise ValueError(
            f"Failed to look up risk matrix '{matrix_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    matrices = data.get("results", []) if isinstance(data, dict) else data

    if not matrices:
        raise ValueError(f"Risk matrix '{matrix_name_or_id}' not found")

    if len(matrices) > 1:
        raise ValueError(
            f"Multiple risk matrices found with name '{matrix_name_or_id}'. Please use UUID instead."
        )

    return matrices[0]["id"]


def resolve_framework_id(framework_name_or_urn_or_id: str) -> str:
    """Helper function to resolve framework name/URN to UUID
    If already a UUID, returns it. If a name or URN, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in framework_name_or_urn_or_id and len(framework_name_or_urn_or_id) == 36:
        return framework_name_or_urn_or_id

    # Otherwise, look up by name or URN
    headers = {
        "Authorization": f"Token {TOKEN}",
    }

    # Try URN search first if it looks like a URN
    if framework_name_or_urn_or_id.startswith("urn:"):
        res = requests.get(
            f"{API_URL}/frameworks/",
            headers=headers,
            params={"urn": framework_name_or_urn_or_id},
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )
    else:
        # Search by name
        res = requests.get(
            f"{API_URL}/frameworks/",
            headers=headers,
            params={"name": framework_name_or_urn_or_id},
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

    if res.status_code != 200:
        raise ValueError(
            f"Failed to look up framework '{framework_name_or_urn_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    frameworks = data.get("results", []) if isinstance(data, dict) else data

    if not frameworks:
        raise ValueError(f"Framework '{framework_name_or_urn_or_id}' not found")

    if len(frameworks) > 1:
        raise ValueError(
            f"Multiple frameworks found with name '{framework_name_or_urn_or_id}'. Please use UUID or URN instead."
        )

    return frameworks[0]["id"]


def resolve_risk_assessment_id(assessment_name_or_id: str) -> str:
    """Helper function to resolve risk assessment name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in assessment_name_or_id and len(assessment_name_or_id) == 36:
        return assessment_name_or_id

    # Otherwise, look up by name
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    res = requests.get(
        f"{API_URL}/risk-assessments/",
        headers=headers,
        params={"name": assessment_name_or_id},
        verify=VERIFY_CERTIFICATE,
        timeout=HTTP_TIMEOUT,
    )

    if res.status_code != 200:
        raise ValueError(
            f"Failed to look up risk assessment '{assessment_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    assessments = data.get("results", []) if isinstance(data, dict) else data

    if not assessments:
        raise ValueError(f"Risk assessment '{assessment_name_or_id}' not found")

    if len(assessments) > 1:
        raise ValueError(
            f"Multiple risk assessments found with name '{assessment_name_or_id}'. Please use UUID instead."
        )

    return assessments[0]["id"]


@mcp.tool()
async def get_stored_libraries(
    object_type: str = None,
    provider: str = None,
):
    """Get available libraries (frameworks) that can be imported into CISO Assistant

    Args:
        object_type: Optional filter by object type (e.g., "framework", "risk_matrix", "requirement_mapping_set")
        provider: Optional filter by provider name

    Returns a list of stored libraries with their URNs, names, versions, and descriptions.
    Use the URN or ID to import a library with import_stored_library().
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        params = {}
        if object_type:
            params["object_type"] = object_type
        if provider:
            params["provider"] = provider

        res = requests.get(
            f"{API_URL}/stored-libraries/",
            headers=headers,
            params=params,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            libraries = data["results"]
        elif isinstance(data, list):
            libraries = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not libraries:
            return "No stored libraries found"

        result = "# Available Libraries (Not Yet Imported)\n\n"
        result += f"Total: {len(libraries)}\n\n"
        result += "|URN|Name|Version|Provider|Description|\n"
        result += "|---|---|---|---|---|\n"

        for lib in libraries:
            urn = lib.get("urn", "N/A")
            name = lib.get("name", "N/A")
            version = lib.get("version", "N/A")
            provider = lib.get("provider", "N/A")
            description = lib.get("description") or ""

            result += f"|{urn}|{name}|{version}|{provider}|{description}|\n"

        result += f"\n**To import a library, use `import_stored_library(urn_or_id)`**"
        return result
    except Exception as e:
        return f"Error in get_stored_libraries: {str(e)}"


@mcp.tool()
async def get_loaded_libraries():
    """Get loaded/imported libraries (frameworks) in CISO Assistant

    Returns a list of libraries that have already been imported and are available for use.
    These are frameworks/libraries that have been activated in the system.
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        res = requests.get(
            f"{API_URL}/loaded-libraries/",
            headers=headers,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            libraries = data["results"]
        elif isinstance(data, list):
            libraries = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not libraries:
            return "No loaded libraries found"

        result = "# Loaded Libraries (Already Imported)\n\n"
        result += f"Total: {len(libraries)}\n\n"
        result += "|URN|Name|Version|Provider|Description|\n"
        result += "|---|---|---|---|---|\n"

        for lib in libraries:
            urn = lib.get("urn", "N/A")
            name = lib.get("name", "N/A")
            version = lib.get("version", "N/A")
            provider = lib.get("provider", "N/A")
            description = lib.get("description") or ""

            result += f"|{urn}|{name}|{version}|{provider}|{description}|\n"

        return result
    except Exception as e:
        return f"Error in get_loaded_libraries: {str(e)}"


@mcp.tool()
async def import_stored_library(urn_or_id: str) -> str:
    """Import a stored library (framework) into CISO Assistant

    Args:
        urn_or_id: URN or ID of the stored library to import (e.g., "urn:intuitem:risk:library:nist-csf-2.0")

    This makes the library available for use (e.g., creating compliance assessments with the framework).
    Use get_stored_libraries() to see available libraries.
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        res = requests.post(
            f"{API_URL}/stored-libraries/{urn_or_id}/import/",
            headers=headers,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 200:
            result = res.json()
            if result.get("status") == "success":
                return f"✅ Library imported successfully: {urn_or_id}"
            else:
                error = result.get("error", "Unknown error")
                return f"Error importing library: {error}"
        else:
            return f"Error importing library: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in import_stored_library: {str(e)}"


@mcp.tool()
async def get_frameworks():
    """Get all frameworks available in CISO Assistant

    Returns a list of frameworks that have been imported/loaded and are available for creating compliance assessments.
    Use this to find framework IDs/URNs/names for creating audits.
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        res = requests.get(
            f"{API_URL}/frameworks/",
            headers=headers,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            frameworks = data["results"]
        elif isinstance(data, list):
            frameworks = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not frameworks:
            return "No frameworks found"

        result = "# Frameworks\n\n"
        result += f"Total: {len(frameworks)}\n\n"
        result += "|ID|URN|Name|Description|Provider|Folder|\n"
        result += "|---|---|---|---|---|---|\n"

        for framework in frameworks:
            framework_id = framework.get("id", "N/A")
            urn = framework.get("urn", "N/A")
            name = framework.get("name", "N/A")
            description = framework.get("description") or ""
            provider = framework.get("provider", "N/A")
            folder = (framework.get("folder") or {}).get("str", "N/A")

            result += (
                f"|{framework_id}|{urn}|{name}|{description}|{provider}|{folder}|\n"
            )

        return result
    except Exception as e:
        return f"Error in get_frameworks: {str(e)}"


@mcp.tool()
async def get_folders():
    """Get all folders (domains) in CISO Assistant
    Returns a list of folders with their IDs and names for reference when creating objects
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        url = f"{API_URL}/folders/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            folders = data["results"]
        elif isinstance(data, list):
            folders = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not folders:
            return "No folders found"

        result = "# Folders (Domains)\n\n"
        result += "|ID|Name|Description|Parent Folder|\n"
        result += "|---|---|---|---|\n"

        for folder in folders:
            folder_id = folder.get("id", "N/A")
            name = folder.get("name", "N/A")
            description = (folder.get("description") or "")[
                :50
            ]  # Truncate long descriptions
            parent = folder.get("parent_folder") or {}
            parent_name = parent.get("str", "Root") if parent else "Root"

            result += f"|{folder_id}|{name}|{description}|{parent_name}|\n"

        return result
    except Exception as e:
        return f"Error in get_folders: {str(e)}"


@mcp.tool()
async def get_perimeters():
    """Get all perimeters in CISO Assistant
    Returns a list of perimeters with their IDs and names for reference when creating assessments
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        url = f"{API_URL}/perimeters/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            perimeters = data["results"]
        elif isinstance(data, list):
            perimeters = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not perimeters:
            return "No perimeters found"

        result = "# Perimeters\n\n"
        result += "|ID|Name|Description|Folder|\n"
        result += "|---|---|---|---|\n"

        for perimeter in perimeters:
            perimeter_id = perimeter.get("id", "N/A")
            name = perimeter.get("name", "N/A")
            description = (perimeter.get("description") or "")[:50]
            folder = (perimeter.get("folder") or {}).get("str", "N/A")

            result += f"|{perimeter_id}|{name}|{description}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_perimeters: {str(e)}"


@mcp.tool()
async def get_risk_matrices():
    """Get all risk matrices in CISO Assistant
    Returns a list of risk matrices with their IDs and names for reference when creating risk assessments
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        url = f"{API_URL}/risk-matrices/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            matrices = data["results"]
        elif isinstance(data, list):
            matrices = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not matrices:
            return "No risk matrices found"

        result = "# Risk Matrices\n\n"
        result += "|ID|Name|Description|Folder|\n"
        result += "|---|---|---|---|\n"

        for matrix in matrices:
            matrix_id = matrix.get("id", "N/A")
            name = matrix.get("name", "N/A")
            description = (matrix.get("description") or "")[:50]
            folder = (matrix.get("folder") or {}).get("str", "N/A")

            result += f"|{matrix_id}|{name}|{description}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_risk_matrices: {str(e)}"


@mcp.tool()
async def get_risk_assessments():
    """Get all risk assessments in CISO Assistant
    Returns a list of risk assessments with their IDs, names, and status
    Use this to find the risk_assessment_id when creating risk scenarios
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        url = f"{API_URL}/risk-assessments/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            assessments = data["results"]
        elif isinstance(data, list):
            assessments = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not assessments:
            return "No risk assessments found"

        result = "# Risk Assessments\n\n"
        result += "|ID|Name|Status|Risk Matrix|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for assessment in assessments:
            assessment_id = assessment.get("id", "N/A")
            name = assessment.get("name", "N/A")
            status = assessment.get("status", "N/A")
            risk_matrix = (assessment.get("risk_matrix") or {}).get("str", "N/A")
            folder = (assessment.get("folder") or {}).get("str", "N/A")

            result += f"|{assessment_id}|{name}|{status}|{risk_matrix}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_risk_assessments: {str(e)}"


@mcp.tool()
async def get_threats():
    """Get all threats in CISO Assistant
    Returns a list of threats with their IDs, names, providers, and descriptions
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        url = f"{API_URL}/threats/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            threats = data["results"]
        elif isinstance(data, list):
            threats = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not threats:
            return "No threats found"

        result = "# Threats\n\n"
        result += f"Total: {len(threats)}\n\n"
        result += "|ID|Name|Provider|Description|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for threat in threats:
            threat_id = threat.get("id", "N/A")
            name = threat.get("name", "N/A")
            provider = threat.get("provider", "N/A")
            description = threat.get("description") or ""
            folder = (threat.get("folder") or {}).get("str", "N/A")

            result += f"|{threat_id}|{name}|{provider}|{description}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_threats: {str(e)}"


@mcp.tool()
async def get_assets():
    """Get all assets in CISO Assistant
    Returns a list of assets with their IDs, names, types, and other details
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        url = f"{API_URL}/assets/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            assets = data["results"]
        elif isinstance(data, list):
            assets = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not assets:
            return "No assets found"

        result = "# Assets\n\n"
        result += "|ID|Name|Type|Business Value|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for asset in assets:
            asset_id = asset.get("id", "N/A")
            name = asset.get("name", "N/A")
            asset_type = asset.get("type", "N/A")
            business_value = asset.get("business_value", "N/A")
            folder = (asset.get("folder") or {}).get("str", "N/A")

            result += f"|{asset_id}|{name}|{asset_type}|{business_value}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_assets: {str(e)}"


@mcp.tool()
async def get_incidents():
    """Get all incidents in CISO Assistant
    Returns a list of incidents with their IDs, names, severity, and status
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        url = f"{API_URL}/incidents/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            incidents = data["results"]
        elif isinstance(data, list):
            incidents = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not incidents:
            return "No incidents found"

        result = "# Incidents\n\n"
        result += "|ID|Name|Severity|Status|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for incident in incidents:
            incident_id = incident.get("id", "N/A")
            name = incident.get("name", "N/A")
            severity = incident.get("severity", "N/A")
            status = incident.get("status", "N/A")
            folder = (incident.get("folder") or {}).get("str", "N/A")

            result += f"|{incident_id}|{name}|{severity}|{status}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_incidents: {str(e)}"


@mcp.tool()
async def get_security_exceptions():
    """Get all security exceptions in CISO Assistant
    Returns a list of security exceptions with their IDs, names, approval status, and expiry dates
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
        }

        url = f"{API_URL}/security-exceptions/"
        res = requests.get(
            url, headers=headers, verify=VERIFY_CERTIFICATE, timeout=HTTP_TIMEOUT
        )

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()

        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            exceptions = data["results"]
        elif isinstance(data, list):
            exceptions = data
        else:
            return f"Error: Unexpected response format: {type(data)}"

        if not exceptions:
            return "No security exceptions found"

        result = "# Security Exceptions\n\n"
        result += "|ID|Name|State|Expiry Date|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for exception in exceptions:
            exception_id = exception.get("id", "N/A")
            name = exception.get("name", "N/A")
            state = exception.get("state", "N/A")
            expiry_date = exception.get("expiry_date") or "N/A"
            folder = (exception.get("folder") or {}).get("str", "N/A")

            result += f"|{exception_id}|{name}|{state}|{expiry_date}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_security_exceptions: {str(e)}"


@mcp.tool()
async def create_folder(
    name: str,
    description: str = "",
    parent_folder_id: str = None,
) -> str:
    """Create a new folder (domain) in CISO Assistant

    Args:
        name: Name of the folder
        description: Optional description of the folder
        parent_folder_id: Optional parent folder ID or name (can use folder name instead of UUID)
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "name": name,
            "description": description,
        }

        # Resolve parent folder name to ID if needed
        if parent_folder_id:
            parent_folder_id = resolve_folder_id(parent_folder_id)
            payload["parent_folder"] = parent_folder_id

        url = f"{API_URL}/folders/"
        res = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 201:
            folder = res.json()
            return f"✅ Folder created successfully: {folder.get('name')} (ID: {folder.get('id')})"
        else:
            return f"Error creating folder: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_folder: {str(e)}"


@mcp.tool()
async def create_perimeter(
    name: str,
    description: str = "",
    folder_id: str = None,
) -> str:
    """Create a new perimeter in CISO Assistant

    Args:
        name: Name of the perimeter
        description: Optional description of the perimeter
        folder_id: Optional folder/domain ID or name where to create the perimeter (can use folder name instead of UUID)
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "description": description,
        }

        if folder_id:
            payload["folder"] = folder_id

        url = f"{API_URL}/perimeters/"
        res = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 201:
            perimeter = res.json()
            return f"✅ Perimeter created successfully: {perimeter.get('name')} (ID: {perimeter.get('id')})"
        else:
            return f"Error creating perimeter: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_perimeter: {str(e)}"


@mcp.tool()
async def create_asset(
    name: str,
    description: str = "",
    asset_type: str = "PR",
    folder_id: str = None,
) -> str:
    """Create a new asset in CISO Assistant

    Args:
        name: Name of the asset
        description: Optional description of the asset
        asset_type: Type of asset - "PR" for Primary or "SP" for Supporting (defaults to "PR")
        folder_id: Optional folder/domain ID or name where to create the asset (can use folder name instead of UUID)
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        # If no folder specified, try to get the default folder
        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "description": description,
            "type": asset_type,
        }

        if folder_id:
            payload["folder"] = folder_id

        url = f"{API_URL}/assets/"
        res = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 201:
            asset = res.json()
            return f"✅ Asset created successfully: {asset.get('name')} (ID: {asset.get('id')})"
        else:
            return f"Error creating asset: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_asset: {str(e)}"


@mcp.tool()
async def create_threat(
    name: str,
    description: str = "",
    provider: str = "",
    ref_id: str = "",
    folder_id: str = None,
) -> str:
    """Create a new threat in CISO Assistant

    Args:
        name: Name of the threat
        description: Optional description of the threat
        provider: Optional provider/source of the threat (e.g., "MITRE ATT&CK", "Custom")
        ref_id: Optional reference ID for the threat
        folder_id: Optional folder/domain ID or name where to create the threat (can use folder name instead of UUID)
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        # If no folder specified, try to get the default folder
        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "description": description,
        }

        if provider:
            payload["provider"] = provider

        if ref_id:
            payload["ref_id"] = ref_id

        if folder_id:
            payload["folder"] = folder_id

        url = f"{API_URL}/threats/"
        res = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 201:
            threat = res.json()
            return f"✅ Threat created successfully: {threat.get('name')} (ID: {threat.get('id')})"
        else:
            return f"Error creating threat: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_threat: {str(e)}"


@mcp.tool()
async def update_asset(
    asset_id: str,
    name: str = None,
    description: str = None,
    asset_type: str = None,
    business_value: str = None,
    parent_assets: list = None,
) -> str:
    """Update an existing asset in CISO Assistant

    Args:
        asset_id: ID or name of the asset to update
        name: Optional new name for the asset
        description: Optional new description
        asset_type: Optional new type - "PR" for Primary or "SP" for Supporting
        business_value: Optional business value (e.g., "low", "medium", "high", "very_high")
        parent_assets: Optional list of parent asset IDs or names (can use asset names instead of UUIDs)
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        # Resolve asset name to ID if needed
        resolved_asset_id = asset_id
        if not ("-" in asset_id and len(asset_id) == 36):
            # Look up by name
            res = requests.get(
                f"{API_URL}/assets/",
                headers=headers,
                params={"name": asset_id},
                verify=VERIFY_CERTIFICATE,
                timeout=HTTP_TIMEOUT,
            )
            if res.status_code != 200:
                return f"Error: Failed to look up asset '{asset_id}': HTTP {res.status_code}"

            data = res.json()
            assets = data.get("results", []) if isinstance(data, dict) else data

            if not assets:
                return f"Error: Asset '{asset_id}' not found"
            if len(assets) > 1:
                return f"Error: Multiple assets found with name '{asset_id}'. Please use UUID instead."

            resolved_asset_id = assets[0]["id"]

        # Build update payload with only provided fields
        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if asset_type is not None:
            payload["type"] = asset_type
        if business_value is not None:
            payload["business_value"] = business_value

        # Resolve parent asset names to IDs if provided
        if parent_assets is not None:
            resolved_parents = []
            for parent in parent_assets:
                if "-" in parent and len(parent) == 36:
                    # Already a UUID
                    resolved_parents.append(parent)
                else:
                    # Look up by name
                    res = requests.get(
                        f"{API_URL}/assets/",
                        headers=headers,
                        params={"name": parent},
                        verify=VERIFY_CERTIFICATE,
                        timeout=HTTP_TIMEOUT,
                    )
                    if res.status_code != 200:
                        return f"Error: Failed to look up parent asset '{parent}': HTTP {res.status_code}"

                    data = res.json()
                    parent_assets_list = (
                        data.get("results", []) if isinstance(data, dict) else data
                    )

                    if not parent_assets_list:
                        return f"Error: Parent asset '{parent}' not found"
                    if len(parent_assets_list) > 1:
                        return f"Error: Multiple assets found with name '{parent}'. Please use UUID instead."

                    resolved_parents.append(parent_assets_list[0]["id"])

            payload["parent_assets"] = resolved_parents

        if not payload:
            return "Error: No fields provided to update"

        url = f"{API_URL}/assets/{resolved_asset_id}/"
        res = requests.patch(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 200:
            asset = res.json()
            return f"✅ Asset updated successfully: {asset.get('name')} (ID: {asset.get('id')})"
        else:
            return f"Error updating asset: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in update_asset: {str(e)}"


@mcp.tool()
async def create_applied_control(
    name: str,
    description: str = "",
    eta: str = None,
    folder_id: str = None,
    category: str = "technical",
    status: str = "planned",
) -> str:
    """Create a new applied control (security measure) in CISO Assistant

    Args:
        name: Name of the control
        description: Optional description of what the control does
        eta: Optional estimated completion date (format: YYYY-MM-DD)
        folder_id: Optional folder/domain ID or name where to create the control (can use folder name instead of UUID)
        category: Control category (technical, physical, organizational, or procedural) - defaults to "technical"
        status: Control status (planned, active, or inactive) - defaults to "planned"
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "description": description,
            "category": category,
            "status": status,
        }

        if folder_id:
            payload["folder"] = folder_id

        if eta:
            payload["eta"] = eta

        url = f"{API_URL}/applied-controls/"
        res = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 201:
            control = res.json()
            return f"✅ Applied control created successfully: {control.get('name')} (ID: {control.get('id')})"
        else:
            return f"Error creating applied control: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_applied_control: {str(e)}"


@mcp.tool()
async def create_risk_assessment(
    name: str,
    risk_matrix_id: str,
    perimeter_id: str,
    description: str = "",
    version: str = "1.0",
    status: str = "planned",
    folder_id: str = None,
) -> str:
    """Create a new risk assessment in CISO Assistant

    Args:
        name: Name of the risk assessment
        risk_matrix_id: ID or name of the risk matrix to use (can use risk matrix name instead of UUID; required)
        perimeter_id: ID or name of the perimeter (scope) for this assessment (can use perimeter name instead of UUID; required)
        description: Optional description
        version: Optional version string (defaults to "1.0")
        status: Optional status - "planned", "in_progress", "in_review", "done", or "deprecated" (defaults to "planned")
        folder_id: Optional folder/domain ID or name where to create the assessment (can use folder name instead of UUID; if not provided, inherits from perimeter)
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        # Resolve risk matrix name to ID if needed
        risk_matrix_id = resolve_risk_matrix_id(risk_matrix_id)

        # Resolve perimeter name to ID if needed
        perimeter_id = resolve_perimeter_id(perimeter_id)

        # Resolve folder name to ID if needed (optional)
        if folder_id:
            folder_id = resolve_folder_id(folder_id)
        elif GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        payload = {
            "name": name,
            "risk_matrix": risk_matrix_id,
            "perimeter": perimeter_id,
            "description": description,
            "version": version,
            "status": status,
        }

        # Folder is optional - if not provided, it inherits from perimeter
        if folder_id:
            payload["folder"] = folder_id

        url = f"{API_URL}/risk-assessments/"
        res = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 201:
            assessment = res.json()
            return f"✅ Risk assessment created successfully: {assessment.get('name')} (ID: {assessment.get('id')})"
        else:
            return f"Error creating risk assessment: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_risk_assessment: {str(e)}"


@mcp.tool()
async def create_risk_scenario(
    name: str,
    description: str = "",
    risk_assessment_id: str = None,
    folder_id: str = None,
    existing_controls: str = "",
    current_proba: int = None,
    current_impact: int = None,
) -> str:
    """Create a new risk scenario in CISO Assistant

    Args:
        name: Name/title of the risk scenario
        description: Description of the risk scenario
        risk_assessment_id: Optional ID or name of the risk assessment to link this scenario to (can use risk assessment name instead of UUID)
        folder_id: Optional folder/domain ID or name where to create the scenario (can use folder name instead of UUID)
        existing_controls: Optional description of existing controls
        current_proba: Optional current probability level (0-4, where 0=very low, 4=very high)
        current_impact: Optional current impact level (0-4, where 0=very low, 4=very high)
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        # Resolve risk assessment name to ID if needed
        if risk_assessment_id:
            risk_assessment_id = resolve_risk_assessment_id(risk_assessment_id)

        payload = {
            "name": name,
            "description": description,
        }

        if folder_id:
            payload["folder"] = folder_id

        if risk_assessment_id:
            payload["risk_assessment"] = risk_assessment_id

        if existing_controls:
            payload["existing_controls"] = existing_controls

        if current_proba is not None:
            payload["current_proba"] = current_proba

        if current_impact is not None:
            payload["current_impact"] = current_impact

        url = f"{API_URL}/risk-scenarios/"
        res = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 201:
            scenario = res.json()
            return f"✅ Risk scenario created successfully: {scenario.get('name')} (ID: {scenario.get('id')})"
        else:
            return f"Error creating risk scenario: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_risk_scenario: {str(e)}"


@mcp.tool()
async def create_business_impact_analysis(
    name: str,
    risk_matrix_id: str,
    perimeter_id: str,
    description: str = "",
    version: str = "1.0",
    status: str = "planned",
    folder_id: str = None,
) -> str:
    """Create a new Business Impact Analysis (BIA) in CISO Assistant

    Args:
        name: Name of the BIA
        risk_matrix_id: ID or name of the risk matrix to use (can use risk matrix name instead of UUID; required)
        perimeter_id: ID or name of the perimeter (scope) for this BIA (can use perimeter name instead of UUID; required)
        description: Optional description
        version: Optional version string (defaults to "1.0")
        status: Optional status - "planned", "in_progress", "in_review", "done", or "deprecated" (defaults to "planned")
        folder_id: Optional folder/domain ID or name where to create the BIA (can use folder name instead of UUID; if not provided, inherits from perimeter)
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        # Resolve risk matrix name to ID if needed
        risk_matrix_id = resolve_risk_matrix_id(risk_matrix_id)

        # Resolve perimeter name to ID if needed
        perimeter_id = resolve_perimeter_id(perimeter_id)

        # Resolve folder name to ID if needed (optional)
        if folder_id:
            folder_id = resolve_folder_id(folder_id)
        elif GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        payload = {
            "name": name,
            "risk_matrix": risk_matrix_id,
            "perimeter": perimeter_id,
            "description": description,
            "version": version,
            "status": status,
        }

        # Folder is optional - if not provided, it inherits from perimeter
        if folder_id:
            payload["folder"] = folder_id

        url = f"{API_URL}/resilience/business-impact-analysis/"
        res = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 201:
            bia = res.json()
            return f"✅ Business Impact Analysis created successfully: {bia.get('name')} (ID: {bia.get('id')})"
        else:
            return f"Error creating Business Impact Analysis: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_business_impact_analysis: {str(e)}"


@mcp.tool()
async def create_compliance_assessment(
    name: str,
    framework_id: str,
    perimeter_id: str,
    description: str = "",
    version: str = "1.0",
    status: str = "planned",
    folder_id: str = None,
) -> str:
    """Create a new compliance assessment (audit) in CISO Assistant

    Args:
        name: Name of the compliance assessment
        framework_id: ID, URN, or name of the framework to use (e.g., "ISO 27001" or "urn:intuitem:risk:library:iso27001-2022")
        perimeter_id: ID or name of the perimeter (scope) for this assessment
        description: Optional description of the assessment
        version: Optional version string (defaults to "1.0")
        status: Optional status - "planned", "in_progress", "in_review", "done", or "deprecated" (defaults to "planned")
        folder_id: Optional folder/domain ID or name where to create the assessment (can use folder name instead of UUID; if not provided, inherits from perimeter)
    """
    try:
        headers = {
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/json",
        }

        # Resolve framework name/URN to ID if needed
        framework_id = resolve_framework_id(framework_id)

        # Resolve perimeter name to ID if needed
        perimeter_id = resolve_perimeter_id(perimeter_id)

        # Resolve folder name to ID if needed (optional)
        if folder_id:
            folder_id = resolve_folder_id(folder_id)
        elif GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        payload = {
            "name": name,
            "framework": framework_id,
            "perimeter": perimeter_id,
            "description": description,
            "version": version,
            "status": status,
        }

        # Folder is optional - if not provided, it inherits from perimeter
        if folder_id:
            payload["folder"] = folder_id

        url = f"{API_URL}/compliance-assessments/"
        res = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_CERTIFICATE,
            timeout=HTTP_TIMEOUT,
        )

        if res.status_code == 201:
            assessment = res.json()
            return f"✅ Compliance assessment created successfully: {assessment.get('name')} (ID: {assessment.get('id')})"
        else:
            return (
                f"Error creating compliance assessment: {res.status_code} - {res.text}"
            )
    except Exception as e:
        return f"Error in create_compliance_assessment: {str(e)}"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
