from uuid import uuid4
from typing import Optional
import ipaddress

from auditlog import middleware
from auditlog.cid import correlation_id, set_cid
from auditlog.context import set_extra_data
from django.utils.functional import SimpleLazyObject
from django.http import HttpRequest


def parse_ip(
    ip_address: str,
) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """
    Parse an IP address (which may come from the `X-Forwarded-For` HTTP header).

    Accepts:
    - `1.2.3.4`, `1.2.3.4:5678`, `2001:db8::1`, `[2001:db8::1]` and `[2001:db8::1]:443`.
    - IPv4-mapped IPv6 addresses (`::ffff:1.2.3.4`) are converted to IPv4.

    Return `None` if `ip_address` is not a valid IP address.
    """
    ip_address = (ip_address or "").strip()
    if ip_address.startswith("["):
        ip_address = ip_address[1:].split("]", 1)[0]
    elif ip_address.count(":") == 1:
        ip_address = ip_address.split(":", 1)[0]

    try:
        parsed_ip = ipaddress.ip_address(ip_address)
    except ValueError:
        return

    if isinstance(parsed_ip, ipaddress.IPv6Address) and parsed_ip.ipv4_mapped:
        return parsed_ip.ipv4_mapped
    return parsed_ip


def resolve_client_ip(request: Optional[HttpRequest]) -> Optional[str]:
    """Return the real client IP address from which the `request` originates (return `None` if resolution fails)."""
    if request is None:
        return

    x_forwarded_ip_entry = request.headers.get("X-Forwarded-For", "").split(",")[-1]
    x_forwarded_ip = parse_ip(x_forwarded_ip_entry)
    if x_forwarded_ip is None:
        # Malformed entry (nothing on its left can be trusted).
        client_ip = parse_ip(request.META.get("REMOTE_ADDR", ""))
        if client_ip is None:
            # IP address resolution failed.
            return
        else:
            return str(client_ip)

    return str(x_forwarded_ip)


# Fix the actor resolution with the custom middleware
# Based on https://stackoverflow.com/questions/40740061/auditlog-with-django-and-drf
#
# Folder/actor enrichment of LogEntry is no longer done here via a post_save
# signal: folder is captured inline at log creation through
# AbstractBaseModel.get_additional_data(), and actor/actor_email are native
# LogEntry columns. This fixes delete events (instance still in memory) and
# covers m2m changes.
class AuditlogMiddleware(middleware.AuditlogMiddleware):
    @staticmethod
    def _get_actor(request):
        return SimpleLazyObject(
            lambda: middleware.AuditlogMiddleware._get_actor(request)
        )

    def __call__(self, request):
        # Reimplements the parent __call__ (cannot super(): it calls set_cid then
        # get_response in one go, leaving no seam to mint a cid between them).
        # set_cid honors an x-correlation-id header and resets the ContextVar per
        # request; mint one when absent so all audit entries in a request share a cid.
        set_cid(request)
        if correlation_id.get() is None:
            correlation_id.set(str(uuid4()))

        context_data = self.get_extra_data(request)
        client_ip = resolve_client_ip(request)
        if client_ip is not None:
            context_data["remote_addr"] = client_ip

        with set_extra_data(context_data=context_data):
            return self.get_response(request)
