"""Microsoft Graph transport: mail over HTTPS instead of SMTP.

For tenants that forbid SMTP AUTH, and for deployments whose only way out is
an HTTP proxy, which SMTP cannot cross. The backend obtains a token with Entra
client credentials through ``core.mail_oauth2`` and posts each message to the
sending mailbox's ``sendMail`` endpoint.

Obtaining the token is the "open" step: a token failure is an unreachable
mailer and ``core.mailer`` fails over, exactly as for a refused SMTP
connection. A request Graph rejects after that is final, like every other
transport. The HTTP client follows the standard proxy environment variables
(``HTTPS_PROXY``, ``NO_PROXY``) and ``SSL_CERT_FILE``, like every other HTTPS
call the backend makes.

Attachments are refused: nothing in the product sends any, and Graph's
upload sessions for large files are not worth carrying for that.
"""

from email.utils import parseaddr
from urllib.parse import quote

import httpx
from django.core.mail.backends.base import BaseEmailBackend

from core import mail_oauth2

GRAPH_URL = "https://graph.microsoft.com/v1.0"
LOGIN_URL = "https://login.microsoftonline.com"
SCOPE = "https://graph.microsoft.com/.default"
DEFAULT_TIMEOUT_SECONDS = 15

# Tests swap in httpx.MockTransport; None means the default transport, which
# is the one that honours the proxy environment variables.
TRANSPORT = None


class GraphError(Exception):
    """Graph refused a request. Carries the HTTP status and Graph's error
    code so the message shown to an administrator is Graph's answer, not
    an exception dump."""

    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"Graph replied {status} {code}: {message}".strip())

    @classmethod
    def from_response(cls, response: httpx.Response) -> "GraphError":
        code, message = "", ""
        try:
            error = response.json().get("error") or {}
            code = str(error.get("code") or "")
            message = str(error.get("message") or "").splitlines()[0]
        except ValueError, AttributeError, IndexError:
            pass
        return cls(response.status_code, code, message[:300])


def token_config(
    *, tenant_id: str, client_id: str, client_secret: str, mailbox: str, timeout: int
) -> dict:
    """The ``core.mail_oauth2`` configuration for a Graph mailer. The token
    URL is Microsoft's, derived from the tenant: the operator supplies no
    URL, so there is nothing to point elsewhere."""
    return {
        "user": mailbox,
        "grant_type": "client_credentials",
        "token_url": f"{LOGIN_URL}/{quote(tenant_id, safe='')}/oauth2/v2.0/token",
        "scope": SCOPE,
        "client_id": client_id,
        "client_secret": client_secret,
        "timeout": timeout,
    }


def _address(value: str) -> dict:
    name, address = parseaddr(value)
    recipient = {"emailAddress": {"address": address}}
    if name:
        recipient["emailAddress"]["name"] = name
    return recipient


class EmailBackend(BaseEmailBackend):
    def __init__(
        self,
        *,
        mailbox: str,
        oauth2: dict,
        timeout: int | None = None,
        graph_url: str = GRAPH_URL,
        **kwargs,
    ):
        # No fail_silently: it is deprecated with MAILERS and the service
        # wants every failure raised.
        super().__init__(**kwargs)
        self.mailbox = mailbox
        self.oauth2 = oauth2
        self.timeout = timeout or DEFAULT_TIMEOUT_SECONDS
        self.graph_url = graph_url.rstrip("/")
        self._token = None
        self._client = None

    def open(self) -> bool:
        """Obtain the token, then the HTTP client every message of the
        session is posted through, so a batch reuses one connection as an
        SMTP session does. Raises ``mail_oauth2.TokenError`` when the token
        endpoint is unreachable or refuses: that is the failover point, as a
        refused SMTP connection is."""
        if self._token is not None:
            return False
        self._token = mail_oauth2.get_token(self.oauth2)
        self._client = httpx.Client(timeout=self.timeout, transport=TRANSPORT)
        return True

    def close(self) -> None:
        client, self._client = self._client, None
        self._token = None
        if client is not None:
            client.close()

    def send_messages(self, email_messages) -> int:
        if not email_messages:
            return 0
        # Every payload is built before anything is posted, so a message
        # this transport cannot carry fails the batch before the first send.
        payloads = [self._payload(message) for message in email_messages]
        opened = self.open()
        try:
            for payload in payloads:
                self._send(payload)
        finally:
            if opened:
                self.close()
        return len(payloads)

    def _send(self, payload: dict) -> None:
        response = self._post(payload, self._token)
        if response.status_code == 401:
            # The cached token was revoked or expired early. One retry with
            # a freshly issued token, then give up.
            mail_oauth2.discard(self.oauth2, self._token)
            self._token = mail_oauth2.get_token(self.oauth2, force_refresh=True)
            response = self._post(payload, self._token)
        if response.status_code != 202:
            raise GraphError.from_response(response)

    def _post(self, payload: dict, token: str) -> httpx.Response:
        url = f"{self.graph_url}/users/{quote(self.mailbox, safe='@')}/sendMail"
        return self._client.post(
            url, json=payload, headers={"Authorization": f"Bearer {token}"}
        )

    def _payload(self, message) -> dict:
        if message.attachments:
            raise ValueError("the Microsoft Graph transport does not send attachments")
        content_type, content = "Text", message.body
        if message.content_subtype == "html":
            content_type = "HTML"
        for alternative in getattr(message, "alternatives", ()):
            if alternative.mimetype == "text/html":
                content_type, content = "HTML", alternative.content
        graph_message = {
            "subject": message.subject,
            "body": {"contentType": content_type, "content": content},
            "toRecipients": [_address(to) for to in message.to],
        }
        if message.cc:
            graph_message["ccRecipients"] = [_address(cc) for cc in message.cc]
        if message.bcc:
            graph_message["bccRecipients"] = [_address(bcc) for bcc in message.bcc]
        if message.reply_to:
            graph_message["replyTo"] = [_address(r) for r in message.reply_to]
        # Graph sends from the mailbox. Naming another sender needs Send As
        # rights on it; only ask when the configured sender is another one.
        sender = parseaddr(message.from_email or "")[1]
        if sender and sender.lower() != self.mailbox.lower():
            graph_message["from"] = _address(message.from_email)
        return {"message": graph_message, "saveToSentItems": False}
