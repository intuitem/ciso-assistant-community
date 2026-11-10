import pytest

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Framework,
    RequirementAssessment,
    RequirementNode,
    TaskTemplate,
)
from core.serializers import ComplianceAssessmentActionPlanSerializer
from iam.models import Folder


@pytest.mark.django_db
def test_tasks_come_from_control_and_its_covered_requirements():
    folder = Folder.get_root_folder()
    framework = Framework.objects.create(name="FW", urn="urn:test:ap:fw", folder=folder)
    node = RequirementNode.objects.create(
        framework=framework, urn="urn:test:ap:req", assessable=True, folder=folder
    )
    audit, other = (
        ComplianceAssessment.objects.create(name=n, framework=framework, folder=folder)
        for n in ("audit", "other")
    )
    control = AppliedControl.objects.create(name="control", folder=folder)
    for ca in (audit, other):
        RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=node, folder=folder
        ).applied_controls.add(control)

    def task(name, **links):
        t = TaskTemplate.objects.create(name=name, folder=folder)
        for field, obj in links.items():
            getattr(t, field).add(obj)

    task("on control", applied_controls=control)
    task(
        "on requirement",
        requirement_assessments=RequirementAssessment.objects.get(
            compliance_assessment=audit
        ),
    )
    task(
        "other audit",
        requirement_assessments=RequirementAssessment.objects.get(
            compliance_assessment=other
        ),
    )
    task("unrelated")

    in_scope = {
        str(ra.id)
        for ra in RequirementAssessment.objects.filter(compliance_assessment=audit)
    }
    data = ComplianceAssessmentActionPlanSerializer(
        control,
        context={"pk": audit.id, "with_tasks": True, "scoped_ra_ids": in_scope},
    ).data

    assert sorted(t["str"] for t in data["task_templates"]) == [
        "on control",
        "on requirement",
    ]
    # the action plan page does not ask for tasks
    page = ComplianceAssessmentActionPlanSerializer(control, context={"pk": audit.id})
    assert page.data["task_templates"] is None
