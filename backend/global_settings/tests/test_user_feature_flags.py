"""
Tests for the per-user feature-flag layer: resolution narrows and never widens,
the effective endpoint stays separate from the raw row the admin form reads, and
the preference write only accepts flags the edition declares hideable.
"""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
from global_settings.utils import (
    clear_feature_flags_cache,
    ff_is_enabled,
    get_supported_feature_flags,
    get_user_hidden_feature_flags,
    get_user_hideable_feature_flags,
    resolve_feature_flags,
)
from iam.models import Folder, Role, RoleAssignment, User, UserGroup


@pytest.fixture
def app_config(db):
    startup(sender=None, **{})


@pytest.fixture
def flags_row(db):
    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    # `auditee_mode` is here to be a non-hideable flag that is on: keys absent
    # from the row now read False, so it has to be stated to mean anything.
    gs.value = {
        "incidents": True,
        "xrays": True,
        "vulnerabilities": False,
        "auditee_mode": True,
    }
    gs.save(update_fields=["value"])
    clear_feature_flags_cache()
    return gs


@pytest.fixture
def user(db):
    return User.objects.create_user(email="ff-prefs@wow.com")


@pytest.fixture
def client(app_config):
    """A non-admin: the per-user layer must not need `view_globalsettings`."""
    user = User.objects.create_user(email="ff-prefs-api@wow.com")
    folder = Folder.objects.create(
        name="ff-prefs-domain",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    group = UserGroup.objects.create(name="ff-prefs-readers", folder=folder)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-AUD"),
        folder=folder,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(folder)
    group.user_set.add(user)

    api = APIClient()
    token = AuthToken.objects.create(user=user)
    api.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    api.user = user
    return api


# --- the hideable set -------------------------------------------------------


def test_hideable_flags_are_a_subset_of_supported():
    assert get_user_hideable_feature_flags() <= get_supported_feature_flags()


def test_hideable_flags_are_declared_on_the_serializer():
    # Same source of truth as the vocabulary and the defaults, so CE and EE
    # cannot drift.
    assert (
        get_user_hideable_feature_flags()
        == FeatureFlagsSerializer.USER_HIDEABLE_FLAGS & get_supported_feature_flags()
    )
    assert "vulnerabilities" in get_user_hideable_feature_flags()


def test_every_supported_flag_declares_a_default():
    """The admin form's "Reset to defaults" reads them off the serializer, so a
    flag declared without one would silently drop out of that reset."""
    from global_settings.utils import get_feature_flag_defaults

    assert get_supported_feature_flags() == set(get_feature_flag_defaults())


@pytest.mark.parametrize(
    "flag",
    ["inherent_risk", "audit_tree_inheritance", "auditee_mode", "outgoing_webhooks"],
)
def test_semantic_flags_are_not_hideable(flag):
    # Flags that change what the data means, rather than which menu is shown,
    # stay instance-only — two users must not read different numbers.
    assert flag in get_supported_feature_flags()
    assert flag not in get_user_hideable_feature_flags()


# --- resolution -------------------------------------------------------------


def test_resolution_without_preferences_is_the_instance_view(flags_row, user):
    resolved = resolve_feature_flags(user)
    assert resolved["incidents"] is True
    assert resolved["vulnerabilities"] is False


def test_a_hidden_flag_is_off_for_that_user_only(flags_row, user):
    user.preferences = {"feature_flags": {"incidents": False}}
    assert resolve_feature_flags(user)["incidents"] is False
    assert resolve_feature_flags(User(preferences={}))["incidents"] is True


def test_a_user_cannot_widen_an_instance_flag(flags_row, user):
    # `vulnerabilities` is off instance-wide. A stored True is not a grant —
    # only False is honoured.
    user.preferences = {"feature_flags": {"vulnerabilities": True}}
    assert resolve_feature_flags(user)["vulnerabilities"] is False
    assert get_user_hidden_feature_flags(user) == {}


def test_a_non_hideable_flag_in_preferences_is_ignored(flags_row, user):
    # `auditee_mode` is on in the row and is not the user's to switch off.
    user.preferences = {"feature_flags": {"auditee_mode": False, "incidents": False}}
    resolved = resolve_feature_flags(user)
    assert resolved["auditee_mode"] is True  # untouched by the user layer
    assert resolved["incidents"] is False


def test_a_malformed_preference_blob_is_ignored(flags_row, user):
    for blob in (None, [], "incidents", {"feature_flags": "incidents"}):
        user.preferences = blob if isinstance(blob, dict) else {"feature_flags": blob}
        assert get_user_hidden_feature_flags(user) == {}


def test_a_key_the_row_is_missing_reads_false(db, user):
    # `incidents` declares default=True but is absent from the row, so
    # `ff_is_enabled` answers False and the effective view has to agree.
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {"xrays": False}}
    )
    clear_feature_flags_cache()
    resolved = resolve_feature_flags(user)
    assert resolved["xrays"] is False
    assert resolved["incidents"] is False


@pytest.mark.parametrize("value", [[], {}, "nonsense"])
def test_a_missing_or_malformed_row_disables_everything(db, user, value):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": value}
    )
    clear_feature_flags_cache()
    assert set(resolve_feature_flags(user).values()) <= {False}


def test_the_effective_view_never_exceeds_enforcement(flags_row, user):
    """The invariant the design rests on: what the UI offers is a subset of what
    `ff_is_enabled` permits."""
    user.preferences = {"feature_flags": {"incidents": False}}
    for name, effective in resolve_feature_flags(user).items():
        if effective:
            assert ff_is_enabled(name), name


# --- endpoints --------------------------------------------------------------


def test_effective_endpoint_reflects_the_users_choice(client, flags_row):
    response = client.get("/api/settings/feature-flags/effective/")
    assert response.status_code == 200
    assert response.json()["flags"]["incidents"] is True
    assert "vulnerabilities" in response.json()["hideable"]

    client.user.preferences = {"feature_flags": {"incidents": False}}
    client.user.save(update_fields=["preferences"])

    response = client.get("/api/settings/feature-flags/effective/")
    assert response.json()["flags"]["incidents"] is False
    assert response.json()["hidden"] == ["incidents"]


def test_effective_endpoint_separates_the_two_reasons_a_flag_is_off(client, flags_row):
    """A module the organisation switched off and one the user hid both read
    false in `flags`; `instance` is what tells them apart."""
    client.user.preferences = {"feature_flags": {"incidents": False}}
    client.user.save(update_fields=["preferences"])

    body = client.get("/api/settings/feature-flags/effective/").json()
    assert body["flags"]["incidents"] is False and body["instance"]["incidents"] is True
    assert (
        body["flags"]["vulnerabilities"] is False
        and body["instance"]["vulnerabilities"] is False
    )
    assert set(body["instance"]) == set(body["hideable"])


def test_raw_retrieve_is_unchanged_by_a_users_choice(client, flags_row):
    """The admin form reads `retrieve` and PUTs the whole body back, so a personal
    hide leaking into it would take the module away from everyone."""
    client.user.preferences = {"feature_flags": {"incidents": False}}
    client.user.save(update_fields=["preferences"])

    response = client.get("/api/settings/feature-flags/")
    assert response.status_code == 200
    assert response.json()["incidents"] is True


def test_preferences_write_stores_only_the_hides(client, flags_row):
    response = client.patch(
        "/api/user-preferences/",
        {"feature_flags": {"incidents": False, "xrays": True}},
        format="json",
    )
    assert response.status_code == 200
    client.user.refresh_from_db()
    # Sparse: only the hide is stored, so `xrays` keeps following the instance.
    assert client.user.preferences["feature_flags"] == {"incidents": False}


def test_preferences_write_unhides(client, flags_row):
    client.user.preferences = {"feature_flags": {"incidents": False}}
    client.user.save(update_fields=["preferences"])

    client.patch(
        "/api/user-preferences/", {"feature_flags": {"incidents": True}}, format="json"
    )
    client.user.refresh_from_db()
    assert client.user.preferences["feature_flags"] == {}


def test_preferences_write_resets_every_flag_to_the_instance(client, flags_row):
    """ "Reset to organization settings" sends every hideable flag as visible, and
    each `true` drops its key rather than storing one."""
    client.user.preferences = {
        "feature_flags": {"incidents": False, "xrays": False, "vulnerabilities": False}
    }
    client.user.save(update_fields=["preferences"])

    hideable = get_user_hideable_feature_flags()
    response = client.patch(
        "/api/user-preferences/",
        {"feature_flags": {flag: True for flag in hideable}},
        format="json",
    )
    assert response.status_code == 200
    client.user.refresh_from_db()
    assert client.user.preferences["feature_flags"] == {}


def test_preferences_write_rejects_a_non_hideable_flag(client, flags_row):
    response = client.patch(
        "/api/user-preferences/",
        {"feature_flags": {"auditee_mode": False}},
        format="json",
    )
    assert response.status_code == 400
    client.user.refresh_from_db()
    assert "feature_flags" not in (client.user.preferences or {})


@pytest.mark.parametrize(
    "payload",
    [
        {"feature_flags": "incidents"},
        {"feature_flags": {"incidents": "false"}},
        {"feature_flags": {"does_not_exist": False}},
    ],
)
def test_preferences_write_rejects_malformed_payloads(client, flags_row, payload):
    assert (
        client.patch("/api/user-preferences/", payload, format="json").status_code
        == 400
    )


def test_preferences_write_leaves_other_preferences_alone(client, flags_row):
    client.patch("/api/user-preferences/", {"lang": "fr"}, format="json")
    client.patch(
        "/api/user-preferences/", {"feature_flags": {"incidents": False}}, format="json"
    )
    client.user.refresh_from_db()
    assert client.user.preferences["lang"] == "fr"
    assert client.user.preferences["feature_flags"] == {"incidents": False}


# --- adversarial ------------------------------------------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        {"vulnerabilities": True},  # instance-disabled, user asks for it
        {"vulnerabilities": 1},  # truthy non-bool
        {"vulnerabilities": "true"},
        {"vulnerabilities": [1]},
        {"vulnerabilities": {"nested": True}},
        {"auditee_mode": True},  # not hideable at all
        {"inherent_risk": True},
        {"__proto__": True},
        {"": True},
    ],
)
def test_a_hostile_preferences_blob_cannot_widen(flags_row, user, hostile):
    """Even writing straight to the column — bypassing the endpoint's validation
    entirely — must not turn a flag on."""
    user.preferences = {"feature_flags": hostile}
    resolved = resolve_feature_flags(user)
    for name, effective in resolved.items():
        if effective:
            assert ff_is_enabled(name), name
    assert resolved["vulnerabilities"] is False


def test_a_falsy_non_bool_is_not_a_hide(flags_row, user):
    """`0` and `""` are equal to False but are not it; only JSON `false` hides,
    so a sloppy client cannot hide a module by accident."""
    user.preferences = {"feature_flags": {"incidents": 0, "xrays": ""}}
    assert get_user_hidden_feature_flags(user) == {}
    assert resolve_feature_flags(user)["incidents"] is True


def test_the_write_endpoint_rejects_non_bool_values(client, flags_row):
    for value in (1, 0, "false", None, [], {}):
        response = client.patch(
            "/api/user-preferences/",
            {"feature_flags": {"incidents": value}},
            format="json",
        )
        assert response.status_code == 400, value
    client.user.refresh_from_db()
    assert not (client.user.preferences or {}).get("feature_flags")


def test_a_user_cannot_patch_another_users_preferences(client, flags_row, user):
    """The endpoint takes no user id — it always acts on request.user."""
    client.patch(
        "/api/user-preferences/",
        {
            "feature_flags": {"incidents": False},
            "user": str(user.pk),
            "id": str(user.pk),
        },
        format="json",
    )
    user.refresh_from_db()
    assert not (user.preferences or {}).get("feature_flags")
    client.user.refresh_from_db()
    assert client.user.preferences["feature_flags"] == {"incidents": False}


def test_hiding_everything_still_leaves_the_flags_resolvable(client, flags_row):
    """The profile page is not itself flag-gated, so a user who hides every
    module can still reach it to undo — the endpoint must keep answering."""
    hideable = get_user_hideable_feature_flags()
    response = client.patch(
        "/api/user-preferences/",
        {"feature_flags": {flag: False for flag in hideable}},
        format="json",
    )
    assert response.status_code == 200
    body = client.get("/api/settings/feature-flags/effective/").json()
    assert sorted(body["hidden"]) == sorted(hideable)
    assert set(body["hideable"]) == set(hideable)
