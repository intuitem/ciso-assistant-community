from django.apps import apps
from django.test import TestCase

from tprm.apps import TprmConfig


class TestTprmConfig(TestCase):
    def test_app_config(self):
        """Testing the TPRM application configuration."""
        self.assertEqual(TprmConfig.name, 'tprm')
        self.assertEqual(TprmConfig.default_auto_field, 'django.db.models.BigAutoField')
        
    def test_app_is_loaded(self):
        """Check that the application is loaded correctly."""
        self.assertTrue('tprm' in apps.app_configs)
        app_config = apps.get_app_config('tprm')
        self.assertIsInstance(app_config, TprmConfig)