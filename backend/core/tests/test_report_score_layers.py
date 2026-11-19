"""Implementation, documentation and maturity scores in audit reports and exports.

When an audit has a documentation score, the reports show the three scores as
Framework Insights does, headlined by the maturity score (their average), and
the exports add the documentation and maturity scores.
"""

import csv
import io

from pypdf import PdfReader
import pytest
from django.urls import reverse
from docx import Document
from openpyxl import load_workbook
from rest_framework import status

from core.framework_report import visible_layers
from core.generators import (
    REPORT_PROFILES,
    audit_context_for_typst,
    gen_audit_context,
)
from core.models import (
    ComplianceAssessment,
    Framework,
    RequirementAssessment,
    RequirementNode,
    StoredLibrary,
    round_score,
)
from core.tests.test_audit_typst_pdf import _tree
from core.tests.test_audit_word_export import (  # noqa: F401  (fixtures)
    _make_audit,
    admin_client,
    app_config,
)
from core.typst_render import localized_template, render_pdf
from global_settings.models import GlobalSettings
from iam.models import User

NA = RequirementAssessment.Result.NOT_APPLICABLE
PREFIX = "urn:intuitem:test:req_node:report-layers"
CAT_A = f"{PREFIX}:cat-a"
CAT_B = f"{PREFIX}:cat-b"
FRAMEWORK_YAML = f"""
urn: urn:intuitem:test:library:report-layers
locale: en
ref_id: REPORT-LAYERS
name: Report score layers
description: Two categories on a 1-5 scale
copyright: Test
version: 1
publication_date: 2025-01-01
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:report-layers
    ref_id: REPORT-LAYERS
    name: Report score layers
    min_score: 1
    max_score: 5
    requirement_nodes:
    - urn: {CAT_A}
      assessable: false
      depth: 1
      ref_id: CAT-A
      name: Category A
    - urn: {PREFIX}:a-1
      assessable: true
      depth: 2
      ref_id: A-1
      parent_urn: {CAT_A}
      name: A one
    - urn: {PREFIX}:a-2
      assessable: true
      depth: 2
      ref_id: A-2
      parent_urn: {CAT_A}
      name: A two
    - urn: {CAT_B}
      assessable: false
      depth: 1
      ref_id: CAT-B
      name: Category B
    - urn: {PREFIX}:b-1
      assessable: true
      depth: 2
      ref_id: B-1
      parent_urn: {CAT_B}
      name: B one
""".lstrip()

EVERYONE_EDIT = {"auditor": "edit", "respondent": "edit"}
AUDITOR_ONLY = {"auditor": "edit", "respondent": "hidden"}


def _set(audit, ref_id, **fields):
    RequirementAssessment.objects.filter(
        compliance_assessment=audit, requirement__ref_id=ref_id
    ).update(**fields)


@pytest.fixture
def layered_audit(app_config):  # noqa: F811
    stored, error = StoredLibrary.store_library_content(FRAMEWORK_YAML.encode("utf-8"))
    assert error is None, error
    assert stored.load() is None
    framework = Framework.objects.get(urn="urn:intuitem:test:framework:report-layers")
    audit = _make_audit(framework, name="Report score layers")
    audit.min_score = 1
    audit.max_score = 5
    audit.field_visibility = {
        "score": EVERYONE_EDIT,
        "is_scored": EVERYONE_EDIT,
        "documentation_score": EVERYONE_EDIT,
    }
    audit.save()
    audit.create_requirement_assessments()
    # Category A: implementation 3, documentation 3, maturity 3.
    _set(audit, "A-1", is_scored=True, score=4, documentation_score=2)
    _set(audit, "A-2", is_scored=True, score=2, documentation_score=4)
    # Category B: implementation 5, documentation 3, maturity 4.
    _set(audit, "B-1", is_scored=True, score=5, documentation_score=3)
    return audit


def _context(audit, **kwargs):
    return gen_audit_context(audit.id, _tree(audit), "en", charts=False, **kwargs)


def _rows(context):
    return {row["ref_id"]: row for row in context["requirement_assessments"]}


def _text(pdf):
    return "".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)


@pytest.mark.django_db
class TestCategoryScores:
    def test_categories_carry_the_three_scores_headlined_by_maturity(
        self, layered_audit
    ):
        context = _context(layered_audit)

        assert context["score_layers"] == [
            "implementation_score",
            "documentation_score",
            "maturity_score",
        ]
        a = context["category_scores"][CAT_A]
        b = context["category_scores"][CAT_B]
        assert (a["implementation_score"], a["documentation_score"]) == (3, 3)
        assert (b["implementation_score"], b["documentation_score"]) == (5, 3)
        assert b["maturity_score"] == 4
        assert b["average_score"] == b["maturity_score"]

    @pytest.mark.parametrize(
        "method",
        [
            ComplianceAssessment.CalculationMethod.AVG,
            ComplianceAssessment.CalculationMethod.AVG_OF_AVG,
        ],
    )
    def test_overall_is_the_audit_global_score(self, layered_audit, method):
        layered_audit.score_calculation_method = method
        layered_audit.save()

        overall = _context(layered_audit)["overall_scores"]

        expected = layered_audit.get_global_score()
        for layer in ("implementation_score", "documentation_score", "maturity_score"):
            assert overall[layer] == round_score(expected[layer]), layer
        assert overall["average_score"] == overall["maturity_score"]

    def test_without_documentation_score_only_the_implementation_score(
        self, layered_audit
    ):
        layered_audit.show_documentation_score = False
        layered_audit.save()

        context = _context(layered_audit)

        assert context["score_layers"] == ["implementation_score"]
        b = context["category_scores"][CAT_B]
        assert "maturity_score" not in b and "documentation_score" not in b
        assert b["average_score"] == b["implementation_score"] == 5
        assert "maturity_score" not in _rows(context)["B-1"]

    def test_documentation_first_setting_orders_the_pair(self, layered_audit):
        settings, _ = GlobalSettings.objects.get_or_create(name="general")
        settings.value = {**(settings.value or {}), "documentation_score_first": True}
        settings.save()

        assert _context(layered_audit)["score_layers"] == [
            "documentation_score",
            "implementation_score",
            "maturity_score",
        ]

    def test_sum_starts_at_the_bottom_of_the_scale(self, layered_audit):
        """A SUM total is projected from the span its requirements can reach,
        so the lowest answers land on the scale's minimum, not above it."""
        layered_audit.score_calculation_method = (
            ComplianceAssessment.CalculationMethod.SUM
        )
        layered_audit.save()
        for ref_id in ("A-1", "A-2", "B-1"):
            _set(layered_audit, ref_id, score=1, documentation_score=1)

        a = _context(layered_audit)["category_scores"][CAT_A]

        assert a["implementation_score"] == 1
        assert a["maturity_score"] == 1

    def test_sum_agrees_with_the_average_on_a_uniform_scale(self, layered_audit):
        averaged = _context(layered_audit)["category_scores"][CAT_A]
        layered_audit.score_calculation_method = (
            ComplianceAssessment.CalculationMethod.SUM
        )
        layered_audit.save()

        summed = _context(layered_audit)["category_scores"][CAT_A]

        for layer in ("implementation_score", "documentation_score", "maturity_score"):
            assert summed[layer] == averaged[layer], layer


@pytest.mark.django_db
class TestRequirementRows:
    def test_rows_carry_the_three_scores(self, layered_audit):
        row = _rows(_context(layered_audit))["A-1"]

        assert row["implementation_score"] == 4
        assert row["documentation_score"] == 2
        assert row["maturity_score"] == 3

    def test_rows_keep_a_missing_documentation_score_empty(self, layered_audit):
        _set(layered_audit, "A-1", documentation_score=None)

        row = _rows(_context(layered_audit))["A-1"]

        assert row["documentation_score"] is None
        # Counted at the bottom of the scale: (4 + 1) / 2.
        assert row["maturity_score"] == 2.5

    def test_rows_are_out_of_the_requirement_own_scale(self, layered_audit):
        RequirementNode.objects.filter(
            framework=layered_audit.framework, ref_id="A-1"
        ).update(min_score=0, max_score=10)
        _set(layered_audit, "A-1", score=8, documentation_score=4)

        context = _context(layered_audit)
        row = _rows(context)["A-1"]

        assert row["max_score"] == 10
        assert (row["implementation_score"], row["maturity_score"]) == (8, 6)
        payload, images = audit_context_for_typst(
            context, layered_audit, "auditor", "en", "full"
        )
        pdf = render_pdf(
            localized_template(REPORT_PROFILES["full"]["template"], "en"),
            payload,
            images=images,
        )
        assert "Implementation: 8/10" in _text(pdf)

    def test_rows_are_out_of_the_audit_scale_when_it_differs(self, layered_audit):
        layered_audit.max_score = 10
        layered_audit.save()

        assert _rows(_context(layered_audit))["B-1"]["max_score"] == 10

    def test_not_applicable_rows_leave_every_score_empty(self, layered_audit):
        _set(layered_audit, "B-1", result=NA)
        layered_audit.anchor_na_to_target = True
        layered_audit.save()

        row = _rows(_context(layered_audit))["B-1"]

        assert row["implementation_score"] is None
        assert row["documentation_score"] is None
        assert row["maturity_score"] is None


@pytest.mark.django_db
class TestRedaction:
    def _hide_documentation_from_respondents(self, audit):
        audit.field_visibility = {**audit.field_visibility}
        audit.field_visibility["documentation_score"] = AUDITOR_ONLY
        audit.save()

    def test_reader_without_documentation_gets_the_implementation_headline(
        self, layered_audit
    ):
        self._hide_documentation_from_respondents(layered_audit)
        context = gen_audit_context(
            layered_audit.id,
            _tree(layered_audit),
            "en",
            score_layers=visible_layers(layered_audit, "respondent"),
        )

        payload, images = audit_context_for_typst(
            context, layered_audit, "respondent", "en", "full"
        )

        assert payload["score_layers"] == ["implementation_score"]
        b = payload["category_scores"][CAT_B]
        assert "maturity_score" not in b and "documentation_score" not in b
        assert b["average_score"] == 5
        row = {r["ref_id"]: r for r in payload["requirement_assessments"]}["A-1"]
        assert "documentation_score" not in row and "maturity_score" not in row
        assert row["score"] == 4
        # Drawn for this reader, from the implementation score: kept.
        assert "category_radar.png" in images

    def test_auditor_context_rendered_for_a_respondent_withholds_maturity(
        self, layered_audit
    ):
        """A context built for the auditor headlines the maturity score; the
        payload must not pass it, nor the radar drawn from it, to a reader who
        may not see the documentation score."""
        self._hide_documentation_from_respondents(layered_audit)
        context = gen_audit_context(layered_audit.id, _tree(layered_audit), "en")

        payload, images = audit_context_for_typst(
            context, layered_audit, "respondent", "en", "full"
        )

        assert payload["score_layers"] == ["implementation_score"]
        for entry in [*payload["category_scores"].values(), payload["overall_scores"]]:
            assert "maturity_score" not in entry
            assert "documentation_score" not in entry
            assert entry["average_score"] == entry["implementation_score"]
        assert "category_radar.png" not in images

    def test_attestation_drops_the_overall_scores(self, layered_audit):
        payload, _ = audit_context_for_typst(
            _context(layered_audit), layered_audit, "auditor", "en", "attestation"
        )

        assert "category_scores" not in payload
        assert "overall_scores" not in payload


@pytest.mark.django_db
class TestPdf:
    @pytest.mark.parametrize(
        "lang,labels",
        [
            ("en", ("Implementation", "Documentation", "Maturity", "Overall")),
            ("fr", ("Implémentation", "Documentation", "Maturité", "Global")),
            ("tr", ("Uygulama", "Dokümantasyon", "Olgunluk", "Genel")),
        ],
    )
    def test_report_shows_the_three_scores(self, layered_audit, lang, labels):
        payload, images = audit_context_for_typst(
            _context(layered_audit), layered_audit, "auditor", lang, "full"
        )
        template = localized_template(REPORT_PROFILES["full"]["template"], lang)

        pdf = render_pdf(template, payload, images=images)

        text = _text(pdf)
        for label in labels:
            assert label in text, label

    @pytest.mark.parametrize(
        "lang,maturity", [("en", "Maturity"), ("fr", "Maturité"), ("tr", "Olgunluk")]
    )
    def test_attestation_rows_show_the_three_scores(
        self, layered_audit, lang, maturity
    ):
        payload, images = audit_context_for_typst(
            _context(layered_audit), layered_audit, "auditor", lang, "attestation"
        )
        template = localized_template(REPORT_PROFILES["attestation"]["template"], lang)

        pdf = render_pdf(template, payload, images=images)

        # A-1: implementation 4, documentation 2, maturity 3.
        assert f"{maturity}: 3/5" in _text(pdf)

    def test_attestation_leaves_a_missing_documentation_score_empty(
        self, layered_audit
    ):
        _set(layered_audit, "A-1", documentation_score=None)
        payload, images = audit_context_for_typst(
            _context(layered_audit), layered_audit, "auditor", "en", "attestation"
        )
        template = localized_template(REPORT_PROFILES["attestation"]["template"], "en")

        text = _text(render_pdf(template, payload, images=images))

        assert "Documentation: 1/5" not in text
        assert "Documentation: –" in text
        assert "Maturity: 2.5/5" in text


@pytest.mark.django_db
class TestExports:
    def test_csv_appends_documentation_and_maturity(
        self,
        admin_client,  # noqa: F811
        layered_audit,
    ):
        url = reverse(
            "compliance-assessments-compliance-assessment-csv",
            kwargs={"pk": str(layered_audit.pk)},
        )
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        reader = csv.DictReader(
            io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"
        )
        assert reader.fieldnames[-2:] == ["documentation_score", "maturity_score"]
        rows = {row["ref_id"]: row for row in reader}
        assert rows["A-1"]["score"] == "4"
        assert rows["A-1"]["documentation_score"] == "2"
        assert float(rows["A-1"]["maturity_score"]) == 3

    def test_csv_columns_unchanged_without_documentation_score(
        self,
        admin_client,  # noqa: F811
        layered_audit,
    ):
        layered_audit.show_documentation_score = False
        layered_audit.save()
        url = reverse(
            "compliance-assessments-compliance-assessment-csv",
            kwargs={"pk": str(layered_audit.pk)},
        )

        header = admin_client.get(url).content.decode("utf-8-sig").splitlines()[0]

        assert header.endswith(";answers")

    def test_xlsx_adds_maturity_last(
        self,
        admin_client,  # noqa: F811
        layered_audit,
    ):
        _set(layered_audit, "B-1", result=NA)
        url = reverse(
            "compliance-assessments-xlsx", kwargs={"pk": str(layered_audit.pk)}
        )
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        values = list(load_workbook(io.BytesIO(response.content)).active.values)
        header, data = values[0], values[1:]
        assert header[-1] == "maturity_score"
        rows = {row[header.index("ref_id")]: row for row in data}
        assert rows["A-1"][header.index("maturity_score")] == 3
        assert rows["B-1"][header.index("maturity_score")] is None


@pytest.mark.django_db
class TestReaderVisibilityInExports:
    """Exports carry only the score layers the requesting reader may see."""

    @pytest.fixture
    def respondent_reader(self, monkeypatch, layered_audit):
        monkeypatch.setattr(
            "core.views.audit_reader_role", lambda user, audit: "respondent"
        )
        layered_audit.field_visibility = {
            **layered_audit.field_visibility,
            "documentation_score": AUDITOR_ONLY,
        }
        layered_audit.save()
        return layered_audit

    def _csv_header(self, client, audit):
        url = reverse(
            "compliance-assessments-compliance-assessment-csv",
            kwargs={"pk": str(audit.pk)},
        )
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        return response.content.decode("utf-8-sig").splitlines()[0].split(";")

    def _xlsx_header(self, client, audit):
        url = reverse("compliance-assessments-xlsx", kwargs={"pk": str(audit.pk)})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        return next(load_workbook(io.BytesIO(response.content)).active.values)

    def test_csv_drops_documentation_and_maturity(
        self,
        admin_client,  # noqa: F811
        respondent_reader,
    ):
        header = self._csv_header(admin_client, respondent_reader)

        assert "score" in header
        assert "documentation_score" not in header
        assert "maturity_score" not in header

    def test_xlsx_drops_documentation_and_maturity(
        self,
        admin_client,  # noqa: F811
        respondent_reader,
    ):
        header = self._xlsx_header(admin_client, respondent_reader)

        assert "score" in header
        assert "documentation_score" not in header
        assert "maturity_score" not in header

    def test_respondent_who_sees_documentation_keeps_it(
        self,
        admin_client,  # noqa: F811
        respondent_reader,
    ):
        respondent_reader.field_visibility = {
            **respondent_reader.field_visibility,
            "documentation_score": EVERYONE_EDIT,
        }
        respondent_reader.save()

        assert self._csv_header(admin_client, respondent_reader)[-2:] == [
            "documentation_score",
            "maturity_score",
        ]
        assert self._xlsx_header(admin_client, respondent_reader)[-1] == (
            "maturity_score"
        )

    def test_word_report_headlines_the_implementation_score(
        self,
        monkeypatch,
        admin_client,  # noqa: F811
        respondent_reader,
    ):
        import core.views

        captured = {}
        render = core.views.render_docx_report

        def capture(doc, context):
            captured.update(context)
            return render(doc, context)

        monkeypatch.setattr("core.views.render_docx_report", capture)
        url = reverse(
            "compliance-assessments-word-report",
            kwargs={"pk": str(respondent_reader.pk)},
        )

        assert admin_client.get(url).status_code == status.HTTP_200_OK
        assert captured["score_layers"] == ["implementation_score"]
        b = captured["category_scores"][CAT_B]
        assert "maturity_score" not in b and "documentation_score" not in b
        assert b["average_score"] == 5


@pytest.mark.django_db
class TestWordReport:
    """The default Word templates print the category scores next to the radar."""

    def _score_table(self, client, audit):
        url = reverse(
            "compliance-assessments-word-report", kwargs={"pk": str(audit.pk)}
        )
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        doc = Document(io.BytesIO(b"".join(response.streaming_content)))
        tables = [
            [[cell.text for cell in row.cells] for row in table.rows]
            for table in doc.tables
        ]
        return next(t for t in tables if t[0][0] in ("Category", "Catégorie"))

    def test_shows_the_three_scores(
        self,
        admin_client,  # noqa: F811
        layered_audit,
    ):
        table = self._score_table(admin_client, layered_audit)
        rows = {
            next(
                (k for k in ("Category A", "Category B", "Overall") if k in row[0]),
                row[0],
            ): row[1:]
            for row in table[1:]
        }
        overall = layered_audit.get_global_score()

        assert table[0] == [
            "Category",
            "Implementation",
            "Documentation",
            "Maturity",
            "Scored",
            "Items",
        ]
        assert rows["Category A"] == ["3", "3", "3", "2", "2"]
        assert rows["Category B"] == ["5", "3", "4", "1", "1"]
        assert rows["Overall"][:3] == [
            f"{round_score(overall[layer]):g}"
            for layer in (
                "implementation_score",
                "documentation_score",
                "maturity_score",
            )
        ]

    def test_follows_the_documentation_first_setting(
        self,
        admin_client,  # noqa: F811
        layered_audit,
    ):
        settings, _ = GlobalSettings.objects.get_or_create(name="general")
        settings.value = {**(settings.value or {}), "documentation_score_first": True}
        settings.save()

        header = self._score_table(admin_client, layered_audit)[0]

        assert header[1:4] == ["Documentation", "Implementation", "Maturity"]

    def test_without_documentation_score_shows_the_average(
        self,
        admin_client,  # noqa: F811
        layered_audit,
    ):
        layered_audit.show_documentation_score = False
        layered_audit.save()

        table = self._score_table(admin_client, layered_audit)
        rows = {
            next(
                (k for k in ("Category A", "Category B", "Overall") if k in row[0]),
                row[0],
            ): row[1:]
            for row in table[1:]
        }

        assert table[0] == ["Category", "Average", "Scored", "Items"]
        assert rows["Category B"] == ["5", "1", "1"]

    def test_french_template(
        self,
        admin_client,  # noqa: F811
        layered_audit,
    ):
        admin = User.objects.get(email="admin@audit-word-export-tests.com")
        admin.preferences = {**(admin.preferences or {}), "lang": "fr"}
        admin.save()

        table = self._score_table(admin_client, layered_audit)

        assert table[0] == [
            "Catégorie",
            "Implémentation",
            "Documentation",
            "Maturité",
            "Évalués",
            "Éléments",
        ]
        assert table[-1][0] == "Global"
