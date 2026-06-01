"""Shared text-building helpers for the indexer and the questionnaire agent.

These were originally co-located with the indexing tasks in ``chat/tasks.py``,
but ``chat/questionnaire.py`` also needs to call them — re-indexing live
objects during ``refresh_folder_index`` and rendering an added control after
``create_and_retry``. Importing them across modules created a circular
dependency that we papered over with lazy imports inside functions; pulling
the helpers into their own module removes the cycle.

The shape of each function is deliberately narrow: for objects whose verdict
matters to questionnaire answering (``RequirementAssessment``, ``AppliedControl``),
we emit only fields that bear on the verdict. For everything else we use a
broader generic representation so existing chat retrieval isn't disturbed.
"""

import re


def _build_object_text(obj, model_name: str) -> str:
    """Build a searchable text representation of a model object.

    For the questionnaire-prefill use case, RequirementAssessment and
    AppliedControl get a deliberately narrow shape — only the fields that
    bear on the verdict. Other indexed models keep the broader, generic
    representation so existing chat features aren't disturbed.
    """
    if model_name == "RequirementAssessment":
        return _text_for_requirement_assessment(obj)
    if model_name == "AppliedControl":
        return _text_for_applied_control(obj)
    return _text_for_generic_model(obj, model_name)


def _text_for_requirement_assessment(obj) -> str:
    """Identity (so retrieval can match by question wording) + verdict + narrative.

    Per first-user feedback, the verdict signal lives in `result` and the
    narrative in `observation`; everything else (descriptions, categories,
    linked controls, etc.) is noise for the questionnaire-answering task.
    """
    parts = ["Type: Requirement assessment"]

    requirement = getattr(obj, "requirement", None)
    if requirement is not None:
        req_ref = (getattr(requirement, "ref_id", "") or "").strip()
        req_name = (getattr(requirement, "name", "") or "").strip()
        req_desc = (getattr(requirement, "description", "") or "").strip()
        if req_ref:
            parts.append(f"Requirement ref: {req_ref}")
        if req_name and req_name != req_ref:
            parts.append(f"Requirement: {req_name}")
        if req_desc:
            parts.append(f"Requirement text: {req_desc}")
        framework = getattr(requirement, "framework", None)
        framework_name = getattr(framework, "name", "") if framework else ""
        if framework_name:
            parts.append(f"Framework: {framework_name}")

    result = getattr(obj, "result", None)
    if result:
        result_display = (
            obj.get_result_display() if hasattr(obj, "get_result_display") else result
        )
        parts.append(f"Result: {result_display}")

    observation = (getattr(obj, "observation", None) or "").strip()
    if observation:
        parts.append(f"Observation: {observation}")

    return "\n".join(parts)


def _text_for_applied_control(obj) -> str:
    """Identity + verdict (status) + narrative (observation).

    Same rationale as RequirementAssessment — keep retrieval focused on
    fields that decide whether the control answers the question.
    """
    parts = ["Type: Applied control"]

    name = (getattr(obj, "name", "") or "").strip()
    if name:
        parts.append(f"Name: {name}")
    ref_id = (getattr(obj, "ref_id", "") or "").strip()
    if ref_id:
        parts.append(f"Reference: {ref_id}")

    status = getattr(obj, "status", None)
    if status:
        status_display = (
            obj.get_status_display() if hasattr(obj, "get_status_display") else status
        )
        parts.append(f"Status: {status_display}")

    observation = (getattr(obj, "observation", None) or "").strip()
    if observation:
        parts.append(f"Observation: {observation}")

    return "\n".join(parts)


def _text_for_generic_model(obj, model_name: str) -> str:
    """Broader representation for other indexed models (RiskScenario, Asset,
    Threat, ComplianceAssessment, RiskAssessment).
    """
    parts = [f"Type: {model_name.replace('_', ' ').title()}"]

    name = getattr(obj, "name", None)
    if name:
        parts.append(f"Name: {name}")

    ref_id = getattr(obj, "ref_id", None)
    if ref_id:
        parts.append(f"Reference: {ref_id}")

    description = getattr(obj, "description", None)
    if description:
        parts.append(f"Description: {description}")

    observation = getattr(obj, "observation", None)
    if observation:
        parts.append(f"Observation: {observation}")

    if hasattr(obj, "current_level"):
        parts.append(
            f"Current risk level: {obj.get_current_level_display() if hasattr(obj, 'get_current_level_display') else obj.current_level}"
        )

    if hasattr(obj, "treatment"):
        parts.append(
            f"Treatment: {obj.get_treatment_display() if hasattr(obj, 'get_treatment_display') else obj.treatment}"
        )

    if hasattr(obj, "status"):
        status_display = (
            obj.get_status_display()
            if hasattr(obj, "get_status_display")
            else obj.status
        )
        parts.append(f"Status: {status_display}")

    if hasattr(obj, "category"):
        cat_display = (
            obj.get_category_display()
            if hasattr(obj, "get_category_display")
            else obj.category
        )
        if cat_display:
            parts.append(f"Category: {cat_display}")

    if hasattr(obj, "business_value"):
        bv = (
            obj.get_business_value_display()
            if hasattr(obj, "get_business_value_display")
            else obj.business_value
        )
        if bv:
            parts.append(f"Business value: {bv}")

    return "\n".join(parts)


def _normalize_model_name(model_name: str) -> str:
    """Convert a model class name (``AppliedControl``) to snake_case
    (``applied_control``). Used as the ``object_type`` payload field in Qdrant.
    """
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", model_name).lower()
