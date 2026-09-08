"""The action plan, rendered by Typst — one document serving two parents."""

from uuid import uuid4

import pymupdf
import pytest

from core.generators import action_plan_context
from core.models import AppliedControl, RequirementAssessment
from core.typst_render import TEMPLATE_DIR, localized_template, render_pdf
from core.tests.test_audit_word_export import (  # noqa: F401
    admin_client,
    app_config,
    audit,
)


def _controls(audit_obj, statuses):
    """`AppliedControl.status` is NOT NULL; "no status" is the `--` sentinel."""
    ras = list(RequirementAssessment.objects.filter(compliance_assessment=audit_obj))
    made = []
    for i, status in enumerate(statuses):
        control = AppliedControl.objects.create(
            name=f"Control {uuid4().hex[:8]}",
            description="Agreed remediation.",
            folder=audit_obj.folder,
            status=status,
        )
        control.requirement_assessments.set([ras[i % len(ras)]])
        made.append(control)
    return made


def _render(assessment, controls, lang="en", linked=None):
    payload = action_plan_context(assessment, controls, lang, linked or {})
    pdf = render_pdf(localized_template("action_plan", lang), payload)
    return pdf, payload


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_renders_in_each_locale(audit, lang):
    pdf, _ = _render(audit, _controls(audit, ["to_do", "active"]), lang=lang)
    assert pdf[:5] == b"%PDF-"


@pytest.mark.django_db
def test_controls_are_grouped_by_status(audit):
    controls = _controls(audit, ["to_do", "to_do", "active", "--"])
    _, payload = _render(audit, controls)

    by_key = {g["status_key"]: g for g in payload["groups"]}
    assert set(by_key) == {"to_do", "active", "--"}
    assert len(by_key["to_do"]["controls"]) == 2
    assert "status" not in by_key["--"], "the raw key travels; the template names it"
    assert payload["total"] == 4


@pytest.mark.django_db
def test_empty_statuses_are_omitted(audit):
    _, payload = _render(audit, _controls(audit, ["to_do"]))
    assert [g["status_key"] for g in payload["groups"]] == ["to_do"]


@pytest.mark.django_db
def test_subject_omits_framework_when_the_parent_has_none(audit):
    """A risk assessment has no framework; the row must not render empty."""

    class ParentWithoutFramework:
        id = audit.id
        name = "Quarterly risk review"
        version = "2.0"
        folder = audit.folder
        perimeter = None

    _, payload = _render(ParentWithoutFramework(), _controls(audit, ["to_do"]))
    assert payload["subject"]["framework"] == ""

    pdf, _ = _render(ParentWithoutFramework(), _controls(audit, ["active"]))
    text = pymupdf.open(stream=pdf, filetype="pdf")[0].get_text()
    assert "Framework" not in text


@pytest.mark.django_db
def test_linked_items_reach_the_last_column(audit):
    controls = _controls(audit, ["to_do"])
    linked = {controls[0].id: ["REQ-1.1 - First requirement"]}
    pdf, _ = _render(audit, controls, linked=linked)
    text = pymupdf.open(stream=pdf, filetype="pdf")[0].get_text()
    assert "REQ-1.1" in text


@pytest.mark.django_db
def test_cover_carries_traceability(audit):
    pdf, payload = _render(audit, _controls(audit, ["to_do"]))
    assert payload["generated_at"]
    text = pymupdf.open(stream=pdf, filetype="pdf")[0].get_text()
    assert str(audit.id) in text


def test_locale_fallback_is_whole_document():
    assert localized_template("action_plan", "de") == "action_plan_en.typ"
    assert localized_template("action_plan", "fr") == "action_plan_fr.typ"


@pytest.mark.django_db
def test_columns_are_fixed_fractions_not_auto(audit):
    """`auto` sizing overflows the page and overlaps neighbouring cells once the
    content is wider than the paper; fractions always sum to the available width."""
    for template in ("action_plan_en.typ", "action_plan_fr.typ"):
        src = (TEMPLATE_DIR / template).read_text()
        spec = src[
            src.index("#let columns-spec = (") : src.index(
                ")", src.index("#let columns-spec = (")
            )
        ]
        assert "auto" not in spec, f"{template} reintroduced auto column sizing"
        assert spec.count("fr,") == 6


@pytest.mark.django_db
def test_column_titles_repeat_on_continuation_pages(audit):
    """A long group spans pages; every page must carry the column titles."""
    controls = _controls(audit, ["to_do"] * 60)
    pdf, _ = _render(audit, controls)
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    assert doc.page_count > 1, "not enough rows to spill onto a second page"
    assert "Description" in doc[1].get_text()


@pytest.mark.django_db
def test_owner_replaces_the_dropped_columns(audit):
    control = _controls(audit, ["to_do"])[0]
    _, payload = _render(audit, [control])
    row = payload["groups"][0]["controls"][0]
    assert "owner" in row
    for dropped in ("csf_function", "effort", "cost", "expiry_date"):
        assert dropped not in row, f"{dropped} does not fit an A4 action plan"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "lang,status,category",
    [("en", "To do", "Technical"), ("fr", "À faire", "Technique")],
)
def test_status_and_category_are_localised_by_the_template(
    audit, lang, status, category
):
    """`Status.choices` and `CATEGORY` read Django's gettext catalog, which is
    fr-only and incomplete; the raw keys travel and each locale names them."""
    control = _controls(audit, ["to_do"])[0]
    control.category = "technical"
    control.save()

    pdf, payload = _render(audit, [control], lang=lang)
    row = payload["groups"][0]["controls"][0]
    assert row["category_key"] == "technical"
    assert "category" not in row

    text = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    assert status in text
    assert category in text


@pytest.mark.django_db
def test_unset_status_group_is_named_by_the_template(audit):
    pdf, _ = _render(audit, _controls(audit, ["--"]))
    text = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    assert "No status" in text


def test_every_status_has_a_fill_and_a_label_in_each_locale():
    """A status missing from either map renders grey and unnamed — the `degraded`
    gap review caught. Cross-check both against the model."""
    import re

    from core.generators import _ACTION_PLAN_STATUS_FILLS

    statuses = {value for value, _ in AppliedControl.Status.choices}
    assert statuses <= set(_ACTION_PLAN_STATUS_FILLS), (
        f"no fill for {statuses - set(_ACTION_PLAN_STATUS_FILLS)}"
    )

    for name in ("action_plan_en.typ", "action_plan_fr.typ"):
        src = (TEMPLATE_DIR / name).read_text()
        block = src[src.index("#let status-label = (") :]
        block = block[: block.index(")")]
        labelled = set(re.findall(r"^\s*([a-z_]+):", block, re.M))
        # `--` is named by the template's own default, not a key.
        missing = {s for s in statuses if s != "--"} - labelled
        assert not missing, f"{name} has no label for {missing}"
