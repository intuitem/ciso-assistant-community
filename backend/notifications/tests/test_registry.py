"""
The notification registry, the titles files and the email templates are three
artefacts describing one set of notification types. Nothing but these tests stops
them drifting apart.
"""

import ast
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from core import tasks
from core.email_utils import TEMPLATE_BASE_PATH
from notifications.registry import NOTIFICATION_REGISTRY

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
def test_context_is_empty_exactly_for_types_with_no_inbox_row(key, meta):
    if "in_app" not in meta["channels"]:
        assert meta["context"] == [], key


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


def _catalog(locale: str):
    """The frontend message catalog, or None when it is not in this checkout.

    Titles moved into the product's message catalogs so they follow the viewer's
    language, which leaves this as the only thing tying a notification type to the
    string that names it. The backend image does not ship the frontend, so this
    skips rather than fails there.
    """
    path = (
        Path(__file__).resolve().parents[3] / "frontend" / "messages" / f"{locale}.json"
    )
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@pytest.mark.parametrize("locale", LOCALES)
def test_every_in_app_type_has_a_title_message(locale):
    catalog = _catalog(locale)
    if catalog is None:
        pytest.skip("frontend messages not present in this checkout")

    missing = [
        key
        for key, meta in NOTIFICATION_REGISTRY.items()
        if "in_app" in meta["channels"]
        and f"notificationTitle{''.join(w.capitalize() for w in key.split('_'))}"
        not in catalog
    ]
    assert not missing, f"{locale}: no title message for {missing}"


@pytest.mark.parametrize("locale", LOCALES)
def test_title_messages_only_use_declared_context(locale):
    """A message referencing a variable the producer never sends would render the
    parameter name to the user."""
    catalog = _catalog(locale)
    if catalog is None:
        pytest.skip("frontend messages not present in this checkout")

    for key, meta in NOTIFICATION_REGISTRY.items():
        name = f"notificationTitle{''.join(w.capitalize() for w in key.split('_'))}"
        message = catalog.get(name)
        if not message:
            continue
        used = set(re.findall(r"\{([a-z_]+)\}", message))
        assert used <= set(meta["context"]), (
            f"{locale}/{key} uses undeclared {sorted(used - set(meta['context']))}"
        )


def _declared_owners() -> Counter:
    """Which producer claims authority over which condition type.

    `clear_stale` deletes every row of a type that is not in the `keep` set it is
    handed, so the caller is asserting it examined the whole population. Two callers
    for one type delete each other's rows on alternate nights -- which is what the
    in_month / in_week / tomorrow trio did before they were consolidated.
    """
    tree = ast.parse(Path(tasks.__file__).read_text(encoding="utf-8"))
    owners = Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # `_sweep_deadline` clears on the caller's behalf, so it counts as the owner.
        if getattr(node.func, "id", None) not in ("clear_stale", "_sweep_deadline"):
            continue
        first = node.args[0] if node.args else None
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            owners[first.value] += 1
    return owners


def test_every_condition_type_has_exactly_one_owner():
    owners = _declared_owners()
    conditions = {
        k for k, v in NOTIFICATION_REGISTRY.items() if v["mode"] == "condition"
    }
    assert set(owners) == conditions, (
        "a condition type is unowned, or a non-condition type clears"
    )
    duplicated = {k: n for k, n in owners.items() if n > 1}
    assert not duplicated, (
        f"two producers clear the same type; they will delete each other's rows: {duplicated}"
    )
