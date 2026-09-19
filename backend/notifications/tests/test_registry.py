"""
The notification registry, the titles files and the email templates are three
artefacts describing one set of notification types. Nothing but these tests stops
them drifting apart.
"""

import re
from pathlib import Path

import pytest

from core.email_utils import TEMPLATE_BASE_PATH
from notifications.registry import NOTIFICATION_REGISTRY
from notifications.service import resolve_title

LOCALES = ("en", "fr")
CATEGORIES = {"assignments", "approvals", "deadlines", "updates", "account"}
MODES = {"condition", "event"}
CHANNELS = {"in_app", "email"}
PLACEHOLDER = re.compile(r"\$\{([a-z_]+)\}")
ENTRIES = sorted(NOTIFICATION_REGISTRY.items())


@pytest.mark.parametrize("key,meta", ENTRIES)
def test_entry_fields_are_valid(key, meta):
    assert meta["category"] in CATEGORIES
    assert meta["mode"] in MODES
    assert meta["channels"] and set(meta["channels"]) <= CHANNELS


@pytest.mark.parametrize("key,meta", ENTRIES)
def test_email_template_is_present_exactly_when_email_is_a_channel(key, meta):
    """`email_template: None` is how an in-app-exclusive type is declared; it must
    not silently coexist with an email channel."""
    if "email" in meta["channels"]:
        assert meta["email_template"], f"{key} has an email channel but no template"
        for locale in LOCALES:
            path = Path(TEMPLATE_BASE_PATH) / locale / f"{meta['email_template']}.yaml"
            assert path.exists(), f"{key} -> missing {path}"
    else:
        assert meta["email_template"] is None, (
            f"{key} has no email channel but names a template"
        )


@pytest.mark.parametrize("key,meta", ENTRIES)
def test_in_app_types_have_a_title_in_every_locale(key, meta):
    for locale in LOCALES:
        title = resolve_title(key, locale)
        if "in_app" in meta["channels"]:
            assert title, f"{key}/{locale} is an in-app type with no title"
        else:
            assert title is None, (
                f"{key}/{locale} has no in-app channel but has a title"
            )


@pytest.mark.parametrize("key,meta", ENTRIES)
def test_title_placeholders_are_declared_as_context(key, meta):
    """A title's variables are the *notification's* context, declared in this layer.

    Deliberately not checked against the email template's variables: a condition
    type's email is a digest (${control_count}, ${control_list}) while its inbox row
    is per object (${control_name}). They are different contexts on purpose, which is
    why the registries are layered rather than merged.
    """
    declared = set(meta["context"])
    for locale in LOCALES:
        title = resolve_title(key, locale)
        if not title:
            continue
        used = set(PLACEHOLDER.findall(title))
        assert used <= declared, (
            f"{key}/{locale} uses undeclared {sorted(used - declared)}"
        )


@pytest.mark.parametrize("key,meta", ENTRIES)
def test_context_is_empty_exactly_for_types_with_no_inbox_row(key, meta):
    if "in_app" not in meta["channels"]:
        assert meta["context"] == [], key


def test_titles_files_have_no_entry_for_a_type_without_an_inbox():
    from notifications.service import _titles

    for locale in LOCALES:
        for key in _titles(locale):
            assert key in NOTIFICATION_REGISTRY, f"{locale}: unknown type {key}"
            assert "in_app" in NOTIFICATION_REGISTRY[key]["channels"], (
                f"{locale}: {key}"
            )


def test_account_types_are_email_only():
    for key, meta in NOTIFICATION_REGISTRY.items():
        if meta["category"] == "account":
            assert meta["channels"] == ["email"], key


def test_condition_mode_matches_the_deadlines_category():
    conditions = {
        k for k, v in NOTIFICATION_REGISTRY.items() if v["mode"] == "condition"
    }
    deadlines = {
        k for k, v in NOTIFICATION_REGISTRY.items() if v["category"] == "deadlines"
    }
    assert conditions == deadlines
    assert len(conditions) == 10


@pytest.mark.django_db
@pytest.mark.parametrize("locale", LOCALES)
def test_an_email_override_cannot_reach_the_title(locale):
    """The layering, asserted: titles live above the email templates, so an
    enterprise override of a template leaves the inbox row untouched."""
    from core.models import CustomEmailTemplate

    before = resolve_title("expired_controls", locale)
    CustomEmailTemplate.objects.create(
        template_key="expired_controls",
        language=locale,
        subject="overridden subject",
        body="overridden body",
        is_active=True,
    )
    assert resolve_title("expired_controls", locale) == before
