"""Integration coverage for SSRF guard wiring in doc_management."""

import pytest

from core.net_safety import BlockedRequestError
from doc_management.views import _safe_url_fetcher


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
