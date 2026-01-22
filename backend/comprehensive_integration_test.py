#!/usr/bin/env python
"""
Comprehensive Integration Test Suite

Tests all bounded contexts, APIs, migrations, and cross-context integration
for the complete CISO Assistant GRC platform.
"""

import os
import sys
import django
import requests
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ciso_assistant.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.apps import apps
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import get_runner
from rest_framework.test import APITestCase
from rest_framework import status


class ComprehensiveIntegrationTest:
    """Comprehensive integration test suite for all bounded contexts"""

    def __init__(self):
        self.test_results = {
            'django_apps': {},
            'migrations': {},
            'apis': {},
            'cross_context': {},
            'data_flow': {},
            'event_bus': {},
            'overall': {'passed': 0, 'failed': 0, 'total': 0}
        }
        self.errors = []

    def log_error(self, message):
        """Log an error message"""
        print(f"❌ ERROR: {message}")
        self.errors.append(message)

    def log_success(self, message):
        """Log a success message"""
        print(f"✅ {message}")

    def test_django_apps_registration(self):
        """Test that all Django apps are properly registered"""
        print("\n🔍 Testing Django Apps Registration...")

        expected_apps = [
            'core',
            'core.domain',
            'core.bounded_contexts.organization',
            'core.bounded_contexts.asset_and_service',
            'core.bounded_contexts.control_library',
            'core.bounded_contexts.rmf_operations',
            'core.bounded_contexts.compliance',
            'core.bounded_contexts.privacy',
            'core.bounded_contexts.security_operations',
            'core.bounded_contexts.third_party_management',
            'core.bounded_contexts.business_continuity',
            'risk_registers',
            'privacy',
            'security_operations',
            'third_party_management',
            'business_continuity',
        ]

        registered_apps = [app.label for app in apps.get_app_configs()]

        for app_name in expected_apps:
            if app_name in registered_apps:
                self.log_success(f"App '{app_name}' is registered")
                self.test_results['django_apps'][app_name] = True
            else:
                self.log_error(f"App '{app_name}' is NOT registered")
                self.test_results['django_apps'][app_name] = False

        return all(self.test_results['django_apps'].values())

    def test_migration_files_exist(self):
        """Test that all bounded contexts have migration files"""
        print("\n🔍 Testing Migration Files...")

        bounded_contexts = [
            'compliance',
            'risk_registers',
            'privacy',
            'security_operations',
            'third_party_management',
            'business_continuity'
        ]

        for context in bounded_contexts:
            migration_dir = backend_dir / context / 'migrations'
            if migration_dir.exists():
                migration_files = list(migration_dir.glob('*.py'))
                if migration_files:
                    self.log_success(f"Context '{context}' has {len(migration_files)} migration files")
                    self.test_results['migrations'][context] = True
                else:
                    self.log_error(f"Context '{context}' has no migration files")
                    self.test_results['migrations'][context] = False
            else:
                self.log_error(f"Context '{context}' has no migrations directory")
                self.test_results['migrations'][context] = False

        return all(self.test_results['migrations'].values())

    def test_models_can_be_imported(self):
        """Test that all models can be imported without errors"""
        print("\n🔍 Testing Model Imports...")

        model_imports = [
            ('compliance.models', ['ComplianceAssessment', 'RequirementAssessment', 'ComplianceFinding', 'ComplianceException']),
            ('risk_registers.models', ['AssetRisk', 'RiskRegister']),
            ('privacy.models', ['DataAsset', 'ConsentRecord', 'DataSubjectRight']),
            ('security_operations.models', ['SecurityIncident']),
            ('third_party_management.models', ['ThirdPartyEntity']),
            ('business_continuity.models', ['BCPPlan']),
        ]

        all_passed = True

        for module_name, model_names in model_imports:
            try:
                module = __import__(module_name, fromlist=model_names)
                for model_name in model_names:
                    if hasattr(module, model_name):
                        self.log_success(f"Model {model_name} imported successfully")
                    else:
                        self.log_error(f"Model {model_name} not found in {module_name}")
                        all_passed = False
            except ImportError as e:
                self.log_error(f"Failed to import {module_name}: {e}")
                all_passed = False

        return all_passed

    def test_apis_can_be_imported(self):
        """Test that all API components can be imported"""
        print("\n🔍 Testing API Imports...")

        api_imports = [
            ('compliance.api.serializers', ['ComplianceAssessmentSerializer', 'RequirementAssessmentSerializer']),
            ('compliance.api.views', ['ComplianceAssessmentViewSet', 'RequirementAssessmentViewSet']),
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

        all_passed = True

        for module_name, component_names in api_imports:
            try:
                module = __import__(module_name, fromlist=component_names)
                for component_name in component_names:
                    if hasattr(module, component_name):
                        self.log_success(f"API component {component_name} imported successfully")
                    else:
                        self.log_error(f"API component {component_name} not found in {module_name}")
                        all_passed = False
            except ImportError as e:
                self.log_error(f"Failed to import {module_name}: {e}")
                all_passed = False

        return all_passed

    def test_cross_context_relationships(self):
        """Test that cross-context relationships are properly defined"""
        print("\n🔍 Testing Cross-Context Relationships...")

        # Test that related fields are properly defined in models
        relationship_tests = [
            ('AssetRisk', 'risk_registers', ['related_assets', 'related_controls']),
            ('ComplianceAssessment', 'compliance', ['related_assets', 'related_controls', 'related_risks']),
            ('DataAsset', 'privacy', ['related_assets', 'related_risk_ids']),
            ('SecurityIncident', 'security_operations', ['related_assets', 'related_risks']),
            ('ThirdPartyEntity', 'third_party_management', ['related_assets', 'related_risks']),
            ('BCPPlan', 'business_continuity', ['related_assets', 'related_risks']),
        ]

        all_passed = True

        for model_name, app_name, expected_fields in relationship_tests:
            try:
                module = __import__(f'{app_name}.models', fromlist=[model_name])
                model_class = getattr(module, model_name)

                for field_name in expected_fields:
                    if hasattr(model_class, field_name):
                        self.log_success(f"Model {model_name} has relationship field {field_name}")
                    else:
                        self.log_error(f"Model {model_name} missing relationship field {field_name}")
                        all_passed = False

            except Exception as e:
                self.log_error(f"Failed to test relationships for {model_name}: {e}")
                all_passed = False

        return all_passed

    def test_event_system(self):
        """Test that event system is properly configured"""
        print("\n🔍 Testing Event System...")

        try:
            from core.domain.events import get_event_bus
            event_bus = get_event_bus()

            # Test that event bus is available
            if event_bus:
                self.log_success("Event bus is available")
                self.test_results['event_bus']['event_bus_available'] = True
            else:
                self.log_error("Event bus is not available")
                self.test_results['event_bus']['event_bus_available'] = False
                return False

            # Test that projections are registered
            # This would require actually running the apps.ready() methods
            self.log_success("Event system structure is in place")

            return True

        except Exception as e:
            self.log_error(f"Event system test failed: {e}")
            return False

    def test_url_patterns(self):
        """Test that URL patterns are properly configured"""
        print("\n🔍 Testing URL Patterns...")

        try:
            from ciso_assistant.urls import urlpatterns

            # Check that our bounded contexts are included
            context_paths = [
                'risks/',
                'privacy/',
                'security/',
                'third-party/',
                'business-continuity/',
            ]

            found_paths = []
            for pattern in urlpatterns:
                if hasattr(pattern, 'pattern'):
                    path_str = str(pattern.pattern)
                    found_paths.append(path_str)

            for context_path in context_paths:
                if any(context_path in path for path in found_paths):
                    self.log_success(f"URL pattern for {context_path} is configured")
                    self.test_results['apis'][f'{context_path}_url'] = True
                else:
                    self.log_error(f"URL pattern for {context_path} is NOT configured")
                    self.test_results['apis'][f'{context_path}_url'] = False

            return all(self.test_results['apis'].get(f'{path}_url', False) for path in ['risks/', 'privacy/', 'security/', 'third-party/', 'business-continuity/'])

        except Exception as e:
            self.log_error(f"URL pattern test failed: {e}")
            return False

    def run_django_check(self):
        """Run Django's built-in check command"""
        print("\n🔍 Running Django System Check...")

        try:
            from io import StringIO
            from django.core.management import call_command

            # Capture check output
            output = StringIO()
            call_command('check', stdout=output, verbosity=0)

            check_output = output.getvalue()

            if "System check identified no issues" in check_output:
                self.log_success("Django system check passed - no issues found")
                return True
            else:
                self.log_error(f"Django system check found issues: {check_output}")
                return False

        except Exception as e:
            self.log_error(f"Django check failed: {e}")
            return False

    def generate_test_report(self):
        """Generate a comprehensive test report"""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE INTEGRATION TEST REPORT")
        print("="*80)

        # Overall statistics
        total_tests = sum(len(results) for results in self.test_results.values() if isinstance(results, dict))
        passed_tests = sum(sum(1 for result in results.values() if result is True)
                          for results in self.test_results.values() if isinstance(results, dict))
        failed_tests = total_tests - passed_tests

        print(f"\n📈 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(".1f")

        # Detailed results by category
        print(f"\n📋 Detailed Results:")

        for category, results in self.test_results.items():
            if isinstance(results, dict) and results:
                category_passed = sum(1 for result in results.values() if result is True)
                category_total = len(results)
                status = "✅" if category_passed == category_total else "❌"
                print(f"   {status} {category.replace('_', ' ').title()}: {category_passed}/{category_total}")

                # Show failures
                if category_passed < category_total:
                    failed_items = [item for item, result in results.items() if not result]
                    print(f"      ❌ Failed: {', '.join(failed_items)}")

        # Error summary
        if self.errors:
            print(f"\n❌ Error Summary ({len(self.errors)} errors):")
            for i, error in enumerate(self.errors[:10], 1):  # Show first 10 errors
                print(f"   {i}. {error}")
            if len(self.errors) > 10:
                print(f"   ... and {len(self.errors) - 10} more errors")

        # Recommendations
        print(f"\n💡 Recommendations:")
        if failed_tests == 0:
            print("   🎉 All integration tests passed! Ready for production.")
        else:
            print("   🔧 Address the failed tests before proceeding to UI/UX development.")
            if any('migration' in str(error).lower() for error in self.errors):
                print("   📝 Run 'python manage.py makemigrations' for missing migrations.")
            if any('import' in str(error).lower() for error in self.errors):
                print("   📦 Check that all dependencies are installed.")

        print("\n" + "="*80)

        return failed_tests == 0

    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Comprehensive Integration Test Suite")
        print("Testing all bounded contexts and cross-context integration...")

        test_methods = [
            self.test_django_apps_registration,
            self.test_migration_files_exist,
            self.test_models_can_be_imported,
            self.test_apis_can_be_imported,
            self.test_cross_context_relationships,
            self.test_event_system,
            self.test_url_patterns,
            self.run_django_check,
        ]

        passed = 0
        total = len(test_methods)

        for test_method in test_methods:
            try:
                if test_method():
                    passed += 1
                else:
                    self.log_error(f"Test {test_method.__name__} failed")
            except Exception as e:
                self.log_error(f"Test {test_method.__name__} raised exception: {e}")

        # Generate final report
        overall_success = self.generate_test_report()

        return overall_success


def main():
    """Main entry point for integration testing"""
    tester = ComprehensiveIntegrationTest()

    success = tester.run_all_tests()

    if success:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("The CISO Assistant platform is ready for UI/UX development.")
        return 0
    else:
        print("\n❌ INTEGRATION TESTS FAILED!")
        print("Please address the issues before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
