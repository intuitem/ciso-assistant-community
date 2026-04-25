"""Draft validation + serialization helpers for the Preset editor."""

import re
import uuid
from typing import Any

from rest_framework.exceptions import ValidationError

from core.models import LoadedLibrary, Preset


REF_RE = re.compile(r"^[A-Za-z0-9_]+$")
KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")

ALLOWED_SCAFFOLD_TYPES = {"compliance_assessment", "risk_assessment"}

ALLOWED_TARGET_MODELS = {
    "accreditations",
    "actors",
    "applied-controls",
    "assets",
    "business-impact-analysis",
    "compliance-assessments",
    "ebios-rm",
    "entities",
    "evidences",
    "findings-assessments",
    "incidents",
    "metric-instances",
    "organisation-issues",
    "organisation-objectives",
    "perimeters",
    "policies",
    "processings",
    "risk-assessments",
    "task-templates",
}


def serialize_preset_to_draft(preset: Preset) -> dict:
    """Snapshot a Preset's live structure into a draft-shaped dict."""
    return {
        "journey_meta": {
            "name": preset.name,
            "description": preset.description or "",
        },
        "scaffolded_objects": list(preset.scaffolded_objects or []),
        "steps": list(preset.steps or []),
    }


def validate_draft(draft: Any, strict: bool = True) -> dict:
    """Return a normalized draft dict or raise ValidationError.

    strict=True (publish): require framework/matrix URNs to resolve to a
    LoadedLibrary. strict=False (save-draft): accept work-in-progress drafts
    where these references may be empty or unresolved.
    """
    if not isinstance(draft, dict):
        raise ValidationError({"draft": "Draft must be an object."})

    meta = draft.get("journey_meta") or {}
    if not isinstance(meta, dict):
        raise ValidationError({"journey_meta": "Must be an object."})
    name = (meta.get("name") or "").strip()
    if not name and strict:
        raise ValidationError({"journey_meta.name": "Name is required."})
    description = meta.get("description") or ""

    scaffolds_in = draft.get("scaffolded_objects") or []
    if not isinstance(scaffolds_in, list):
        raise ValidationError({"scaffolded_objects": "Must be a list."})
    scaffolds, refs = _validate_scaffolds(scaffolds_in, strict=strict)

    steps_in = draft.get("steps") or []
    if not isinstance(steps_in, list):
        raise ValidationError({"steps": "Must be a list."})
    steps = _validate_steps(steps_in, refs, strict=strict)

    return {
        "journey_meta": {"name": name, "description": description},
        "scaffolded_objects": scaffolds,
        "steps": steps,
    }


_PRESERVED_SCAFFOLD_FIELDS = ("description", "step_ref_id", "translations")


def _carry_over(normalized: dict, item: dict) -> dict:
    for f in _PRESERVED_SCAFFOLD_FIELDS:
        if f in item and item[f] is not None:
            normalized[f] = item[f]
    return normalized


def _validate_scaffolds(scaffolds: list, strict: bool = True) -> tuple[list, set[str]]:
    seen_refs: set[str] = set()
    out = []
    for i, item in enumerate(scaffolds):
        if not isinstance(item, dict):
            raise ValidationError({f"scaffolded_objects[{i}]": "Must be an object."})
        scaffold_type = item.get("type")
        if not scaffold_type:
            raise ValidationError(
                {f"scaffolded_objects[{i}].type": "Type is required."}
            )
        if scaffold_type not in ALLOWED_SCAFFOLD_TYPES:
            normalized = dict(item)
            ref = item.get("ref") or ""
            if ref:
                if not REF_RE.match(ref):
                    raise ValidationError(
                        {f"scaffolded_objects[{i}].ref": "Must match [A-Za-z0-9_]+."}
                    )
                if ref in seen_refs:
                    raise ValidationError(
                        {f"scaffolded_objects[{i}].ref": f"Duplicate ref '{ref}'."}
                    )
                seen_refs.add(ref)
            out.append(normalized)
            continue
        ref = item.get("ref") or ""
        if not REF_RE.match(ref):
            raise ValidationError(
                {f"scaffolded_objects[{i}].ref": "Must match [A-Za-z0-9_]+."}
            )
        if ref in seen_refs:
            raise ValidationError(
                {f"scaffolded_objects[{i}].ref": f"Duplicate ref '{ref}'."}
            )
        seen_refs.add(ref)
        name = (item.get("name") or "").strip()
        if not name and strict:
            raise ValidationError(
                {f"scaffolded_objects[{i}].name": "Name is required."}
            )
        normalized: dict = _carry_over(
            {"type": scaffold_type, "ref": ref, "name": name}, item
        )
        if scaffold_type == "compliance_assessment":
            framework = item.get("framework") or ""
            if framework and not LoadedLibrary.objects.filter(urn=framework).exists():
                if strict:
                    raise ValidationError(
                        {
                            f"scaffolded_objects[{i}].framework": (
                                "Framework URN must resolve to a loaded library."
                            )
                        }
                    )
            elif not framework and strict:
                raise ValidationError(
                    {f"scaffolded_objects[{i}].framework": "Framework is required."}
                )
            normalized["framework"] = framework
            igs = item.get("implementation_groups")
            if igs is not None:
                if not isinstance(igs, list) or not all(
                    isinstance(x, str) for x in igs
                ):
                    raise ValidationError(
                        {
                            f"scaffolded_objects[{i}].implementation_groups": (
                                "Must be a list of strings."
                            )
                        }
                    )
                normalized["implementation_groups"] = igs
        elif scaffold_type == "risk_assessment":
            risk_matrix = item.get("risk_matrix") or ""
            if (
                risk_matrix
                and not LoadedLibrary.objects.filter(urn=risk_matrix).exists()
            ):
                if strict:
                    raise ValidationError(
                        {
                            f"scaffolded_objects[{i}].risk_matrix": (
                                "Risk matrix URN must resolve to a loaded library."
                            )
                        }
                    )
            elif not risk_matrix and strict:
                raise ValidationError(
                    {f"scaffolded_objects[{i}].risk_matrix": "Risk matrix is required."}
                )
            normalized["risk_matrix"] = risk_matrix
        translations = item.get("translations")
        if translations is not None:
            if not isinstance(translations, dict):
                raise ValidationError(
                    {f"scaffolded_objects[{i}].translations": "Must be an object."}
                )
            normalized["translations"] = translations
        out.append(normalized)
    return out, seen_refs


def _validate_steps(steps: list, scaffold_refs: set[str], strict: bool = True) -> list:
    seen_keys: set[str] = set()
    out = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValidationError({f"steps[{i}]": "Must be an object."})
        key = (step.get("key") or "").strip()
        if not key or not KEY_RE.match(key):
            raise ValidationError(
                {f"steps[{i}].key": "Required, must match [A-Za-z0-9_-]+."}
            )
        if key in seen_keys:
            raise ValidationError({f"steps[{i}].key": f"Duplicate key '{key}'."})
        seen_keys.add(key)

        title = (step.get("title") or "").strip()
        if not title and strict:
            raise ValidationError({f"steps[{i}].title": "Title is required."})

        normalized: dict = {
            "id": _coerce_step_id(step.get("id"), i),
            "key": key,
            "title": title,
            "description": step.get("description") or "",
        }

        # Pointer mode is signalled by presence (string) vs absence (None) of
        # target_model / target_url. Empty string = "user is in this mode but
        # hasn't picked a value yet" — preserve through round-trip.
        if "target_model" in step and step["target_model"] is not None:
            target_model = step["target_model"]
            if target_model and target_model not in ALLOWED_TARGET_MODELS:
                raise ValidationError(
                    {
                        f"steps[{i}].target_model": (
                            f"Must be one of: {sorted(ALLOWED_TARGET_MODELS)}."
                        )
                    }
                )
            if strict and not target_model:
                raise ValidationError({f"steps[{i}].target_model": "Pick a model."})
            normalized["target_model"] = target_model

        target_ref = step.get("target_ref")
        if target_ref:
            if target_ref not in scaffold_refs:
                # Allow raw uuids too — but in editor we only use scaffold refs.
                if not _is_uuid(target_ref):
                    raise ValidationError(
                        {
                            f"steps[{i}].target_ref": (
                                f"Must be a scaffold ref or UUID; got '{target_ref}'."
                            )
                        }
                    )
            normalized["target_ref"] = target_ref

        if "target_url" in step and step["target_url"] is not None:
            target_url = step["target_url"]
            if target_url and (
                not isinstance(target_url, str)
                or not target_url.startswith("/")
                or target_url.startswith("//")
                or "://" in target_url
            ):
                raise ValidationError(
                    {
                        f"steps[{i}].target_url": (
                            "Must be a path starting with '/', no scheme, no '//'."
                        )
                    }
                )
            if strict and not target_url:
                raise ValidationError({f"steps[{i}].target_url": "Enter a URL path."})
            normalized["target_url"] = target_url

        target_params = step.get("target_params")
        if target_params is not None:
            if not isinstance(target_params, dict):
                raise ValidationError(
                    {f"steps[{i}].target_params": "Must be an object."}
                )
            normalized["target_params"] = target_params

        translations = step.get("translations")
        if translations is not None:
            if not isinstance(translations, dict):
                raise ValidationError(
                    {f"steps[{i}].translations": "Must be an object."}
                )
            normalized["translations"] = translations

        normalized["order"] = i
        out.append(normalized)
    return out


def _coerce_step_id(value, index):
    if value is None or value == "":
        return None
    if isinstance(value, str) and _is_uuid(value):
        return value
    raise ValidationError({f"steps[{index}].id": "Must be a UUID or null."})


def _is_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
