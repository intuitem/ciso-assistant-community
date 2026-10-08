"""`entity.tier`: an accepted response sets its vendor's tier.

Config (on the form's `on_accept` entry), tiers named by their stable key:

    bands:                       # optional: the form score
      thresholds:                # highest tier first; the last may omit `min`
        - {tier: critical, min: 3.3}
        - {tier: low-impact}
    mapping:                     # optional: the form's rules
      - {outcome: <yes/no rule>, tier: critical}
      - {outcome: <number rule>, thresholds: [{tier: important, min: 2}, ...]}

The tier is the highest, by rank, of every band reached and every yes/no rule
that fired. Nothing resolved means nothing written. A key this scale does not
have, or a hidden tier, is never replaced by a guess: the response goes to
review with the reason.
"""

from itertools import pairwise

from core.quick_form_targets import Proposal, Target, register
from tprm.models import Tier, TierSource

SCORE = "score"


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


def _dicts(value) -> list[dict]:
    return [r for r in value if isinstance(r, dict)] if isinstance(value, list) else []


def _band_sets(config) -> list[tuple[str, list[dict]]]:
    """(what the bands read, their thresholds): the form score, then each
    number-rule row in order."""
    bands = config.get("bands") if isinstance(config.get("bands"), dict) else {}
    sets = [(SCORE, _dicts(bands.get("thresholds")))] if bands else []
    for row in _dicts(config.get("mapping")):
        if "thresholds" in row:
            sets.append((str(row.get("outcome") or ""), _dicts(row.get("thresholds"))))
    return sets


def _tier_rows(config) -> list[dict]:
    """The yes/no rows: a rule and the tier it gives."""
    return [r for r in _dicts(config.get("mapping")) if "thresholds" not in r]


def _used_keys(config) -> list[str]:
    keys = [str(r.get("tier")) for r in _tier_rows(config)]
    for _, thresholds in _band_sets(config):
        keys += [str(r.get("tier")) for r in thresholds]
    return keys


def _threshold_errors(thresholds) -> list[str]:
    if not isinstance(thresholds, list) or not thresholds:
        return ["thresholdsRequired"]
    errors = []
    previous_min = None
    for index, row in enumerate(thresholds):
        if not isinstance(row, dict) or not row.get("tier"):
            errors.append("thresholdMalformed")
            continue
        minimum = _number(row.get("min"))
        if minimum is None and index != len(thresholds) - 1:
            errors.append("thresholdMinRequired")
        if previous_min is not None and minimum is not None and minimum >= previous_min:
            errors.append("thresholdsMustDescendByMin")
        previous_min = minimum
    return errors


def _out_of_order(thresholds, tiers) -> bool:
    """Bands are read top-down, the first minimum reached wins: out of order, a
    high value would stop at a low band. Refused, never reordered."""
    mins = [_number(row.get("min")) for row in thresholds]
    ranks = [tiers[str(row.get("tier"))].rank for row in thresholds]
    return (
        any(a <= b for a, b in pairwise(ranks))
        or None in mins[:-1]
        or any(a <= b for a, b in pairwise(mins) if b is not None)
    )


def _band_reached(thresholds, value, tiers):
    for row in thresholds:
        minimum = _number(row.get("min"))
        if minimum is None or value >= minimum:
            return tiers.get(str(row.get("tier")))
    return None


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
            # Bands on a rule belong to that rule's row.
            if set(bands) - {"thresholds"}:
                errors.append("bandsReadTheScore")
            errors += _threshold_errors(bands.get("thresholds"))

        if mapping:
            if not isinstance(mapping, list):
                return errors + ["mappingMalformed"]
            for row in mapping:
                if not isinstance(row, dict):
                    errors.append("mappingMalformed")
                    continue
                outcome = row.get("outcome")
                if "thresholds" in row:
                    if outcome not in numeric:
                        errors.append("bandsOutcomeNotNumeric")
                    errors += _threshold_errors(row.get("thresholds"))
                elif not row.get("tier"):
                    errors.append("mappingMalformed")
                elif outcome not in boolean:
                    errors.append("mappingOutcomeUnknown")
        return sorted(set(errors), key=errors.index)

    def health(self, config, quick_form, cache=None) -> list[str]:
        problems = self.validate_config(config, quick_form)
        if cache is None:
            cache = {}
        if "tiers_by_key" not in cache:
            cache["tiers_by_key"] = {t.key: t for t in Tier.objects.all()}
        tiers = cache["tiers_by_key"]
        used = _used_keys(config)
        if any(key not in tiers for key in used):
            problems.append("unknownTier")
        if any(key in tiers and not tiers[key].is_visible for key in used):
            problems.append("tierHidden")
        for _, thresholds in _band_sets(config):
            ranks = [
                tiers[str(r.get("tier"))].rank
                for r in thresholds
                if str(r.get("tier")) in tiers
            ]
            if any(a <= b for a, b in pairwise(ranks)):
                problems.append("thresholdsMustDescendByRank")
                break
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

        # A setup the form's rules no longer support (a renamed rule…) would
        # apply only the part that still matches: refused, never half-read.
        quick_form = getattr(response, "quick_form", None)
        if quick_form is not None and self.validate_config(config, quick_form):
            return Proposal.refuse("tierSetupInvalid")
        tiers = {t.key: t for t in Tier.objects.all()}
        # A key this scale lacks would let a lower band or mapping win: the
        # tier written would not be the one the form asked for.
        if any(key not in tiers for key in _used_keys(config)):
            return Proposal.refuse("unknownTier")
        band_sets = _band_sets(config)
        bands = config.get("bands")
        # Score bands naming a rule were meant for that rule, not the score.
        stray = isinstance(bands, dict) and set(bands) - {"thresholds"}
        if stray or any(_out_of_order(t, tiers) for _, t in band_sets):
            return Proposal.refuse("tierSetupInvalid")

        # (tier, value read, what was read): bands first, then fired rules.
        candidates: list[tuple[Tier, float | None, str]] = []
        values = response.computed_values or {}
        for source, thresholds in band_sets:
            value = _number(
                getattr(response, "score", None)
                if source == SCORE
                else values.get(source)
            )
            tier = (
                _band_reached(thresholds, value, tiers) if value is not None else None
            )
            if tier is not None:
                candidates.append((tier, value, source))
        fired = set((response.computed_outcome or {}).keys())
        for row in _tier_rows(config):
            if row.get("outcome") in fired:
                candidates.append((tiers[str(row.get("tier"))], None, row["outcome"]))

        if not candidates:
            return Proposal.refuse("noTierResolved")
        tier = max(candidates, key=lambda c: c[0].rank)[0]
        # Hidden since the config was saved: never written, as a manual change
        # could not pick it either. The reviewer sees why and can override.
        if not tier.is_visible:
            return Proposal.refuse("tierHidden")
        winning = [c for c in candidates if c[0].id == tier.id]
        # The band value is kept only when a band produced the winning tier.
        band = next((c for c in winning if c[1] is not None), None)
        proposal = self._proposal(tier, band[1] if band else None)
        proposal.extra["outcomes"] = [o for _, v, o in winning if v is None]
        if band is not None:
            if band[2] == SCORE:
                proposal.extra["band_source"] = SCORE
            else:
                proposal.extra["band"] = band[2]
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
