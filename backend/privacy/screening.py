from core.models import Actor, Answer, Question, QuickForm, QuickFormResponse
from django.db import transaction
from django.utils import timezone
from global_settings.models import GlobalSettings
from rest_framework.exceptions import ValidationError

from .models import Dpia, Processing

DEFAULT_SCREENING_QUICK_FORM_URN = "urn:intuitem:risk:quick_form:pre-dpia-screening"
REQUIRED_OUTCOME = "dpia_required"
NAME_QUESTION = "name"
PURPOSE_QUESTION = "purpose"
CRITERIA_QUESTION = "criteria"


def leaf(urn: str | None) -> str:
    return (urn or "").rsplit(":", 1)[-1]


def is_screening_compatible(quick_form: QuickForm) -> bool:
    return any(
        outcome.get("ref_id") == REQUIRED_OUTCOME
        for outcome in quick_form.outcomes_definition or []
    )


def screening_quick_form() -> QuickForm:
    settings = GlobalSettings.objects.filter(name="general").only("value").first()
    configured = (settings.value or {}).get("dpia_screening_form") if settings else None
    quick_form = QuickForm.objects.filter(id=configured).first() if configured else None
    if quick_form is None:
        quick_form = QuickForm.objects.filter(
            urn=DEFAULT_SCREENING_QUICK_FORM_URN
        ).first()
    if quick_form is None:
        raise ValidationError({"error": "screeningLibraryNotLoaded"})
    return quick_form


def _questions_by_name(quick_form: QuickForm) -> dict[str, Question]:
    return {
        leaf(q.urn): q
        for q in Question.objects.filter(page__quick_form=quick_form).prefetch_related(
            "choices"
        )
    }


def prefilled_answers(processing: Processing, quick_form: QuickForm) -> dict:
    questions = _questions_by_name(quick_form)
    answers = {}
    if NAME_QUESTION in questions:
        answers[questions[NAME_QUESTION].urn] = processing.name
    purposes = [p.name for p in processing.purposes.all() if p.name]
    if purposes and PURPOSE_QUESTION in questions:
        answers[questions[PURPOSE_QUESTION].urn] = "; ".join(purposes)
    criteria = questions.get(CRITERIA_QUESTION)
    if criteria is not None and processing.has_sensitive_personal_data:
        sensitive = [
            c.urn
            for c in criteria.choices.all()
            if leaf(c.urn) == Dpia.Reason.SENSITIVE_DATA
        ]
        if sensitive:
            answers[criteria.urn] = sensitive
    return answers


def start_screening(processing: Processing, request) -> tuple[QuickFormResponse, bool]:
    from core.serializers import QuickFormResponseWriteSerializer

    current = processing.dpia_screening
    if current is not None and current.status == QuickFormResponse.Status.DRAFT:
        return current, True

    quick_form = screening_quick_form()
    requester = Actor.objects.filter(user=request.user, entity__isnull=True).first()
    serializer = QuickFormResponseWriteSerializer(
        data={
            "quick_form": quick_form.id,
            "folder": processing.folder_id,
            "name": processing.name,
            "respondents": [requester.id] if requester else [],
            "answers": prefilled_answers(processing, quick_form),
            "start_now": True,
        },
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        response = serializer.save()
        processing.dpia_screening = response
        processing.save(update_fields=["dpia_screening", "updated_at"])
    return response, False


def screening_reasons(response: QuickFormResponse) -> list[str]:
    answers = Answer.objects.filter(response=response).select_related("question")
    for answer in answers.prefetch_related("selected_choices"):
        if leaf(answer.question.urn) == CRITERIA_QUESTION:
            selected = {leaf(c.urn) for c in answer.selected_choices.all()}
            return [str(r) for r in Dpia.Reason if str(r) in selected]
    return []


def screening_verdict(outcome_refs: str | None) -> bool | None:
    refs = set(filter(None, (outcome_refs or "").split(",")))
    if "exemption_claimed" in refs:
        return None
    if REQUIRED_OUTCOME in refs:
        return True
    if "dpia_not_required" in refs:
        return False
    return None


def apply_screening_verdict(response: QuickFormResponse) -> None:
    outcome_refs = (
        QuickFormResponse.objects.filter(pk=response.pk)
        .values_list("outcome_refs", flat=True)
        .first()
    )
    verdict = screening_verdict(outcome_refs)
    if verdict is None:
        return
    Processing.objects.filter(dpia_screening=response).update(
        dpia_required=verdict, updated_at=timezone.now()
    )
