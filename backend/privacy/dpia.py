"""`processing.dpia`: an accepted DPIA, a quick form response on the processing,
becomes the processing's DPIA of record. No config: the form is the DPIA."""

from django.utils.translation import gettext as _

from core.quick_form_targets import Proposal, Target, register


@register
class ProcessingDpiaTarget(Target):
    key = "processing.dpia"
    subject_model = "privacy.Processing"
    permission = "change_processing"
    label = "dpia"

    def current(self, subject):
        dpia = subject.dpia
        return (str(dpia.pk), dpia.ref_id or dpia.name) if dpia else (None, "")

    def resolve(self, response, config, override=None) -> Proposal:
        # A preview passes the form's results only, not the response itself.
        pk = getattr(response, "pk", None)
        label = getattr(response, "ref_id", "") or getattr(response, "name", "")
        return Proposal(
            ok=True, value=str(pk) if pk else None, display=label or _("This DPIA")
        )

    def apply(self, subject, proposal, *, response, user) -> None:
        subject.dpia = response
        subject.save(update_fields=["dpia"])
