"""Library management MCP tools for CISO Assistant"""

from ..client import make_get_request, make_post_request, fetch_all_results


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
        params = {}
        if object_type:
            params["object_type"] = object_type
        if provider:
            params["provider"] = provider

        # Fetch all stored libraries (with pagination)
        libraries, error = fetch_all_results("/stored-libraries/", params=params)
        if error:
            return error

        if not libraries:
            return "No stored libraries found"

        result = f"Found {len(libraries)} stored libraries\n\n"
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


async def get_loaded_libraries():
    """Get loaded/imported libraries (frameworks) in CISO Assistant

    Returns a list of libraries that have already been imported and are available for use.
    These are frameworks/libraries that have been activated in the system.
    """
    try:
        # Fetch all loaded libraries (with pagination)
        libraries, error = fetch_all_results("/loaded-libraries/")
        if error:
            return error

        if not libraries:
            return "No loaded libraries found"

        result = f"Found {len(libraries)} loaded libraries\n\n"
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
    """Import a stored library (framework) into CISO Assistant

    Args:
        urn_or_id: URN or ID of the stored library to import (e.g., "urn:intuitem:risk:library:nist-csf-2.0")

    This makes the library available for use (e.g., creating compliance assessments with the framework).
    Use get_stored_libraries() to see available libraries.
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
