"""`entity.tier`: an accepted response sets its vendor's tier.

Config (on the form's `on_accept` entry), tiers named by their stable key:

    bands:                       # optional; reads one of:
      source: score              #   the form score
      outcome: <ref_id of a numeric rule>  # or a number rule
      thresholds:                # highest tier first; the last may omit `min`
        - {tier: critical, min: 3.3}
        - {tier: low-impact}
    mapping:                     # optional
      - {outcome: <ref_id of a yes/no rule>, tier: critical}

The tier is the highest, by rank, of the band the value reaches and the tiers
of every mapped outcome that fired. Nothing resolved means nothing written. A
key this scale does not have, or a hidden tier, is never replaced by a guess:
the response goes to review with the reason.
"""

from core.quick_form_targets import Proposal, Target, register
from tprm.models import Tier, TierSource


def _rules(quick_form) -> tuple[set[str], set[str]]:
    """(numeric ref_ids, yes/no ref_ids) of the form."""
    numeric, boolean = set(), set()
    for rule in quick_form.outcomes_definition or []:
        ref_id = rule.get("ref_id")
        if not ref_id:
            continue
        (numeric if rule.get("kind") == "number" else boolean).add(ref_id)
    return numeric, boolean


SCORE_SOURCE = "score"


def _band_value(response, bands) -> float | None:
    if bands.get("source") == SCORE_SOURCE:
        return _number(getattr(response, "score", None))
    return _number((response.computed_values or {}).get(bands.get("outcome")))


def _number(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _rows(config) -> tuple[dict, list, list]:
    """(bands, thresholds, mapping), each empty when absent or malformed."""
    bands = config.get("bands") if isinstance(config.get("bands"), dict) else {}
    thresholds = bands.get("thresholds")
    mapping = config.get("mapping")
    return (
        bands,
        [r for r in thresholds if isinstance(r, dict)]
        if isinstance(thresholds, list)
        else [],
        [r for r in mapping if isinstance(r, dict)]
        if isinstance(mapping, list)
        else [],
    )


@register
class EntityTierTarget(Target):
    key = "entity.tier"
    subject_model = "tprm.Entity"
    permission = "change_entity"
    label = "tier"

    def validate_config(self, config, quick_form) -> list[str]:
        """The config's own shape against the form's rules. Which tiers exist
        is the instance's business: see `health`."""
        bands = config.get("bands")
        mapping = config.get("mapping")
        if not bands and not mapping:
            return ["bandsOrMappingRequired"]
        numeric, boolean = _rules(quick_form)
        errors = []

        if bands:
            if not isinstance(bands, dict):
                return ["bandsMalformed"]
            source = bands.get("source")
            if source not in (None, "", SCORE_SOURCE):
                errors.append("bandsSourceUnknown")
            elif source != SCORE_SOURCE and bands.get("outcome") not in numeric:
                errors.append("bandsOutcomeNotNumeric")
            thresholds = bands.get("thresholds")
            if not isinstance(thresholds, list) or not thresholds:
                errors.append("thresholdsRequired")
                thresholds = []
            previous_min = None
            for index, row in enumerate(thresholds):
                if not isinstance(row, dict) or not row.get("tier"):
                    errors.append("thresholdMalformed")
                    continue
                minimum = _number(row.get("min"))
                if minimum is None and index != len(thresholds) - 1:
                    errors.append("thresholdMinRequired")
                if (
                    previous_min is not None
                    and minimum is not None
                    and minimum >= previous_min
                ):
                    errors.append("thresholdsMustDescendByMin")
                previous_min = minimum

        if mapping:
            if not isinstance(mapping, list):
                return errors + ["mappingMalformed"]
            for row in mapping:
                if not isinstance(row, dict) or not row.get("tier"):
                    errors.append("mappingMalformed")
                    continue
                if row.get("outcome") not in boolean:
                    errors.append("mappingOutcomeUnknown")
        return sorted(set(errors), key=errors.index)

    def health(self, config, quick_form, cache=None) -> list[str]:
        problems = self.validate_config(config, quick_form)
        _, thresholds, mapping = _rows(config)
        if cache is None:
            cache = {}
        if "tiers_by_key" not in cache:
            cache["tiers_by_key"] = {t.key: t for t in Tier.objects.all()}
        tiers = cache["tiers_by_key"]
        used = [str(row.get("tier")) for row in [*thresholds, *mapping]]
        if any(key not in tiers for key in used):
            problems.append("unknownTier")
        if any(key in tiers and not tiers[key].is_visible for key in used):
            problems.append("tierHidden")
        ranks = [
            tiers[str(r.get("tier"))].rank
            for r in thresholds
            if str(r.get("tier")) in tiers
        ]
        if any(a <= b for a, b in zip(ranks, ranks[1:])):
            problems.append("thresholdsMustDescendByRank")
        return problems

    def current(self, subject):
        tier = subject.tier
        return (str(tier.id) if tier else None, tier.name if tier else "")

    def _proposal(self, tier: Tier, value=None, **extra) -> Proposal:
        return Proposal(
            ok=True,
            value={"tier": str(tier.id), "value": value},
            display=tier.name,
            extra={"hexcolor": tier.hexcolor, "rank": tier.rank},
            **extra,
        )

    def resolve(self, response, config, override=None) -> Proposal:
        if override:
            note = str(override.get("note") or "").strip()
            if not note:
                return Proposal.refuse("noteRequired")
            tier = Tier.objects.filter(id=override.get("tier"), is_visible=True).first()
            if tier is None:
                return Proposal.refuse("unknownTier")
            return self._proposal(tier, overridden=True, note=note)

        tiers = {t.key: t for t in Tier.objects.all()}
        _, thresholds, mapping = _rows(config)
        # A key this scale lacks would let a lower band or mapping win: the
        # tier written would not be the one the form asked for.
        if any(str(row.get("tier")) not in tiers for row in [*thresholds, *mapping]):
            return Proposal.refuse("unknownTier")
        # Bands are read top-down, the first minimum reached wins: out of order,
        # a high score would stop at a low band. Refused, never reordered.
        mins = [_number(row.get("min")) for row in thresholds]
        ranks = [tiers[str(row.get("tier"))].rank for row in thresholds]
        if (
            any(a <= b for a, b in zip(ranks, ranks[1:]))
            or None in mins[:-1]
            or any(a <= b for a, b in zip(mins, mins[1:]) if b is not None)
        ):
            return Proposal.refuse("tierSetupInvalid")
        candidates: list[tuple[Tier, float | None]] = []

        bands = config.get("bands") or {}
        value = _band_value(response, bands) if bands else None
        if value is not None:
            for row in thresholds:
                tier = tiers.get(str(row.get("tier")))
                minimum = _number(row.get("min"))
                if tier is not None and (minimum is None or value >= minimum):
                    candidates.append((tier, value))
                    break

        fired = set((response.computed_outcome or {}).keys())
        mapped: list[tuple[Tier, str]] = []
        for row in mapping:
            tier = tiers.get(str(row.get("tier")))
            if tier is not None and row.get("outcome") in fired:
                candidates.append((tier, None))
                mapped.append((tier, row.get("outcome")))

        if not candidates:
            return Proposal.refuse("noTierResolved")
        tier, _ = max(candidates, key=lambda c: c[0].rank)
        # Hidden since the config was saved: never written, as a manual change
        # could not pick it either. The reviewer sees why and can override.
        if not tier.is_visible:
            return Proposal.refuse("tierHidden")
        # The band value is kept only when it is what produced the winning tier.
        band_value = next(
            (v for t, v in candidates if t.id == tier.id and v is not None), None
        )
        proposal = self._proposal(tier, band_value)
        proposal.extra["outcomes"] = [o for t, o in mapped if t.id == tier.id]
        if band_value is not None:
            if bands.get("source") == SCORE_SOURCE:
                proposal.extra["band_source"] = SCORE_SOURCE
            else:
                proposal.extra["band"] = bands.get("outcome")
        return proposal

    def apply(self, subject, proposal, *, response, user) -> None:
        from tprm.tiers import set_entity_tier

        tier = Tier.objects.get(id=proposal.value["tier"])
        set_entity_tier(
            subject,
            tier,
            source=TierSource.OVERRIDE
            if proposal.overridden
            else TierSource.ASSESSMENT,
            user=user,
            note=proposal.note,
            value=proposal.value.get("value"),
            response=response,
        )
