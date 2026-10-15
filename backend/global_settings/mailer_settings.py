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
