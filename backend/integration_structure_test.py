#!/usr/bin/env python
"""
Integration Structure Test Suite

Tests the file structure and basic imports for all bounded contexts
without requiring Django to be fully configured.
"""

import os
import sys
from pathlib import Path

# Backend directory
backend_dir = Path(__file__).parent

class StructureIntegrationTest:
    """Test the structure and basic imports of all bounded contexts"""

    def __init__(self):
        self.results = {
            'directories': {},
            'files': {},
            'imports': {},
            'overall': {'passed': 0, 'failed': 0, 'total': 0}
        }
        self.errors = []

    def log_error(self, message):
        print(f"❌ {message}")
        self.errors.append(message)

    def log_success(self, message):
        print(f"✅ {message}")

    def test_directory_structure(self):
        """Test that all required directories exist"""
        print("\n🏗️  Testing Directory Structure...")

        expected_contexts = [
            'compliance',
            'risk_registers',
            'privacy',
            'security_operations',
            'third_party_management',
            'business_continuity'
        ]

        expected_subdirs = ['models', 'repositories', 'services', 'api', 'tests']

        all_passed = True

        for context in expected_contexts:
            context_dir = backend_dir / context
            if context_dir.exists():
                self.log_success(f"Context directory '{context}' exists")

                # Check subdirectories
                for subdir in expected_subdirs:
                    sub_path = context_dir / subdir
                    if sub_path.exists():
                        self.log_success(f"  ├── {subdir}/ exists")
                    else:
                        self.log_error(f"  ├── {subdir}/ missing")
                        all_passed = False

                self.results['directories'][context] = True
            else:
                self.log_error(f"Context directory '{context}' missing")
                self.results['directories'][context] = False
                all_passed = False

        return all_passed

    def test_file_structure(self):
        """Test that all required files exist"""
        print("\n📄 Testing File Structure...")

        file_requirements = {
            'compliance': {
                'models/__init__.py': ['ComplianceAssessment', 'RequirementAssessment', 'ComplianceFinding', 'ComplianceException'],
                'repositories/__init__.py': ['ComplianceAssessmentRepository'],
                'services/__init__.py': ['ComplianceAssessmentService'],
                'api/serializers.py': ['ComplianceAssessmentSerializer'],
                'api/views.py': ['ComplianceAssessmentViewSet'],
                'api/urls.py': ['router'],
                'apps.py': ['ComplianceConfig'],
            },
            'risk_registers': {
                'models/__init__.py': ['AssetRisk', 'RiskRegister'],
                'repositories/__init__.py': ['AssetRiskRepository', 'RiskRegisterRepository'],
                'services/__init__.py': ['RiskAssessmentService', 'RiskReportingService'],
                'api/serializers.py': ['AssetRiskSerializer', 'RiskRegisterSerializer'],
                'api/views.py': ['AssetRiskViewSet', 'RiskRegisterViewSet'],
                'apps.py': ['RiskRegistersConfig'],
            },
            'privacy': {
                'models/__init__.py': ['DataAsset', 'ConsentRecord', 'DataSubjectRight'],
                'repositories/__init__.py': ['DataAssetRepository', 'ConsentRecordRepository', 'DataSubjectRightRepository'],
                'services/__init__.py': ['PrivacyAssessmentService'],
                'api/serializers.py': ['DataAssetSerializer', 'ConsentRecordSerializer', 'DataSubjectRightSerializer'],
                'api/views.py': ['DataAssetViewSet', 'ConsentRecordViewSet', 'DataSubjectRightViewSet'],
                'apps.py': ['PrivacyConfig'],
            },
            'security_operations': {
                'models/__init__.py': ['SecurityIncident'],
                'repositories/__init__.py': ['SecurityIncidentRepository'],
                'services/__init__.py': [],  # Services can be empty for now
                'api/serializers.py': ['SecurityIncidentSerializer'],
                'api/views.py': ['SecurityIncidentViewSet'],
                'apps.py': ['SecurityOperationsConfig'],
            },
            'third_party_management': {
                'models/__init__.py': ['ThirdPartyEntity'],
                'repositories/__init__.py': [],  # Repositories can be empty for now
                'services/__init__.py': [],  # Services can be empty for now
                'api/serializers.py': ['ThirdPartyEntitySerializer'],
                'api/views.py': ['ThirdPartyEntityViewSet'],
                'apps.py': ['ThirdPartyManagementConfig'],
            },
            'business_continuity': {
                'models/__init__.py': ['BCPPlan'],
                'repositories/__init__.py': [],  # Repositories can be empty for now
                'services/__init__.py': [],  # Services can be empty for now
                'api/serializers.py': ['BCPPlanSerializer'],
                'api/views.py': ['BCPPlanViewSet'],
                'apps.py': ['BusinessContinuityConfig'],
            }
        }

        all_passed = True

        for context, files in file_requirements.items():
            context_dir = backend_dir / context
            if not context_dir.exists():
                continue

            for file_path, expected_components in files.items():
                full_path = context_dir / file_path
                if full_path.exists():
                    self.log_success(f"{context}/{file_path} exists")
                    self.results['files'][f"{context}/{file_path}"] = True

                    # Test file content if it has expected components
                    if expected_components:
                        try:
                            with open(full_path, 'r') as f:
                                content = f.read()

                            missing_components = []
                            for component in expected_components:
                                if component not in content:
                                    missing_components.append(component)

                            if missing_components:
                                self.log_error(f"  Missing components in {context}/{file_path}: {missing_components}")
                                all_passed = False
                            else:
                                self.log_success(f"  All expected components found in {context}/{file_path}")

                        except Exception as e:
                            self.log_error(f"  Error reading {context}/{file_path}: {e}")
                            all_passed = False
                else:
                    self.log_error(f"{context}/{file_path} missing")
                    self.results['files'][f"{context}/{file_path}"] = False
                    all_passed = False

        return all_passed

    def test_django_settings(self):
        """Test that Django settings include all bounded contexts"""
        print("\n⚙️  Testing Django Settings...")

        settings_file = backend_dir / 'ciso_assistant' / 'settings.py'

        if not settings_file.exists():
            self.log_error("Django settings file not found")
            return False

        try:
            with open(settings_file, 'r') as f:
                settings_content = f.read()

            expected_apps = [
                'privacy',  # This one was already there
                'risk_registers',
                'security_operations',
                'third_party_management',
                'business_continuity'
            ]

            all_found = True
            for app in expected_apps:
                if app in settings_content:
                    self.log_success(f"App '{app}' found in INSTALLED_APPS")
                else:
                    self.log_error(f"App '{app}' NOT found in INSTALLED_APPS")
                    all_found = False

            return all_found

        except Exception as e:
            self.log_error(f"Error reading settings file: {e}")
            return False

    def test_url_configuration(self):
        """Test that URLs are properly configured"""
        print("\n🔗 Testing URL Configuration...")

        urls_file = backend_dir / 'core' / 'urls.py'

        if not urls_file.exists():
            self.log_error("Core URLs file not found")
            return False

        try:
            with open(urls_file, 'r') as f:
                urls_content = f.read()

            expected_paths = [
                'risks/',
                'privacy/',
                'security/',
                'third-party/',
                'business-continuity/'
            ]

            all_found = True
            for path in expected_paths:
                if path in urls_content:
                    self.log_success(f"URL path '{path}' found in configuration")
                else:
                    self.log_error(f"URL path '{path}' NOT found in configuration")
                    all_found = False

            return all_found

        except Exception as e:
            self.log_error(f"Error reading URLs file: {e}")
            return False

    def test_migration_structure(self):
        """Test that migrations are properly structured"""
        print("\n🗃️  Testing Migration Structure...")

        contexts_with_migrations = ['compliance', 'risk_registers']

        all_passed = True

        for context in contexts_with_migrations:
            migration_dir = backend_dir / context / 'migrations'
            if migration_dir.exists():
                migration_files = list(migration_dir.glob('*.py'))
                if migration_files:
                    self.log_success(f"{context} has {len(migration_files)} migration files")
                else:
                    self.log_error(f"{context} has migration directory but no files")
                    all_passed = False
            else:
                self.log_error(f"{context} missing migrations directory")
                all_passed = False

        return all_passed

    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n" + "="*80)
        print("📊 INTEGRATION STRUCTURE TEST REPORT")
        print("="*80)

        # Overall statistics
        total_tests = len(self.results['directories']) + len(self.results['files'])
        passed_tests = sum(self.results['directories'].values()) + sum(self.results['files'].values())
        failed_tests = total_tests - passed_tests

        print(f"\n📈 Overall Results:")
        print(f"   Total Structure Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        if total_tests > 0:
            print(".1f")

        # Detailed results
        print(f"\n📋 Detailed Results:")
        print(f"   ✅ Directories: {sum(self.results['directories'].values())}/{len(self.results['directories'])}")
        print(f"   ✅ Files: {sum(self.results['files'].values())}/{len(self.results['files'])}")

        # Show failures
        failed_dirs = [ctx for ctx, result in self.results['directories'].items() if not result]
        if failed_dirs:
            print(f"   ❌ Failed Directories: {', '.join(failed_dirs)}")

        failed_files = [file for file, result in self.results['files'].items() if not result]
        if failed_files:
            print(f"   ❌ Failed Files: {', '.join(failed_files[:5])}")
            if len(failed_files) > 5:
                print(f"      ... and {len(failed_files) - 5} more")

        # Error summary
        if self.errors:
            print(f"\n❌ Error Summary ({len(self.errors)} errors):")
            for i, error in enumerate(self.errors[:5], 1):
                print(f"   {i}. {error}")
            if len(self.errors) > 5:
                print(f"   ... and {len(self.errors) - 5} more errors")

        # Recommendations
        print(f"\n💡 Recommendations:")
        if failed_tests == 0:
            print("   🎉 All structure tests passed! File organization is correct.")
            print("   📝 Ready to proceed with Django configuration and migration testing.")
        else:
            print("   🔧 Address the structural issues before proceeding.")
            print("   📝 Missing files need to be created or moved to correct locations.")

        print("\n" + "="*80)

        return failed_tests == 0

    def run_all_tests(self):
        """Run all structure tests"""
        print("🚀 Starting Integration Structure Test Suite")
        print("Testing file organization and basic structure...")

        test_methods = [
            self.test_directory_structure,
            self.test_file_structure,
            self.test_django_settings,
            self.test_url_configuration,
            self.test_migration_structure,
        ]

        results = []
        for test_method in test_methods:
            try:
                result = test_method()
                results.append(result)
            except Exception as e:
                self.log_error(f"Test {test_method.__name__} failed with exception: {e}")
                results.append(False)

        # Generate final report
        overall_success = self.generate_report()

        return overall_success


def main():
    """Main entry point"""
    tester = StructureIntegrationTest()

    success = tester.run_all_tests()

    if success:
        print("\n🎉 ALL STRUCTURE TESTS PASSED!")
        print("File organization and basic setup are correct.")
        return 0
    else:
        print("\n❌ STRUCTURE TESTS FAILED!")
        print("Please address the structural issues before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
