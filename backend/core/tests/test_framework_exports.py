"""Framework-specific exports go through core.framework_exports: base models
and views offer and serve whatever an export module registers."""

import pytest
from django.urls import reverse
from knox.models import AuthToken
from rest_framework.test import APIClient

from core import framework_exports
from core.apps import startup
from core.framework_exports import ExportFile, FrameworkExport
from core.models import ComplianceAssessment, Framework
from iam.models import Folder, User, UserGroup

PLAIN_TEXT = FrameworkExport(
    ref_id="plain-text",
    title="exportPlainText",
    description="exportPlainTextDesc",
    format="MD",
    supports=lambda audit: audit.framework.urn == "urn:test:framework:exports",
    build=lambda audit: ExportFile(
        f"# {audit.name}".encode(), "résumé.md", "text/markdown"
    ),
)


@pytest.fixture
def plain_text_export(monkeypatch):
    monkeypatch.setitem(framework_exports._registry, PLAIN_TEXT.ref_id, PLAIN_TEXT)


@pytest.fixture
def admin_client():
    startup(sender=None)
    admin = User.objects.create_superuser("admin@framework-exports-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


def _audit(urn):
    root = Folder.get_root_folder()
    framework = Framework.objects.create(name="Exports", urn=urn, folder=root)
    return ComplianceAssessment.objects.create(
        name="Audit", framework=framework, folder=root
    )


@pytest.mark.django_db
class TestFrameworkExportRegistry:
    def test_registered_export_is_offered_and_served(
        self, admin_client, plain_text_export
    ):
        audit = _audit("urn:test:framework:exports")
        detail = admin_client.get(
            reverse("compliance-assessments-detail", kwargs={"pk": str(audit.pk)})
        ).json()
        assert detail["framework_exports"] == [
            {
                "ref_id": "plain-text",
                "title": "exportPlainText",
                "description": "exportPlainTextDesc",
                "format": "MD",
            }
        ]

        response = admin_client.get(
            reverse(
                "compliance-assessments-framework-export",
                kwargs={"pk": str(audit.pk), "export_id": "plain-text"},
            )
        )
        assert response.status_code == 200
        assert response.content == b"# Audit"
        assert response["Content-Type"] == "text/markdown"
        # Non-ASCII file names are encoded, not dropped.
        assert "filename*=utf-8''r%C3%A9sum%C3%A9.md" in response["Content-Disposition"]

    def test_export_is_only_offered_to_audits_it_supports(
        self, admin_client, plain_text_export
    ):
        audit = _audit("urn:test:framework:other")
        assert audit.framework_exports == []
        response = admin_client.get(
            reverse(
                "compliance-assessments-framework-export",
                kwargs={"pk": str(audit.pk), "export_id": "plain-text"},
            )
        )
        assert response.status_code == 400
