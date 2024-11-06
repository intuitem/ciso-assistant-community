from typing import Any, Optional

import structlog
from allauth.headless.tokens.sessions import SessionTokenStrategy
from django.http import HttpRequest
from knox.models import AuthToken

logger = structlog.get_logger(__name__)


def generate_token(user):
    _auth_token = AuthToken.objects.create(user=user)
    return _auth_token[1]


class KnoxTokenStrategy(SessionTokenStrategy):
    def create_access_token(self, request: HttpRequest) -> str:
        token = generate_token(request.user)
        return token

    def create_access_token_payload(
        self, request: HttpRequest
    ) -> Optional[dict[str, Any]]:
        access_token = self.create_access_token(request)
        if not access_token:
            return None
        return {"access_token": access_token}
