"""Not applicable requirements in report category scores and audit exports."""

import csv
import io

import pytest
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status

from core.generators import gen_audit_context
from core.models import RequirementAssessment
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
    audit.save()
    audit.create_requirement_assessments()
    _set(audit, "REQ-1.1", is_scored=True, score=80, result="compliant")
    _set(audit, "REQ-1.2", is_scored=True, score=40, result="partially_compliant")
    # A score left over from before the requirement was marked N/A.
    _set(audit, "REQ-1.3", is_scored=True, score=0, result=NA)
    _set(audit, "REQ-1.4", is_scored=False, score=None, result="not_assessed")
    return audit


def _category(audit):
    context = gen_audit_context(audit.id, _tree(audit), "en", charts=False)
    return context["category_scores"][CATEGORY_URN]


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

        assert category["average_score"] == pytest.approx(73.3)
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
