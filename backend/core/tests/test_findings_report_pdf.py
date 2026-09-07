"""The findings report, rendered by Typst."""

import pymupdf
import pytest
from django.urls import reverse
from rest_framework import status as http

from core.generators import findings_assessment_context
from core.models import Finding, FilteringLabel, FindingsAssessment
from core.typst_render import TEMPLATE_DIR, localized_template, render_pdf
from core.tests.test_audit_word_export import (  # noqa: F401
    admin_client,
    app_config,
)
from iam.models import Folder


@pytest.fixture
def assessment(app_config):  # noqa: F811
    folder = Folder.objects.create(
        name="Findings report domain", content_type=Folder.ContentType.DOMAIN
    )
    return FindingsAssessment.objects.create(name="Q3 pentest", folder=folder)


def _findings(assessment_obj, severities, rich=False):
    """`rich` populates every optional block; the default fixture left labels,
    controls and evidences empty, so those branches were never compiled."""
    made = []
    for i, severity in enumerate(severities):
        made.append(
            Finding.objects.create(
                findings_assessment=assessment_obj,
                folder=assessment_obj.folder,
                ref_id=f"F-{i + 1:03d}",
                name=f"Finding {i + 1}",
                description="Observed during the review.",
                severity=severity,
                status="identified",
                observation="Confirmed with the owner." if rich else "",
            )
        )
    if rich:
        for finding in made:
            finding.filtering_labels.add(
                FilteringLabel.objects.create(label=f"tag-{finding.ref_id}")
            )
    return made


def _render(assessment_obj, lang="en"):
    findings = Finding.objects.filter(findings_assessment=assessment_obj).order_by(
        "ref_id"
    )
    payload = findings_assessment_context(assessment_obj, findings, lang)
    pdf = render_pdf(localized_template("findings_report", lang), payload)
    return pdf, payload


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_renders_in_each_locale(assessment, lang):
    _findings(assessment, [4, 2])
    pdf, _ = _render(assessment, lang)
    assert pdf[:5] == b"%PDF-"


@pytest.mark.django_db
def test_findings_are_grouped_by_severity_worst_first(assessment):
    _findings(assessment, [1, 4, 2, 4])
    _, payload = _render(assessment)
    assert [g["severity_key"] for g in payload["groups"]] == [
        "critical",
        "medium",
        "low",
    ]
    assert len(payload["groups"][0]["findings"]) == 2


@pytest.mark.django_db
def test_empty_severities_are_omitted(assessment):
    _findings(assessment, [3])
    _, payload = _render(assessment)
    assert [g["severity_key"] for g in payload["groups"]] == ["high"]
    # ... but the severity chart still lists every level, including the zeros.
    assert len(payload["severity_rows"]) == 6


@pytest.mark.django_db
def test_many_findings_do_not_get_a_page_each(assessment):
    """The HTML original forced a page break between findings; 30 of them should
    not become 30 pages."""
    _findings(assessment, [2] * 30)
    pdf, _ = _render(assessment)
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    assert doc.page_count < 12, f"{doc.page_count} pages for 30 findings"


@pytest.mark.django_db
def test_cover_carries_traceability(assessment):
    _findings(assessment, [2])
    pdf, payload = _render(assessment)
    assert payload["generated_at"]
    cover = pymupdf.open(stream=pdf, filetype="pdf")[0].get_text()
    assert str(assessment.id) in cover


@pytest.mark.django_db
def test_open_and_closed_counts_split_the_total(assessment):
    findings = _findings(assessment, [2, 2, 2])
    findings[0].status = "closed"
    findings[0].save()

    _, payload = _render(assessment)
    metrics = payload["metrics"]
    assert metrics["open"] + metrics["closed"] == metrics["total"]
    assert metrics["closed"] == 1


@pytest.mark.django_db
def test_endpoint_returns_a_pdf(admin_client, assessment):  # noqa: F811
    _findings(assessment, [3])
    url = reverse("findings-assessments-pdf", kwargs={"pk": str(assessment.pk)})
    response = admin_client.get(url)
    assert response.status_code == http.HTTP_200_OK
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"


def test_locale_fallback_is_whole_document():
    assert localized_template("findings_report", "de") == "findings_report_en.typ"
    assert localized_template("findings_report", "fr") == "findings_report_fr.typ"


def test_templates_avoid_auto_column_sizing():
    """`auto` overflows and overlaps once content is wider than the page."""
    for name in ("findings_report_en.typ", "findings_report_fr.typ"):
        src = (TEMPLATE_DIR / name).read_text()
        assert "columns: (auto, 1fr, auto, 1fr, auto, 1fr)" not in src


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_optional_block_compiles(assessment, lang):
    """Optional blocks are only compiled when their data is present: a fixture
    with empty labels never reaches the label branch, which is how a broken
    method chain in it shipped past the other tests."""
    _findings(assessment, [4, 2], rich=True)
    pdf, payload = _render(assessment, lang)
    assert pdf[:5] == b"%PDF-"

    finding = payload["groups"][0]["findings"][0]
    assert finding["labels"], "fixture must exercise the label branch"
    assert finding["observation"], "fixture must exercise the observation branch"

    text = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    assert "tag-F-001" in text


def test_no_method_chain_is_broken_across_lines():
    """In content mode a newline after `#name` ends the expression; the remaining
    lines are read as text, so a string like "#dbeafe" becomes a variable."""
    import re

    for template in sorted(TEMPLATE_DIR.glob("*.typ")):
        lines = template.read_text().split("\n")
        for number, line in enumerate(lines[:-1], start=1):
            if re.search(r"#[A-Za-z_][A-Za-z0-9_.-]*\s*$", line) and lines[
                number
            ].lstrip().startswith("."):
                raise AssertionError(
                    f"{template.name}:{number} chain broken across lines: {line.strip()!r}"
                )


@pytest.mark.django_db
def test_actors_are_named_and_observations_are_whole(assessment):
    """Carried over from PR #4768, which fixed these on the HTML template this
    report replaced: actors render as names (not emails) and observations are
    not truncated."""
    from iam.models import User

    author = User.objects.create_user(
        "author@tests.com", first_name="Ada", last_name="Author"
    )
    owner = User.objects.create_user(
        "owner@tests.com", first_name="Olu", last_name="Owner"
    )
    assessment.authors.add(author.actor)

    long_observation = "word " * 60
    finding = _findings(assessment, [3])[0]
    finding.observation = long_observation
    finding.save()
    finding.owner.add(owner.actor)

    pdf, payload = _render(assessment)
    assert payload["assessment"]["authors"] == "Ada Author"
    assert payload["groups"][0]["findings"][0]["owners"] == "Olu Owner"

    text = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    assert "…" not in text, "observation was truncated"
    assert text.count("word") >= 60, "observation was cut short"
