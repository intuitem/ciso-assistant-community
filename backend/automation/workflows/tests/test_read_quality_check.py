"""`read_objects` can hand a workflow the quality check of an audit or of a
single requirement — but only when the node asks for it, since resolving one
walks the whole audit."""

import json
from types import SimpleNamespace

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
    # The X-rays envelope, plus the same findings as text. A workflow writing a
    # document needs the messages joined, and the template grammar cannot pluck
    # `msg` out of a list of dicts or join them.
    assert set(findings) == {
        "errors",
        "warnings",
        "info",
        "count",
        "flagged",
        "messages",
        "text",
    }
    assert findings["count"] > 0
    # `count` includes info, which no workflow branches on; `flagged` is the
    # errors-or-warnings question a condition can read as a boolean.
    assert findings["flagged"] is True
    assert findings["messages"]
    assert findings["text"].startswith("  - ")
    assert findings["text"].count("\n") == len(findings["messages"]) - 1
    assert json.dumps(row)


@pytest.mark.django_db
def test_read_objects_advertises_what_can_be_included():
    """The builder renders a checkbox per includable name, so the registry is
    the only place the list is declared."""
    action = ACTION_REGISTRY["read_objects"]
    assert action.action_type == "read_objects"
    assert sorted(READABLE_MODELS["requirement_assessment"].optional_computed) == [
        "applied_controls",
        "evidences",
        "quality_check",
    ]


@pytest.mark.django_db
def test_a_requirements_own_name_is_dropped_from_its_findings(audit):
    """Three rules tripping on one requirement repeated its name three times.
    Read one object the prefix is noise; read a whole audit it is the only thing
    telling the lines apart, so it survives there."""
    compliance_assessment, ra = audit
    entry = READABLE_MODELS["requirement_assessment"]

    row = _serialize_read_row(
        ra,
        entry.readable_fields(),
        _effective_computed(
            entry, {"model": "requirement_assessment", "include": ["quality_check"]}
        ),
    )
    findings = row["quality_check"]
    assert findings["messages"]
    assert not any(message.startswith(str(ra)) for message in findings["messages"])

    audit_entry = READABLE_MODELS["compliance_assessment"]
    audit_row = _serialize_read_row(
        compliance_assessment,
        audit_entry.readable_fields(),
        _effective_computed(
            audit_entry,
            {"model": "compliance_assessment", "include": ["quality_check"]},
        ),
    )
    audit_findings = audit_row["quality_check"]
    # The audit's findings span its requirements and its own assessment-level
    # rules, so nothing is shared and every line keeps saying what it is about.
    assert any(str(ra) in message for message in audit_findings["messages"])


@pytest.mark.django_db
def test_info_alone_does_not_flag(audit):
    """A requirement carrying only info findings has nothing to act on, so a
    workflow routing on `flagged` must not treat it as a concern."""
    compliance_assessment, ra = audit
    ra.applied_controls.clear()
    ra.result = RequirementAssessment.Result.NOT_ASSESSED
    ra.status = RequirementAssessment.Status.IN_PROGRESS
    ra.save()

    entry = READABLE_MODELS["requirement_assessment"]
    row = _serialize_read_row(
        ra,
        entry.readable_fields(),
        _effective_computed(
            entry, {"model": "requirement_assessment", "include": ["quality_check"]}
        ),
    )
    findings = row["quality_check"]
    assert findings["errors"] == [] and findings["warnings"] == []
    assert findings["flagged"] is False


@pytest.mark.django_db
def test_the_backing_is_opt_in_too(audit):
    """A page carrying every control, its evidence and their revisions is how a
    read outgrows one node output. Most reads want none of it."""
    compliance_assessment, ra = audit
    entry = READABLE_MODELS["requirement_assessment"]

    plain = _serialize_read_row(
        ra,
        entry.readable_fields(),
        _effective_computed(entry, {"model": "requirement_assessment"}),
    )
    assert "applied_controls" not in plain
    assert "evidences" not in plain

    asked = _serialize_read_row(
        ra,
        entry.readable_fields(),
        _effective_computed(
            entry,
            {
                "model": "requirement_assessment",
                "include": ["applied_controls", "evidences"],
            },
        ),
    )
    assert asked["applied_controls"]


def test_the_prefetches_are_keyed_by_what_needs_them():
    """Each group hangs off the computed value it serves, so a read that did not
    ask for one does not pay for its queries either."""
    entry = READABLE_MODELS["requirement_assessment"]
    assert set(entry.prefetch_scoped) <= set(entry.optional_computed)
    assert set(entry.prefetch_scoped) == {"applied_controls", "evidences"}
    assert (
        "applied_controls__evidences__revisions"
        in (entry.prefetch_scoped["applied_controls"])
    )
