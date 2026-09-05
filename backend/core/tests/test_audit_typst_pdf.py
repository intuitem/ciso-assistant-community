"""Smoke + redaction tests for the Typst audit posture PDF."""

from django.urls import reverse
from rest_framework import status

import pymupdf
import pytest

from core.generators import audit_context_for_typst, gen_audit_context
from core.models import RequirementAssessment
from core.typst_render import render_pdf
from core.helpers import (
    annotate_tree_with_aggregated_scores,
    get_sorted_requirement_nodes,
)
from core.models import RequirementNode

from core.tests.test_audit_word_export import (  # noqa: F401  (fixtures)
    admin_client,
    app_config,
    audit,
)


def _context(audit_obj):
    tree = get_sorted_requirement_nodes(
        RequirementNode.objects.filter(framework=audit_obj.framework).all(),
        RequirementAssessment.objects.filter(compliance_assessment=audit_obj).all(),
        audit_obj.max_score
        if audit_obj.max_score is not None
        else audit_obj.framework.max_score,
        audit_obj.min_score
        if audit_obj.min_score is not None
        else audit_obj.framework.min_score,
    )
    annotate_tree_with_aggregated_scores(tree, audit_obj)
    return gen_audit_context(audit_obj.id, tree, "en")


def _render(audit_obj, role, profile="full"):
    payload, images = audit_context_for_typst(
        _context(audit_obj), audit_obj, role, "en", profile
    )
    return render_pdf("audit_report.typ", payload, images=images), payload


@pytest.mark.django_db
def test_renders_a_pdf_for_the_auditor(audit):
    pdf, _ = _render(audit, "auditor")
    assert pdf[:5] == b"%PDF-", "output is not a PDF"
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    assert doc.page_count >= 2
    assert audit.name in doc[0].get_text()


@pytest.mark.django_db
def test_respondent_render_omits_hidden_fields(audit):
    _, payload = _render(audit, "respondent")
    hidden = set(payload["hidden_fields"])
    assert hidden, "expected the default visibility map to hide something"
    for ra in payload["requirement_assessments"]:
        assert not (hidden & set(ra)), f"hidden field leaked into payload: {ra}"


@pytest.mark.django_db
def test_respondent_pdf_text_has_no_auditor_only_values(audit):
    reqs = list(RequirementAssessment.objects.filter(compliance_assessment=audit))
    for req in reqs:
        req.observation = "canary-observation"
        req.save()

    pdf, payload = _render(audit, "respondent")
    text = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    assert "canary-observation" in text, "sanity: visible content must be rendered"
    if "status" in set(payload["hidden_fields"]):
        assert "Progress:" not in text
    if "score" in set(payload["hidden_fields"]):
        assert "Score:" not in text


@pytest.mark.django_db
def test_posture_pdf_endpoint_returns_pdf(admin_client, audit):
    url = reverse("compliance-assessments-posture-pdf", kwargs={"pk": str(audit.pk)})
    response = admin_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"] == "application/pdf"
    assert "_full.pdf" in response["Content-Disposition"]
    assert response.content[:5] == b"%PDF-"


@pytest.mark.django_db
def test_posture_pdf_endpoint_rejects_anonymous(audit):
    from rest_framework.test import APIClient

    url = reverse("compliance-assessments-posture-pdf", kwargs={"pk": str(audit.pk)})
    response = APIClient().get(url)
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )


@pytest.mark.django_db
def test_attestation_profile_renders_and_drops_measurement(audit):
    pdf, payload = _render(audit, "auditor", profile="attestation")
    assert pdf[:5] == b"%PDF-"

    text = "".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    assert "Signatures" in text, "attestation must carry a signature block"

    # Dropped by the profile even though the reader is an auditor: the values must
    # be absent from the payload, not merely hidden by a template flag.
    for ra in payload["requirement_assessments"]:
        assert "score" not in ra
        assert "max_score" not in ra
        assert "extended_result" not in ra
    assert "category_scores" not in payload
    assert payload["charts"] == []


@pytest.mark.django_db
def test_full_profile_is_the_superset(audit):
    _, payload = _render(audit, "auditor", profile="full")
    assert payload["charts"], "full profile renders charts"
    assert "commitments" in payload
    assert "signatures" not in payload["sections"]


@pytest.mark.django_db
def test_scores_follow_the_audit_visibility_map(audit):
    """`score` is hidden from everyone by default; a scoring framework turns it on."""
    _, hidden_payload = _render(audit, "auditor", profile="full")
    assert "score" in hidden_payload["hidden_fields"]
    assert "category_scores" not in hidden_payload
    assert "category_radar.png" not in hidden_payload["charts"], (
        "a chart drawn from a hidden field must be dropped with it"
    )

    audit.field_visibility = {"score": {"auditor": "edit", "respondent": "hidden"}}
    audit.save()

    _, shown_payload = _render(audit, "auditor", profile="full")
    assert "score" not in shown_payload["hidden_fields"]
    assert "category_scores" in shown_payload
    assert "category_radar.png" in shown_payload["charts"]


@pytest.mark.django_db
def test_attestation_takes_the_respondent_column_but_discloses_the_verdict(audit):
    """Mirrors THIRD_PARTY_VISIBILITY: the verdict is auditor-only during the
    questionnaire, and the attestation is where it gets stated for agreement."""
    audit.field_visibility = {
        "result": {"auditor": "edit", "respondent": "hidden"},
        "score": {"auditor": "edit", "respondent": "hidden"},
        "applied_controls": {"auditor": "edit", "respondent": "hidden"},
    }
    audit.save()

    _, full = _render(audit, "auditor", profile="full")
    assert "score" not in full["hidden_fields"]

    _, att = _render(audit, "auditor", profile="attestation")
    # Configured hidden-from-respondent fields drop, even for an auditor caller.
    assert "score" in att["hidden_fields"]
    assert "applied_controls" in att["hidden_fields"]
    # ... except the one the document exists to communicate.
    assert "result" not in att["hidden_fields"]
    for ra in att["requirement_assessments"]:
        assert "result" in ra
        assert "score" not in ra
        assert "applied_controls" not in ra


@pytest.mark.django_db
def test_respondent_cannot_escalate_via_the_full_profile(audit):
    _, payload = _render(audit, "respondent", profile="full")
    assert "status" in payload["hidden_fields"]


@pytest.mark.django_db
def test_unknown_profile_is_rejected(admin_client, audit):
    url = reverse("compliance-assessments-posture-pdf", kwargs={"pk": str(audit.pk)})
    assert admin_client.get(url, {"profile": "nope"}).status_code == 400
    assert admin_client.get(url, {"profile": "attestation"}).status_code == 200


@pytest.mark.django_db
def test_attestation_endpoint_filename_carries_the_profile(admin_client, audit):
    url = reverse("compliance-assessments-posture-pdf", kwargs={"pk": str(audit.pk)})
    response = admin_client.get(url, {"profile": "attestation"})
    assert response.status_code == status.HTTP_200_OK
    assert "_attestation.pdf" in response["Content-Disposition"]
    assert response.content[:5] == b"%PDF-"


@pytest.mark.django_db
def test_attestation_is_a_content_record_not_an_analysis(audit):
    """Same content selection as the zip's audit_report.html: no generated aggregates."""
    _, payload = _render(audit, "auditor", profile="attestation")
    sections = payload["sections"]
    for generated in ("summary", "charts", "drifts", "categories", "controls"):
        assert generated not in sections, (
            f"{generated} is derived, not recorded content"
        )
    for recorded in ("requirements", "answers", "commitments", "tasks"):
        assert recorded in sections
    assert payload["charts"] == []


@pytest.mark.django_db
def test_requirement_rows_carry_questions_and_answers(audit):
    _, payload = _render(audit, "auditor", profile="attestation")
    assert all("answers" in ra for ra in payload["requirement_assessments"]), (
        "the respondent's input is what the countersigned copy records"
    )


@pytest.mark.django_db
def test_disclosure_never_overrides_a_framework_wide_hide(audit):
    """A field hidden from the auditor too is hidden for a reason the attestation
    must not second-guess — the external copy can never show more than the internal."""
    audit.field_visibility = {"result": {"auditor": "hidden", "respondent": "hidden"}}
    audit.save()

    _, att = _render(audit, "auditor", profile="attestation")
    assert "result" in att["hidden_fields"]
    for ra in att["requirement_assessments"]:
        assert "result" not in ra


@pytest.mark.django_db
def test_counterparty_block_is_absent_for_a_plain_internal_audit(audit):
    """An audit not reached through an entity assessment identifies no counterparty."""
    _, payload = _render(audit, "auditor", profile="attestation")
    assert payload["counterparty"] is None


@pytest.mark.django_db
def test_requirement_rows_carry_evidences_and_opted_in_tasks(audit):
    """`evidences` is visible by default; `task_templates` is HIDDEN until the audit
    opts in (third-party questionnaires do, via THIRD_PARTY_VISIBILITY)."""
    _, default_payload = _render(audit, "auditor", profile="full")
    for ra in default_payload["requirement_assessments"]:
        assert "evidences" in ra
        assert "task_templates" not in ra

    audit.field_visibility = {
        "task_templates": {"auditor": "edit", "respondent": "edit"}
    }
    audit.save()

    _, opted_in = _render(audit, "auditor", profile="full")
    for ra in opted_in["requirement_assessments"]:
        assert "task_templates" in ra
