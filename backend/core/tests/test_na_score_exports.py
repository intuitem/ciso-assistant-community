"""Not applicable requirements in report category scores and audit exports."""

import csv
import io

import pytest
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status

from core.generators import gen_audit_context
from core.models import (
    ComplianceAssessment,
    Framework,
    RequirementAssessment,
    StoredLibrary,
)
from core.tests.test_audit_typst_pdf import _tree
from core.tests.test_audit_word_export import (  # noqa: F401  (fixtures)
    _load_framework,
    _make_audit,
    admin_client,
    app_config,
)

NA = RequirementAssessment.Result.NOT_APPLICABLE
CATEGORY_URN = "urn:intuitem:test:req_node:audit-word-reg:cat-1"


def _set(audit, ref_id, **fields):
    RequirementAssessment.objects.filter(
        compliance_assessment=audit, requirement__ref_id=ref_id
    ).update(**fields)


@pytest.fixture
def na_audit(app_config):  # noqa: F811
    audit = _make_audit(_load_framework(), name="NA score exports")
    audit.min_score = 0
    audit.max_score = 100
    audit.field_visibility = dict.fromkeys(
        ("score", "is_scored"),
        {"auditor": "edit", "respondent": "edit"},
    )
    audit.save()
    audit.create_requirement_assessments()
    _set(audit, "REQ-1.1", is_scored=True, score=80, result="compliant")
    _set(audit, "REQ-1.2", is_scored=True, score=40, result="partially_compliant")
    # A score left over from before the requirement was marked N/A.
    _set(audit, "REQ-1.3", is_scored=True, score=0, result=NA)
    _set(audit, "REQ-1.4", is_scored=False, score=None, result="not_assessed")
    return audit


def _category(audit, urn=CATEGORY_URN):
    context = gen_audit_context(audit.id, _tree(audit), "en", charts=False)
    return context["category_scores"][urn]


NESTED_PREFIX = "urn:intuitem:test:req_node:na-score-nested"
NESTED_FRAMEWORK_YAML = f"""
urn: urn:intuitem:test:library:na-score-nested
locale: en
ref_id: NA-SCORE-NESTED
name: NA score nested
description: Scored parent with scored children
copyright: Test
version: 1
publication_date: 2025-01-01
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:na-score-nested
    ref_id: NA-SCORE-NESTED
    name: NA score nested
    min_score: 0
    max_score: 100
    requirement_nodes:
    - urn: {NESTED_PREFIX}:cat
      assessable: false
      depth: 1
      ref_id: CAT
      name: Category
    - urn: {NESTED_PREFIX}:parent
      assessable: true
      depth: 2
      ref_id: PARENT
      parent_urn: {NESTED_PREFIX}:cat
      name: Parent
    - urn: {NESTED_PREFIX}:child-1
      assessable: true
      depth: 3
      ref_id: CHILD-1
      parent_urn: {NESTED_PREFIX}:parent
      name: Child 1
    - urn: {NESTED_PREFIX}:child-2
      assessable: true
      depth: 3
      ref_id: CHILD-2
      parent_urn: {NESTED_PREFIX}:parent
      name: Child 2
""".lstrip()


@pytest.fixture
def nested_audit(app_config):  # noqa: F811
    stored, error = StoredLibrary.store_library_content(
        NESTED_FRAMEWORK_YAML.encode("utf-8")
    )
    assert error is None, error
    assert stored.load() is None
    framework = Framework.objects.get(urn="urn:intuitem:test:framework:na-score-nested")
    audit = _make_audit(framework, name="NA score nested")
    audit.min_score = 0
    audit.max_score = 100
    audit.save()
    audit.create_requirement_assessments()
    _set(audit, "PARENT", is_scored=True, score=20, result="partially_compliant")
    _set(audit, "CHILD-1", is_scored=True, score=80, result="compliant")
    _set(audit, "CHILD-2", is_scored=True, score=80, result="compliant")
    return audit


@pytest.mark.django_db
class TestCategoryScores:
    def test_not_applicable_is_left_out(self, na_audit):
        category = _category(na_audit)

        assert category["average_score"] == 60
        assert category["scored_count"] == 2
        assert category["item_count"] == 2
        assert category["total_score"] == 120

    def test_not_applicable_anchored_counts_at_max_without_target(self, na_audit):
        na_audit.anchor_na_to_target = True
        na_audit.save()

        category = _category(na_audit)

        assert category["average_score"] == pytest.approx(73.33)
        assert category["scored_count"] == 3
        assert category["item_count"] == 3

    def test_not_applicable_anchored_counts_at_target(self, na_audit):
        na_audit.anchor_na_to_target = True
        na_audit.target_score = 90
        na_audit.save()

        category = _category(na_audit)

        assert category["average_score"] == 70
        assert category["scored_count"] == 3

    def test_category_matches_global_score(self, na_audit):
        category = _category(na_audit)

        assert (
            category["average_score"]
            == na_audit.get_global_score()["implementation_score"]
        )

    def test_sum_is_projected_onto_audit_scale(self, na_audit):
        na_audit.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        na_audit.save()

        category = _category(na_audit)

        assert category["average_score"] == 60
        assert category["scored_count"] == 2

    @pytest.mark.parametrize(
        "method,expected",
        [
            (ComplianceAssessment.CalculationMethod.AVG, 60),
            (ComplianceAssessment.CalculationMethod.AVG_OF_AVG, 20),
        ],
    )
    def test_scored_parent_counts_like_global_score(
        self, nested_audit, method, expected
    ):
        nested_audit.score_calculation_method = method
        nested_audit.save()

        category = _category(nested_audit, f"{NESTED_PREFIX}:cat")

        assert category["average_score"] == expected
        assert (
            category["average_score"]
            == nested_audit.get_global_score()["implementation_score"]
        )
        assert category["scored_count"] == 3
        assert category["item_count"] == 3

    def test_all_not_applicable_category_is_flagged(self, na_audit):
        RequirementAssessment.objects.filter(compliance_assessment=na_audit).update(
            result=NA
        )

        category = _category(na_audit)

        assert category["nothing_applicable"] is True
        assert category["average_score"] == 0
        assert category["scored_count"] == 0


@pytest.mark.django_db
class TestRequirementRowScores:
    def test_report_rows_hide_not_applicable_score(self, na_audit):
        context = gen_audit_context(na_audit.id, _tree(na_audit), "en", charts=False)
        rows = {r["ref_id"]: r for r in context["requirement_assessments"]}

        assert rows["REQ-1.3"]["score"] is None
        assert rows["REQ-1.3"]["max_score"] is None
        assert rows["REQ-1.1"]["score"] == 80

    def test_csv_hides_not_applicable_score(self, admin_client, na_audit):  # noqa: F811
        url = reverse(
            "compliance-assessments-compliance-assessment-csv",
            kwargs={"pk": str(na_audit.pk)},
        )
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        text = response.content.decode("utf-8-sig")
        rows = {
            r["ref_id"]: r for r in csv.DictReader(io.StringIO(text), delimiter=";")
        }
        assert rows["REQ-1.3"]["score"] == ""
        assert rows["REQ-1.1"]["score"] == "80"

    @pytest.mark.parametrize("show_documentation_score", [False, True])
    def test_xlsx_hides_not_applicable_score(
        self,
        admin_client,  # noqa: F811
        na_audit,
        show_documentation_score,
    ):
        na_audit.show_documentation_score = show_documentation_score
        na_audit.save()
        _set(na_audit, "REQ-1.3", documentation_score=3)
        url = reverse("compliance-assessments-xlsx", kwargs={"pk": str(na_audit.pk)})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        sheet = load_workbook(io.BytesIO(response.content)).active
        values = list(sheet.values)
        header, data = values[0], values[1:]
        rows = {row[header.index("ref_id")]: row for row in data}
        score_col = "implementation_score" if show_documentation_score else "score"

        assert rows["REQ-1.3"][header.index(score_col)] is None
        assert rows["REQ-1.1"][header.index(score_col)] == 80
        if show_documentation_score:
            assert rows["REQ-1.3"][header.index("documentation_score")] is None
