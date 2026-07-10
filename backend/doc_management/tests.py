"""Integration coverage for SSRF guard wiring in doc_management."""

import pytest

from core.models import Policy
from core.net_safety import BlockedRequestError
from doc_management.models import DocumentContainer
from doc_management.serializers import ManagedDocumentWriteSerializer
from doc_management.views import _safe_url_fetcher
from iam.models import Folder


class TestSafeUrlFetcher:
    def test_blocks_file_scheme(self):
        with pytest.raises(BlockedRequestError):
            _safe_url_fetcher("file:///etc/passwd")

    def test_blocks_http_scheme(self):
        with pytest.raises(BlockedRequestError):
            _safe_url_fetcher("http://example.com/img.png")

    def test_data_uri_passes_through(self):
        # data: URIs are delegated to WeasyPrint's default fetcher and
        # must not be rejected by our SSRF guard.
        _safe_url_fetcher(
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
        )


@pytest.mark.django_db
class TestContainerGrouping:
    """Stream A: documents group under a DocumentContainer, per-locale lifecycle.

    Uses an empty serializer context to unit-test the grouping logic without the
    IAM add-permission gate (which early-returns when no request is present).
    """

    def _create(self, **data):
        s = ManagedDocumentWriteSerializer(data=data, context={})
        s.is_valid(raise_exception=True)
        return s.save()

    def test_policy_document_creates_container_and_links_policy(self):
        folder = Folder.objects.create(
            name="D1", parent_folder=Folder.get_root_folder()
        )
        policy = Policy.objects.create(name="P1", folder=folder)
        doc = self._create(policy=str(policy.id), locale="en", name="P1 doc")
        assert doc.container is not None
        assert list(doc.container.policies.all()) == [policy]
        assert doc.folder_id == folder.id
        assert doc.default_locale is True

    def test_second_locale_reuses_container(self):
        folder = Folder.objects.create(
            name="D2", parent_folder=Folder.get_root_folder()
        )
        policy = Policy.objects.create(name="P2", folder=folder)
        en = self._create(policy=str(policy.id), locale="en")
        fr = self._create(policy=str(policy.id), locale="fr")
        assert en.container_id == fr.container_id
        assert fr.default_locale is False
        assert DocumentContainer.objects.filter(policies=policy).count() == 1

    def test_standalone_document_creates_own_container(self):
        folder = Folder.objects.create(
            name="D3", parent_folder=Folder.get_root_folder()
        )
        doc = self._create(
            folder=str(folder.id),
            locale="en",
            name="Charter",
            document_type="charter",
        )
        assert doc.container is not None
        assert doc.container.policies.count() == 0
        assert doc.container.document_type == "charter"
        assert doc.folder_id == folder.id

    def test_template_used_seeds_content_from_db(self):
        from doc_management.models import DocumentTemplate

        folder = Folder.objects.create(
            name="DT", parent_folder=Folder.get_root_folder()
        )
        # builtin -> resolvable without a request (the create() path scopes custom
        # templates to the requesting user's accessible folders).
        DocumentTemplate.objects.create(
            ref_id="my_tmpl",
            locale="en",
            name="My Template",
            content="# Hello from template",
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        doc = self._create(
            folder=str(folder.id), locale="en", template_used="my_tmpl", name="D"
        )
        assert doc.revisions.first().content == "# Hello from template"

    def test_references_computed_from_content_links(self):
        from doc_management.models import DocumentReference

        folder = Folder.objects.create(
            name="DR", parent_folder=Folder.get_root_folder()
        )
        target = self._create(folder=str(folder.id), locale="en", name="Target")
        source = self._create(folder=str(folder.id), locale="en", name="Source")

        rev = source.revisions.first()
        rev.content = f"See [Target](document:{target.container_id}) for details."
        rev.save()

        assert DocumentReference.objects.filter(
            source_container=source.container, target_container=target.container
        ).exists()
        # self-links and dangling ids are dropped
        rev.content += " and [self](document:%s)" % source.container_id
        rev.save()
        assert not DocumentReference.objects.filter(
            source_container=source.container, target_container=source.container
        ).exists()
        # removing the link drops the edge
        rev.content = "no links here"
        rev.save()
        assert not DocumentReference.objects.filter(
            source_container=source.container
        ).exists()

    def test_custom_html_override_used_when_active(self):
        from core.models import CustomDocHtmlTemplate
        from django.core.files.base import ContentFile
        from doc_management.views import DocumentRevisionViewSet

        folder = Folder.objects.create(
            name="OV", parent_folder=Folder.get_root_folder()
        )
        doc = self._create(folder=str(folder.id), locale="en", name="Doc")
        rev = doc.revisions.first()

        vs = DocumentRevisionViewSet()
        # no override -> built-in template
        default_html = vs._resolve_document_html(
            rev, {"title": "T", "content": "<p>C</p>"}
        )
        assert "OVERRIDE-MARKER" not in default_html

        tmpl = CustomDocHtmlTemplate.objects.create(
            template_key="document_pdf",
            language="en",
            is_active=True,
            folder=Folder.get_root_folder(),
        )
        tmpl.file.save("ov.html", ContentFile(b"<h1>OVERRIDE-MARKER {{ title }}</h1>"))

        html = vs._resolve_document_html(rev, {"title": "Hello", "content": "<p>C</p>"})
        assert "OVERRIDE-MARKER Hello" in html
        # inactive override is ignored
        tmpl.is_active = False
        tmpl.save()
        assert "OVERRIDE-MARKER" not in vs._resolve_document_html(rev, {"title": "T"})

    def test_sync_parses_document_type_from_frontmatter(self, tmp_path, monkeypatch):
        from django.core.management import call_command
        from doc_management.management.commands import sync_document_templates as cmd
        from doc_management.models import DocumentTemplate

        en = tmp_path / "en"
        en.mkdir()
        (en / "my_charter.md").write_text(
            "---\ntitle: My Charter\ndocument_type: charter\n---\nbody",
            encoding="utf-8",
        )
        (en / "plain.md").write_text("# no frontmatter", encoding="utf-8")
        (en / "bad_type.md").write_text(
            "---\ndocument_type: nonsense\n---\nx", encoding="utf-8"
        )
        monkeypatch.setattr(cmd, "TEMPLATES_DIR", tmp_path)
        call_command("sync_document_templates")

        get = lambda ref: DocumentTemplate.objects.get(ref_id=ref, locale="en")
        assert get("my_charter").document_type == "charter"
        # no frontmatter -> default policy
        assert get("plain").document_type == "policy"
        # invalid type -> falls back to policy
        assert get("bad_type").document_type == "policy"

    def test_import_templates_from_zip(self):
        import io
        import zipfile
        from doc_management.template_import import import_templates_from_zip
        from doc_management.models import DocumentTemplate

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "en/access_ctl.md",
                "---\ntitle: Access Control\ndocument_type: procedure\n---\n# body",
            )
            zf.writestr("fr/access_ctl.md", "---\ntitle: Contrôle\n---\n# corps")
            zf.writestr("en/notes.txt", "ignored non-markdown")
            zf.writestr("toplevel.md", "no locale dir")
        buf.seek(0)

        result = import_templates_from_zip(buf, Folder.get_root_folder())
        assert result["created"] == 2
        en = DocumentTemplate.objects.get(ref_id="access_ctl", locale="en")
        assert en.document_type == "procedure"
        assert en.builtin is False
        assert en.default_locale is True
        assert (
            DocumentTemplate.objects.get(ref_id="access_ctl", locale="fr").document_type
            == "policy"
        )
        assert any("toplevel.md" in e for e in result["errors"])

        # re-import upserts (no duplicates)
        buf.seek(0)
        again = import_templates_from_zip(buf, Folder.get_root_folder())
        assert again["updated"] == 2 and again["created"] == 0

    def test_custom_html_forbidden_tags_fall_back(self):
        from core.models import CustomDocHtmlTemplate
        from django.core.files.base import ContentFile
        from doc_management.views import DocumentRevisionViewSet
        from doc_management.html_templates import find_forbidden_template_tags

        assert find_forbidden_template_tags("{% load x %}{{ title }}") == ["load"]
        assert find_forbidden_template_tags("<h1>{{ title }}</h1>") == []

        folder = Folder.objects.create(
            name="FT", parent_folder=Folder.get_root_folder()
        )
        doc = self._create(folder=str(folder.id), locale="en", name="Doc")
        rev = doc.revisions.first()
        tmpl = CustomDocHtmlTemplate.objects.create(
            template_key="document_pdf",
            language="en",
            is_active=True,
            folder=Folder.get_root_folder(),
        )
        tmpl.file.save(
            "bad.html", ContentFile(b"{% include 'x.html' %}OVERRIDE-MARKER")
        )
        # a forbidden tag -> the override is skipped, built-in layout used
        html = DocumentRevisionViewSet()._resolve_document_html(rev, {"title": "T"})
        assert "OVERRIDE-MARKER" not in html

    def test_linked_document_revision(self):
        folder = Folder.objects.create(
            name="LK", parent_folder=Folder.get_root_folder()
        )
        doc = self._create(folder=str(folder.id), locale="en", name="External")
        rev = doc.revisions.first()
        rev.source = "link"
        rev.content = ""
        rev.url = "https://example.com/policy"
        rev.save()  # exercises recompute_references with no content
        rev.refresh_from_db()
        assert rev.source == "link"
        assert rev.url == "https://example.com/policy"
