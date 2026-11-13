"""The fill preview: a quick form answered with trial answers, nothing stored.

One pipeline for a library draft (`LibraryDraftViewSet.quick_form_fill_preview`)
and a loaded form (`QuickFormViewSet.preview`), so the two previews cannot show
different things: both turn their form into the document shape a library gives,
then call `fill_preview`.
"""


def loaded_form_document(quick_form) -> dict:
    """A loaded form back in its library's document shape, labels in the active
    language, with everything the evaluator reads (scales, on_accept)."""
    from core.models import QuickFormPage

    pages = (
        QuickFormPage.objects.filter(quick_form=quick_form)
        .prefetch_related("questions__choices")
        .order_by("order")
    )
    return {
        "urn": quick_form.urn,
        "name": quick_form.get_name_translated,
        "description": quick_form.get_description_translated,
        "outcomes_definition": quick_form.outcomes_definition or [],
        "scores_definition": quick_form.scores_definition,
        "scales_definition": quick_form.scales_definition or [],
        "on_accept": quick_form.on_accept or [],
        "pages": [
            {
                "urn": page.urn,
                "ref_id": page.ref_id,
                "name": page.get_name_translated,
                "description": page.get_description_translated,
                "visibility_expression": page.visibility_expression,
                "aggregation": page.aggregation,
                "questions": page.get_questions_translated() or {},
            }
            for page in pages
        ],
    }


def fill_preview(quick_form: dict, answers) -> dict:
    """The form as a respondent meets it, evaluated against `answers`: its pages
    (hidden or not), progress, score, outcomes, values, ratings and what accepting
    would propose."""
    from core.cel_service import evaluate_quick_form_document
    from core.quick_form_apply import project
    from core.quick_form_ratings import ratings_for_display

    evaluation = evaluate_quick_form_document(
        quick_form, answers if isinstance(answers, dict) else {}
    )
    # Scale questions carry their levels as choices there, as on a loaded form.
    evaluated = evaluation["quick_form"]
    hidden = set(evaluation["hidden_pages"])
    scored_complete = evaluation["context"]["response"]["scored_complete"]
    return {
        "name": evaluated.get("name") or "",
        "description": evaluated.get("description") or "",
        "outcomes_definition": evaluated.get("outcomes_definition") or [],
        "pages": [
            {
                "urn": page.get("urn"),
                "ref_id": page.get("ref_id"),
                "name": page.get("name") or "",
                "description": page.get("description") or "",
                "hidden": page.get("urn") in hidden,
                "questions": page.get("questions") or {},
            }
            for page in evaluated.get("pages") or []
        ],
        "hidden_pages": evaluation["hidden_pages"],
        "missing_required": evaluation["missing_required"],
        "progress": evaluation["progress"],
        "score": evaluation["score"],
        "scored_complete": scored_complete,
        "computed_outcome": evaluation["computed_outcome"],
        "computed_values": evaluation["computed_values"],
        # Rating outcomes with their points, labels in the active language.
        "ratings": ratings_for_display(evaluated, evaluation.get("ratings") or []),
        # Authors want to see where answers lead.
        "projection": project(
            evaluated.get("on_accept") or [],
            evaluation["computed_values"],
            evaluation["computed_outcome"],
            ready=scored_complete,
            score=evaluation["score"],
        ),
    }
