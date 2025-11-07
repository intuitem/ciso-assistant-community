"""Response formatting utilities for better LLM tool calling

These utilities help open-source models avoid infinite loops and retry issues
by providing clear completion signals and next-step guidance.
"""

from typing import Optional, Dict, Any


def success_response(
    data: str, tool_name: str, next_action: Optional[str] = None
) -> str:
    """Format successful tool response with completion signals

    Args:
        data: The actual data/result to return
        tool_name: Name of the tool that was called
        next_action: Optional hint for what to do next

    Returns:
        Formatted response string with success markers
    """
    response = f"{data}\n\n"
    response += f"[SUCCESS] {tool_name} completed.\n"

    if next_action:
        response += f"NEXT: {next_action}\n"
    else:
        response += "NEXT: Use this data to answer the user's question.\n"

    response += "WARNING: Do not call this tool again with identical parameters.\n"

    return response


def error_response(
    error_type: str, message: str, next_action: str, retry_allowed: bool = False
) -> str:
    """Format error response with clear guidance

    Args:
        error_type: Type of error (e.g., "Not Found", "Authentication Failed")
        message: Detailed error message
        next_action: What the LLM should do next
        retry_allowed: Whether retrying with different params makes sense

    Returns:
        Formatted error response string
    """
    response = f"[ERROR] {error_type}\n"
    response += f"Details: {message}\n\n"
    response += "[COMPLETED] Tool execution finished.\n"
    response += f"NEXT: {next_action}\n"

    if not retry_allowed:
        response += "WARNING: Do NOT retry - this request will fail again.\n"
    else:
        response += "HINT: You may retry with different parameters.\n"

    return response


def empty_response(resource_type: str, filters: Optional[Dict[str, Any]] = None) -> str:
    """Format response when no data found

    Args:
        resource_type: Type of resource searched (e.g., "risk scenarios")
        filters: Filters that were applied to the search

    Returns:
        Formatted empty result response
    """
    response = f"[RESULT] No {resource_type} found.\n"

    if filters:
        filter_str = ", ".join(f"{k}={v}" for k, v in filters.items() if v)
        if filter_str:
            response += f"Filters applied: {filter_str}\n"

    response += f"\n[SUCCESS] Search completed (0 results).\n"
    response += "This is a valid result, not an error.\n"
    response += "NEXT STEPS:\n"
    response += "- Try different search filters, OR\n"
    response += "- Inform the user no matching items exist, OR\n"
    response += "- Suggest creating new items if appropriate.\n"
    response += f"WARNING: Do not retry the same search for {resource_type}.\n"

    return response


def http_error_response(status_code: int, error_text: str) -> str:
    """Format HTTP error responses with actionable guidance

    Args:
        status_code: HTTP status code
        error_text: Error response text from server

    Returns:
        Formatted error response with next steps
    """
    if status_code == 401:
        return error_response(
            "Authentication Failed",
            "API token is invalid or expired",
            "Inform the user to check their CISO Assistant API token configuration",
            retry_allowed=False,
        )
    elif status_code == 403:
        return error_response(
            "Permission Denied",
            "User does not have permission to access this resource",
            "Inform the user they lack permissions for this operation",
            retry_allowed=False,
        )
    elif status_code == 404:
        return error_response(
            "Not Found",
            "The specified resource does not exist",
            "Verify the resource name/ID or try listing available resources first",
            retry_allowed=True,
        )
    elif status_code >= 500:
        return error_response(
            "Server Error",
            f"CISO Assistant server error: {error_text}",
            "Inform the user that the server is experiencing issues",
            retry_allowed=False,
        )
    else:
        return error_response(
            f"HTTP {status_code}",
            error_text,
            "Report this error to the user",
            retry_allowed=False,
        )
