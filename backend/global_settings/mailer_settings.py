"""Helpers for the custom mailer settings: effective mailers from stored rows
and the test token that proves a configuration was tested before it is saved.

The token binds a digest of the exact mailers and sender address that were
tested, secrets included, so a form edited after a successful test needs a
new test. It is signed with the project secret and short-lived.
"""

import hashlib
import json

from django.core import signing

from core.mailer import SOURCE_CUSTOM, MailerSpec

TEST_TOKEN_SALT = "custom-mailer-test"
TEST_TOKEN_MAX_AGE_SECONDS = 30 * 60


def check_network_policy(row) -> None:
    """Apply the deployment's SSRF policy to a mailer an administrator typed
    in: the SMTP host, and the token URL for OAuth, must resolve to public
    addresses unless ALLOW_PRIVATE_NETWORK_REQUESTS is set, exactly like the
    LLM, integration and audit-sink URLs. Raises ValueError with a message
    meant for the administrator. Environment mailers are the operator's own
    and are not checked."""
    from core.net_safety import (
        BlockedRequestError,
        DnsLookupError,
        assert_public_host_unless_dev,
        assert_public_url_unless_dev,
    )

    targets = [("host", lambda: assert_public_host_unless_dev(row.host))]
    if row.transport == row.Transport.SMTP_OAUTH2:
        targets.append(
            ("token URL", lambda: assert_public_url_unless_dev(row.oauth2_token_url))
        )
    for label, check in targets:
        try:
            check()
        except BlockedRequestError:
            raise ValueError(
                f"the {label} must resolve to a public address "
                "(set ALLOW_PRIVATE_NETWORK_REQUESTS=True to allow private networks)"
            ) from None
        except DnsLookupError:
            raise ValueError(f"the {label} could not be resolved") from None


def specs_from_rows(rows) -> list[MailerSpec]:
    """``MailerSpec`` for each row, validated. Raises ValueError."""
    specs = []
    for row in rows:
        entry = row.mailer_entry()
        specs.append(
            MailerSpec(row.alias, entry["BACKEND"], entry["OPTIONS"], SOURCE_CUSTOM)
        )
    return specs


def configuration_digest(from_email: str, specs: list[MailerSpec]) -> str:
    payload = [
        from_email or "",
        [[spec.alias, spec.backend, spec.options] for spec in specs],
    ]
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def issue_test_token(digest: str) -> str:
    return signing.dumps({"digest": digest}, salt=TEST_TOKEN_SALT)


def test_token_matches(token: str | None, digest: str) -> bool:
    if not token:
        return False
    try:
        data = signing.loads(
            token, salt=TEST_TOKEN_SALT, max_age=TEST_TOKEN_MAX_AGE_SECONDS
        )
    except signing.BadSignature:
        return False
    return data.get("digest") == digest
