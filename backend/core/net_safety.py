"""SSRF guard. assert_public_* resolve-then-check, which leaves a TOCTOU
window (hostile DNS with TTL=0 can flip the answer between check and
connect); PublicSession closes it by checking the address actually
connected to, before any byte is sent.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool

# RFC 6598 Shared Address Space (CGNAT). `ipaddress` treats this as
# neither private nor global, so we reject it explicitly.
_CGNAT_NET = ipaddress.ip_network("100.64.0.0/10")


class BlockedRequestError(ValueError):
    # Inherits ValueError so WeasyPrint's URL fetcher contract (which
    # treats ValueError as "skip this resource, degrade gracefully")
    # still applies. Don't change to bare Exception without verifying
    # the PDF render path still degrades.
    pass


class DnsLookupError(Exception):
    """Transient DNS failure. Distinct from BlockedRequestError so callers
    can retry DNS hiccups while treating policy denials as terminal."""

    pass


def assert_public_url(
    url: str, *, allowed_schemes: tuple[str, ...] = ("https",)
) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in allowed_schemes:
        raise BlockedRequestError(
            f"Blocked URL scheme {parsed.scheme!r}; allowed: {allowed_schemes}"
        )
    hostname = parsed.hostname
    if not hostname:
        raise BlockedRequestError(f"Blocked URL: no hostname in {url!r}")
    assert_public_host(hostname)


def assert_public_host(hostname: str) -> None:
    """Same policy as assert_public_url for a bare host name (an SMTP server,
    for instance): every address it resolves to must be public."""
    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise DnsLookupError(f"DNS lookup failed for {hostname!r}: {exc}") from exc

    for *_, sockaddr in addrinfo:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        if _is_non_public(ip):
            raise BlockedRequestError(
                f"Blocked URL: {hostname!r} resolves to non-public address {ip}"
            )


def _is_non_public(ip) -> bool:
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
        or (ip.version == 4 and ip in _CGNAT_NET)
    )


def _assert_public_peer(sock, host) -> None:
    ip = ipaddress.ip_address(sock.getpeername()[0].split("%")[0])
    if _is_non_public(ip):
        sock.close()
        raise BlockedRequestError(
            f"Blocked URL: {host!r} connected to non-public address {ip}"
        )


class _PublicHTTPConnection(HTTPConnection):
    def _new_conn(self):
        sock = super()._new_conn()
        _assert_public_peer(sock, self.host)
        return sock


class _PublicHTTPSConnection(HTTPSConnection):
    def _new_conn(self):
        sock = super()._new_conn()
        _assert_public_peer(sock, self.host)
        return sock


class _PublicHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = _PublicHTTPConnection


class _PublicHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _PublicHTTPSConnection


class _PublicAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {
            "http": _PublicHTTPConnectionPool,
            "https": _PublicHTTPSConnectionPool,
        }


class PublicSession(requests.Session):
    """requests.Session that refuses to talk to a non-public address, checked
    on the connected socket so DNS rebinding can't slip past assert_public_url.
    Raises BlockedRequestError. Requests through a configured HTTP(S)_PROXY
    connect to the proxy, not the target, and are not checked here: the proxy
    owns egress policy then. No-op under ALLOW_PRIVATE_NETWORK_REQUESTS."""

    def __init__(self):
        from django.conf import settings

        super().__init__()
        if not getattr(settings, "ALLOW_PRIVATE_NETWORK_REQUESTS", False):
            self.mount("http://", _PublicAdapter())
            self.mount("https://", _PublicAdapter())


def public_request(method, url, **kwargs):
    """requests.request over a PublicSession."""
    with PublicSession() as session:
        return session.request(method, url, **kwargs)


def public_get(url, **kwargs):
    return public_request("GET", url, **kwargs)


def public_post(url, **kwargs):
    return public_request("POST", url, **kwargs)


def assert_public_url_unless_dev(
    url: str, *, allowed_schemes: tuple[str, ...] = ("https",)
) -> None:
    """assert_public_url, skipped when ALLOW_PRIVATE_NETWORK_REQUESTS is set."""
    from django.conf import settings

    if getattr(settings, "ALLOW_PRIVATE_NETWORK_REQUESTS", False):
        return
    assert_public_url(url, allowed_schemes=allowed_schemes)


def assert_public_host_unless_dev(hostname: str) -> None:
    """assert_public_host, skipped when ALLOW_PRIVATE_NETWORK_REQUESTS is set."""
    from django.conf import settings

    if getattr(settings, "ALLOW_PRIVATE_NETWORK_REQUESTS", False):
        return
    assert_public_host(hostname)


def check_integration_url(url: str, source: str) -> None:
    """SSRF check for admin-configured integration URLs (Jira, ServiceNow).

    Raises ValueError with a user-facing message on policy denial; callers
    log the raw cause via their structured logger before letting it
    propagate.
    """
    try:
        assert_public_url_unless_dev(url)
    except BlockedRequestError as exc:
        raise ValueError(f"{source} URL must be a public HTTPS endpoint") from exc
