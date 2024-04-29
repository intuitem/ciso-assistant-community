from django.utils.translation import gettext_lazy as _
from re import sub
from enum import Enum
import hashlib


def camel_case(s):
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

    def __str__(self) -> str:
        return self.value


BUILTIN_ROLE_CODENAMES = {
    str(RoleCodename.ADMINISTRATOR): _("Administrator"),
    str(RoleCodename.DOMAIN_MANAGER): _("Domain manager"),
    str(RoleCodename.ANALYST): _("Analyst"),
    str(RoleCodename.APPROVER): _("Approver"),
    str(RoleCodename.READER): _("Reader"),
}

BUILTIN_USERGROUP_CODENAMES = {
    str(UserGroupCodename.ADMINISTRATOR): _("Administrator"),
    str(UserGroupCodename.GLOBAL_READER): _("Reader"),
    str(UserGroupCodename.GLOBAL_APPROVER): _("Approver"),
    str(UserGroupCodename.DOMAIN_MANAGER): _("Domain manager"),
    str(UserGroupCodename.ANALYST): _("Analyst"),
    str(UserGroupCodename.APPROVER): _("Approver"),
    str(UserGroupCodename.READER): _("Reader"),
}

COUNTRY_FLAGS = {
    "fr": "🇫🇷",
    "en": "🇬🇧",
}

LANGUAGES = {
    "fr": _("French"),
    "en": _("English"),
}
