"""Library management MCP tools for CISO Assistant"""

from ..client import (
    fetch_all_results,
    found_line,
    make_get_request,
    make_post_request,
)
from ..utils.response_formatter import (
    empty_response,
    error_response,
    http_error_response,
    success_response,
)

# Library object types are plural; models may still send the legacy singular,
# which the API only matches against libraries written with that spelling.
PLURAL_OBJECT_TYPES = {
    "framework": "frameworks",
    "risk_matrix": "risk_matrices",
    "requirement_mapping_set": "requirement_mapping_sets",
}


async def get_stored_libraries(
    object_type: str = None,
    provider: str = None,
    search: str = None,
    offset: int = None,
):
    """List available libraries (frameworks) for import. Use URN/ID with import_stored_library()

    There are several hundred stored libraries, more than one response can hold.
    Prefer `search` to find one by name; use `offset` to walk the whole catalogue.

    Args:
        object_type: Object type (e.g. "frameworks", "risk_matrices")
        provider: Provider name
        search: Free-text match on name, description, URN or ref_id
        offset: Row to start from, for paging past the first response
    """
    try:
        params = {}
        if object_type:
            params["object_type"] = PLURAL_OBJECT_TYPES.get(object_type, object_type)
        if provider:
            params["provider"] = provider
        if search:
            params["search"] = search
        if offset:
            params["offset"] = offset

        # Fetch all stored libraries (with pagination)
        libraries, error = fetch_all_results("/stored-libraries/", params=params)
        if error:
            return error

        if not libraries:
            return "No stored libraries found"

        # truncation here hides the URN import_stored_library needs
        result = (
            found_line(libraries, "stored libraries", paginated=True, offset=offset)
            + "\n\n"
        )
        result += "|URN|Name|Version|Provider|\n"
        result += "|---|---|---|---|\n"

        for lib in libraries:
            urn = lib.get("urn", "N/A")
            name = lib.get("name", "N/A")
            version = lib.get("version", "N/A")
            provider = lib.get("provider", "N/A")

            result += f"|{urn}|{name}|{version}|{provider}|\n"

        return result
    except Exception as e:
        return f"Error in get_stored_libraries: {str(e)}"


async def get_loaded_libraries(search: str = None, offset: int = None):
    """List loaded/imported libraries (frameworks) activated in the system

    Args:
        search: Free-text match on name, description, URN or ref_id
        offset: Row to start from, for paging past the first response
    """
    try:
        params = {}
        if search:
            params["search"] = search
        if offset:
            params["offset"] = offset

        # Fetch all loaded libraries (with pagination)
        libraries, error = fetch_all_results("/loaded-libraries/", params=params)
        if error:
            return error

        if not libraries:
            return "No loaded libraries found"

        result = (
            found_line(libraries, "loaded libraries", paginated=True, offset=offset)
            + "\n\n"
        )
        result += "|URN|Name|Version|Provider|\n"
        result += "|---|---|---|---|\n"

        for lib in libraries:
            urn = lib.get("urn", "N/A")
            name = lib.get("name", "N/A")
            version = lib.get("version", "N/A")
            provider = lib.get("provider", "N/A")

            result += f"|{urn}|{name}|{version}|{provider}|\n"

        return result
    except Exception as e:
        return f"Error in get_loaded_libraries: {str(e)}"


async def import_stored_library(urn_or_id: str) -> str:
    """Import library (framework) to make it available for compliance assessments. Use get_stored_libraries() to find URNs

    Args:
        urn_or_id: Library URN/ID (e.g. "urn:intuitem:risk:library:nist-csf-2.0")
    """
    try:
        res = make_post_request(f"/stored-libraries/{urn_or_id}/import/", {})

        if res.status_code == 200:
            result = res.json()
            if result.get("status") == "success":
                return f"Imported library: {urn_or_id}"
            else:
                error = result.get("error", "Unknown error")
                return f"Error importing library: {error}"
        else:
            return f"Error importing library: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in import_stored_library: {str(e)}"


async def find_requirements(
    framework: str = None, ref_id: str = None, search: str = None
):
    """Find requirements of the framework library (loaded or not) by reference and/or text.

    Use this to answer "what is A.5.1 in ISO 27001?" (framework + ref_id) or
    "which requirement covers X?" (framework + search). Returns each match's urn,
    usable with get_requirement_mappings().

    Args:
        framework: Framework name or reference, loosely matched, e.g. "ISO 27001:2022", "NIST CSF 2.0"
        ref_id: Exact requirement reference, e.g. "A.5.1", "GV.OC-01"
        search: Words that must all appear in the requirement reference, name or description
    """
    try:
        if not (ref_id or search):
            return error_response(
                "Missing argument",
                "Give ref_id or search.",
                "Retry with ref_id or search.",
                retry_allowed=True,
            )
        res = make_get_request(
            "/library-knowledge/requirements/",
            params={"framework": framework, "ref_id": ref_id, "search": search},
        )
        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)
        data = res.json()
        if data.get("unknown_framework"):
            return error_response(
                "Framework not found",
                f"No framework matches '{framework}'.",
                f"Retry with one of: {', '.join(data['frameworks'])}",
                retry_allowed=True,
            )
        rows = data["requirements"]
        if not rows:
            return empty_response(
                "requirements",
                {"framework": framework, "ref_id": ref_id, "search": search},
            )
        out = (
            (data["note"] + "\n\n" if data.get("note") else "")
            + found_line(rows, "requirements")
            + "\n\n|urn|framework|ref_id|name|description|\n|---|---|---|---|---|\n"
        )
        for r in rows:
            desc = (
                (r.get("description") or "").replace("\n", " ").replace("|", "/")[:300]
            )
            out += f"|{r['urn']}|{r.get('framework_ref_id') or r.get('framework')}|{r.get('ref_id') or ''}|{r.get('name') or ''}|{desc}|\n"
        return success_response(
            out,
            "find_requirements",
            "Use get_requirement_mappings(source_framework=<framework>, ref_id=<ref_id>) for requirements it maps to in other frameworks.",
        )
    except Exception as e:
        return error_response("Internal Error", str(e), "Report this error to the user")


async def get_requirement_mappings(
    source_framework: str = None,
    ref_id: str = None,
    framework: str = None,
    requirement: str = None,
):
    """List requirements of other frameworks that one requirement maps to, from the library mappings.

    For "which X requirements map to Y A.5.1?": source_framework="Y", ref_id="A.5.1",
    framework="X". A requirement can map to dozens of others; `framework` keeps only
    the ones in the framework you are asked about.

    Args:
        source_framework: Framework of the requirement, loosely matched, e.g. "ISO 27001:2022"
        ref_id: The requirement's reference in that framework, e.g. "A.5.1", "GV.SC-10"
        framework: Target framework name or reference, loosely matched, e.g. "NIST CSF 2.0"
        requirement: Alternatively, the requirement's urn from find_requirements()
    """
    try:
        if not (ref_id or requirement):
            return error_response(
                "Missing argument",
                "Give source_framework and ref_id (or a requirement urn).",
                "Retry with source_framework and ref_id.",
                retry_allowed=True,
            )
        res = make_get_request(
            "/library-knowledge/mappings/",
            params={
                "source_framework": source_framework,
                "ref_id": ref_id,
                "requirement": requirement,
                "framework": framework,
            },
        )
        if res.status_code == 404:
            return error_response(
                "Requirement not found",
                f"No requirement '{ref_id or requirement}' in '{source_framework or 'any framework'}'.",
                "Check the framework and reference with find_requirements().",
                retry_allowed=True,
            )
        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)
        data = res.json()
        if data.get("ambiguous"):
            return error_response(
                "Several requirements match",
                f"'{ref_id}' exists in: "
                + ", ".join(
                    str(r.get("framework_ref_id") or r["framework"])
                    for r in data["ambiguous"]
                ),
                "Retry with the framework the user means as source_framework.",
                retry_allowed=True,
            )
        rows = data["mappings"]
        if data.get("elsewhere"):
            return error_response(
                "No mappings in that framework",
                f"This requirement maps to nothing in '{framework}'. It maps to: "
                + ", ".join(f"{fw} ({n})" for fw, n in data["elsewhere"].items()),
                "If the framework the user asked about is listed, retry with its name as framework; if not, answer that there is no mapping.",
                retry_allowed=True,
            )
        if not rows:
            return empty_response(
                "requirement mappings",
                {
                    "source_framework": source_framework,
                    "ref_id": ref_id,
                    "requirement": requirement,
                    "framework": framework,
                },
            )
        counts = {}
        for r in rows:
            counts[r["framework"]] = counts.get(r["framework"], 0) + 1
        out = (
            (data["note"] + "\n\n" if data.get("note") else "")
            + found_line(rows, "mapped requirements")
            + " in "
            + ", ".join(f"{fw} ({n})" for fw, n in counts.items())
            + "\n\n|framework|ref_id|name|relationship|\n|---|---|---|---|\n"
        )
        for r in rows:
            out += f"|{r['framework']}|{r.get('ref_id') or ''}|{r.get('name') or ''}|{r.get('relationship') or ''}|\n"
        return success_response(
            out,
            "get_requirement_mappings",
            "Report every mapped requirement listed for the framework asked about, not a sample.",
        )
    except Exception as e:
        return error_response("Internal Error", str(e), "Report this error to the user")
