"""The incident report, rendered by Typst."""

from datetime import datetime, timezone

import pymupdf
import pytest
from django.urls import reverse
from rest_framework import status as http

from core.generators import incident_context
from core.models import Incident, Terminology, TimelineEntry
from core.typst_render import TEMPLATE_DIR, localized_template, render_pdf
from core.tests.test_audit_word_export import (  # noqa: F401
    admin_client,
    app_config,
)
from iam.models import Folder

ENTRY_TYPES = [
    "detection",
    "mitigation",
    "observation",
    "severity_changed",
    "status_changed",
]


@pytest.fixture
def incident(app_config):  # noqa: F811
    folder = Folder.objects.create(
        name="Incident report domain", content_type=Folder.ContentType.DOMAIN
    )
    return Incident.objects.create(
        name="Ransomware on the file server",
        ref_id="INC-2026-014",
        folder=folder,
        description="Encrypted shares detected on the primary file server.",
    )


def _entries(incident_obj, types, rich=False):
    made = []
    for i, entry_type in enumerate(types):
        made.append(
            TimelineEntry.objects.create(
                incident=incident_obj,
                folder=incident_obj.folder,
                entry=f"Event {i + 1}",
                entry_type=entry_type,
                timestamp=datetime(2026, 3, 1, 9, i % 60, tzinfo=timezone.utc),
                observation="Confirmed by the on-call engineer." if rich else "",
            )
        )
    return made


def _render(incident_obj, lang="en"):
    entries = TimelineEntry.objects.filter(incident=incident_obj).order_by("timestamp")
    payload = incident_context(incident_obj, entries, lang)
    pdf = render_pdf(localized_template("incident_report", lang), payload)
    return pdf, payload


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_renders_in_each_locale(incident, lang):
    _entries(incident, ["detection", "mitigation"])
    pdf, _ = _render(incident, lang)
    assert pdf[:5] == b"%PDF-"


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_entry_type_and_optional_block_compiles(incident, lang):
    """Each entry type takes its own branch for label and accent colour, and the
    optional blocks only compile when their data exists — the trap that let a
    broken method chain ship in the findings report."""
    incident.resolution = "Restored from backup; credentials rotated."
    incident.save()
    # Qualifications are `Terminology` rows scoped by `field_path`; startup seeds
    # them, and name+field_path is unique, so reuse rather than create.
    # Uniqueness is scoped, and startup seeds the standard set, so use a name
    # that cannot collide with it.
    incident.qualifications.add(
        Terminology.objects.create(
            name="Report-test qualification",
            field_path=Terminology.FieldPath.QUALIFICATIONS,
            is_visible=True,
        )
    )
    _entries(incident, ENTRY_TYPES, rich=True)

    pdf, payload = _render(incident, lang)
    assert pdf[:5] == b"%PDF-"
    assert {e["type_key"] for e in payload["timeline"]} == set(ENTRY_TYPES)
    assert payload["incident"]["qualifications"], "scope branch must be exercised"
    assert payload["incident"]["resolution"], "resolution branch must be exercised"


@pytest.mark.django_db
def test_timeline_is_chronological_and_counted(incident):
    _entries(incident, ["observation", "detection", "detection", "mitigation"])
    _, payload = _render(incident)
    stamps = [e["timestamp"] for e in payload["timeline"]]
    assert stamps == sorted(stamps)
    assert payload["counts"] == {"total": 4, "detection": 2, "mitigation": 1}


@pytest.mark.django_db
def test_scope_sections_are_omitted_when_empty(incident):
    _entries(incident, ["detection"])
    pdf, payload = _render(incident)
    assert payload["incident"]["assets"] == []
    text = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    assert "Affected assets" not in text


@pytest.mark.django_db
def test_cover_carries_traceability(incident):
    _entries(incident, ["detection"])
    pdf, payload = _render(incident)
    assert payload["generated_at"]
    assert str(incident.id) in pymupdf.open(stream=pdf, filetype="pdf")[0].get_text()


@pytest.mark.django_db
def test_endpoint_returns_a_pdf(admin_client, incident):  # noqa: F811
    _entries(incident, ["detection"])
    url = reverse("incidents-pdf", kwargs={"pk": str(incident.pk)})
    response = admin_client.get(url)
    assert response.status_code == http.HTTP_200_OK
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"


def test_locale_fallback_is_whole_document():
    assert localized_template("incident_report", "de") == "incident_report_en.typ"
    assert localized_template("incident_report", "fr") == "incident_report_fr.typ"


def test_no_weasyprint_template_remains():
    assert not (
        TEMPLATE_DIR.parent / "templates" / "core" / "incident_pdf.html"
    ).exists()
