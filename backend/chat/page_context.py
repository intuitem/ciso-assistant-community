"""
Parse frontend page context (URL path) into a structured parent reference.
Used to make chat tools context-aware — e.g., auto-scoping queries to the
current risk assessment, or auto-filling parent FK when creating child objects.
"""

import re
from dataclasses import dataclass

# UUID pattern (v4 format)
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


@dataclass
class ParsedContext:
    """Structured representation of the user's current page."""

    model_key: str  # e.g., "risk_assessment"
    object_id: str | None  # UUID string, or None for list pages
    page_type: str  # "list" | "detail" | "edit"


def parse_page_context(page_context: dict) -> ParsedContext | None:
    """
    Parse a page_context dict from the frontend into a structured ParsedContext.

    Handles URL patterns like:
        /risk-assessments               → list page
        /risk-assessments/{uuid}        → detail page
        /requirement-assessments/{uuid}/edit  → edit page
        /compliance-assessments/{uuid}  → detail page
    """
    path = page_context.get("path", "")
    if not path:
        return None

    # Build reverse map: url_slug → model_key (lazy import to avoid circular)
    from .tools import MODEL_MAP

    slug_to_key = {}
    for model_key, (_, _, _, url_slug) in MODEL_MAP.items():
        slug_to_key[url_slug] = model_key

    # Strip leading/trailing slashes and split
    segments = [s for s in path.strip("/").split("/") if s]
    if not segments:
        return None

    # Find the model slug — it's the first segment that matches a known url_slug
    model_slug = segments[0]
    if model_slug not in slug_to_key:
        return None

    model_key = slug_to_key[model_slug]

    # Check for object ID (UUID) in second segment
    object_id = None
    page_type = "list"

    if len(segments) >= 2 and _UUID_RE.match(segments[1]):
        object_id = segments[1]
        page_type = "detail"

        # Check for /edit suffix
        if len(segments) >= 3 and segments[2] == "edit":
            page_type = "edit"

    return ParsedContext(
        model_key=model_key,
        object_id=object_id,
        page_type=page_type,
    )
