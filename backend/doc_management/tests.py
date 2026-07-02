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
        DocumentTemplate.objects.create(
            ref_id="my_tmpl",
            locale="en",
            name="My Template",
            content="# Hello from template",
            folder=Folder.get_root_folder(),
        )
        doc = self._create(
            folder=str(folder.id), locale="en", template_used="my_tmpl", name="D"
        )
        assert doc.revisions.first().content == "# Hello from template"
