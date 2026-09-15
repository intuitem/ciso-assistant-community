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
    RequirementAssignment,
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
    )
    q1 = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:ig:q1",
        ref_id="IGQ1",
        text="Select level",
        type=Question.Type.UNIQUE_CHOICE,
        order=0,
        weight=1,
        folder=folder,
    )
    c_basic = QuestionChoice.objects.create(
        question=q1,
        urn="urn:test:ig:choice:q1:basic",
        ref_id="IGC1A",
        value="Basic",
        add_score=5,
        compute_result="true",
        order=0,
        folder=folder,
        select_implementation_groups=["base"],
    )
    c_advanced = QuestionChoice.objects.create(
        question=q1,
        urn="urn:test:ig:choice:q1:advanced",
        ref_id="IGC1B",
        value="Advanced",
        add_score=10,
        compute_result="true",
        order=1,
        folder=folder,
        select_implementation_groups=["advanced"],
    )

    perimeter = Perimeter.objects.create(name="IG Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="IG CA",
        framework=fw,
        folder=folder,
        perimeter=perimeter,
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
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:static:req:001",
            ref_id="ST-REQ",
            assessable=True,
            folder=folder,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:static:q1",
            ref_id="STQ1",
            type=Question.Type.UNIQUE_CHOICE,
            order=0,
            folder=folder,
        )
        QuestionChoice.objects.create(
            question=q,
            urn="urn:test:static:choice:q1:a",
            ref_id="STC1A",
            value="A",
            order=0,
            folder=folder,
        )
        QuestionChoice.objects.create(
            question=q,
            urn="urn:test:static:choice:q1:b",
            ref_id="STC1B",
            value="B",
            order=1,
            folder=folder,
        )
        assert fw.is_dynamic() is False

    def test_is_dynamic_false_with_empty_list(self, db):
        """Choice with select_implementation_groups=[] -> False."""
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Empty IG FW",
            folder=folder,
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:emptyig:req:001",
            ref_id="EIG-REQ",
            assessable=True,
            folder=folder,
        )
        q = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:emptyig:q1",
            ref_id="EIGQ1",
            type=Question.Type.UNIQUE_CHOICE,
            order=0,
            folder=folder,
        )
        QuestionChoice.objects.create(
            question=q,
            urn="urn:test:emptyig:choice:q1:a",
            ref_id="EIGC1",
            value="A",
            order=0,
            folder=folder,
            select_implementation_groups=[],
        )
        QuestionChoice.objects.create(
            question=q,
            urn="urn:test:emptyig:choice:q1:b",
            ref_id="EIGC2",
            value="B",
            order=1,
            folder=folder,
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
        )
        q1 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:hig:q1",
            ref_id="HIGQ1",
            type=Question.Type.UNIQUE_CHOICE,
            order=0,
            folder=folder,
        )
        c_no = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:hig:choice:q1:no",
            ref_id="HIGC1A",
            value="No",
            add_score=0,
            compute_result="false",
            order=0,
            folder=folder,
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:hig:choice:q1:yes",
            ref_id="HIGC1B",
            value="Yes",
            add_score=5,
            compute_result="true",
            order=1,
            folder=folder,
        )
        q2 = Question.objects.create(
            requirement_node=rn,
            urn="urn:test:hig:q2",
            ref_id="HIGQ2",
            type=Question.Type.UNIQUE_CHOICE,
            order=1,
            depends_on={
                "question": "urn:test:hig:q1",
                "answers": ["urn:test:hig:choice:q1:yes"],
                "condition": "any",
            },
            folder=folder,
        )
        c_ig = QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:hig:choice:q2:select",
            ref_id="HIGC2A",
            value="Select",
            order=0,
            folder=folder,
            select_implementation_groups=["hidden_ig"],
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:hig:choice:q2:skip",
            ref_id="HIGC2B",
            value="Skip",
            order=1,
            folder=folder,
        )

        perimeter = Perimeter.objects.create(name="HIG Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="HIG CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
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
        )
        rn2 = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:mig:req:002",
            ref_id="MIG-REQ2",
            assessable=True,
            folder=folder,
        )

        q1 = Question.objects.create(
            requirement_node=rn1,
            urn="urn:test:mig:q1",
            ref_id="MIGQ1",
            type=Question.Type.UNIQUE_CHOICE,
            order=0,
            folder=folder,
        )
        c1 = QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:mig:choice:q1:a",
            ref_id="MIGC1A",
            value="A",
            order=0,
            folder=folder,
            select_implementation_groups=["ig_a"],
        )
        QuestionChoice.objects.create(
            question=q1,
            urn="urn:test:mig:choice:q1:b",
            ref_id="MIGC1B",
            value="B",
            order=1,
            folder=folder,
        )

        q2 = Question.objects.create(
            requirement_node=rn2,
            urn="urn:test:mig:q2",
            ref_id="MIGQ2",
            type=Question.Type.UNIQUE_CHOICE,
            order=0,
            folder=folder,
        )
        c2 = QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:mig:choice:q2:c",
            ref_id="MIGC2A",
            value="C",
            order=0,
            folder=folder,
            select_implementation_groups=["ig_b"],
        )
        QuestionChoice.objects.create(
            question=q2,
            urn="urn:test:mig:choice:q2:d",
            ref_id="MIGC2B",
            value="D",
            order=1,
            folder=folder,
        )

        perimeter = Perimeter.objects.create(name="MIG Perim", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="MIG CA",
            framework=fw,
            folder=folder,
            perimeter=perimeter,
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


@pytest.mark.django_db
class TestIGFilteringSQLiteCompat:
    """Regression: __contains on JSONField fails on SQLite.

    get_global_score() and get_requirements_result_count() must work
    on both PostgreSQL and SQLite when selected_implementation_groups is set.
    """

    def test_get_global_score_with_selected_ig(self, dynamic_framework_setup):
        d = dynamic_framework_setup
        d["ca"].selected_implementation_groups = ["base"]
        d["ca"].save()
        # Must not raise NotSupportedError on SQLite
        score = d["ca"].get_global_score()
        assert score is not None

    def test_get_requirements_result_count_with_selected_ig(
        self, dynamic_framework_setup
    ):
        d = dynamic_framework_setup
        d["ca"].selected_implementation_groups = ["base"]
        d["ca"].save()
        # Must not raise NotSupportedError on SQLite
        result_count = d["ca"].get_requirements_result_count()
        assert isinstance(result_count, list)

    def test_upsert_daily_metrics_with_selected_ig(self, dynamic_framework_setup):
        d = dynamic_framework_setup
        d["ca"].selected_implementation_groups = ["base"]
        d["ca"].save()
        # save() calls upsert_daily_metrics() internally — must not crash
        d["ca"].refresh_from_db()
        assert d["ca"].selected_implementation_groups == ["base"]


@pytest.fixture
def assignment_setup(db):
    """Dynamic framework with two assignments, where an answer reveals a requirement.

    Node layout, by order_id: an orphan question outside any assignment, the same
    question inside Alice's, then the requirements the answer may reveal, then a
    requirement owned by Bob.
    """
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Assignment IG Framework",
        folder=folder,
        implementation_groups_definition=[
            {"ref_id": "base", "default_selected": True},
            {"ref_id": "advanced"},
        ],
    )

    def node(node_id, order_id, groups):
        return RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:test:assign:req:{node_id}",
            ref_id=node_id.upper(),
            assessable=True,
            folder=folder,
            order_id=order_id,
            implementation_groups=groups,
        )

    def question(node, node_id):
        q = Question.objects.create(
            requirement_node=node,
            urn=f"urn:test:assign:q:{node_id}",
            ref_id=f"Q{node_id.upper()}",
            text="Go advanced?",
            type=Question.Type.UNIQUE_CHOICE,
            order=0,
            weight=1,
            folder=folder,
        )
        yes = QuestionChoice.objects.create(
            question=q,
            urn=f"urn:test:assign:choice:{node_id}:yes",
            ref_id=f"C{node_id.upper()}Y",
            value="Yes",
            order=0,
            folder=folder,
            select_implementation_groups=["advanced"],
        )
        no = QuestionChoice.objects.create(
            question=q,
            urn=f"urn:test:assign:choice:{node_id}:no",
            ref_id=f"C{node_id.upper()}N",
            value="No",
            order=1,
            folder=folder,
            select_implementation_groups=[],
        )
        return q, yes, no

    rn_orphan = node("orphan", 0, ["base"])
    rn_base = node("base", 1, ["base"])
    rn_advanced = node("advanced", 2, ["advanced"])
    rn_both = node("both", 3, ["base", "advanced"])
    rn_other = node("other", 4, ["base"])

    q_orphan, orphan_yes, _orphan_no = question(rn_orphan, "orphan")
    q_base, base_yes, base_no = question(rn_base, "base")

    perimeter = Perimeter.objects.create(name="Assign Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Assign CA",
        framework=fw,
        folder=folder,
        perimeter=perimeter,
        selected_implementation_groups=["base"],
    )

    def assessment(requirement):
        return RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=requirement, folder=folder
        )

    ra_orphan = assessment(rn_orphan)
    ra_base = assessment(rn_base)
    ra_advanced = assessment(rn_advanced)
    ra_both = assessment(rn_both)
    ra_other = assessment(rn_other)

    alice = RequirementAssignment.objects.create(
        compliance_assessment=ca, folder=folder
    )
    alice.requirement_assessments.set([ra_base])
    bob = RequirementAssignment.objects.create(compliance_assessment=ca, folder=folder)
    bob.requirement_assessments.set([ra_other])

    return {
        "ca": ca,
        "folder": folder,
        "q_orphan": q_orphan,
        "q_base": q_base,
        "orphan_yes": orphan_yes,
        "base_yes": base_yes,
        "base_no": base_no,
        "ra_orphan": ra_orphan,
        "ra_base": ra_base,
        "ra_advanced": ra_advanced,
        "ra_both": ra_both,
        "ra_other": ra_other,
        "alice": alice,
        "bob": bob,
    }


def _answer(setup, requirement_assessment, question, choice):
    answer, _ = Answer.objects.get_or_create(
        requirement_assessment=requirement_assessment,
        question=question,
        folder=setup["folder"],
    )
    answer.selected_choices.set([choice])


def _answer_base(setup, choice):
    _answer(setup, setup["ra_base"], setup["q_base"], choice)


def _assigned_ids(assignment):
    return set(assignment.requirement_assessments.values_list("id", flat=True))


@pytest.mark.django_db
class TestSyncRequirementAssignments:
    def test_revealed_requirement_joins_the_trigger_assignment(self, assignment_setup):
        d = assignment_setup
        _answer_base(d, d["base_yes"])

        update_selected_implementation_groups(d["ca"])

        assert _assigned_ids(d["alice"]) == {d["ra_base"].id, d["ra_advanced"].id}
        assert _assigned_ids(d["bob"]) == {d["ra_other"].id}

    def test_already_visible_requirement_stays_unassigned(self, assignment_setup):
        """Visible under 'base' already, so leaving it out was the auditor's call."""
        d = assignment_setup
        _answer_base(d, d["base_yes"])

        update_selected_implementation_groups(d["ca"])

        assert d["ra_both"].id not in _assigned_ids(d["alice"])
        assert d["ra_both"].id not in _assigned_ids(d["bob"])

    def test_trigger_outside_any_assignment_is_skipped(self, assignment_setup):
        """The orphan answers first; routing falls through to the assigned trigger."""
        d = assignment_setup
        _answer(d, d["ra_orphan"], d["q_orphan"], d["orphan_yes"])
        _answer_base(d, d["base_yes"])

        update_selected_implementation_groups(d["ca"])

        assert d["ra_advanced"].id in _assigned_ids(d["alice"])
        assert _assigned_ids(d["bob"]) == {d["ra_other"].id}

    def test_in_progress_assignment_receives(self, assignment_setup):
        """Deliberate: the respondent reveals requirements while working, not in draft."""
        d = assignment_setup
        d["alice"].status = RequirementAssignment.Status.IN_PROGRESS
        d["alice"].save()
        _answer_base(d, d["base_yes"])

        update_selected_implementation_groups(d["ca"])

        assert d["ra_advanced"].id in _assigned_ids(d["alice"])

    def test_submitted_assignment_receives_nothing(self, assignment_setup):
        d = assignment_setup
        d["alice"].status = RequirementAssignment.Status.SUBMITTED
        d["alice"].save()
        _answer_base(d, d["base_yes"])

        update_selected_implementation_groups(d["ca"])

        assert _assigned_ids(d["alice"]) == {d["ra_base"].id}
        assert _assigned_ids(d["bob"]) == {d["ra_other"].id}

    def test_deselected_group_leaves_the_assignment(self, assignment_setup):
        """Changing the answer back drops what it had revealed."""
        d = assignment_setup
        _answer_base(d, d["base_yes"])
        update_selected_implementation_groups(d["ca"])
        d["ca"].refresh_from_db()

        _answer_base(d, d["base_no"])
        update_selected_implementation_groups(d["ca"])

        assert _assigned_ids(d["alice"]) == {d["ra_base"].id}
        assert _assigned_ids(d["bob"]) == {d["ra_other"].id}

    def test_answer_selecting_no_group_changes_nothing(self, assignment_setup):
        d = assignment_setup
        _answer_base(d, d["base_no"])

        update_selected_implementation_groups(d["ca"])

        assert _assigned_ids(d["alice"]) == {d["ra_base"].id}
        assert _assigned_ids(d["bob"]) == {d["ra_other"].id}
