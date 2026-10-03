"""`entity.tier`: an accepted response sets its vendor's tier.

Config (on the publication's `on_accept` entry):

    bands:                       # optional
      outcome: <ref_id of a numeric rule>
      thresholds:                # highest tier first; the last may omit `min`
        - {tier: <tier id>, min: 18}
        - {tier: <tier id>}
    mapping:                     # optional
      - {outcome: <ref_id of a yes/no rule>, tier: <tier id>}

The tier is the highest, by rank, of the band the value reaches and the tiers
of every mapped outcome that fired. Nothing resolved means nothing written.
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


def _number(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


@register
class EntityTierTarget(Target):
    key = "entity.tier"
    subject_model = "tprm.Entity"
    permission = "change_entity"
    label = "tier"

    def validate_config(self, config, quick_form) -> list[str]:
        bands = config.get("bands")
        mapping = config.get("mapping")
        if not bands and not mapping:
            return ["bandsOrMappingRequired"]
        numeric, boolean = _rules(quick_form)
        tiers = {str(t.id): t for t in Tier.objects.all()}
        errors = []

        if bands:
            if not isinstance(bands, dict):
                return ["bandsMalformed"]
            if bands.get("outcome") not in numeric:
                errors.append("bandsOutcomeNotNumeric")
            thresholds = bands.get("thresholds")
            if not isinstance(thresholds, list) or not thresholds:
                errors.append("thresholdsRequired")
                thresholds = []
            previous_rank = previous_min = None
            for index, row in enumerate(thresholds):
                if not isinstance(row, dict):
                    errors.append("thresholdMalformed")
                    continue
                tier = tiers.get(str(row.get("tier")))
                if tier is None:
                    errors.append("unknownTier")
                    continue
                is_last = index == len(thresholds) - 1
                minimum = _number(row.get("min"))
                if minimum is None and not is_last:
                    errors.append("thresholdMinRequired")
                if previous_rank is not None and tier.rank >= previous_rank:
                    errors.append("thresholdsMustDescendByRank")
                if (
                    previous_min is not None
                    and minimum is not None
                    and minimum >= previous_min
                ):
                    errors.append("thresholdsMustDescendByMin")
                previous_rank = tier.rank
                previous_min = minimum

        if mapping:
            if not isinstance(mapping, list):
                return errors + ["mappingMalformed"]
            for row in mapping:
                if not isinstance(row, dict):
                    errors.append("mappingMalformed")
                    continue
                if row.get("outcome") not in boolean:
                    errors.append("mappingOutcomeUnknown")
                if str(row.get("tier")) not in tiers:
                    errors.append("unknownTier")
        return sorted(set(errors), key=errors.index)

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

        tiers = {str(t.id): t for t in Tier.objects.all()}
        candidates: list[tuple[Tier, float | None]] = []

        bands = config.get("bands") or {}
        value = _number((response.computed_values or {}).get(bands.get("outcome")))
        if bands and value is not None:
            for row in bands.get("thresholds") or []:
                tier = tiers.get(str(row.get("tier")))
                minimum = _number(row.get("min"))
                if tier is not None and (minimum is None or value >= minimum):
                    candidates.append((tier, value))
                    break

        fired = set((response.computed_outcome or {}).keys())
        for row in config.get("mapping") or []:
            tier = tiers.get(str(row.get("tier")))
            if tier is not None and row.get("outcome") in fired:
                candidates.append((tier, None))

        if not candidates:
            return Proposal.refuse("noTierResolved")
        tier, _ = max(candidates, key=lambda c: c[0].rank)
        # The band value is kept only when it is what produced the winning tier.
        band_value = next(
            (v for t, v in candidates if t.id == tier.id and v is not None), None
        )
        return self._proposal(tier, band_value)

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
