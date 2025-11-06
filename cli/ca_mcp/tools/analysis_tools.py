"""Analysis MCP tools for CISO Assistant"""

import sys
from rich import print as rprint
from ..client import make_get_request, fetch_all_results


async def get_all_audits_with_metrics():
    """List all audits with compliance metrics breakdown (uses 'result' field for compliance outcome, not 'status')"""
    try:
        # Get all compliance assessments (with pagination)
        audits, error = fetch_all_results("/compliance-assessments/")
        if error:
            return error

        if not audits:
            return "No audits found"

        # Fetch all requirement assessments (with pagination)
        all_requirements, error = fetch_all_results("/requirement-assessments/")
        if error:
            return f"Error fetching requirements: {error}"

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


async def get_audit_gap_analysis(audit_name: str):
    """Perform gap analysis on audit: identify non-compliant and not-assessed requirements (uses 'result' not 'status')

    Args:
        audit_name: Audit/compliance assessment name
    """
    # First, find the compliance assessment by name (with pagination)
    audits, error = fetch_all_results("/compliance-assessments/")
    if error:
        rprint(f"Error: check credentials.", file=sys.stderr)
        return "Error: Unable to fetch audits"

    audit = None
    for item in audits:
        if item.get("name") == audit_name:
            audit = item
            break

    if not audit:
        return f"Error: Audit '{audit_name}' not found"

    # Get all requirement assessments for this compliance assessment (with pagination)
    params = {"compliance_assessment": audit["id"]}
    requirements, error = fetch_all_results("/requirement-assessments/", params=params)

    if error:
        rprint(f"Error: Unable to fetch requirement assessments.", file=sys.stderr)
        return "Error: Unable to fetch requirements"

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
