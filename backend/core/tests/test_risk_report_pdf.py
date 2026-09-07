"""The risk assessment report, rendered by Typst."""

import pymupdf
import pytest

from core.generators import risk_assessment_context
from core.typst_render import TEMPLATE_DIR, localized_template, render_pdf


class FakeMatrix:
    """A 2x3 matrix: two probability rows, three impact columns."""

    RISK = [
        {"name": "Low", "hexcolor": "#22c55e"},
        {"name": "Medium", "hexcolor": "#eab308"},
        {"name": "High", "hexcolor": "#ef4444"},
    ]

    def __str__(self):
        return "Test matrix 2x3"

    def parse_json_translated(self):
        return {
            "probability": [
                {"name": "Unlikely", "description": ""},
                {"name": "Likely", "description": ""},
            ],
            "impact": [
                {"name": "Minor", "description": ""},
                {"name": "Moderate", "description": ""},
                {"name": "Severe", "description": ""},
            ],
        }

    def render_grid_as_colors(self):
        # row 0 = lowest probability
        return [
            [self.RISK[0], self.RISK[0], self.RISK[1]],
            [self.RISK[1], self.RISK[2], self.RISK[2]],
        ]


class FakeAssessment:
    id = "11111111-1111-1111-1111-111111111111"
    name = "Quarterly review"
    version = "1.2"
    description = "Scope covers the payment platform."
    folder = "Group / IT"
    perimeter = "Payments"
    eta = None
    due_date = None
    risk_matrix = FakeMatrix()
    status = "in_progress"

    class _Actors:
        @staticmethod
        def all():
            return ["Ada Author"]

    authors = _Actors()
    reviewers = _Actors()


def _clusters(current=None, residual=None, inherent=None):
    def build(marks):
        grid = [[set(), set(), set()], [set(), set(), set()]]
        for (r, c), refs in (marks or {}).items():
            grid[r][c] = set(refs)
        return grid

    clusters = {"current": build(current), "residual": build(residual)}
    if inherent is not None:
        clusters["inherent"] = build(inherent)
    return clusters


class FakeM2M:
    def __init__(self, names):
        self._names = names

    def all(self):
        return [
            type("C", (), {"name": n, "get_name_translated": n})() for n in self._names
        ]


class FakeScenario:
    ref_id = "R.07"
    name = "Supplier outage"
    description = "The supplier cannot deliver."
    treatment = "cancelled"
    justification = ""
    strength_of_knowledge = "Medium"

    def __init__(self, existing=(), extra=()):
        self.threats = FakeM2M(["Outage"])
        self.assets = FakeM2M(["Order platform"])
        self.qualifications = FakeM2M(["Availability"])
        self.existing_applied_controls = FakeM2M(existing)
        self.applied_controls = FakeM2M(extra)

    def get_inherent_risk(self):
        return {"name": "High", "hexcolor": "#ef4444"}

    get_current_risk = get_inherent_risk
    get_residual_risk = get_inherent_risk


def _render(
    clusters,
    swap=False,
    flip=False,
    lang="en",
    scenarios=(),
    standard="ISO",
    risk_category_label=False,
):
    payload = risk_assessment_context(
        FakeAssessment(),
        scenarios,
        clusters,
        swap,
        flip,
        lang,
        standard,
        risk_category_label,
    )
    pdf = render_pdf(localized_template("risk_report", lang), payload)
    return pdf, payload


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_renders_in_each_locale(lang):
    pdf, _ = _render(_clusters(current={(1, 2): ["R.01"]}), lang=lang)
    assert pdf[:5] == b"%PDF-"


def test_worst_row_is_on_top_by_default():
    """Clusters arrive lowest-probability-first; a matrix reads worst-first."""
    _, payload = _render(_clusters())
    view = payload["matrix_views"][0]
    assert [row["name"] for row in view["y_axis"]] == ["Likely", "Unlikely"]
    assert [c["name"] for c in view["cells"][0]] == ["Medium", "High", "High"]


def test_flip_vertical_keeps_the_source_order():
    _, payload = _render(_clusters(), flip=True)
    view = payload["matrix_views"][0]
    assert [row["name"] for row in view["y_axis"]] == ["Unlikely", "Likely"]


def test_swap_axes_transposes_the_grid_and_the_labels():
    _, payload = _render(_clusters(), swap=True, flip=True)
    view = payload["matrix_views"][0]
    assert [row["name"] for row in view["y_axis"]] == ["Minor", "Moderate", "Severe"]
    assert [col["name"] for col in view["x_axis"]] == ["Unlikely", "Likely"]
    assert len(view["cells"]) == 3 and len(view["cells"][0]) == 2


def test_scenario_refs_follow_their_cell_through_the_transform():
    marks = {(1, 2): ["R.07"]}
    _, plain = _render(_clusters(current=marks))
    _, swapped = _render(_clusters(current=marks), swap=True, flip=True)

    def find(payload):
        view = next(v for v in payload["matrix_views"] if v["key"] == "current")
        return [
            (r, c)
            for r, row in enumerate(view["cells"])
            for c, cell in enumerate(row)
            if cell["refs"] == ["R.07"]
        ]

    assert len(find(plain)) == 1
    assert len(find(swapped)) == 1
    assert find(plain) != find(swapped), "the transform must move the cell"


def test_inherent_view_appears_only_when_the_flag_supplied_it():
    _, without = _render(_clusters())
    assert [v["key"] for v in without["matrix_views"]] == ["current", "residual"]

    _, with_inherent = _render(_clusters(inherent={}))
    assert [v["key"] for v in with_inherent["matrix_views"]] == [
        "inherent",
        "current",
        "residual",
    ]


def test_cover_carries_traceability():
    pdf, payload = _render(_clusters())
    assert payload["generated_at"]
    cover = pymupdf.open(stream=pdf, filetype="pdf")[0].get_text()
    assert FakeAssessment.id in cover


def test_locale_fallback_is_whole_document():
    assert localized_template("risk_report", "de") == "risk_report_en.typ"
    assert localized_template("risk_report", "fr") == "risk_report_fr.typ"


def test_the_four_matrix_html_variants_are_gone():
    snippets = TEMPLATE_DIR.parent / "templates" / "snippets"
    for name in (
        "risk_matrix.html",
        "risk_matrix_swapaxes.html",
        "risk_matrix_vflip.html",
        "risk_matrix_swapaxes_vflip.html",
    ):
        assert not (snippets / name).exists(), f"{name} survived the migration"


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_existing_and_extra_controls_are_both_listed(lang):
    """`existing_applied_controls` and `applied_controls` are distinct relations;
    the deprecated free-text `existing_controls` field is not rendered."""
    scenario = FakeScenario(existing=["Backup power"], extra=["Second supplier"])
    pdf, payload = _render(_clusters(), lang=lang, scenarios=[scenario])

    row = payload["scenarios"][0]
    assert row["existing_controls"] == ["Backup power"]
    assert row["controls"] == ["Second supplier"]

    text = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    assert "Backup power" in text
    assert "Second supplier" in text


def test_control_rows_are_omitted_when_empty():
    _, payload = _render(_clusters(), scenarios=[FakeScenario()])
    row = payload["scenarios"][0]
    assert row["existing_controls"] == [] and row["controls"] == []


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_inherent_is_omitted_when_the_flag_is_off(lang):
    """The flag reaches the builder as the presence of the inherent cluster; it must
    gate the per-scenario level as well as the matrix view."""
    scenario = FakeScenario()

    _, off = _render(_clusters(), lang=lang, scenarios=[scenario])
    assert off["include_inherent"] is False
    assert "inherent" not in off["scenarios"][0]
    assert [v["key"] for v in off["matrix_views"]] == ["current", "residual"]

    _, on = _render(_clusters(inherent={}), lang=lang, scenarios=[scenario])
    assert on["include_inherent"] is True
    assert "inherent" in on["scenarios"][0]
    assert [v["key"] for v in on["matrix_views"]][0] == "inherent"


def test_scenario_rows_follow_the_risk_story_order():
    """inherent -> existing controls -> current -> extra controls -> residual."""
    scenario = FakeScenario(existing=["Backup power"], extra=["Second supplier"])
    pdf, _ = _render(_clusters(inherent={}), scenarios=[scenario])
    full = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    # Several of these labels also head a summary-table column, so look only at
    # the detail section.
    text = full[full.index("Risk scenarios") :]

    order = [
        "Description",
        "Qualifications",
        "Assets",
        "Threats",
        "Inherent level",
        "Existing controls",
        "Current level",
        "Extra controls",
        "Residual level",
        "Strength of knowledge",
        "Treatment",
    ]
    positions = [text.index(label) for label in order]
    assert positions == sorted(positions), "scenario fields are out of order"


def test_empty_rows_are_omitted():
    _, payload = _render(_clusters(), scenarios=[FakeScenario()])
    pdf, _ = _render(_clusters(), scenarios=[FakeScenario()])
    text = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    assert "Existing controls" not in text
    assert "Extra controls" not in text


def _text(pdf):
    return "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))


def test_label_standard_switches_the_axis_titles():
    """`risk_matrix_labels`: ISO says Impact, EBIOS says Severity."""
    iso, _ = _render(_clusters(), scenarios=[FakeScenario()])
    ebios, _ = _render(_clusters(), scenarios=[FakeScenario()], standard="EBIOS")

    assert "Impact" in _text(iso) and "Severity" not in _text(iso)
    assert "Severity" in _text(ebios) and "Impact" not in _text(ebios)


def test_axis_titles_follow_the_swap():
    _, plain = _render(_clusters())
    _, swapped = _render(_clusters(), swap=True)
    assert (plain["matrix_views"][0]["y_type"], plain["matrix_views"][0]["x_type"]) == (
        "probability",
        "impact",
    )
    assert (
        swapped["matrix_views"][0]["y_type"],
        swapped["matrix_views"][0]["x_type"],
    ) == ("impact", "probability")


def test_use_risk_category_label_renames_qualifications():
    scenario = FakeScenario()
    off, _ = _render(_clusters(), scenarios=[scenario])
    on, _ = _render(_clusters(), scenarios=[scenario], risk_category_label=True)

    assert "Qualifications" in _text(off)
    assert "Risk categories" in _text(on)
    assert "Qualifications" not in _text(on)


def test_summary_table_lists_every_scenario():
    scenarios = [FakeScenario(), FakeScenario()]
    pdf, payload = _render(_clusters(inherent={}), scenarios=scenarios)
    text = _text(pdf)
    assert "Scenario summary" in text
    for column in ("Ref.", "Name", "Description", "Inherent", "Current", "Residual"):
        assert column in text, f"summary table is missing {column}"


def test_summary_table_drops_the_inherent_column_with_the_flag():
    pdf, _ = _render(_clusters(), scenarios=[FakeScenario()])
    text = _text(pdf)
    assert "Scenario summary" in text
    assert "Inherent" not in text


def test_summary_rows_link_to_their_scenario_block():
    """Each ref in the summary is an internal jump to the detail block below."""
    scenarios = [FakeScenario(), FakeScenario()]
    pdf, _ = _render(_clusters(), scenarios=scenarios)

    doc = pymupdf.open(stream=pdf, filetype="pdf")
    internal = [
        link
        for page in doc
        for link in page.get_links()
        if link["kind"] == pymupdf.LINK_GOTO
    ]
    assert len(internal) == len(scenarios), "one link per summary row"
    detail_page = next(
        i for i, page in enumerate(doc) if "Strength of knowledge" in page.get_text()
    )
    assert all(link["page"] == detail_page for link in internal)


def test_summary_table_carries_the_treatment():
    pdf, _ = _render(_clusters(), scenarios=[FakeScenario()])
    header = pymupdf.open(stream=pdf, filetype="pdf")[
        next(
            i
            for i, page in enumerate(pymupdf.open(stream=pdf, filetype="pdf"))
            if "Scenario summary" in page.get_text()
        )
    ].get_text()
    assert "Treatment" in header


@pytest.mark.parametrize("lang,expected", [("en", "Cancelled"), ("fr", "Annulé")])
def test_treatment_is_localised_by_the_template(lang, expected):
    """`get_treatment_display()` reads Django's gettext catalog, which is fr-only
    and incomplete — "cancelled" came through untranslated. The raw key travels
    instead and each locale template names it."""
    _, payload = _render(_clusters(), lang=lang, scenarios=[FakeScenario()])
    assert payload["scenarios"][0]["treatment_key"] == "cancelled"
    assert "treatment" not in payload["scenarios"][0]

    pdf, _ = _render(_clusters(), lang=lang, scenarios=[FakeScenario()])
    assert expected in _text(pdf)


@pytest.mark.parametrize("lang,expected", [("en", "In progress"), ("fr", "En cours")])
def test_assessment_status_is_localised_by_the_template(lang, expected):
    pdf, payload = _render(_clusters(), lang=lang)
    assert payload["assessment"]["status_key"] == "in_progress"
    assert "status" not in payload["assessment"]
    assert expected in _text(pdf)
