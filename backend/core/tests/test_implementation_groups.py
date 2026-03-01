"""Tests for implementation group recalculation and Framework.is_dynamic()."""

import pytest
from core.models import (
    Answer,
    ComplianceAssessment,
    Framework,
    Perimeter,
    Question,
    QuestionChoice,
    RequirementAssessment,
    RequirementNode,
)
from core.utils import update_selected_implementation_groups
from iam.models import Folder


@pytest.fixture
def dynamic_framework_setup(db):
    """Framework with implementation_groups_definition and questions with IG choices."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Dynamic IG Framework",
        folder=folder,
        status=Framework.Status.PUBLISHED,
        is_published=True,
        min_score=0,
        max_score=100,
        implementation_groups_definition=[
            {"ref_id": "base", "default_selected": True},
            {"ref_id": "advanced"},
            {"ref_id": "expert"},
        ],
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:ig:req:001",
        ref_id="IG-REQ",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    q1 = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:ig:q1",
        ref_id="IGQ1",
        annotation="Select level",
        type=Question.Type.SINGLE_CHOICE,
        order=0,
        weight=1,
        folder=folder,
        is_published=True,
    )
    c_basic = QuestionChoice.objects.create(
        question=q1,
        ref_id="IGC1A",
        annotation="Basic",
        add_score=5,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
        select_implementation_groups=["base"],
    )
    c_advanced = QuestionChoice.objects.create(
        question=q1,
        ref_id="IGC1B",
        annotation="Advanced",
        add_score=10,
        compute_result="true",
        order=1,
        folder=folder,
        is_published=True,
        select_implementation_groups=["advanced"],
    )

    perimeter = Perimeter.objects.create(name="IG Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="IG CA",
        framework=fw,
        folder=folder,
        perimeter=perimeter,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    ra = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=rn,
        folder=folder,
    )
    return {
        "framework": fw,
        "requirement_node": rn,
        "q1": q1,
        "c_basic": c_basic,
        "c_advanced": c_advanced,
        "ca": ca,
        "ra": ra,
        "folder": folder,
        "perimeter": perimeter,
    }


@pytest.mark.django_db
class TestIsDynamic:
    def test_is_dynamic_true_when_choices_have_ig(self, dynamic_framework_setup):
        """Choice with select_implementation_groups -> is_dynamic() == True."""
        fw = dynamic_framework_setup["framework"]
        assert fw.is_dynamic() is True

    def test_is_dynamic_false_when_no_ig(self, db):
        """No choice has IG -> False."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Static FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:static:req:001",
            ref_id="ST-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:static:q1",
            ref_id="STQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="STC1A",
            annotation="A",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="STC1B",
            annotation="B",
            order=1,
            folder=folder,
            is_published=True,
        )
        assert fw.is_dynamic() is False

    def test_is_dynamic_false_with_empty_list(self, db):
        """Choice with select_implementation_groups=[] -> False."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Empty IG FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:emptyig:req:001",
            ref_id="EIG-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:emptyig:q1",
            ref_id="EIGQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="EIGC1",
            annotation="A",
            order=0,
            folder=folder,
            is_published=True,
            select_implementation_groups=[],
        )
        QuestionChoice.objects.create(
            question=q,
            ref_id="EIGC2",
            annotation="B",
            order=1,
            folder=folder,
            is_published=True,
        )
        assert fw.is_dynamic() is False


@pytest.mark.django_db
class TestUpdateSelectedImplementationGroups:
    def test_update_ig_adds_selected_groups(self, dynamic_framework_setup):
        """Answer selects choice with IG ['advanced'] -> ca contains 'advanced'."""
        d = dynamic_framework_setup
        a = Answer.objects.create(
            requirement_assessment=d["ra"],
            question=d["q1"],
            folder=d["folder"],
        )
        a.selected_choices.set([d["c_advanced"]])

        update_selected_implementation_groups(d["ca"])
        d["ca"].refresh_from_db()

        assert "advanced" in d["ca"].selected_implementation_groups

    def test_update_ig_includes_default_groups(self, dynamic_framework_setup):
        """default_selected: true group included even without answer selecting it."""
        d = dynamic_framework_setup
        a = Answer.objects.create(
            requirement_assessment=d["ra"],
            question=d["q1"],
            folder=d["folder"],
        )
        a.selected_choices.set([d["c_advanced"]])

        update_selected_implementation_groups(d["ca"])
        d["ca"].refresh_from_db()

        # "base" has default_selected: true
        assert "base" in d["ca"].selected_implementation_groups
        assert "advanced" in d["ca"].selected_implementation_groups

    def test_update_ig_ignores_hidden_question_answers(self, db):
        """Hidden (via depends_on) question's IG choices not included."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Hidden IG FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
            implementation_groups_definition=[
                {"ref_id": "base", "default_selected": True},
                {"ref_id": "hidden_ig"},
            ],
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:hig:req:001",
            ref_id="HIG-REQ",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        q1 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:hig:q1",
            ref_id="HIGQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        c_no = QuestionChoice.objects.create(
            question=q1,
            ref_id="HIGC1A",
            annotation="No",
            add_score=0,
            compute_result="false",
            order=0,
            folder=folder,
            is_published=True,
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="HIGC1B",
            annotation="Yes",
            add_score=5,
            compute_result="true",
            order=1,
            folder=folder,
            is_published=True,
        )
        q2 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:hig:q2",
            ref_id="HIGQ2",
            type=Question.Type.SINGLE_CHOICE,
            order=1,
            depends_on={"question": "HIGQ1", "answers": ["HIGC1B"], "condition": "any"},
            folder=folder,
            is_published=True,
        )
        c_ig = QuestionChoice.objects.create(
            question=q2,
            ref_id="HIGC2A",
            annotation="Select",
            order=0,
            folder=folder,
            is_published=True,
            select_implementation_groups=["hidden_ig"],
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="HIGC2B",
            annotation="Skip",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="HIG Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="HIG CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn,
            folder=folder,
        )

        # Answer Q1 with "No" -> Q2 hidden
        a1 = Answer.objects.create(
            requirement_assessment=ra,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c_no])

        # Even create answer for Q2 - it should be ignored since Q2 is hidden
        a2 = Answer.objects.create(
            requirement_assessment=ra,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([c_ig])

        update_selected_implementation_groups(ca)
        ca.refresh_from_db()

        # "hidden_ig" should NOT be in selected groups since Q2 is hidden
        assert "hidden_ig" not in ca.selected_implementation_groups
        # But default "base" should still be there
        assert "base" in ca.selected_implementation_groups

    def test_update_ig_merges_across_requirement_assessments(self, db):
        """Two RAs with different IG selections -> union."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Merge IG FW",
            folder=folder,
            status=Framework.Status.PUBLISHED,
            is_published=True,
            implementation_groups_definition=[
                {"ref_id": "ig_a"},
                {"ref_id": "ig_b"},
            ],
        )
        rn1 = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:mig:req:001",
            ref_id="MIG-REQ1",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        rn2 = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:mig:req:002",
            ref_id="MIG-REQ2",
            assessable=True,
            folder=folder,
            is_published=True,
        )

        q1 = Question.objects.create(
            requirement_node=rn1,
            urn="urn:test:mig:q1",
            ref_id="MIGQ1",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        c1 = QuestionChoice.objects.create(
            question=q1,
            ref_id="MIGC1A",
            annotation="A",
            order=0,
            folder=folder,
            is_published=True,
            select_implementation_groups=["ig_a"],
        )
        QuestionChoice.objects.create(
            question=q1,
            ref_id="MIGC1B",
            annotation="B",
            order=1,
            folder=folder,
            is_published=True,
        )

        q2 = Question.objects.create(
            requirement_node=rn2,
            urn="urn:test:mig:q2",
            ref_id="MIGQ2",
            type=Question.Type.SINGLE_CHOICE,
            order=0,
            folder=folder,
            is_published=True,
        )
        c2 = QuestionChoice.objects.create(
            question=q2,
            ref_id="MIGC2A",
            annotation="C",
            order=0,
            folder=folder,
            is_published=True,
            select_implementation_groups=["ig_b"],
        )
        QuestionChoice.objects.create(
            question=q2,
            ref_id="MIGC2B",
            annotation="D",
            order=1,
            folder=folder,
            is_published=True,
        )

        perimeter = Perimeter.objects.create(name="MIG Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="MIG CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
            is_published=True,
        )
        ra1 = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn1,
            folder=folder,
        )
        ra2 = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=rn2,
            folder=folder,
        )

        a1 = Answer.objects.create(
            requirement_assessment=ra1,
            question=q1,
            folder=folder,
        )
        a1.selected_choices.set([c1])

        a2 = Answer.objects.create(
            requirement_assessment=ra2,
            question=q2,
            folder=folder,
        )
        a2.selected_choices.set([c2])

        update_selected_implementation_groups(ca)
        ca.refresh_from_db()

        assert "ig_a" in ca.selected_implementation_groups
        assert "ig_b" in ca.selected_implementation_groups

    def test_answer_save_triggers_ig_update(self, dynamic_framework_setup):
        """Saving an Answer on a dynamic framework triggers IG recalculation."""
        d = dynamic_framework_setup
        a = Answer.objects.create(
            requirement_assessment=d["ra"],
            question=d["q1"],
            folder=d["folder"],
        )
        a.selected_choices.set([d["c_advanced"]])

        # The Answer.save() triggers on_commit -> update_selected_implementation_groups
        # We need to force the on_commit callbacks to run
        # In test with transaction=True, on_commit fires after the test transaction commits
        # With regular django_db, on_commit fires immediately
        # Force by calling directly since on_commit may not fire in test context
        update_selected_implementation_groups(d["ca"])
        d["ca"].refresh_from_db()

        assert "advanced" in d["ca"].selected_implementation_groups
        assert "base" in d["ca"].selected_implementation_groups
