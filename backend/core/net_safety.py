"""SSRF guard. Resolve-then-fetch has a TOCTOU window (hostile DNS with
TTL=0 can flip the answer between check and connect); closing that
fully needs IP-pinning at the socket layer.
"""

import ipaddress
import socket
from urllib.parse import urlparse


class BlockedRequestError(ValueError):
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
        raise BlockedRequestError(
            f"Blocked URL: DNS lookup failed for {hostname!r}: {exc}"
        ) from exc

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
        ):
            raise BlockedRequestError(
                f"Blocked URL: {hostname!r} resolves to non-public address {ip}"
            )
