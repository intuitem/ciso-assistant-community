"""
Custom middleware for WebSocket authentication.
"""

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from knox.auth import TokenAuthentication
from django.contrib.auth import get_user_model
import structlog

logger = structlog.get_logger(__name__)

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_key):
    """
    Get user from Knox token.
    """
    try:
        token_auth = TokenAuthentication()
        # Knox tokens are passed as "Token <key>"
        user, auth_token = token_auth.authenticate_credentials(token_key.encode())
        return user
    except Exception as e:
        logger.warning("Token authentication failed", error=str(e))
        return AnonymousUser()


@database_sync_to_async
def get_user_from_session(session_key):
    """
    Get user from Django session.
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    try:
        session = Session.objects.get(
            session_key=session_key, expire_date__gte=timezone.now()
        )
        uid = session.get_decoded().get("_auth_user_id")
        if uid:
            return User.objects.get(pk=uid)
    except Exception as e:
        logger.warning("Session authentication failed", error=str(e))

    return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using Knox tokens or session.

    Supports:
    1. Query parameter: ?token=<knox_token>
    2. Session cookie (fallback)
    """

    async def __call__(self, scope, receive, send):
        # Parse query string for token
        query_string = scope.get("query_string", b"").decode()
        query_params = dict(
            qc.split("=") for qc in query_string.split("&") if "=" in qc
        )
        token_from_query = query_params.get("token")

        # Get cookies from headers
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode()

        # Parse cookies
        cookies = {}
        for cookie in cookie_header.split(";"):
            cookie = cookie.strip()
            if "=" in cookie:
                key, value = cookie.split("=", 1)
                cookies[key] = value

        logger.info(
            "WebSocket auth attempt",
            query_string=query_string,
            has_cookies=bool(cookie_header),
            cookie_keys=list(cookies.keys()),
        )

        # Try different authentication methods in order
        token = token_from_query or cookies.get("token")

        if token:
            logger.info(
                "Attempting token authentication",
                token_source="query" if token_from_query else "cookie",
            )
            scope["user"] = await get_user_from_token(token)
        elif cookies.get("sessionid"):
            logger.info("Attempting session authentication")
            scope["user"] = await get_user_from_session(cookies["sessionid"])
        else:
            logger.warning("No authentication method available")
            scope["user"] = AnonymousUser()

        logger.info(
            "Auth result",
            user_type=type(scope["user"]).__name__,
            is_authenticated=getattr(scope["user"], "is_authenticated", False),
        )

        return await super().__call__(scope, receive, send)
