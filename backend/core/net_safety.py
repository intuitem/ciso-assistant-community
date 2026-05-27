"""SSRF guard. Resolve-then-fetch has a TOCTOU window (hostile DNS with
TTL=0 can flip the answer between check and connect); closing that
fully needs IP-pinning at the socket layer.
"""

import ipaddress
import socket
from urllib.parse import urlparse

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

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise DnsLookupError(f"DNS lookup failed for {hostname!r}: {exc}") from exc

    for *_, sockaddr in addrinfo:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
            or (ip.version == 4 and ip in _CGNAT_NET)
        ):
            raise BlockedRequestError(
                f"Blocked URL: {hostname!r} resolves to non-public address {ip}"
            )


def assert_public_url_unless_dev(
    url: str, *, allowed_schemes: tuple[str, ...] = ("https",)
) -> None:
    """assert_public_url, skipped when WEBHOOK_ALLOW_PRIVATE_IPS is set
    (shared dev/loopback escape hatch across webhooks and integrations).
    """
    from django.conf import settings

    if getattr(settings, "WEBHOOK_ALLOW_PRIVATE_IPS", False):
        return
    assert_public_url(url, allowed_schemes=allowed_schemes)


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
