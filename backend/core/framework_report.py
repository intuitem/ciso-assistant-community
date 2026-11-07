"""Scores of the framework report (Framework Insights).

Each audit is scored as on its own page, by get_scores_for (its calculation
method, N/A anchoring and weights), so a report over a single audit shows that
audit's numbers. The page averages them across audits.
"""

from collections import defaultdict
from copy import copy

from core.audit_inheritance import _ca_scale
from core.utils import is_field_visible_to

LAYERS = ("implementation_score", "documentation_score", "maturity_score")

# Where the page puts requirements whose parent is not a section node.
TOP_SECTION = "__top__"

# Set on an inherited reading whose source audit is on another scale.
OTHER_SCALE = "_inherited_from_other_scale"


def visible_layers(ca, role: str) -> frozenset[str]:
    """Score layers the viewer may read on the audit: a layer shows only when
    every field it is computed from does."""

    def visible(field):
        return is_field_visible_to(ca, field, role)

    # Compliance may stay hidden: whether a requirement is N/A is part of what
    # its score means (the applicability toggle sets it in score-only audits).
    if not (visible("score") and visible("is_scored")):
        return frozenset()
    if ca.show_documentation_score and not visible("documentation_score"):
        # The maturity score would give the documentation score away.
        return frozenset({"implementation_score"})
    return frozenset(LAYERS)


def _layers(ca, scores: dict, visible, *, inherited: bool, other_scale: bool) -> dict:
    if other_scale:
        # Scores on different scales are never combined.
        visible = frozenset()
    elif inherited and ca.show_documentation_score:
        # Inheritance carries no documentation score, so neither the
        # documentation nor the maturity score of an inherited answer exists.
        visible = visible & {"implementation_score"}
    return {layer: scores[layer] if layer in visible else None for layer in LAYERS}


def requirement_scores(ca, ra, visible, *, inherited: bool) -> dict:
    """A requirement's scores as its audit counts them, on its own scale."""
    requirement = ra.requirement
    return _layers(
        ca,
        ca.requirement_layer_scores(
            result=ra.result,
            is_scored=ra.is_scored,
            score=ra.score,
            documentation_score=ra.documentation_score,
            min_score=requirement.min_score,
            max_score=requirement.max_score,
        ),
        visible,
        inherited=inherited,
        other_scale=getattr(ra, OTHER_SCALE, False),
    )


def inherited_requirement(ca, ra, overlay):
    """The requirement assessment as the combined view reads it: the compliance
    and implementation score inherited from the winning audit in place of its
    own, or None when it inherits nothing. ``overlay`` is the row's redacted
    inheritance block. The score is the winning audit's as recorded; when that
    audit is on another scale, it is marked (OTHER_SCALE) and never combined."""
    if not overlay or not overlay.get("inherited"):
        return None
    source = overlay.get("source") or {}
    source_scale = source.get("scale") or {}
    effective = copy(ra)
    effective.result = overlay.get("effective_result")
    # effective_score is None when the source has no score or the viewer may
    # not read it; raw_score is the same value before any rescaling.
    effective.score = (
        source.get("raw_score") if overlay.get("effective_score") is not None else None
    )
    effective.is_scored = effective.score is not None
    effective.documentation_score = None
    setattr(
        effective,
        OTHER_SCALE,
        (source_scale.get("min"), source_scale.get("max")) != _ca_scale(ca),
    )
    return effective


def audit_scores(ca, ras, *, section_of, visible, inherited_ids) -> dict:
    """The audit's scores over its in-scope requirement assessments, in total
    and per report section. ``inherited_ids`` are the ids of the assessments
    replaced by their inherited reading (combined view)."""

    def scores(group):
        return _layers(
            ca,
            ca.get_scores_for(group),
            visible,
            inherited=any(ra.id in inherited_ids for ra in group),
            other_scale=any(getattr(ra, OTHER_SCALE, False) for ra in group),
        )

    by_section = defaultdict(list)
    for ra in ras:
        by_section[section_of(ra)].append(ra)
    return {
        "total": scores(ras),
        "sections": {key: scores(group) for key, group in by_section.items()},
    }
