import hashlib
from enum import Enum
from re import sub
from typing import Literal

from django.utils.translation import gettext_lazy as _


def camel_case(s):
    if not s:
        return ""
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")

    return "".join([s[0].lower(), s[1:]])


def sha256(string: bytes) -> str:
    """Return the SHA256-hashed hexadecimal representation of the bytes object given as argument."""
    h = hashlib.new("SHA256")
    h.update(string)
    return h.hexdigest()


class RoleCodename(Enum):
    ADMINISTRATOR = "BI-RL-ADM"
    DOMAIN_MANAGER = "BI-RL-DMA"
    ANALYST = "BI-RL-ANA"
    APPROVER = "BI-RL-APP"
    READER = "BI-RL-AUD"
    THIRD_PARTY_RESPONDENT = "BI-RL-TPR"

    def __str__(self) -> str:
        return self.value


class UserGroupCodename(Enum):
    ADMINISTRATOR = "BI-UG-ADM"
    GLOBAL_READER = "BI-UG-GAD"
    GLOBAL_APPROVER = "BI-UG-GAP"
    DOMAIN_MANAGER = "BI-UG-DMA"
    ANALYST = "BI-UG-ANA"
    APPROVER = "BI-UG-APP"
    READER = "BI-UG-AUD"
    THIRD_PARTY_RESPONDENT = "BI-UG-TPR"

    def __str__(self) -> str:
        return self.value


BUILTIN_ROLE_CODENAMES = {
    str(RoleCodename.ADMINISTRATOR): _("Administrator"),
    str(RoleCodename.DOMAIN_MANAGER): _("Domain manager"),
    str(RoleCodename.ANALYST): _("Analyst"),
    str(RoleCodename.APPROVER): _("Approver"),
    str(RoleCodename.READER): _("Reader"),
    str(RoleCodename.THIRD_PARTY_RESPONDENT): _("Third-party respondent"),
}

BUILTIN_USERGROUP_CODENAMES = {
    str(UserGroupCodename.ADMINISTRATOR): _("Administrator"),
    str(UserGroupCodename.GLOBAL_READER): _("Reader"),
    str(UserGroupCodename.GLOBAL_APPROVER): _("Approver"),
    str(UserGroupCodename.DOMAIN_MANAGER): _("Domain manager"),
    str(UserGroupCodename.ANALYST): _("Analyst"),
    str(UserGroupCodename.APPROVER): _("Approver"),
    str(UserGroupCodename.READER): _("Reader"),
    str(UserGroupCodename.THIRD_PARTY_RESPONDENT): _("Third-party respondent"),
}

# NOTE: This is set to "Main" now, but will be changed to a unique identifier
# for internationalization.
MAIN_ENTITY_DEFAULT_NAME = "Main"

COUNTRY_FLAGS = {
    "fr": "🇫🇷",
    "en": "🇬🇧",
}

LANGUAGES = {
    "fr": _("French"),
    "en": _("English"),
}


class VersionFormatError(Exception):
    """Raised when a version string is not properly formatted."""

    pass


def parse_version(version: str) -> list[int]:
    """
    Parses a version string that starts with 'v' and contains dot-separated numbers.
    Accepts strings like 'v1', 'v1.2', or 'v1.2.3'.
    """
    if not version.startswith("v"):
        raise VersionFormatError(f"Version must start with 'v': {version}")
    # Remove leading 'v' and split on dots
    parts = version.lstrip("v").split(".")
    try:
        return [int(part) for part in parts]
    except ValueError:
        raise VersionFormatError(f"Non-numeric version component in {version}")


def compare_versions(
    version_a: str, version_b: str, level: Literal["major", "minor", "patch"] = "patch"
) -> int:
    """
    Compares two version strings at the specified level of granularity.

    Parameters:
        version_a (str): A version string (e.g., 'v1.2.3' or 'v1.2').
        version_b (str): Another version string.
        level (str): Granularity to compare: 'major' (only the first component),
                     'minor' (first two components), or 'patch' (all three components).
                     For example, comparing 'v1.2' with 'v1.2.0' at level='minor' will be equal.

    Returns:
        int: -1 if version_a is lower than version_b;
             0 if they are equal (up to the specified level);
             1 if version_a is greater than version_b.

    Raises:
        VersionFormatError: if either version string is not formatted correctly.
        ValueError: if an invalid level is specified.

    Example:
        >>> compare_versions("v1.2", "v1.2.0", level="minor")
        0
        >>> compare_versions("v1.2.1", "v1.2.0", level="patch")
        1
        >>> compare_versions("v2", "v1.9.9", level="major")
        1
    """
    level_to_parts = {"major": 1, "minor": 2, "patch": 3}
    if level not in level_to_parts:
        raise ValueError(
            "Invalid level specified; choose 'major', 'minor', or 'patch'."
        )
    parts_to_check = level_to_parts[level]

    va = parse_version(version_a)
    vb = parse_version(version_b)

    # Pad with zeros if necessary
    while len(va) < parts_to_check:
        va.append(0)
    while len(vb) < parts_to_check:
        vb.append(0)

    # Compare component-wise using tuple comparison
    if tuple(va[:parts_to_check]) < tuple(vb[:parts_to_check]):
        return -1
    elif tuple(va[:parts_to_check]) > tuple(vb[:parts_to_check]):
        return 1
    return 0
