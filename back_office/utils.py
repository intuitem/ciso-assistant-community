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
    ADMINISTRATORS = 'BI-UG-ADM'
    GLOBAL_AUDITORS = 'BI-UG-GAD'
    DOMAIN_MANAGERS = 'BI-UG-DMA'
    ANALYSTS = 'BI-UG-ANA'
    AUDITORS = 'BI-UG-AUD'

    def __str__(self) -> str:
        return self.value

BUILTIN_ROLE_CODENAMES = {
    str(RoleCodename.ADMINISTRATOR): _('Administrator'),
    str(RoleCodename.DOMAIN_MANAGER): _('Domain manager'),
    str(RoleCodename.ANALYST): _('Analyst'),
    str(RoleCodename.AUDITOR): _('Auditor'),
}

BUILTIN_USERGROUP_CODENAMES = {
    str(UserGroupCodename.ADMINISTRATORS): _('Administrators'),
    str(UserGroupCodename.GLOBAL_AUDITORS): _('Global auditors'),
    str(UserGroupCodename.DOMAIN_MANAGERS): _('Domain managers'),
    str(UserGroupCodename.ANALYSTS): _('Analysts'),
    str(UserGroupCodename.AUDITORS): _('Auditors'),
}