"""`processing.dpia_required`: an accepted screening sets whether its processing
needs a DPIA.

Config (on the form's `on_accept` entry), outcomes named by ref_id:

    mapping:                     # a fired yes/no rule and the verdict it gives
      - {outcome: dpia_required, value: true}
      - {outcome: dpia_not_required, value: false}
    review: [exemption_claimed]  # optional: rules that leave the call to a reviewer

Rules that disagree, or none that fired, also leave it to review.
"""

from django.utils.translation import gettext as _

from core.quick_form_targets import Proposal, Target, register

from .models import DpiaRequirementSource


def _boolean_rules(quick_form) -> set[str]:
    return {
        rule["ref_id"]
        for rule in quick_form.outcomes_definition or []
        if rule.get("ref_id") and rule.get("kind") != "number"
    }


def _display(value: bool) -> str:
    return _("DPIA required") if value else _("No DPIA required")


@register
class ProcessingDpiaRequiredTarget(Target):
    key = "processing.dpia_required"
    subject_model = "privacy.Processing"
    permission = "change_processing"
    label = "dpiaRequired"

    def validate_config(self, config, quick_form) -> list[str]:
        mapping = config.get("mapping")
        if not isinstance(mapping, list) or not mapping:
            return ["mappingRequired"]
        rules = _boolean_rules(quick_form)
        errors = []
        for row in mapping:
            if not isinstance(row, dict) or not isinstance(row.get("value"), bool):
                errors.append("verdictMappingMalformed")
            elif row.get("outcome") not in rules:
                errors.append("mappingOutcomeUnknown")
        review = config.get("review", [])
        if not isinstance(review, list) or any(r not in rules for r in review):
            errors.append("reviewOutcomeUnknown")
        return sorted(set(errors), key=errors.index)

    def applies_to(self, subject) -> bool:
        return subject.dpia_applies

    def current(self, subject):
        return subject.dpia_required, _display(subject.dpia_required)

    def origin(self, subject, response):
        source = subject.dpia_screening
        if (
            subject.dpia_required_source == DpiaRequirementSource.MANUAL
            or source is None
            or source.quick_form_id == response.quick_form_id
        ):
            return None
        set_at = subject.dpia_required_set_at or source.submitted_at
        return {
            "form": source.quick_form.get_name_translated,
            "set_at": set_at.isoformat() if set_at else None,
        }

    def resolve(self, response, config, override=None) -> Proposal:
        if override:
            note = str(override.get("note") or "").strip()
            if not note:
                return Proposal.refuse("noteRequired")
            value = override.get("value")
            if not isinstance(value, bool):
                return Proposal.refuse("verdictRequired")
            return Proposal(
                ok=True,
                value=value,
                display=_display(value),
                overridden=True,
                note=note,
            )

        quick_form = getattr(response, "quick_form", None)
        if quick_form is not None and self.validate_config(config, quick_form):
            return Proposal.refuse("screeningSetupInvalid")
        fired = set((response.computed_outcome or {}).keys())
        if fired & set(config.get("review") or []):
            return Proposal.refuse("reviewerDecides")
        verdicts = {
            row["value"] for row in config["mapping"] if row.get("outcome") in fired
        }
        if not verdicts:
            return Proposal.refuse("noVerdictResolved")
        if len(verdicts) > 1:
            return Proposal.refuse("conflictingVerdicts")
        value = verdicts.pop()
        return Proposal(ok=True, value=value, display=_display(value))

    def apply(self, subject, proposal, *, response, user) -> None:
        from .dpia_requirement import set_dpia_required

        set_dpia_required(
            subject,
            proposal.value,
            source=DpiaRequirementSource.OVERRIDE
            if proposal.overridden
            else DpiaRequirementSource.ASSESSMENT,
            user=user,
            note=proposal.note,
            response=response,
        )
