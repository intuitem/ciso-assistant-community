"""Tests for the SSRF guard helpers in `core.net_safety`."""

import socket
from unittest.mock import patch

import pytest

from core.net_safety import BlockedRequestError, DnsLookupError, assert_public_url


def _addrinfo(*addrs):
    """Build a fake getaddrinfo() return value for the given IP strings."""
    return [
        (socket.AF_INET6 if ":" in addr else socket.AF_INET, 1, 6, "", (addr, 0))
        for addr in addrs
    ]


class TestAssertPublicUrl:
    def test_allows_public_https(self):
        with patch("socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
            assert_public_url("https://example.com/logo.png")

    def test_blocks_non_https_scheme(self):
        with pytest.raises(BlockedRequestError):
            assert_public_url("http://example.com/")
        with pytest.raises(BlockedRequestError):
            assert_public_url("file:///etc/passwd")
        with pytest.raises(BlockedRequestError):
            assert_public_url("gopher://example.com/")

    def test_blocks_missing_hostname(self):
        with pytest.raises(BlockedRequestError):
            assert_public_url("https:///nohost")

    def test_blocks_aws_imds(self):
        with patch(
            "socket.getaddrinfo",
            return_value=_addrinfo("169.254.169.254"),
        ):
            with pytest.raises(BlockedRequestError, match="non-public"):
                assert_public_url("https://metadata.attacker.example/latest/meta-data")

    def test_blocks_loopback(self):
        with patch("socket.getaddrinfo", return_value=_addrinfo("127.0.0.1")):
            with pytest.raises(BlockedRequestError):
                assert_public_url("https://localhost.attacker/admin")

    def test_blocks_rfc1918(self):
        for ip in ("10.0.0.5", "172.16.0.1", "192.168.1.1"):
            with patch("socket.getaddrinfo", return_value=_addrinfo(ip)):
                with pytest.raises(BlockedRequestError):
                    assert_public_url(f"https://internal-{ip}.attacker/")

    def test_blocks_ipv6_loopback(self):
        with patch("socket.getaddrinfo", return_value=_addrinfo("::1")):
            with pytest.raises(BlockedRequestError):
                assert_public_url("https://v6.attacker/")

    def test_blocks_ipv6_link_local(self):
        with patch("socket.getaddrinfo", return_value=_addrinfo("fe80::1")):
            with pytest.raises(BlockedRequestError):
                assert_public_url("https://v6-ll.attacker/")

    def test_blocks_when_any_resolution_is_private(self):
        """Reject the domain even if it ALSO resolves to a public IP.
        A multi-A record can return a public IP first and a private IP
        second; routing decisions would pick either, so refuse.
        """
        with patch(
            "socket.getaddrinfo",
            return_value=_addrinfo("93.184.216.34", "10.0.0.1"),
        ):
            with pytest.raises(BlockedRequestError):
                assert_public_url("https://mixed.attacker/")

    def test_dns_failure_raises_dns_lookup_error_not_blocked(self):
        # Transient DNS hiccups must surface as DnsLookupError, distinct
        # from BlockedRequestError, so callers can retry them.
        with patch("socket.getaddrinfo", side_effect=socket.gaierror("nope")):
            with pytest.raises(DnsLookupError, match="DNS lookup failed"):
                assert_public_url("https://nope.invalid/")

    def test_blocks_rfc6598_cgnat(self):
        # 100.64.0.0/10 is shared CGNAT space; ipaddress treats it as
        # neither private nor global, so we reject it explicitly.
        for ip in ("100.64.0.1", "100.127.255.254"):
            with patch("socket.getaddrinfo", return_value=_addrinfo(ip)):
                with pytest.raises(BlockedRequestError):
                    assert_public_url(f"https://cgnat-{ip}.attacker/")

    def test_custom_allowed_schemes(self):
        """Webhook callers may want to allow http: too."""
        with patch("socket.getaddrinfo", return_value=_addrinfo("8.8.8.8")):
            # Defaults reject http://
            with pytest.raises(BlockedRequestError):
                assert_public_url("http://example.com/")
            # Caller can opt in.
            assert_public_url("http://example.com/", allowed_schemes=("http", "https"))
