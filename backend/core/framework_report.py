"""Scores of the framework report (Framework Insights).

Each audit is scored as on its own page, by get_scores_for (its calculation
method, N/A anchoring and weights), so a report over a single audit shows that
audit's numbers. The page averages them across audits.
"""

from collections import defaultdict
from copy import copy

from core.audit_inheritance import _ca_scale, normalize_score
from core.utils import is_field_visible_to

LAYERS = ("implementation_score", "documentation_score", "maturity_score")

# Where the page puts requirements whose parent is not a section node.
TOP_SECTION = "__top__"


def visible_layers(ca, role: str) -> frozenset[str]:
    """Score layers the viewer may read on the audit: a layer shows only when
    every field it is computed from does."""

    def visible(field):
        return is_field_visible_to(ca, field, role)

    if not (visible("score") and visible("is_scored")):
        return frozenset()
    if ca.anchor_na_to_target and not visible("result"):
        # An N/A requirement counts at the target: its scores would tell.
        return frozenset()
    if ca.show_documentation_score and not visible("documentation_score"):
        # The maturity score would give the documentation score away.
        return frozenset({"implementation_score"})
    return frozenset(LAYERS)


def _layers(ca, scores: dict, visible, *, inherited: bool) -> dict:
    if inherited and ca.show_documentation_score:
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
    )


def inherited_requirement(ca, ra, overlay):
    """The requirement assessment as the combined view reads it: the compliance
    and implementation score inherited from the winning audit in place of its
    own, or None when it inherits nothing. ``overlay`` is the row's redacted
    inheritance block; its score is on the overlay's scale, brought back to the
    audit's."""
    if not overlay or not overlay.get("inherited"):
        return None
    scale = overlay.get("scale") or {}
    effective = copy(ra)
    effective.result = overlay.get("effective_result")
    effective.score = normalize_score(
        overlay.get("effective_score"),
        (scale.get("min"), scale.get("max")),
        _ca_scale(ca),
    )
    effective.is_scored = effective.score is not None
    effective.documentation_score = None
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
        )

    by_section = defaultdict(list)
    for ra in ras:
        by_section[section_of(ra)].append(ra)
    return {
        "total": scores(ras),
        "sections": {key: scores(group) for key, group in by_section.items()},
    }
