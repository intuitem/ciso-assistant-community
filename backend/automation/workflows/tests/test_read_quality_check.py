"""`read_objects` can hand a workflow the quality check of an audit or of a
single requirement — but only when the node asks for it, since resolving one
walks the whole audit."""

import json

import pytest

from automation.workflows.actions import (
    ACTION_REGISTRY,
    READABLE_MODELS,
    ActionError,
    _effective_computed,
    _serialize_read_row,
)
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder


@pytest.fixture
def audit():
    root_folder = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root_folder, name="wf quality")
    perimeter = Perimeter.objects.create(name="wf quality", folder=folder)
    framework = Framework.objects.create(
        name="WF Quality Framework",
        urn="urn:test:wf-quality-framework",
        folder=root_folder,
    )
    RequirementNode.objects.create(
        framework=framework,
        urn="urn:test:wf-quality-framework:req0",
        ref_id="REQ-0",
        name="Requirement 0",
        assessable=True,
        folder=root_folder,
    )
    compliance_assessment = ComplianceAssessment.objects.create(
        name="WF quality audit",
        framework=framework,
        perimeter=perimeter,
        folder=folder,
    )
    compliance_assessment.create_requirement_assessments()
    ra = compliance_assessment.requirement_assessments.first()
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="Planned control",
            folder=folder,
            status=AppliedControl.Status.TO_DO,
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()
    return compliance_assessment, ra


@pytest.mark.parametrize("model", ["compliance_assessment", "requirement_assessment"])
def test_quality_check_is_opt_in(model):
    entry = READABLE_MODELS[model]
    assert "quality_check" in entry.optional_computed
    assert "quality_check" not in entry.computed

    without = _effective_computed(entry, {"model": model})
    assert "quality_check" not in without

    with_it = _effective_computed(entry, {"model": model, "include": ["quality_check"]})
    assert "quality_check" in with_it
    # The always-on values are still there.
    assert set(entry.computed) <= set(with_it)


def test_unknown_include_is_rejected():
    entry = READABLE_MODELS["compliance_assessment"]
    with pytest.raises(ActionError) as excinfo:
        _effective_computed(
            entry, {"model": "compliance_assessment", "include": ["not_a_field"]}
        )
    assert "not_a_field" in str(excinfo.value)


def test_a_model_without_optional_values_rejects_any_include():
    with pytest.raises(ActionError):
        _effective_computed(
            READABLE_MODELS["applied_control"],
            {"model": "applied_control", "include": ["quality_check"]},
        )


@pytest.mark.django_db
@pytest.mark.parametrize("model", ["compliance_assessment", "requirement_assessment"])
def test_serialized_row_is_json_safe(audit, model):
    """`node_outputs` is a plain JSONField with no encoder, so anything a read
    returns has to survive stock json.dumps — findings carry UUIDs."""
    compliance_assessment, ra = audit
    obj = compliance_assessment if model == "compliance_assessment" else ra
    entry = READABLE_MODELS[model]

    row = _serialize_read_row(
        obj,
        entry.readable_fields(),
        _effective_computed(entry, {"model": model, "include": ["quality_check"]}),
    )

    findings = row["quality_check"]
    assert set(findings) == {"errors", "warnings", "info", "count"}
    assert findings["count"] > 0
    assert json.dumps(row)


@pytest.mark.django_db
def test_read_objects_advertises_what_can_be_included():
    """The builder renders a checkbox per includable name, so the registry is
    the only place the list is declared."""
    action = ACTION_REGISTRY["read_objects"]
    assert action.action_type == "read_objects"
    assert sorted(READABLE_MODELS["requirement_assessment"].optional_computed) == [
        "quality_check"
    ]
