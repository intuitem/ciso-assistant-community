"""Library management MCP tools for CISO Assistant"""

from ..client import make_post_request, fetch_all_results, found_line


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
        object_type: Object type (e.g. "framework", "risk_matrix")
        provider: Provider name
        search: Free-text match on name, description, URN or ref_id
        offset: Row to start from, for paging past the first response
    """
    try:
        params = {}
        if object_type:
            params["object_type"] = object_type
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

        # A truncated catalogue is not a cosmetic loss here: the URN is the key
        # import_stored_library needs, so a library that never gets listed
        # cannot be imported at all.
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
