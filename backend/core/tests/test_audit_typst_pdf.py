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


def _render(audit_obj, role):
    payload, images = audit_context_for_typst(_context(audit_obj), audit_obj, role)
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
    assert "_posture.pdf" in response["Content-Disposition"]
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
