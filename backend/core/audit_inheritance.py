"""Audit result inheritance across the domain (Folder) tree.

When the same framework is audited at several levels of a domain hierarchy
(e.g. org-wide domain A -> business unit B -> system C), a child audit can
inherit results and scores for requirements covered by an ancestor audit.

Inheritance is always a non-destructive *overlay*: the child's stored
``RequirementAssessment.result`` / ``score`` are never modified. The resolver
computes an "effective" result/score plus the full inheritance path so the UI
can show where each value came from, with clickable links back to the source
audit.

The combination strategy is an org-wide setting
(``GlobalSettings.general -> audit_tree_aggregation_strategy``):

- ``none``        : no inheritance (feature off, the default)
- ``parent_wins`` : nearest ancestor with a value overrides the child
- ``child_wins``  : the child's own value wins; ancestors only fill gaps
- ``best_case``   : strongest result across the chain (optimistic)
- ``worst_case``  : weakest result across the chain (prudent)

Source selection per ancestor domain: among same-framework audits in that
folder, only "live" ones (in_progress / in_review / done) are eligible, and the
most recently updated one wins. ``RequirementAssessment.save()`` bumps the
parent CA's ``updated_at`` (see ``trigger_compliance_assessment_update_hooks``),
so ``updated_at`` reliably tracks last activity on an audit.

When audits use different score scales, every score is normalized to the
top-most participating ancestor's scale ("the top level parent scale").
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

# Statuses considered "live" for cross-audit rollups. Mirrors the filter used by
# FrameworkViewSet.report so the two stay consistent.
LIVE_STATUSES = ("in_progress", "in_review", "done")


class AuditTreeAggregationStrategy(TextChoices):
    NONE = "none", _("No inheritance")
    PARENT_WINS = "parent_wins", _("Parent always wins")
    CHILD_WINS = "child_wins", _("Child always wins")
    BEST_CASE = "best_case", _("Best case (optimistic)")
    WORST_CASE = "worst_case", _("Worst case (prudent)")


# Ordered compliance strength, used by best_case / worst_case. Results outside
# this map (not_assessed, not_applicable) carry no comparable strength and are
# handled explicitly below.
RESULT_STRENGTH = {
    "non_compliant": 0,
    "partially_compliant": 1,
    "compliant": 2,
}

NOT_ASSESSED = "not_assessed"
NOT_APPLICABLE = "not_applicable"


def get_strategy() -> str:
    """Return the org-wide aggregation strategy, defaulting to ``none``.

    Gated by the ``audit_tree_inheritance`` feature flag: when the flag is off
    (the default), this returns ``none`` regardless of the configured strategy,
    so every inheritance surface — analytics panels, report toggle — disappears
    while the backend logic stays intact behind the flag.
    """
    from global_settings.models import GlobalSettings

    try:
        flags = GlobalSettings.objects.get(
            name=GlobalSettings.Names.FEATURE_FLAGS
        ).value
    except GlobalSettings.DoesNotExist:
        flags = {}
    if not (flags or {}).get("audit_tree_inheritance", False):
        return AuditTreeAggregationStrategy.NONE

    try:
        gs = GlobalSettings.objects.get(name=GlobalSettings.Names.GENERAL)
    except GlobalSettings.DoesNotExist:
        return AuditTreeAggregationStrategy.NONE
    strategy = (gs.value or {}).get(
        "audit_tree_aggregation_strategy", AuditTreeAggregationStrategy.NONE
    )
    # Normalize: a typo or legacy value must disable inheritance, never silently
    # fall through to the pessimistic worst_case branch in _pick_result.
    if strategy not in AuditTreeAggregationStrategy.values:
        return AuditTreeAggregationStrategy.NONE
    return strategy


def _ca_scale(ca) -> tuple[Optional[int], Optional[int]]:
    """Effective score scale of a compliance assessment (CA override, else framework)."""
    mn = ca.min_score if ca.min_score is not None else ca.framework.min_score
    mx = ca.max_score if ca.max_score is not None else ca.framework.max_score
    return (mn, mx)


def normalize_score(
    score: Optional[int],
    src_scale: tuple[Optional[int], Optional[int]],
    dst_scale: tuple[Optional[int], Optional[int]],
) -> Optional[int]:
    """Linearly rebase ``score`` from ``src_scale`` onto ``dst_scale``.

    Returns the score unchanged when scales match or any bound is unknown.
    Lossy by nature (rounding); only used for display overlays.
    """
    if score is None:
        return None
    smin, smax = src_scale
    dmin, dmax = dst_scale
    if None in (smin, smax, dmin, dmax) or smax == smin:
        return score
    if (smin, smax) == (dmin, dmax):
        return score
    frac = (score - smin) / (smax - smin)
    return round(dmin + frac * (dmax - dmin))


@dataclass(frozen=True)
class ChainEntry:
    """One audit's take on a single requirement, positioned in the domain chain."""

    ca_id: str
    ca_name: str
    folder_id: Optional[str]
    folder_name: Optional[str]
    distance: int  # 0 = the target audit itself, 1 = parent, 2 = grandparent, ...
    result: Optional[str]
    score: Optional[int]
    is_scored: bool
    scale: tuple[Optional[int], Optional[int]]

    def has_result(self) -> bool:
        """A real result verdict — `not_assessed` carries no opinion."""
        return self.result not in (None, NOT_ASSESSED)

    def has_score(self) -> bool:
        """An actual score — an unscored requirement carries no opinion."""
        return self.is_scored and self.score is not None


@dataclass
class AncestorAudit:
    ca: object  # ComplianceAssessment
    distance: int

    def as_meta(self) -> dict:
        folder = self.ca.folder
        return {
            "ca_id": str(self.ca.id),
            "ca_name": self.ca.name,
            "folder_id": str(folder.id) if folder else None,
            "folder_name": folder.name if folder else None,
            "distance": self.distance,
            "scale": {"min": _ca_scale(self.ca)[0], "max": _ca_scale(self.ca)[1]},
        }


def select_ancestor_audits(
    target_ca, *, viewable_ca_ids: Optional[Iterable] = None
) -> list[AncestorAudit]:
    """Nearest-first list of inheritable ancestor audits on the same framework.

    Exactly one audit per ancestor domain: live status, most recently updated.
    The Global root folder participates too — an org-wide audit placed there is a
    legitimate inheritance source (common capabilities flowing down to every
    domain).
    """
    from core.models import ComplianceAssessment

    folder = target_ca.folder
    if folder is None:
        return []

    result: list[AncestorAudit] = []
    viewable = set(viewable_ca_ids) if viewable_ca_ids is not None else None
    distance = 0
    for ancestor in folder.get_parent_folders():  # nearest-first
        distance += 1
        qs = ComplianceAssessment.objects.filter(
            folder=ancestor,
            framework_id=target_ca.framework_id,
            status__in=LIVE_STATUSES,
        ).select_related("folder", "framework")
        if viewable is not None:
            qs = qs.filter(id__in=viewable)
        ca = qs.order_by("-updated_at").first()
        if ca is not None:
            result.append(AncestorAudit(ca=ca, distance=distance))
    return result


def _pick_nearest(strategy: str, own, ancestors):
    """Shared nearest/parent/child selection over a pre-filtered candidate set.

    ``own`` is the target's qualifying entry (distance 0) or None; ``ancestors``
    are qualifying ancestor entries, nearest-first. Used by both result and
    score resolution after each has excluded entries lacking that dimension.
    """
    if strategy == AuditTreeAggregationStrategy.CHILD_WINS:
        return own or (ancestors[0] if ancestors else None)
    if strategy == AuditTreeAggregationStrategy.PARENT_WINS:
        return ancestors[0] if ancestors else own
    return None  # best/worst handled by the dimension-specific picker


def _pick_result(strategy: str, own: Optional[ChainEntry], chain: list[ChainEntry]):
    """Winning entry for the *result* verdict — entries without a real result
    (``not_assessed``) never count toward the decision."""
    ancestors = [e for e in chain if e.has_result()]
    own_r = own if (own is not None and own.has_result()) else None

    if strategy in (
        AuditTreeAggregationStrategy.CHILD_WINS,
        AuditTreeAggregationStrategy.PARENT_WINS,
    ):
        return _pick_nearest(strategy, own_r, ancestors)

    # best_case / worst_case: compare compliance strength across the chain.
    pool = ([own_r] if own_r else []) + ancestors
    ranked = [e for e in pool if e.result in RESULT_STRENGTH]
    if ranked:
        if strategy == AuditTreeAggregationStrategy.BEST_CASE:
            return max(ranked, key=lambda e: (RESULT_STRENGTH[e.result], -e.distance))
        return min(ranked, key=lambda e: (RESULT_STRENGTH[e.result], e.distance))
    # Only not_applicable values present: surface the nearest one.
    return pool[0] if pool else None


def resolve_requirement(
    strategy: str,
    own: Optional[ChainEntry],
    chain: list[ChainEntry],
    canonical_scale: tuple[Optional[int], Optional[int]],
) -> Optional[dict]:
    """Compute the inheritance overlay for one requirement.

    Returns None when no ancestor audit covers this requirement (nothing to
    overlay — the child's own value stands alone).

    Result and score come from the SAME winning assessment: the strategy picks
    one source by result (entries that are ``not_assessed`` never count), and the
    score is whatever that source recorded — absent when that source didn't score
    it. A score is only meaningful paired with the result it was given for, so it
    never rides along with a different audit's verdict.
    """
    if not chain:
        return None

    chosen = _pick_result(strategy, own, chain)
    inherited = bool(chosen is not None and chosen.distance > 0)

    effective_result = chosen.result if chosen else NOT_ASSESSED
    effective_score = (
        normalize_score(chosen.score, chosen.scale, canonical_scale)
        if (chosen is not None and chosen.has_score())
        else None
    )

    def entry_meta(e: ChainEntry) -> dict:
        return {
            "ca_id": e.ca_id,
            "ca_name": e.ca_name,
            "folder_id": e.folder_id,
            "folder_name": e.folder_name,
            "distance": e.distance,
            "result": e.result,
            "score": normalize_score(e.score, e.scale, canonical_scale),
            "raw_score": e.score,
            "is_scored": e.is_scored,
            "scale": {"min": e.scale[0], "max": e.scale[1]},
        }

    return {
        "strategy": strategy,
        "inherited": inherited,
        "effective_result": effective_result,
        "effective_score": effective_score,
        "scale": {"min": canonical_scale[0], "max": canonical_scale[1]},
        "own": (
            {
                "result": own.result,
                "score": own.score,
                "is_scored": own.is_scored,
                "scale": {"min": own.scale[0], "max": own.scale[1]},
            }
            if own
            else None
        ),
        "source": entry_meta(chosen) if chosen is not None else None,
        # Full chain (ancestors covering this requirement), nearest-first, so the
        # UI can render a clickable inheritance path back to each source audit.
        "path": [entry_meta(e) for e in chain],
    }


def build_overlay_map(
    target_ca,
    *,
    viewable_ca_ids: Optional[Iterable] = None,
    strategy: Optional[str] = None,
) -> dict:
    """Build the full inheritance overlay for a target audit.

    Returns ``{strategy, overlay, ancestors, canonical_scale}`` where ``overlay``
    maps ``str(requirement_id) -> overlay dict`` (only requirements an ancestor
    actually covers). When the feature is off or there are no ancestor audits,
    ``overlay`` is empty.
    """
    from core.models import RequirementAssessment

    if strategy is None:
        strategy = get_strategy()

    own_scale = _ca_scale(target_ca)
    empty = {
        "strategy": strategy,
        "overlay": {},
        "ancestors": [],
        "canonical_scale": {"min": own_scale[0], "max": own_scale[1]},
    }
    if strategy == AuditTreeAggregationStrategy.NONE:
        return empty

    ancestors = select_ancestor_audits(target_ca, viewable_ca_ids=viewable_ca_ids)
    if not ancestors:
        return empty

    # "Top level parent scale": the most distant participating ancestor sets the
    # canonical scale that every score is normalized into.
    canonical_scale = _ca_scale(ancestors[-1].ca)

    meta_by_ca = {str(a.ca.id): a.as_meta() for a in ancestors}
    distance_by_ca = {str(a.ca.id): a.distance for a in ancestors}
    scale_by_ca = {str(a.ca.id): _ca_scale(a.ca) for a in ancestors}

    chain_by_req: dict[str, list[ChainEntry]] = defaultdict(list)
    ancestor_ras = RequirementAssessment.objects.filter(
        compliance_assessment_id__in=[a.ca.id for a in ancestors]
    ).only("requirement_id", "compliance_assessment_id", "result", "score", "is_scored")
    for ra in ancestor_ras:
        ca_id = str(ra.compliance_assessment_id)
        meta = meta_by_ca[ca_id]
        chain_by_req[str(ra.requirement_id)].append(
            ChainEntry(
                ca_id=meta["ca_id"],
                ca_name=meta["ca_name"],
                folder_id=meta["folder_id"],
                folder_name=meta["folder_name"],
                distance=distance_by_ca[ca_id],
                result=ra.result,
                score=ra.score,
                is_scored=ra.is_scored,
                scale=scale_by_ca[ca_id],
            )
        )
    for entries in chain_by_req.values():
        entries.sort(key=lambda e: e.distance)

    target_folder = target_ca.folder
    own_by_req: dict[str, ChainEntry] = {}
    own_ras = RequirementAssessment.objects.filter(
        compliance_assessment=target_ca
    ).only("requirement_id", "result", "score", "is_scored")
    for ra in own_ras:
        own_by_req[str(ra.requirement_id)] = ChainEntry(
            ca_id=str(target_ca.id),
            ca_name=target_ca.name,
            folder_id=str(target_folder.id) if target_folder else None,
            folder_name=target_folder.name if target_folder else None,
            distance=0,
            result=ra.result,
            score=ra.score,
            is_scored=ra.is_scored,
            scale=own_scale,
        )

    overlay: dict[str, dict] = {}
    for req_id, chain in chain_by_req.items():
        ov = resolve_requirement(
            strategy, own_by_req.get(req_id), chain, canonical_scale
        )
        if ov is not None:
            overlay[req_id] = ov

    return {
        "strategy": strategy,
        "overlay": overlay,
        "ancestors": [a.as_meta() for a in ancestors],
        "canonical_scale": {"min": canonical_scale[0], "max": canonical_scale[1]},
    }
