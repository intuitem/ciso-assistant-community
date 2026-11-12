import uuid
from urllib.parse import urlsplit

import structlog
from allauth.idp.oidc.models import Client, Token
from django.db import transaction
from django.db.models import Q
from rest_framework import status, views
from rest_framework.response import Response

from core.pagination import CustomLimitOffsetPagination
from core.permissions import IsGlobalAdmin
from iam.authentication import is_self_registered
from iam.mcp_access import revoke_app_tokens
from iam.models import AppGrant, ConnectedAppUse

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


def _connections(tokens, with_user=False) -> list[dict]:
    """One row per (user, app) holding a valid access or refresh token, most
    recently used first, never used last."""
    grouped = {}
    for token in tokens.filter(
        type__in=GRANT_TOKEN_TYPES, client__isnull=False
    ).valid():
        row = grouped.setdefault(
            (token.user_id, token.client_id), {"token": token, "scopes": set()}
        )
        row["scopes"].update(token.get_scopes())
    users = {user for user, _ in grouped}
    clients = {client for _, client in grouped}
    uses = {
        (use.user_id, use.client_id): use
        for use in ConnectedAppUse.objects.filter(
            user_id__in=users, client_id__in=clients
        )
    }
    grants = {
        (grant.user_id, grant.client_id): grant
        for grant in AppGrant.objects.filter(
            user_id__in=users, client_id__in=clients
        ).select_related("profile")
    }
    rows = []
    for key, row in grouped.items():
        token, use, grant = row["token"], uses.get(key), grants.get(key)
        item = {
            "client_id": token.client_id,
            "name": token.client.name,
            # nobody vetted the name of a self-registered app: the redirect
            # hosts are what identify it
            "self_registered": is_self_registered(token.client),
            "redirect_hosts": _redirect_hosts(token.client),
            "scopes": sorted(row["scopes"]),
            "authorized_at": use.authorized_at if use else None,
            "last_used_at": use.last_used_at if use else None,
            "profile": (
                {
                    "id": grant.profile.id,
                    "name": grant.profile.name,
                    "actions": grant.profile.actions,
                }
                if grant
                else None
            ),
        }
        if with_user:
            item["user"] = {"id": token.user_id, "email": token.user.email}
        rows.append(item)
    used = sorted(
        (row for row in rows if row["last_used_at"]),
        key=lambda row: row["last_used_at"],
        reverse=True,
    )
    return used + [row for row in rows if not row["last_used_at"]]


class ConnectedAppsView(views.APIView):
    """OAuth apps the current user has authorized and still holds tokens for."""

    def get(self, request, *args, **kwargs):
        tokens = Token.objects.filter(user=request.user).select_related("client")
        return Response(_connections(tokens))


class ConnectedAppDetailView(views.APIView):
    def delete(self, request, *args, **kwargs):
        if not Token.objects.filter(user=request.user, client_id=kwargs["pk"]).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        revoke_app_tokens([request.user.pk], [kwargs["pk"]])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AllConnectedAppsView(views.APIView):
    permission_classes = [IsGlobalAdmin]

    def get(self, request, *args, **kwargs):
        tokens = Token.objects.filter(user__isnull=False).select_related(
            "client", "user"
        )
        params = request.query_params
        if params.get("user"):
            try:
                tokens = tokens.filter(user_id=uuid.UUID(params["user"]))
            except ValueError:
                return Response(
                    {"user": ["Not a valid user ID."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if params.get("client"):
            tokens = tokens.filter(client_id=params["client"])
        if params.get("search"):
            tokens = tokens.filter(
                Q(user__email__icontains=params["search"])
                | Q(client__name__icontains=params["search"])
            )
        rows = _connections(tokens, with_user=True)
        if params.get("self_registered") in ("true", "1"):
            rows = [row for row in rows if row["self_registered"]]
        paginator = CustomLimitOffsetPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(page if page is not None else rows)


class UserConnectedAppView(views.APIView):
    permission_classes = [IsGlobalAdmin]

    def delete(self, request, user_id, client_id, *args, **kwargs):
        if not Token.objects.filter(user_id=user_id, client_id=client_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        revoke_app_tokens([user_id], [client_id])
        logger.info(
            "connected app revoked by admin",
            admin=request.user.id,
            user=user_id,
            client_id=client_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConnectedAppGroupView(views.APIView):
    """One app across all its users: what "revoke for everyone" would cut, then
    the revocation itself. Only the selected registration: a self-registered
    app chooses its own name, so registrations that look alike are not proven
    to be the same app."""

    permission_classes = [IsGlobalAdmin]

    def get(self, request, client_id, *args, **kwargs):
        client = Client.objects.filter(id=client_id).first()
        if client is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        users = (
            Token.objects.filter(client=client, user__isnull=False)
            .values("user_id")
            .distinct()
            .count()
        )
        return Response(
            {
                "name": client.name,
                "self_registered": is_self_registered(client),
                "redirect_hosts": _redirect_hosts(client),
                "users": users,
            }
        )

    def delete(self, request, client_id, *args, **kwargs):
        client = Client.objects.filter(id=client_id).first()
        if client is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            users = (
                Token.objects.filter(client=client, user__isnull=False)
                .values("user_id")
                .distinct()
                .count()
            )
            # by client, not by a list read beforehand: a token issued meanwhile
            # must go too
            revoke_app_tokens(None, [client.id])
            # deleting a self-registered client stops its ID being reused; an
            # admin-registered one is configuration and stays
            if is_self_registered(client):
                client.delete()
        logger.info(
            "connected app revoked for everyone",
            admin=request.user.id,
            name=client.name,
            client=client_id,
            users=users,
        )
        return Response({"users": users}, status=status.HTTP_200_OK)
