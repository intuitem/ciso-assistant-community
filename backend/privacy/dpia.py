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


@register
class ProcessingControlsTarget(Target):
    """`processing.controls`: the measures the form picks join the processing's
    controls. Only adds: a control the form leaves out stays on the processing."""

    key = "processing.controls"
    subject_model = "privacy.Processing"
    permission = "change_processing"
    label = "associatedControls"

    def current(self, subject):
        controls = list(subject.associated_controls.order_by("name"))
        return [str(c.pk) for c in controls], ", ".join(str(c) for c in controls)

    def resolve(self, response, config, override=None) -> Proposal:
        from core.models import AppliedControl, Question

        # A preview passes the form's results only: the picks are not among them.
        if getattr(response, "pk", None) is None:
            return Proposal(ok=True, value=None, display=_("The measures picked"))
        ids = set()
        for answer in response.answers.filter(
            question__type=Question.Type.OBJECT_REFERENCE,
            question__config__model="applied_control",
        ):
            ids.update(answer.value or [])
        controls = AppliedControl.objects.filter(pk__in=ids).order_by("name")
        return Proposal(
            ok=True,
            value=[str(c.pk) for c in controls],
            display=", ".join(str(c) for c in controls) or _("None"),
        )

    def apply(self, subject, proposal, *, response, user) -> None:
        subject.associated_controls.add(*proposal.value)
