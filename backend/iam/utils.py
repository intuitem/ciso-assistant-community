from typing import Any, Optional

import structlog
from allauth.account.internal.stagekit import unstash_login, clear_login
from allauth.account.stages import LoginStageController
from allauth.headless.tokens.strategies.sessions import SessionTokenStrategy
from allauth.mfa.internal.constants import LoginStageKey
from django.contrib.auth import login as auth_login
from django.http import HttpRequest
from knox.models import AuthToken

logger = structlog.get_logger(__name__)


def generate_token(user):
    _auth_token = AuthToken.objects.create(user=user)
    return _auth_token[1]


def complete_sso_login_bypassing_mfa(request):
    """
    When an SSO user has local MFA enabled, allauth's MFA stage blocks
    login(). Since the IdP already authenticated the user, mark the MFA
    stage as handled and complete the Django login.

    Returns the user if MFA was bypassed, None otherwise.
    """
    login = unstash_login(request, peek=True)
    if not login or not login.user:
        return None

    ctrl = LoginStageController(request, login)
    pending = ctrl.get_pending_stage()
    if not pending or pending.key != LoginStageKey.MFA_AUTHENTICATE.value:
        return None

    logger.info(
        "Bypassing local MFA for SSO login",
        user_id=str(login.user.id),
    )
    ctrl.set_handled(LoginStageKey.MFA_AUTHENTICATE.value)
    if hasattr(LoginStageKey, "MFA_TRUST"):
        ctrl.set_handled(LoginStageKey.MFA_TRUST.value)

    auth_login(request, login.user)
    clear_login(request)
    return login.user


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
