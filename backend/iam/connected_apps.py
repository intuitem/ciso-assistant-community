from urllib.parse import urlsplit

import structlog
from allauth.idp.oidc.models import Token
from rest_framework import status, views
from rest_framework.response import Response

from iam.authentication import is_self_registered
from iam.models import ConnectedAppUse

logger = structlog.get_logger(__name__)

GRANT_TOKEN_TYPES = (Token.Type.ACCESS_TOKEN, Token.Type.REFRESH_TOKEN)


def _redirect_hosts(client) -> list[str]:
    return sorted(
        {
            urlsplit(uri).hostname
            for uri in client.get_redirect_uris()
            if urlsplit(uri).hostname
        }
    )


class ConnectedAppsView(views.APIView):
    """OAuth apps the current user has authorized and still holds tokens for."""

    def get(self, request, *args, **kwargs):
        apps = {}
        tokens = (
            Token.objects.filter(
                user=request.user, type__in=GRANT_TOKEN_TYPES, client__isnull=False
            )
            .valid()
            .select_related("client")
        )
        for token in tokens:
            app = apps.setdefault(
                token.client_id, {"client": token.client, "scopes": set()}
            )
            app["scopes"].update(token.get_scopes())
        last_used = dict(
            ConnectedAppUse.objects.filter(
                user=request.user, client_id__in=apps
            ).values_list("client_id", "last_used_at")
        )
        rows = [
            {
                "client_id": client_id,
                "name": app["client"].name,
                # nobody vetted the name of a self-registered app: the
                # redirect hosts are what identify it
                "self_registered": is_self_registered(app["client"]),
                "redirect_hosts": _redirect_hosts(app["client"]),
                "scopes": sorted(app["scopes"]),
                "last_used_at": last_used.get(client_id),
            }
            for client_id, app in apps.items()
        ]
        used = sorted(
            (row for row in rows if row["last_used_at"]),
            key=lambda row: row["last_used_at"],
            reverse=True,
        )
        never_used = [row for row in rows if not row["last_used_at"]]
        return Response(used + never_used)


class ConnectedAppDetailView(views.APIView):
    def delete(self, request, *args, **kwargs):
        # every token type, so a pending authorization code cannot be redeemed later
        deleted, _ = Token.objects.filter(
            user=request.user, client_id=kwargs["pk"]
        ).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ConnectedAppUse.objects.filter(
            user=request.user, client_id=kwargs["pk"]
        ).delete()
        logger.info(
            "connected app revoked",
            client_id=kwargs["pk"],
            user=request.user.id,
            deleted_tokens=deleted,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
