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
        assert "filename*=UTF-8''r%C3%A9sum%C3%A9.md" in response["Content-Disposition"]

    def test_audit_name_cannot_break_the_filename_header(
        self, admin_client, monkeypatch
    ):
        named = FrameworkExport(
            ref_id="named",
            title="exportNamed",
            description="exportNamedDesc",
            format="MD",
            supports=lambda audit: True,
            build=lambda audit: ExportFile(b"", f"{audit.name}.md", "text/markdown"),
        )
        monkeypatch.setitem(framework_exports._registry, named.ref_id, named)
        audit = _audit("urn:test:framework:named")
        audit.name = 'Q3 "final"\r\nSet-Cookie: x=1'
        audit.save()
        response = admin_client.get(
            reverse(
                "compliance-assessments-framework-export",
                kwargs={"pk": str(audit.pk), "export_id": "named"},
            )
        )
        assert response.status_code == 200
        header = response["Content-Disposition"]
        assert "\r" not in header and "\n" not in header
        assert 'filename="Q3 finalSet-Cookie: x=1.md"' in header

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


def _domain_audit(urn):
    """An audit in a domain with its builtin user groups."""
    domain = Folder.objects.create(
        name=f"Exports {urn}",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(domain)
    framework = Framework.objects.create(name="Exports", urn=urn, folder=domain)
    audit = ComplianceAssessment.objects.create(
        name="Audit", framework=framework, folder=domain
    )
    return domain, audit


@pytest.mark.django_db
class TestFrameworkExportPermissions:
    def _get(self, user, audit):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.get(
            reverse(
                "compliance-assessments-framework-export",
                kwargs={"pk": str(audit.pk), "export_id": "plain-text"},
            )
        )

    def test_respondents_cannot_export_the_whole_audit(self, plain_text_export):
        startup(sender=None)
        domain, audit = _domain_audit("urn:test:framework:exports")
        auditee = User.objects.create_user("auditee@framework-exports-tests.com")
        UserGroup.objects.get(name="BI-UG-ADE", folder=domain).user_set.add(auditee)
        assert self._get(auditee, audit).status_code == 403

    def test_users_without_access_cannot_export(self, plain_text_export):
        startup(sender=None)
        _domain, audit = _domain_audit("urn:test:framework:exports")
        outsider = User.objects.create_user("outsider@framework-exports-tests.com")
        assert self._get(outsider, audit).status_code == 403


class TestRegistry:
    def test_duplicate_id_is_refused(self, plain_text_export):
        with pytest.raises(ValueError, match="already registered"):
            framework_exports.register(PLAIN_TEXT)

    def test_id_outside_the_route_is_refused(self):
        with pytest.raises(ValueError, match="Invalid framework export id"):
            framework_exports.register(
                FrameworkExport(
                    ref_id="no/slash",
                    title="t",
                    description="d",
                    format="MD",
                    supports=lambda audit: True,
                    build=lambda audit: None,
                )
            )
