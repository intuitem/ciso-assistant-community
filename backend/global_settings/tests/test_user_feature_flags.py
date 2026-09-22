"""
Tests for the per-user feature-flag layer: resolution narrows the instance
flags and can never widen them, the effective endpoint is separate from the
raw row the admin form reads, and the preference write only accepts flags the
edition declares hideable.
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
    """An authenticated non-admin: the per-user layer is everyone's, and it must
    not need `view_globalsettings`."""
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
    """`get_instance_feature_flags` is only total because every flag field carries
    a `default`. A flag added without one would read as missing on a row that
    predates it."""
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
    # `auditee_mode` defaults to True and is not the user's to switch off.
    user.preferences = {"feature_flags": {"auditee_mode": False, "incidents": False}}
    resolved = resolve_feature_flags(user)
    assert resolved["auditee_mode"] is True  # untouched by the user layer
    assert resolved["incidents"] is False


def test_a_malformed_preference_blob_is_ignored(flags_row, user):
    for blob in (None, [], "incidents", {"feature_flags": "incidents"}):
        user.preferences = blob if isinstance(blob, dict) else {"feature_flags": blob}
        assert get_user_hidden_feature_flags(user) == {}


def test_a_key_the_row_is_missing_reads_false(db, user):
    # `incidents` defaults to True in the serializer but is absent from the row,
    # and `ff_is_enabled` answers False for it. The effective view must agree —
    # offering a module the API refuses is the failure mode.
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
    """The invariant the whole design rests on: what the UI offers is a subset of
    what `ff_is_enabled` permits, so a user can never be shown a module the API
    will refuse."""
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
    """The admin form reads `retrieve` and PUTs the whole body back. If a
    personal hide leaked into it, saving any toggle would take the module away
    from everyone."""
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
    """ "Reset to organization settings" sends every hideable flag as visible.
    Each `true` drops its key rather than storing one, so the user ends up with
    nothing stored and follows the instance again."""
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
