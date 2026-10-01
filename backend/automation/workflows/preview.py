"""Editor-side evaluation of a compute row, so an author sees `= 16 (int)` or
the run-time error while typing instead of after publishing.

Evaluates against a reference run of the same workflow when there is one
(its variables and node outputs), otherwise against the draft's variable
defaults. Pure: nothing is written, and the same evaluator the engine uses is
what answers, so what the preview shows is what the run will compute.
"""

from __future__ import annotations

from .context import temporal_seeds
from .expressions import ExpressionError, evaluate

MAX_EXPRESSION_LENGTH = 2000
MAX_ROWS_ABOVE = 50


class PreviewRequestError(ValueError):
    """The request is malformed (not an evaluation failure): reported as 400
    with `code`, a stable identifier the frontend can translate. Only the
    code leaves the server."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def type_name(value):
    """The CEL-facing type of a JSON-shaped result. int vs double is the one
    an author has to care about, hence naming both."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "map"
    return type(value).__name__


def preview_context(version, instance=None):
    """What a compute row can read: a reference run's variables and node
    outputs, or the draft's defaults with the engine seeds and no outputs."""
    if instance is not None:
        return {**instance.variables, "nodes": instance.node_outputs}
    context = {v.key: v.default_value for v in version.variables.all()}
    context.update(temporal_seeds())
    context["payload"] = {}
    context["nodes"] = {}
    return context


def _rows(raw):
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_ROWS_ABOVE:
        raise PreviewRequestError("previewRowsInvalid")
    rows = []
    for row in raw:
        if not isinstance(row, dict):
            raise PreviewRequestError("previewRowsInvalid")
        key = str(row.get("key") or "")
        expression = row.get("expression") or ""
        if not isinstance(expression, str) or len(expression) > MAX_EXPRESSION_LENGTH:
            raise PreviewRequestError("previewExpressionTooLong")
        rows.append((key, expression))
    return rows


def preview_compute_row(version, expression, rows_above=None, instance=None):
    """Evaluate `expression` after the rows above it, the way the compute
    action would. Returns {"ok": True, "value", "type"} or {"ok": False,
    "error"}; a row above that fails is reported as this row's error, since
    this row cannot run without it."""
    if not isinstance(expression, str) or len(expression) > MAX_EXPRESSION_LENGTH:
        raise PreviewRequestError("previewExpressionTooLong")
    context = preview_context(version, instance)
    results = {}
    for key, above in _rows(rows_above):
        if not key or not above.strip():
            continue
        try:
            results[key] = evaluate(above, {**context, **results})
        except ExpressionError as e:
            return {"ok": False, "error": f"'{key}' (a row above) failed: {e}"}
    try:
        value = evaluate(expression, {**context, **results})
    except ExpressionError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "value": value, "type": type_name(value)}
