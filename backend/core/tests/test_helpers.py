from django.contrib.auth.models import Permission
import pytest
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from core.helpers import get_rating_options, get_rating_options_abbr
from core.models import (
    Perimeter,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    StoredLibrary,
)
from core.utils import (
    VersionFormatError,
    compare_versions,
    parse_version,
    compare_schema_versions,
)
from iam.models import Folder, Role, RoleAssignment, User


@pytest.fixture
def risk_matrix_fixture():
    library = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:critical_risk_matrix_5x5"
    ).last()
    assert library is not None
    library.load()


@pytest.mark.django_db
def test_get_rating_options_no_matrix():
    user = User.objects.create(email="test@test.com", password="test")
    assert get_rating_options(user) == []


@pytest.mark.usefixtures("risk_matrix_fixture")
@pytest.mark.django_db
def test_get_rating_options_no_perm_to_view_matrix(risk_matrix_fixture):
    user = User.objects.create(email="test@test.com", password="test")
    assert get_rating_options(user) == []


@pytest.mark.usefixtures("risk_matrix_fixture")
@pytest.mark.django_db
def test_get_rating_options_perm_to_view_matrix():
    user = User.objects.create(email="test@test.com", password="test")
    folder = Folder.objects.create(
        name="test",
        content_type=Folder.ContentType.DOMAIN,
        builtin=False,
        parent_folder=Folder.objects.get(content_type=Folder.ContentType.ROOT),
    )
    perimeter = Perimeter.objects.create(name="test", folder=folder)
    risk_assessment = RiskAssessment.objects.create(
        name="test",
        perimeter=perimeter,
        risk_matrix=RiskMatrix.objects.latest("created_at"),
    )
    RiskScenario.objects.create(name="test", risk_assessment=risk_assessment)
    role = Role.objects.create(name="test")
    reader_permissions = Permission.objects.filter(
        codename__in=[
            "view_perimeter",
            "view_riskassessment",
            "view_appliedcontrol",
            "view_riskscenario",
            "view_riskacceptance",
            "view_asset",
            "view_threat",
            "view_referencecontrol",
            "view_folder",
            "view_usergroup",
        ]
    )
    role.permissions.set(reader_permissions)
    role.save()
    role_assignment = RoleAssignment.objects.create(
        user=user,
        role=role,
        folder=folder,
        is_recursive=True,
    )
    role_assignment.perimeter_folders.add(folder)
    role_assignment.save()

    assert get_rating_options(user) == [
        (0, _("Very Low")),
        (1, _("Low")),
        (2, _("Medium")),
        (3, _("High")),
        (4, _("Very High")),
    ]


@pytest.mark.django_db
def test_get_rating_options_abbr_no_matrix():
    user = User.objects.create(email="test@test.com", password="test")
    assert get_rating_options_abbr(user) == []


@pytest.mark.usefixtures("risk_matrix_fixture")
@pytest.mark.django_db
def test_get_rating_options_abbr_no_perm_to_view_matrix(risk_matrix_fixture):
    user = User.objects.create(email="test@test.com", password="test")
    assert get_rating_options_abbr(user) == []


@pytest.mark.usefixtures("risk_matrix_fixture")
@pytest.mark.django_db
def test_get_rating_options_abbr_perm_to_view_matrix():
    user = User.objects.create(email="test@test.com", password="test")
    folder = Folder.objects.create(
        name="test",
        content_type=Folder.ContentType.DOMAIN,
        builtin=False,
        parent_folder=Folder.objects.get(content_type=Folder.ContentType.ROOT),
    )
    perimeter = Perimeter.objects.create(name="test", folder=folder)
    risk_assessment = RiskAssessment.objects.create(
        name="test",
        perimeter=perimeter,
        risk_matrix=RiskMatrix.objects.latest("created_at"),
    )
    RiskScenario.objects.create(name="test", risk_assessment=risk_assessment)
    role = Role.objects.create(name="test")
    reader_permissions = Permission.objects.filter(
        codename__in=[
            "view_perimeter",
            "view_riskassessment",
            "view_appliedcontrol",
            "view_riskscenario",
            "view_riskacceptance",
            "view_asset",
            "view_threat",
            "view_referencecontrol",
            "view_folder",
            "view_usergroup",
        ]
    )
    role.permissions.set(reader_permissions)
    role.save()
    role_assignment = RoleAssignment.objects.create(
        user=user,
        role=role,
        folder=folder,
        is_recursive=True,
    )
    role_assignment.perimeter_folders.add(folder)
    role_assignment.save()

    assert get_rating_options_abbr(user) == [
        ("VL", _("Very Low")),
        ("L", _("Low")),
        ("M", _("Medium")),
        ("H", _("High")),
        ("VH", _("Very High")),
    ]


# --- Tests for parse_version ---


def test_parse_version_single_component():
    assert parse_version("v1") == [1]


def test_parse_version_two_components():
    assert parse_version("v1.2") == [1, 2]


def test_parse_version_three_components():
    assert parse_version("v1.2.3") == [1, 2, 3]


def test_parse_version_invalid_missing_v():
    with pytest.raises(VersionFormatError) as exc_info:
        parse_version("1.2.3")
    assert "must start with 'v'" in str(exc_info.value)


def test_parse_version_invalid_non_numeric():
    with pytest.raises(VersionFormatError) as exc_info:
        parse_version("v1.2.a")
    assert "Non-numeric version component" in str(exc_info.value)


# --- Tests for compare_versions ---
# Using parametrize to cover multiple scenarios


@pytest.mark.parametrize(
    "version_a, version_b, level, expected",
    [
        # When comparing only major versions
        ("v1.2", "v1.9.9", "major", 0),  # both major=1
        ("v2", "v1.9.9", "major", 1),  # 2 > 1
        ("v1", "v2.0.0", "major", -1),  # 1 < 2
        # When comparing major+minor (padding shorter versions with zeros)
        ("v1.2", "v1.2.0", "minor", 0),  # [1,2] vs [1,2]
        ("v1.1", "v1.2", "minor", -1),  # [1,1] vs [1,2]
        ("v1.2", "v1.1", "minor", 1),  # [1,2] vs [1,1]
        # When comparing patch (all three components)
        ("v1.2.1", "v1.2.0", "patch", 1),  # [1,2,1] > [1,2,0]
        ("v1.2", "v1.2.1", "patch", -1),  # "v1.2" becomes [1,2,0] vs [1,2,1]
        ("v1.2.5", "v1.2.5", "patch", 0),  # identical values
        # Mixing shorter version strings with extra components in one version
        ("v1.2", "v1.2.0", "patch", 0),  # [1,2,0] vs [1,2,0]
    ],
)
def test_compare_versions(version_a, version_b, level, expected):
    result = compare_versions(version_a, version_b, level)
    assert result == expected


def test_compare_versions_invalid_level():
    with pytest.raises(ValueError) as exc_info:
        compare_versions("v1.2", "v1.3", level="invalid")
    assert "Invalid level" in str(exc_info.value)


def test_compare_versions_invalid_version_a():
    with pytest.raises(VersionFormatError):
        compare_versions("1.2", "v1.2")


def test_compare_versions_invalid_version_b():
    with pytest.raises(VersionFormatError):
        compare_versions("v1.2", "1.2")


def test_compare_versions_padding_behavior():
    # "v1" should be padded to [1, 0, 0] at patch level
    assert compare_versions("v1", "v1.0.0", level="patch") == 0
    # When comparing "v1.2.3" vs "v1.2" at minor level,
    # "v1.2" is padded to [1, 2] so they compare equal.
    assert compare_versions("v1.2.3", "v1.2", level="minor") == 0


# --- Example of comparing using all levels ---
def test_compare_versions_different_levels():
    # Even if patch level distinguishes, at minor level they might be equal.
    assert compare_versions("v1.2.1", "v1.2.0", level="patch") == 1
    assert compare_versions("v1.2.1", "v1.2.0", level="minor") == 0


# NOTE: These tests rely on the behavior defined in compare_schema_versions.
#       When schema_ver_a is provided (not None):
#         - If schema_ver_a equals schema_ver_b, the function succeeds.
#         - Otherwise, it raises a ValidationError with {"error": "backupGreaterVersionError"}.
#       When schema_ver_a is None (fallback to semantic version check):
#         - It uses compare_versions(version_a, version_b, level="minor").
#         - If the backup version (version_a) is greater than the current (version_b), it
#           raises a ValidationError with {"error": "backupGreaterVersionError"}.
#         - If version_a is less than version_b, it raises a ValidationError with
#           {"error": "importVersionNotCompatibleWithCurrentVersion"}.
#         - If they compare equal at the minor level, the function succeeds.


# Test case 1: Happy path – schema version provided and matches current schema version.
def test_schema_version_match():
    schema_ver_a = 2
    schema_ver_b = 2
    version_a = "v1.2.3"
    version_b = "v1.2.3"
    # Should not raise any error
    compare_schema_versions(schema_ver_a, version_a, version_b, schema_ver_b)


# Test case 2: Unhappy path – schema version provided but does not match current schema version.
def test_schema_version_mismatch():
    schema_ver_a = 3
    schema_ver_b = 2
    version_a = "v1.2.3"
    version_b = "v1.2.3"
    with pytest.raises(ValidationError) as excinfo:
        compare_schema_versions(schema_ver_a, version_a, version_b, schema_ver_b)
    # Verify that the error message corresponds to the backup version being greater.
    assert excinfo.value.args[0]["error"] == "backupGreaterVersionError"


# Test case 3: Happy path – no schema version provided and backup version equals current version.
def test_semver_equal_no_schema():
    schema_ver_a = None
    # Using versions that are equal at the 'minor' level.
    version_a = "v1.2.0"
    version_b = "v1.2"  # compare_versions pads "v1.2" to "v1.2.0" for a 'minor' check
    # Should not raise an error because compare_versions("v1.2.0", "v1.2", level="minor") returns 0.
    compare_schema_versions(schema_ver_a, version_a, version_b, schema_ver_b=1)


# Test case 4: Unhappy path – no schema version provided and backup version is greater than current version.
def test_semver_backup_greater():
    schema_ver_a = None
    # At 'minor' level, [1, 3] > [1, 2]
    version_a = "v1.3.0"
    version_b = "v1.2.9"
    with pytest.raises(ValidationError) as excinfo:
        compare_schema_versions(schema_ver_a, version_a, version_b, schema_ver_b=1)
    assert excinfo.value.args[0]["error"] == "backupGreaterVersionError"


# Test case 5: Unhappy path – no schema version provided and backup version is lower than current version.
def test_semver_backup_less():
    schema_ver_a = None
    # At 'minor' level, [1, 1] < [1, 2]
    version_a = "v1.1.0"
    version_b = "v1.2.0"
    with pytest.raises(ValidationError) as excinfo:
        compare_schema_versions(schema_ver_a, version_a, version_b, schema_ver_b=1)
    assert (
        excinfo.value.args[0]["error"] == "importVersionNotCompatibleWithCurrentVersion"
    )


# Test case 6: Edge case – version strings missing the patch version.
def test_version_edge_case_padding():
    schema_ver_a = None
    # "1.2" should be padded to "1.2.0" for comparison
    version_a = "v1.2"
    version_b = "v1.2.0"
    # They are equal at the 'minor' level (i.e. [1, 2] == [1, 2]).
    compare_schema_versions(schema_ver_a, version_a, version_b, schema_ver_b=1)


# Test case 7: Edge case – invalid semantic version string.
def test_invalid_semver_format():
    schema_ver_a = None
    version_a = (
        "invalid_version"  # This should trigger a formatting error in compare_versions.
    )
    version_b = "1.2.3"
    with pytest.raises(VersionFormatError):
        compare_schema_versions(schema_ver_a, version_a, version_b, schema_ver_b=1)


# --- Additional tests for core.utils functions ---


def test_sizeof_json_dict():
    """Test sizeof_json with a dictionary"""
    from core.utils import sizeof_json

    obj = {"key": "value", "number": 42}
    result = sizeof_json(obj)
    assert result > 0
    assert isinstance(result, int)


def test_sizeof_json_bytes():
    """Test sizeof_json with bytes input"""
    from core.utils import sizeof_json

    obj = b"test bytes"
    result = sizeof_json(obj)
    assert result == len(obj)


def test_sizeof_json_bytearray():
    """Test sizeof_json with bytearray input"""
    from core.utils import sizeof_json

    obj = bytearray(b"test bytearray")
    result = sizeof_json(obj)
    assert result == len(obj)


def test_sizeof_json_memoryview():
    """Test sizeof_json with memoryview input"""
    from core.utils import sizeof_json

    obj = memoryview(b"test memoryview")
    result = sizeof_json(obj)
    assert result == len(obj)


def test_camel_case_standard():
    """Test camel_case with standard inputs"""
    from core.utils import camel_case

    assert camel_case("hello_world") == "helloWorld"
    assert camel_case("test-case") == "testCase"
    assert camel_case("multiple_word_test") == "multipleWordTest"


def test_camel_case_empty():
    """Test camel_case with empty string"""
    from core.utils import camel_case

    assert camel_case("") == ""
    assert camel_case(None) == ""


def test_camel_case_single_word():
    """Test camel_case with single word"""
    from core.utils import camel_case

    assert camel_case("hello") == "hello"


def test_camel_case_mixed_separators():
    """Test camel_case with mixed separators"""
    from core.utils import camel_case

    assert camel_case("hello_world-test") == "helloWorldTest"


def test_sha256_hash():
    """Test sha256 hash function"""
    from core.utils import sha256

    result = sha256(b"test string")
    assert len(result) == 64  # SHA256 produces 64 hex characters
    assert isinstance(result, str)
    # Test consistency
    assert sha256(b"test string") == sha256(b"test string")
    # Test different inputs produce different hashes
    assert sha256(b"test1") != sha256(b"test2")


def test_time_state_future():
    """Test time_state with future date"""
    from core.utils import time_state
    from datetime import datetime, timedelta

    future_date = (datetime.now() + timedelta(days=10)).isoformat()
    result = time_state(future_date)
    assert result["name"] == "incoming"
    assert result["hexcolor"] == "#93c5fd"


def test_time_state_past():
    """Test time_state with past date"""
    from core.utils import time_state
    from datetime import datetime, timedelta

    past_date = (datetime.now() - timedelta(days=10)).isoformat()
    result = time_state(past_date)
    assert result["name"] == "outdated"
    assert result["hexcolor"] == "#f87171"


def test_get_auditee_filtered_folder_ids_no_assignments():
    """Test get_auditee_filtered_folder_ids with no assignments"""
    from core.utils import get_auditee_filtered_folder_ids
    from iam.models import User

    user = User.objects.create(email="test@example.com")
    result = get_auditee_filtered_folder_ids(user)
    assert isinstance(result, set)


def test_schema_version_lower():
    """Test compare_schema_versions when backup schema is lower"""
    schema_ver_a = 1
    schema_ver_b = 2
    version_a = "v1.2.3"
    version_b = "v1.2.3"
    with pytest.raises(ValidationError) as excinfo:
        compare_schema_versions(schema_ver_a, version_a, version_b, schema_ver_b)
    assert excinfo.value.args[0]["error"] == "backupLowerVersionError"