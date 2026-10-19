"""Score aggregation for quick forms.

Pure functions shared by the live evaluator (`evaluate_quick_form`) and the
builder preview (`evaluate_quick_form_document`), so the two cannot drift.

Each scorable question is an item `{score, max_score, weight, answered, lo, hi}`;
`score` and `max_score` already carry the question weight, `lo` and `hi` are its
unweighted reachable range. Results are floats:
CEL compares a double against an int literal (`score > 17`) but not an int
against a double literal (`3 > 2.5`), so averages and sums share one type.
"""

from core.utils import project_weighted_sum

PAGE_AGGREGATIONS = ("sum", "max", "mean")
FORM_AGGREGATIONS = ("sum", "mean", "pages_sum", "pages_mean")


def normalize_page_aggregation(value) -> str:
    return value if value in PAGE_AGGREGATIONS else "sum"


def normalize_form_aggregation(value) -> str:
    return value if value in FORM_AGGREGATIONS else "sum"


def project_sum(total, items: list[dict]):
    """A weighted SUM over `items` projected onto their unweighted scale.

    A question weight means the same thing here as in an audit: the range spans
    every scorable question, a skipped optional one counting as 0. Every sum the
    context exposes goes through it, so `score`, `score_sum` and `score_max` stay
    comparable. Unweighted, the total comes back as is, type included.
    """
    weighted_lo = sum(i["lo"] * i["weight"] for i in items)
    weighted_hi = sum(i["hi"] * i["weight"] for i in items)
    lo = sum(i["lo"] for i in items)
    hi = sum(i["hi"] for i in items)
    if (weighted_lo, weighted_hi) == (lo, hi):
        return total
    return project_weighted_sum(total, weighted_lo, weighted_hi, lo, hi)


def aggregate_page(items: list[dict], aggregation: str) -> dict | None:
    """Score of one visible page from its visible scorable questions; None
    when it has none, so it stays out of a page mean."""
    if not items:
        return None
    answered = [i for i in items if i["answered"]]
    aggregation = normalize_page_aggregation(aggregation)
    if aggregation == "max":
        score = max((i["score"] for i in answered), default=0)
        score_max = max(i["max_score"] for i in items)
    elif aggregation == "mean":
        answered_weight = sum(i["weight"] for i in answered)
        score = (
            sum(i["score"] for i in answered) / answered_weight
            if answered_weight
            else 0
        )
        score_max = sum(i["max_score"] for i in items) / (
            sum(i["weight"] for i in items) or 1
        )
    else:
        score = project_sum(sum(i["score"] for i in answered), items)
        score_max = project_sum(sum(i["max_score"] for i in items), items)
    return {"score": float(score), "score_max": float(score_max)}


def aggregate_form(
    items: list[dict], page_results: list[dict], aggregation: str
) -> float | None:
    """Raw form score. Question modes need at least one answered scorable
    question; page modes need at least one scored page."""
    aggregation = normalize_form_aggregation(aggregation)
    if aggregation in ("pages_sum", "pages_mean"):
        if not page_results:
            return None
        total = sum(p["score"] for p in page_results)
        if aggregation == "pages_mean":
            total /= len(page_results)
        return float(total)
    answered = [i for i in items if i["answered"]]
    if not answered:
        return None
    total = sum(i["score"] for i in answered)
    if aggregation == "mean":
        total /= sum(i["weight"] for i in answered) or 1
    else:
        total = project_sum(total, items)
    return float(total)


def clamp(score: float | None, bounds: tuple[int, int]) -> float | None:
    if score is None:
        return None
    lo, hi = bounds
    return float(max(lo, min(hi, score)))


def score_bounds(scores_definition) -> tuple[int, int]:
    definition = scores_definition or {}
    try:
        lo, hi = int(definition.get("min", 0)), int(definition.get("max", 100))
    except TypeError, ValueError:
        return 0, 100
    return (lo, hi) if lo < hi else (0, 100)
