"""
Django management command for comprehensive integration testing
"""

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.core.management import call_command
from django.db import connection
from pathlib import Path


class Command(BaseCommand):
    help = 'Run comprehensive integration tests for all bounded contexts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Skip migration testing',
        )
        parser.add_argument(
            '--skip-models',
            action='store_true',
            help='Skip model import testing',
        )
        parser.add_argument(
            '--skip-apis',
            action='store_true',
            help='Skip API testing',
        )

    def handle(self, *args, **options):
        """Run the integration tests"""
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting Comprehensive Integration Tests')
        )

        success = True

        # Test 1: Django Apps
        if not self.test_django_apps():
            success = False

        # Test 2: Migrations (unless skipped)
        if not options['skip_migrations']:
            if not self.test_migrations():
                success = False
        else:
            self.stdout.write('⏭️  Skipping migration tests')

        # Test 3: Model Imports (unless skipped)
        if not options['skip_models']:
            if not self.test_model_imports():
                success = False
        else:
            self.stdout.write('⏭️  Skipping model import tests')

        # Test 4: API Components (unless skipped)
        if not options['skip_apis']:
            if not self.test_api_components():
                success = False
        else:
            self.stdout.write('⏭️  Skipping API tests')

        # Test 5: URL Configuration
        if not self.test_url_configuration():
            success = False

        # Test 6: Cross-Context Relationships
        if not self.test_cross_context_relationships():
            success = False

        # Final Report
        if success:
            self.stdout.write(
                self.style.SUCCESS('🎉 ALL INTEGRATION TESTS PASSED!')
            )
            self.stdout.write(
                self.style.SUCCESS('The CISO Assistant platform is ready for UI/UX development.')
            )
        else:
            self.stdout.write(
                self.style.ERROR('❌ INTEGRATION TESTS FAILED!')
            )
            self.stdout.write(
                self.style.ERROR('Please address the issues before proceeding.')
            )

        return success

    def test_django_apps(self):
        """Test that all Django apps are properly registered"""
        self.stdout.write('\n🔍 Testing Django Apps Registration...')

        expected_apps = [
            'core',
            'core.domain',
            'core.bounded_contexts.organization',
            'core.bounded_contexts.asset_and_service',
            'core.bounded_contexts.control_library',
            'core.bounded_contexts.rmf_operations',
            'core.bounded_contexts.compliance',
            'privacy',
            'risk_registers',
            'security_operations',
            'third_party_management',
            'business_continuity'
        ]

        registered_apps = [app.label for app in apps.get_app_configs()]
        missing_apps = []

        for app_name in expected_apps:
            if app_name in registered_apps:
                self.stdout.write(f'   ✅ {app_name}')
            else:
                self.stdout.write(f'   ❌ {app_name} - NOT REGISTERED')
                missing_apps.append(app_name)

        if missing_apps:
            self.stdout.write(
                self.style.ERROR(f'❌ {len(missing_apps)} apps not registered')
            )
            return False

        self.stdout.write(
            self.style.SUCCESS('✅ All Django apps registered successfully')
        )
        return True

    def test_migrations(self):
        """Test that migrations can be created and validated"""
        self.stdout.write('\n🔍 Testing Migrations...')

        try:
            # Test makemigrations (dry run)
            self.stdout.write('   Testing makemigrations...')
            call_command('makemigrations', dry_run=True, verbosity=0)

            # Test migration validation
            self.stdout.write('   Testing migration validity...')
            call_command('check', verbosity=0)

            self.stdout.write(
                self.style.SUCCESS('✅ Migrations are valid')
            )
            return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Migration test failed: {e}')
            )
            return False

    def test_model_imports(self):
        """Test that all models can be imported"""
        self.stdout.write('\n🔍 Testing Model Imports...')

        model_imports = [
            ('core.bounded_contexts.compliance.models', ['ComplianceAssessment', 'RequirementAssessment', 'ComplianceFinding', 'ComplianceException']),
            ('risk_registers.models', ['AssetRisk', 'RiskRegister']),
            ('privacy.models', ['DataAsset', 'ConsentRecord', 'DataSubjectRight']),
            ('security_operations.models', ['SecurityIncident']),
            ('third_party_management.models', ['ThirdPartyEntity']),
            ('business_continuity.models', ['BCPPlan']),
        ]

        failed_imports = []

        for module_name, model_names in model_imports:
            try:
                module = __import__(module_name, fromlist=model_names)
                for model_name in model_names:
                    if hasattr(module, model_name):
                        self.stdout.write(f'   ✅ {model_name}')
                    else:
                        self.stdout.write(f'   ❌ {model_name} not found in {module_name}')
                        failed_imports.append(f'{module_name}.{model_name}')
            except ImportError as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to import {module_name}: {e}')
                )
                failed_imports.extend([f'{module_name}.{name}' for name in model_names])

        if failed_imports:
            self.stdout.write(
                self.style.ERROR(f'❌ {len(failed_imports)} model import failures')
            )
            return False

        self.stdout.write(
            self.style.SUCCESS('✅ All models imported successfully')
        )
        return True

    def test_api_components(self):
        """Test that all API components can be imported"""
        self.stdout.write('\n🔍 Testing API Components...')

        api_imports = [
            ('core.bounded_contexts.compliance.api.serializers', ['ComplianceAssessmentSerializer', 'RequirementAssessmentSerializer']),
            ('core.bounded_contexts.compliance.api.views', ['ComplianceAssessmentViewSet', 'RequirementAssessmentViewSet']),
            ('risk_registers.api.serializers', ['AssetRiskSerializer', 'RiskRegisterSerializer']),
            ('risk_registers.api.views', ['AssetRiskViewSet', 'RiskRegisterViewSet']),
            ('privacy.api.serializers', ['DataAssetSerializer', 'ConsentRecordSerializer']),
            ('privacy.api.views', ['DataAssetViewSet', 'ConsentRecordViewSet']),
            ('security_operations.api.serializers', ['SecurityIncidentSerializer']),
            ('security_operations.api.views', ['SecurityIncidentViewSet']),
            ('third_party_management.api.serializers', ['ThirdPartyEntitySerializer']),
            ('third_party_management.api.views', ['ThirdPartyEntityViewSet']),
            ('business_continuity.api.serializers', ['BCPPlanSerializer']),
            ('business_continuity.api.views', ['BCPPlanViewSet']),
        ]

        failed_imports = []

        for module_name, component_names in api_imports:
            try:
                module = __import__(module_name, fromlist=component_names)
                for component_name in component_names:
                    if hasattr(module, component_name):
                        self.stdout.write(f'   ✅ {component_name}')
                    else:
                        self.stdout.write(f'   ❌ {component_name} not found in {module_name}')
                        failed_imports.append(f'{module_name}.{component_name}')
            except ImportError as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to import {module_name}: {e}')
                )
                failed_imports.extend([f'{module_name}.{name}' for name in component_names])

        if failed_imports:
            self.stdout.write(
                self.style.ERROR(f'❌ {len(failed_imports)} API component import failures')
            )
            return False

        self.stdout.write(
            self.style.SUCCESS('✅ All API components imported successfully')
        )
        return True

    def test_url_configuration(self):
        """Test that URL patterns are properly configured"""
        self.stdout.write('\n🔍 Testing URL Configuration...')

        try:
            from ciso_assistant.urls import urlpatterns

            expected_paths = [
                'risks/',
                'privacy/',
                'security/',
                'third-party/',
                'business-continuity/',
                'compliance/',  # This might be under control-library or similar
            ]

            found_paths = []
            for pattern in urlpatterns:
                if hasattr(pattern, 'pattern'):
                    path_str = str(pattern.pattern)
                    found_paths.append(path_str)

            missing_paths = []
            for expected_path in expected_paths:
                if any(expected_path in path for path in found_paths):
                    self.stdout.write(f'   ✅ {expected_path}')
                else:
                    self.stdout.write(f'   ❌ {expected_path} not found')
                    missing_paths.append(expected_path)

            if missing_paths:
                self.stdout.write(
                    self.style.ERROR(f'❌ {len(missing_paths)} URL patterns missing')
                )
                return False

            self.stdout.write(
                self.style.SUCCESS('✅ All URL patterns configured')
            )
            return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ URL configuration test failed: {e}')
            )
            return False

    def test_cross_context_relationships(self):
        """Test cross-context relationships"""
        self.stdout.write('\n🔍 Testing Cross-Context Relationships...')

        # Test some basic relationships exist in the models
        relationship_checks = [
            ('AssetRisk', 'risk_registers', ['related_assets', 'related_controls']),
            ('ComplianceAssessment', 'core.bounded_contexts.compliance', ['related_assets', 'related_controls', 'related_risks']),
            ('DataAsset', 'privacy', ['related_assets', 'related_risk_ids']),
            ('SecurityIncident', 'security_operations', ['related_assets', 'related_risks']),
            ('ThirdPartyEntity', 'third_party_management', ['related_assets', 'related_risks']),
            ('BCPPlan', 'business_continuity', ['related_assets', 'related_risks']),
        ]

        failed_checks = []

        for model_name, app_name, expected_fields in relationship_checks:
            try:
                module = __import__(f'{app_name}.models', fromlist=[model_name])
                model_class = getattr(module, model_name)

                missing_fields = []
                for field_name in expected_fields:
                    if not hasattr(model_class, field_name):
                        missing_fields.append(field_name)

                if missing_fields:
                    self.stdout.write(f'   ❌ {model_name} missing fields: {missing_fields}')
                    failed_checks.extend([f'{model_name}.{field}' for field in missing_fields])
                else:
                    self.stdout.write(f'   ✅ {model_name} relationships OK')

            except Exception as e:
                self.stdout.write(f'   ❌ Error checking {model_name}: {e}')
                failed_checks.append(model_name)

        if failed_checks:
            self.stdout.write(
                self.style.ERROR(f'❌ {len(failed_checks)} relationship check failures')
            )
            return False

        self.stdout.write(
            self.style.SUCCESS('✅ All cross-context relationships validated')
        )
        return True
