"""MCP tokens on the backend. The backend is the MCP resource server: whoever
presents an MCP token, the MCP server or an app calling the API directly, it
gets the same checks. The token's connection decides, and only the operations
the MCP tools use are open to it."""

import structlog
from allauth.idp.oidc.models import Token
from auditlog import get_logentry_model
from django.db.models.signals import pre_save
from django.http import JsonResponse
from django.urls import Resolver404, resolve
from rest_framework import permissions, views
from rest_framework.response import Response

from core.context import mcp_access_var
from iam.mcp_access import is_mcp_token, mcp_access
from iam.mcp_inventory import is_inventoried
from iam.models import ConnectedAppUse

BEARER = "bearer "


def _bearer(request) -> str | None:
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.lower().startswith(BEARER):
        return None
    return header[len(BEARER) :].strip() or None


def _refuse(status, detail):
    return JsonResponse({"detail": detail}, status=status)


class MCPTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # cleared when each request starts, never at its end: a streaming
        # response still runs after this middleware returns
        mcp_access_var.set(None)
        raw = _bearer(request)
        token = (
            Token.objects.select_related("user", "client")
            .valid()
            .by_value(raw)
            .filter(type=Token.Type.ACCESS_TOKEN)
            .first()
            if raw
            else None
        )
        if token is None or not is_mcp_token(token):
            return self.get_response(request)
        access = mcp_access(token)
        if access is None:
            return _refuse(401, "This AI app connection is not allowed.")
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return _refuse(404, "Not found.")
        if not is_inventoried(request.method, match):
            return _refuse(403, "This operation is not available to AI apps.")
        mcp_access_var.set(access)
        # the request log names the app: reads stay traceable
        structlog.contextvars.bind_contextvars(mcp_app=access.client.id)
        ConnectedAppUse.record(access.user.pk, access.client.pk)
        return self.get_response(request)


class IsMCPConnection(permissions.BasePermission):
    def has_permission(self, request, view):
        return mcp_access_var.get() is not None


class MCPAccessView(views.APIView):
    """What the presented MCP token may do. The MCP server asks this with the
    token itself, so it needs no secret, and it learns nothing about any other
    credential: they are refused here."""

    permission_classes = [IsMCPConnection]

    def get(self, request, *args, **kwargs):
        access = mcp_access_var.get()
        return Response(
            {
                "user": str(access.user.pk),
                "client_id": access.client.id,
                **access.claims(),
            }
        )


def _tag_log_entry(sender, instance, **kwargs):
    # a change made by an AI app must not look like the user did it in the UI
    access = mcp_access_var.get()
    if access is not None and instance._state.adding:
        instance.additional_data = {
            **(instance.additional_data or {}),
            "via_app": access.via_app(),
        }


pre_save.connect(
    _tag_log_entry, sender=get_logentry_model(), dispatch_uid="mcp-via-app"
)
