from django.utils.translation import gettext_lazy as _

BUILTIN_ROLE_CODENAMES = {
    'BI-RL-ADM': _('Administrator'),
    'BI-RL-DMA': _('Domain manager'),
    'BI-RL-ANA': _('Analyst'),
    'BI-RL-AUD': _('Auditor'),
}

BUILTIN_USERGROUP_CODENAMES = {
    'BI-UG-ADM': _('Administrators'),
    'BI-UG-GAD': _('Global auditors'),
    'BI-UG-DMA': _('Domain managers'),
    'BI-UG-ANA': _('Analysts'),
    'BI-UG-AUD': _('Auditors'),
}