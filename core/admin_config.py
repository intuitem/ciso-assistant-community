# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _

config = {
    'SITE_TITLE': 'MIRA',
    'INDEX_TITLE': _('Back office'),
    'MENU_TITLE': _('Menu'),
}

def get_config(key):
    value = config.get(key, None)
    return value
