"""Aggregate (count / breakdown) MCP tools.

Aggregate questions must never be answered by counting rows in a list response:
list responses are bounded for context, so row-counting silently under-reports.
These tools ask the API for exact counts instead and return no rows at all, so
the answer is both correct and cheap regardless of register size.
"""

import re

from ..client import make_get_request
from ..utils.response_formatter import (
    success_response,
    error_response,
    http_error_response,
)

from .generic_tools import OBJECTS as COUNTABLE

MAX_GROUPS = 25

# Django field names: no separators, no traversal.
FIELD_NAME = re.compile(r"[a-z][a-z0-9_]*")


def _count(endpoint, params):
    """Exact server-side count; fetches one row, never the register."""
    p = dict(params or {})
    p["limit"] = 1
    res = make_get_request(f"/{endpoint}/", params=p)
    if res.status_code != 200:
        return None, res
    return res.json().get("count"), res


async def count_objects(
    object_type: str,
    group_by: str = None,
    folder: str = None,
    filters: dict = None,
):
    """Count, total or tally objects exactly. Returns numbers only, never rows.

    Use this whenever the answer is a NUMBER rather than a list of things:
    "how many", "count", "total", "how much", "what proportion", "what
    percentage", "share of", "distribution of", "breakdown by", "split by".

    Do NOT answer those questions from the list tools (get_assets,
    get_vulnerabilities, ...): their responses are capped for size, so counting
    their rows under-reports the true number.

    To count inside a domain, pass folder="<domain name>" here. This is the tool
    for "how many X are in domain Y" -- get_folders lists domains, it does not
    count the things inside one.

    Args:
        object_type: One of the supported types, e.g. risk_scenarios, applied_controls, vulnerabilities, incidents, assets
        group_by: Field to break the count down by, e.g. status, treatment, severity, priority. Use for "distribution"/"breakdown" questions.
        folder: Domain/folder name or ID to scope the count to
        filters: Extra query filters as a mapping, e.g. {"status": "to_do"}
    """
    try:
        endpoint = COUNTABLE.get(object_type)
        if not endpoint:
            return error_response(
                "Unknown object type",
                f"'{object_type}' is not countable.",
                "Choose one of: " + ", ".join(sorted(COUNTABLE)),
                retry_allowed=True,
            )

        params = dict(filters or {})
        if folder:
            from ..resolvers import resolve_folder_id

            params["folder"] = resolve_folder_id(folder)

        total, res = _count(endpoint, params)
        if total is None:
            return http_error_response(res.status_code, res.text)

        # django-filter silently DROPS unrecognised query params, so a mistyped
        # filter name returns the unfiltered total -- a confidently wrong number.
        # Values are validated server-side; keys are not. Compare against the
        # unfiltered baseline and say so rather than let it pass as a real count.
        caveat = ""
        if params:
            baseline, _ = _count(endpoint, None)
            if baseline is not None and baseline == total:
                caveat = (
                    f"\n\nWARNING: this filter matched every {object_type} "
                    f"({total} of {total}). Either it genuinely excludes nothing, or a "
                    f"filter name was not recognised — unknown filter names are ignored "
                    f"silently rather than rejected. Verify the field names before "
                    f"reporting this as a filtered count.\n"
                )

        scope = []
        if folder:
            scope.append(f"folder={folder}")
        scope += [f"{k}={v}" for k, v in (filters or {}).items()]
        scope_str = f" ({', '.join(scope)})" if scope else ""

        if not group_by:
            return success_response(
                f"{object_type}{scope_str}: **{total}**{caveat}",
                "count_objects",
                "This is an exact count from the server, not a row count.",
            )

        # group_by is caller-controlled and lands in a URL path. A value with "/"
        # or ".." would re-point the request at a different API path (relative-path
        # injection inside API_URL, not SSRF). A field-name charset check removes
        # that without maintaining a per-type whitelist.
        if not FIELD_NAME.fullmatch(group_by):
            return error_response(
                "Invalid group_by field",
                f"'{group_by}' is not a valid field name.",
                "Use a plain field name such as status, treatment, severity or priority.",
                retry_allowed=True,
            )

        choices_res = make_get_request(f"/{endpoint}/{group_by}/")
        if choices_res.status_code != 200:
            return error_response(
                "Unknown group_by field",
                f"'{group_by}' is not a groupable field on {object_type}.",
                "Call count_objects without group_by, or try status/treatment/severity.",
                retry_allowed=True,
            )
        choices = choices_res.json()
        if not isinstance(choices, dict) or not choices:
            return error_response(
                "Unsupported group_by field",
                f"'{group_by}' returned no choices.",
                "Call count_objects without group_by.",
                retry_allowed=True,
            )
        if len(choices) > MAX_GROUPS:
            return error_response(
                "Too many groups",
                f"'{group_by}' has {len(choices)} values (limit {MAX_GROUPS}).",
                "Pick a field with fewer distinct values, or filter first.",
                retry_allowed=True,
            )

        rows, accounted = [], 0
        for value, label in choices.items():
            n, _ = _count(endpoint, {**params, group_by: value})
            if n is None:
                continue
            accounted += n
            pct = f"{n * 100 // total}%" if total else "-"
            rows.append(f"|{label}|{n}|{pct}|")

        out = f"{object_type} by {group_by}{scope_str} — total **{total}**\n\n"
        out += f"|{group_by}|count|share|\n|---|---|---|\n" + "\n".join(rows) + "\n"
        if accounted != total:
            # Self-check: choice filters need not partition the set (nulls,
            # multi-valued fields). Say so rather than let the model assume.
            out += (
                f"\nNote: the breakdown accounts for {accounted} of {total}; "
                f"{total - accounted} are not covered by these values.\n"
            )
        return success_response(
            out + caveat,
            "count_objects",
            "These are exact server-side counts, not row counts.",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )
