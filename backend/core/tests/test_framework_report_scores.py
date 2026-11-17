"""Scores of the framework report (Framework Insights).

The report scores each audit as its own page does (calculation method, N/A
anchoring, weights), so a report over one audit shows that audit's numbers:
implementation, documentation and maturity, in total, per section and per
requirement.
"""

import pytest
from django.urls import reverse
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.framework_report import visible_layers
from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
    StoredLibrary,
)
from global_settings.models import GlobalSettings
from iam.models import Folder, User, UserGroup

EDIT = {"auditor": "edit", "respondent": "edit"}
HIDDEN = {"auditor": "hidden", "respondent": "hidden"}
SCORES_SHOWN = {"score": EDIT, "is_scored": EDIT, "documentation_score": EDIT}

URN = "urn:intuitem:test:req_node:frs"

# Function > categories > subcategories > requirements, as in CyFun: the report
# sections are the subcategories, the total averages the categories.
YAML = f"""
urn: urn:intuitem:test:library:frs
locale: en
ref_id: FRS
name: framework report scores
description: x
copyright: x
version: 1
publication_date: 2025-01-01
provider: t
packager: t
objects:
  framework:
    urn: urn:intuitem:test:framework:frs
    ref_id: FRS
    name: frs
    description: x
    min_score: 1
    max_score: 5
    requirement_nodes:
    - urn: {URN}:f
      assessable: false
      depth: 1
      ref_id: F
      name: function
    - urn: {URN}:c1
      assessable: false
      depth: 2
      parent_urn: {URN}:f
      ref_id: C1
      name: category 1
    - urn: {URN}:s11
      assessable: false
      depth: 3
      parent_urn: {URN}:c1
      ref_id: S11
      name: subcategory 11
    - urn: {URN}:r111
      assessable: true
      depth: 4
      parent_urn: {URN}:s11
      ref_id: R111
      name: r111
    - urn: {URN}:r112
      assessable: true
      depth: 4
      parent_urn: {URN}:s11
      ref_id: R112
      name: r112
    - urn: {URN}:c2
      assessable: false
      depth: 2
      parent_urn: {URN}:f
      ref_id: C2
      name: category 2
    - urn: {URN}:s21
      assessable: false
      depth: 3
      parent_urn: {URN}:c2
      ref_id: S21
      name: subcategory 21
    - urn: {URN}:r211
      assessable: true
      depth: 4
      parent_urn: {URN}:s21
      ref_id: R211
      name: r211
""".lstrip()

LAYERS = ("implementation_score", "documentation_score", "maturity_score")


def _layers(implementation, documentation, maturity):
    return dict(zip(LAYERS, (implementation, documentation, maturity)))


@pytest.fixture
def admin_client(db):
    startup(sender=None)
    admin = User.objects.create_superuser("admin@frs.com")
    group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = group.folder
    admin.save()
    group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def framework(admin_client):
    stored, err = StoredLibrary.store_library_content(YAML.encode())
    assert err is None, err
    assert stored.load() is None
    return Framework.objects.get(urn="urn:intuitem:test:framework:frs")


def _audit(name, folder, framework, answers, field_visibility=SCORES_SHOWN):
    """An in-progress CyFun-like audit: average of averages, N/A at target 3.
    ``answers`` maps a requirement ref_id to (result, score, documentation_score)."""
    audit = ComplianceAssessment.objects.create(
        name=name,
        framework=framework,
        folder=folder,
        perimeter=Perimeter.objects.create(name=f"p-{name}", folder=folder),
        status="in_progress",
        field_visibility=field_visibility,
        score_calculation_method=ComplianceAssessment.CalculationMethod.AVG_OF_AVG,
        anchor_na_to_target=True,
        target_score=3,
    )
    audit.create_requirement_assessments()
    for ref_id, (result, score, documentation_score) in answers.items():
        ra = RequirementAssessment.objects.get(
            compliance_assessment=audit, requirement__ref_id=ref_id
        )
        ra.result = result
        ra.score = score
        ra.documentation_score = documentation_score
        ra.is_scored = score is not None
        ra.save()
    return audit


ANSWERS = {
    "R111": ("partially_compliant", 4, 2),
    "R112": ("not_applicable", None, None),  # counts at the target, 3
    "R211": ("compliant", 5, None),  # no documentation score: bottom, 1
}


def _report(client, framework):
    response = client.get(
        reverse("frameworks-report", kwargs={"pk": str(framework.pk)})
    )
    assert response.status_code == 200, response.content
    return response.json()


def _audit_entry(report, name):
    return next(ca for ca in report["compliance_assessments"] if ca["name"] == name)


def _row_scores(report, name):
    return {
        row["requirement_ref_id"]: row
        for row in report["rows"]
        if row["compliance_assessment_name"] == name
    }


@pytest.mark.django_db
def test_report_scores_match_the_audit(admin_client, framework):
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    audit = _audit("Audit", root, framework, ANSWERS)

    report = _report(admin_client, framework)
    entry = _audit_entry(report, "Audit")

    # Average of averages over the categories (C1, C2), N/A at 3, a missing
    # documentation score at 1: implementation (0.625 + 1) / 2 -> 4.25,
    # documentation (0.375 + 0) / 2 -> 1.75, maturity their average.
    assert entry["score_scale"] == {
        "min": 1,
        "max": 5,
        "calculation_method": "average_of_averages",
    }
    assert entry["documentation_score_visible"] is True
    assert entry["scores"]["total"] == _layers(4.25, 1.75, 3.0)
    global_score = audit.get_global_score()
    assert entry["scores"]["total"] == {layer: global_score[layer] for layer in LAYERS}

    # Sections are the subcategories, scored as the audit scores a subset.
    sections = entry["scores"]["sections"]
    assert set(sections) == {f"{URN}:s11", f"{URN}:s21"}
    assert sections[f"{URN}:s11"] == _layers(3.5, 2.5, 3.0)
    assert sections[f"{URN}:s21"] == _layers(5.0, 1.0, 3.0)
    s11 = RequirementAssessment.objects.filter(
        compliance_assessment=audit, requirement__parent_urn=f"{URN}:s11"
    ).select_related("requirement", "compliance_assessment")
    expected = audit.get_scores_for(list(s11))
    assert sections[f"{URN}:s11"] == {layer: expected[layer] for layer in LAYERS}

    # Each requirement as the audit counts it.
    rows = _row_scores(report, "Audit")
    assert rows["R111"]["scores"] == _layers(4, 2, 3.0)
    assert rows["R112"]["scores"] == _layers(3.0, 3.0, 3.0)
    assert rows["R211"]["scores"] == _layers(5, 1, 3.0)
    assert all(row["combined_scores"] is None for row in rows.values())
    assert entry["combined_scores"] is None
    assert entry["result_visible"] is True
    assert {ref: row["not_applicable"] for ref, row in rows.items()} == {
        "R111": False,
        "R112": True,
        "R211": False,
    }


@pytest.mark.django_db
def test_score_only_audit_keeps_its_scores(admin_client, framework):
    """Compliance hidden (score-only, CyFun): the scores stay, N/A included,
    and the page is told to leave compliance out."""
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    _audit(
        "Audit",
        root,
        framework,
        ANSWERS,
        field_visibility={**SCORES_SHOWN, "result": HIDDEN},
    )
    report = _report(admin_client, framework)
    entry = _audit_entry(report, "Audit")
    assert entry["result_visible"] is False
    assert entry["scores"]["total"] == _layers(4.25, 1.75, 3.0)
    rows = _row_scores(report, "Audit")
    assert rows["R112"]["result"] is None
    assert rows["R112"]["not_applicable"] is True
    assert rows["R112"]["scores"] == _layers(3.0, 3.0, 3.0)


@pytest.mark.django_db
def test_report_scores_follow_the_implementation_group_filter(admin_client, framework):
    """Narrowing the report scores only the requirements left in scope."""
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    _audit("Audit", root, framework, ANSWERS)
    RequirementNode.objects.filter(urn=f"{URN}:r211").update(
        implementation_groups=["B"]
    )
    response = admin_client.get(
        reverse("frameworks-report", kwargs={"pk": str(framework.pk)}),
        {"implementation_group": "B"},
    )
    assert response.status_code == 200, response.content
    entry = _audit_entry(response.json(), "Audit")
    assert entry["scores"]["total"] == _layers(5.0, 1.0, 3.0)
    assert set(entry["scores"]["sections"]) == {f"{URN}:s21"}


@pytest.mark.django_db
def test_every_status_counts_unless_live_only(admin_client, framework):
    """All but deprecated audits count by default; `statuses=live` leaves planned out too."""
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    _audit("Live", root, framework, ANSWERS)
    planned = _audit("Planned", root, framework, ANSWERS)
    ComplianceAssessment.objects.filter(pk=planned.pk).update(status="planned")
    deprecated = _audit("Deprecated", root, framework, ANSWERS)
    ComplianceAssessment.objects.filter(pk=deprecated.pk).update(status="deprecated")

    report = _report(admin_client, framework)
    assert not report["live_only"]
    assert _audit_entry(report, "Planned")["is_counted"]
    assert not _audit_entry(report, "Deprecated")["is_counted"]
    assert {r["compliance_assessment_name"] for r in report["rows"]} == {
        "Live",
        "Planned",
    }

    response = admin_client.get(
        reverse("frameworks-report", kwargs={"pk": str(framework.pk)}),
        {"statuses": "live"},
    )
    assert response.status_code == 200, response.content
    report = response.json()
    assert report["live_only"]
    assert _audit_entry(report, "Live")["is_counted"]
    assert not _audit_entry(report, "Planned")["is_counted"]
    assert {r["compliance_assessment_name"] for r in report["rows"]} == {"Live"}


@pytest.mark.django_db
def test_audit_without_documentation_score(admin_client, framework):
    """Maturity is the implementation score when the audit has no documentation
    score, which the report then never shows."""
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    _audit(
        "Audit",
        root,
        framework,
        ANSWERS,
        field_visibility={"score": EDIT, "is_scored": EDIT},
    )
    report = _report(admin_client, framework)
    entry = _audit_entry(report, "Audit")
    assert entry["documentation_score_visible"] is False
    assert entry["scores"]["total"] == _layers(4.25, None, 4.25)
    assert _row_scores(report, "Audit")["R111"]["scores"] == _layers(4, None, 4)


@pytest.mark.django_db
def test_hidden_scores_stay_hidden(admin_client, framework):
    """An audit that hides its scores (the default) shows none in the report."""
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    _audit("Audit", root, framework, ANSWERS, field_visibility={})
    report = _report(admin_client, framework)
    entry = _audit_entry(report, "Audit")
    empty = _layers(None, None, None)
    assert entry["scores"]["total"] == empty
    assert all(scores == empty for scores in entry["scores"]["sections"].values())
    assert all(row["scores"] == empty for row in _row_scores(report, "Audit").values())
    assert all(
        row["not_applicable"] is None for row in _row_scores(report, "Audit").values()
    )


@pytest.mark.parametrize(
    "field_visibility, anchor, role, expected",
    [
        (SCORES_SHOWN, True, "auditor", set(LAYERS)),
        ({}, True, "auditor", set()),
        # The maturity score would give a hidden documentation score away.
        (
            {**SCORES_SHOWN, "documentation_score": {**EDIT, "respondent": "hidden"}},
            True,
            "respondent",
            {"implementation_score"},
        ),
        # Score-only audits hide compliance: whether a requirement is N/A is
        # part of its score, whichever way the audit counts N/A.
        ({**SCORES_SHOWN, "result": HIDDEN}, True, "auditor", set(LAYERS)),
        ({**SCORES_SHOWN, "result": HIDDEN}, False, "auditor", set(LAYERS)),
    ],
)
@pytest.mark.django_db
def test_visible_layers(field_visibility, anchor, role, expected):
    audit = ComplianceAssessment(
        field_visibility=field_visibility, anchor_na_to_target=anchor
    )
    assert visible_layers(audit, role) == expected


def _enable_inheritance(strategy):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS,
        defaults={"value": {"audit_tree_inheritance": True}},
    )
    general, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.GENERAL, defaults={"value": {}}
    )
    general.value = {
        **(general.value or {}),
        "audit_tree_aggregation_strategy": strategy,
    }
    general.save()


@pytest.mark.django_db
def test_combined_view_scores(admin_client, framework):
    """The combined view reads inherited answers: their compliance and
    implementation score come from the winning audit. Inheritance carries no
    documentation score, so whatever an inherited answer feeds has none."""
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    child_folder = Folder.objects.create(name="Child", parent_folder=root)
    _audit("Parent", root, framework, {"R111": ("non_compliant", 2, 1)})
    _audit("Child", child_folder, framework, ANSWERS)
    _enable_inheritance("parent_wins")

    report = _report(admin_client, framework)
    rows = _row_scores(report, "Child")
    assert rows["R111"]["inheritance"]["inherited"] is True
    assert rows["R111"]["scores"] == _layers(4, 2, 3.0)
    assert rows["R111"]["combined_scores"] == _layers(2, None, None)
    # The parent assessed nothing else: the child's own answers stand.
    assert rows["R211"]["combined_scores"] is None

    entry = _audit_entry(report, "Child")
    assert entry["scores"]["total"] == _layers(4.25, 1.75, 3.0)
    # Implementation: S11 (0.25 + 0.5) / 2, C2 1 -> (0.375 + 1) / 2 -> 3.75.
    combined = entry["combined_scores"]
    assert combined["total"] == _layers(3.75, None, None)
    assert combined["sections"][f"{URN}:s11"] == _layers(2.5, None, None)
    # A section with no inherited answer keeps all its scores.
    assert combined["sections"][f"{URN}:s21"] == _layers(5.0, 1.0, 3.0)


@pytest.mark.django_db
def test_combined_view_leaves_out_other_scales(admin_client, framework):
    """Scores on different scales are never combined: an answer inherited from
    an audit on another scale leaves out every combined score it would feed."""
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    child_folder = Folder.objects.create(name="Child", parent_folder=root)
    parent = _audit("Parent", root, framework, {"R111": ("non_compliant", 50, 1)})
    ComplianceAssessment.objects.filter(pk=parent.pk).update(min_score=0, max_score=100)
    _audit("Child", child_folder, framework, ANSWERS)
    _enable_inheritance("parent_wins")

    report = _report(admin_client, framework)
    rows = _row_scores(report, "Child")
    assert rows["R111"]["inheritance"]["inherited"] is True
    assert rows["R111"]["combined_scores"] == _layers(None, None, None)

    entry = _audit_entry(report, "Child")
    assert entry["scores"]["total"] == _layers(4.25, 1.75, 3.0)
    combined = entry["combined_scores"]
    assert combined["total"] == _layers(None, None, None)
    assert combined["sections"][f"{URN}:s11"] == _layers(None, None, None)
    assert combined["sections"][f"{URN}:s21"] == _layers(5.0, 1.0, 3.0)


@pytest.mark.django_db
def test_combined_view_keeps_scoreless_answers_from_other_scales(
    admin_client, framework
):
    """An answer inherited from an audit on another scale brings no score of
    that scale when it has none, or when it is N/A (it counts at this audit's
    own target): the combined scores stay."""
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    child_folder = Folder.objects.create(name="Child", parent_folder=root)
    parent = _audit(
        "Parent",
        root,
        framework,
        {
            "R111": ("compliant", None, None),
            "R211": ("not_applicable", None, None),
        },
    )
    ComplianceAssessment.objects.filter(pk=parent.pk).update(min_score=0, max_score=100)
    _audit("Child", child_folder, framework, ANSWERS)
    _enable_inheritance("parent_wins")

    report = _report(admin_client, framework)
    rows = _row_scores(report, "Child")
    assert rows["R111"]["inheritance"]["inherited"] is True
    assert rows["R111"]["combined_scores"] == _layers(None, None, None)
    assert rows["R211"]["combined_scores"] == _layers(3.0, None, None)

    # Implementation: S11 counts R112 (N/A, 0.5), S21 R211 (N/A, 0.5) -> 3.0.
    combined = _audit_entry(report, "Child")["combined_scores"]
    assert combined["total"] == _layers(3.0, None, None)
    assert combined["sections"][f"{URN}:s21"] == _layers(3.0, None, None)


@pytest.mark.django_db
def test_evidence_export_without_evidence_is_empty(admin_client, framework):
    """A selection with no evidence returns 204 rather than an empty zip."""
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    audit = _audit("Audit", root, framework, ANSWERS)
    ra_ids = [
        str(i)
        for i in RequirementAssessment.objects.filter(
            compliance_assessment=audit
        ).values_list("id", flat=True)
    ]
    response = admin_client.post(
        reverse("frameworks-requirement-evidences", kwargs={"pk": str(framework.pk)}),
        {"requirement_assessments": ra_ids},
        format="json",
    )
    assert response.status_code == 204, response.content
