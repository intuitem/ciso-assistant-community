from django.utils.translation import gettext_lazy as _
from enum import Enum

class RoleCodename(Enum):
    ADMINISTRATOR = 'BI-RL-ADM'
    DOMAIN_MANAGER = 'BI-RL-DMA'
    ANALYST = 'BI-RL-ANA'
    AUDITOR = 'BI-RL-AUD'

    def __str__(self) -> str:
        return self.value

class UserGroupCodename(Enum):
    ADMINISTRATOR = 'BI-UG-ADM'
    GLOBAL_AUDITOR = 'BI-UG-GAD'
    DOMAIN_MANAGER = 'BI-UG-DMA'
    ANALYST = 'BI-UG-ANA'
    AUDITOR = 'BI-UG-AUD'

    def __str__(self) -> str:
        return self.value

BUILTIN_ROLE_CODENAMES = {
    str(RoleCodename.ADMINISTRATOR): _('Administrator'),
    str(RoleCodename.DOMAIN_MANAGER): _('Domain manager'),
    str(RoleCodename.ANALYST): _('Analyst'),
    str(RoleCodename.AUDITOR): _('Auditor'),
}

BUILTIN_USERGROUP_CODENAMES = {
    str(UserGroupCodename.ADMINISTRATOR): _('Administrator'),
    str(UserGroupCodename.GLOBAL_AUDITOR): _('Auditor'),
    str(UserGroupCodename.DOMAIN_MANAGER): _('Domain manager'),
    str(UserGroupCodename.ANALYST): _('Analyst'),
    str(UserGroupCodename.AUDITOR): _('Auditor'),
}

COUNTRY_FLAGS = {
    'ar': '🇸🇦',
    'fr': '🇫🇷',
    'en': '🇬🇧',
}

LANGUAGES = {
    'ar': _('Arabic'),
    'fr': _('French'),
    'en': _('English'),
}