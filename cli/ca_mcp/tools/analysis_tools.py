"""Analysis MCP tools for CISO Assistant"""

from ..client import make_get_request, fetch_all_results
from ..utils.response_formatter import (
    success_response,
    error_response,
)


async def get_all_audits_with_metrics(
    folder: str = None,
    perimeter: str = None,
    status: str = None,
    framework: str = None,
):
    """List audits with, for each, the compliance-result breakdown (compliant / non-compliant / partially / not-assessed / not-applicable counts) AND the score. The audit "score" is the maturity score (the headline figure); implementation and documentation scores are its components. Use this for 'show the audits with scores' or overall compliance-status questions. Use filters to avoid large responses.

    Args:
        folder: Folder ID/name
        perimeter: Perimeter ID/name
        status: Filter by status: created | in_progress | in_review | done | deprecated
        framework: Framework ID/name
    """
    try:
        from ..resolvers import (
            resolve_folder_id,
            resolve_perimeter_id,
            resolve_framework_id,
        )

        params = {}
        if folder:
            params["folder"] = resolve_folder_id(folder)
        if perimeter:
            params["perimeter"] = resolve_perimeter_id(perimeter)
        if status:
            params["status"] = status
        if framework:
            params["framework"] = resolve_framework_id(framework)

        # Filtered listing (with pagination) — carries the native status/progress
        # fields and honours all four filters.
        audits, error = fetch_all_results("/compliance-assessments/", params=params)
        if error:
            return error

        if not audits:
            return "No audits found matching the given filters"

        # Fetch compliance-result counts + aggregate scores for every accessible
        # audit in ONE server-side prefetched call, replacing the previous
        # per-audit requirement-assessment fetch (no more N+1). /recap/ takes no
        # filters, so we use it purely as an id -> metrics map and display only
        # the filtered subset above. Best-effort: if recap is unavailable, each
        # audit's metrics degrade to "unavailable" rather than failing the run.
        # recap returns a bare (non-paginated) list, so we read it directly.
        metrics_map = {}
        recap_res = make_get_request("/compliance-assessments/recap/")
        if recap_res.status_code == 200:
            recap_data = recap_res.json()
            if isinstance(recap_data, list):
                for entry in recap_data:
                    metrics_map[str(entry.get("id"))] = entry

        def _fmt_score(value):
            # -1 is the backend sentinel for "nothing scored"
            return "N/A" if value is None or value == -1 else value

        result = "# Compliance Assessments - Summary\n\n"
        result += f"Total Audits: {len(audits)}\n\n"

        for audit in audits:
            audit_id = audit.get("id")
            audit_name = audit.get("name", "N/A")
            fw = (audit.get("framework") or {}).get("str", "N/A")
            audit_status = audit.get("status", "N/A")
            progress = audit.get("progress", "N/A")
            domain = (audit.get("folder") or {}).get("str", "N/A")

            result += f"## {audit_name}\n"
            result += f"- **Framework:** {fw}\n"
            result += f"- **Domain:** {domain}\n"
            result += f"- **Audit Status:** {audit_status}\n"
            result += f"- **Progress:** {progress}%\n"

            entry = metrics_map.get(str(audit_id))
            if entry is None:
                result += "- Metrics unavailable (audit not returned by recap)\n\n"
                continue

            # Aggregate score (server-computed). The headline "score" is the
            # maturity score; implementation/documentation are its components.
            gs = entry.get("global_score") or {}
            result += f"- **Score (Maturity):** {_fmt_score(gs.get('maturity_score'))}\n"
            result += f"  - Implementation: {_fmt_score(gs.get('implementation_score'))}\n"
            doc_score = gs.get("documentation_score")
            if doc_score is not None:
                result += f"  - Documentation: {_fmt_score(doc_score)}\n"

            # Compliance-result counts (assessable requirements only), taken from
            # the donut breakdown rather than re-counted client-side.
            donut_values = (
                ((entry.get("donut") or {}).get("result") or {}).get("values") or []
            )
            counts = {v.get("name"): v.get("value", 0) for v in donut_values}
            total = sum(counts.values())

            compliant = counts.get("compliant", 0)
            non_compliant = counts.get("non_compliant", 0)
            partially_compliant = counts.get("partially_compliant", 0)
            not_applicable = counts.get("not_applicable", 0)
            not_assessed = counts.get("not_assessed", 0)

            result += f"- **Total Requirements:** {total}\n"
            if total > 0:
                result += f"\n**Compliance Results:**\n"
                result += f"  - Compliant: {compliant} ({compliant * 100 // total}%)\n"
                result += f"  - Partially Compliant: {partially_compliant} ({partially_compliant * 100 // total}%)\n"
                result += f"  - Non-Compliant: {non_compliant} ({non_compliant * 100 // total}%)\n"
                result += f"  - Not Assessed: {not_assessed} ({not_assessed * 100 // total}%)\n"
                result += f"  - Not Applicable: {not_applicable} ({not_applicable * 100 // total}%)\n"

                gaps = non_compliant + not_assessed
                if gaps > 0:
                    result += f"  - Gaps: {gaps} requirements need attention\n"
                else:
                    result += f"  - No gaps\n"
            else:
                result += f"  - No requirements found\n"

            result += "\n"

        return result
    except Exception as e:
        return f"Error in get_all_audits_with_metrics: {str(e)}"


async def get_audit_gap_analysis(audit_name: str):
    """Perform gap analysis on audit: identify non-compliant and not-assessed requirements (uses 'result' not 'status')

    Args:
        audit_name: Audit/compliance assessment name or ID
    """
    from ..resolvers import resolve_compliance_assessment_id

    # Resolve audit name to ID
    try:
        audit_id = resolve_compliance_assessment_id(audit_name)
    except ValueError as e:
        return error_response(
            "Not Found",
            str(e),
            "Use get_audits_progress() to see available audits",
            retry_allowed=True,
        )

    # Fetch the audit details
    audit_res = make_get_request(f"/compliance-assessments/{audit_id}/")
    if audit_res.status_code != 200:
        return error_response(
            "API Error",
            f"Unable to fetch audit: {audit_res.status_code}",
            "Verify API token configuration",
            retry_allowed=False,
        )

    audit = audit_res.json()

    # Get all requirement assessments for this compliance assessment (with pagination)
    params = {"compliance_assessment": audit["id"]}
    requirements, error = fetch_all_results("/requirement-assessments/", params=params)

    if error:
        return error_response(
            "API Error",
            "Unable to fetch requirement assessments",
            "Report this error to the user",
            retry_allowed=False,
        )

    if not requirements:
        return success_response(
            f"Audit '{audit_name}' has no requirements.",
            "get_audit_gap_analysis",
            "Inform the user this audit has no requirements to assess",
        )

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
        result += f"## No Gaps Found\n\n[SUCCESS] All requirements are either compliant or not applicable.\n"

    return success_response(
        result,
        "get_audit_gap_analysis",
        "Use this gap analysis to answer the user's question about audit compliance",
    )


async def get_audit_global_score(audit_name: str):
    """Get an audit's score. The audit "score" is the maturity score (the headline figure: the average of the enabled implementation and documentation layers); implementation and documentation scores are its components. Server-computed with correct weighting, implementation-group filtering and N/A anchoring, without fetching individual requirement assessments.

    Args:
        audit_name: Audit/compliance assessment name or ID
    """
    from ..resolvers import resolve_compliance_assessment_id

    # Resolve audit name to ID
    try:
        audit_id = resolve_compliance_assessment_id(audit_name)
    except ValueError as e:
        return error_response(
            "Not Found",
            str(e),
            "Use get_audits_progress() to see available audits",
            retry_allowed=True,
        )
    except Exception as e:
        return error_response(
            "API Error",
            f"Unable to resolve audit: {e}",
            "Verify the API connection and token configuration",
            retry_allowed=True,
        )

    # Single O(1) call to the server-side aggregate endpoint. Guard the request
    # and JSON decode so timeouts, connection errors, or a malformed body return
    # a structured tool error instead of escaping as an unhandled exception.
    try:
        res = make_get_request(f"/compliance-assessments/{audit_id}/global_score/")
    except Exception as e:
        return error_response(
            "API Error",
            f"Unable to fetch global score: {e}",
            "Verify the API connection and token configuration",
            retry_allowed=True,
        )

    if res.status_code != 200:
        return error_response(
            "API Error",
            f"Unable to fetch global score: {res.status_code}",
            "Verify the audit exists and API token configuration",
            retry_allowed=False,
        )

    try:
        scores = res.json()
    except ValueError as e:
        return error_response(
            "API Error",
            f"Invalid response decoding global score: {e}",
            "Report this error to the user",
            retry_allowed=False,
        )

    def _fmt(value):
        # -1 is the backend sentinel for "nothing scored"
        return "N/A" if value is None or value == -1 else value

    if not scores.get("scoring_enabled", True):
        return success_response(
            f"Scoring is not enabled for audit '{audit_name}'.",
            "get_audit_global_score",
            "Inform the user this audit has no scoring configured",
        )

    result = f"# Score: {audit_name}\n\n"
    result += f"- **Score (Maturity):** {_fmt(scores.get('maturity_score'))}\n"
    result += f"\n_Components:_\n"
    result += (
        f"- **Implementation:** {_fmt(scores.get('implementation_score'))}\n"
    )
    documentation_score = scores.get("documentation_score")
    if documentation_score is not None:
        result += f"- **Documentation:** {_fmt(documentation_score)}\n"
    result += (
        f"- **Score Range:** {scores.get('min_score', 'N/A')} - "
        f"{scores.get('max_score', 'N/A')} (total max {scores.get('total_max_score', 'N/A')})\n"
    )

    return success_response(
        result,
        "get_audit_global_score",
        "The audit's score is the maturity score; use it to answer the user's question about the audit's overall score",
    )
