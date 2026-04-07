import pytest

from core.models import (
    Asset,
    ComplianceAssessment,
    Framework,
    LoadedLibrary,
    Perimeter,
    RequirementNode,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    StoredLibrary,
)
from iam.models import Folder, User
from library.preset_executor import PresetExecutor


def _create_test_libraries(root):
    """Create the framework and risk matrix libraries needed by presets."""
    framework_library = LoadedLibrary.objects.create(
        urn="urn:test:framework-lib",
        locale="en",
        version=1,
        name="Framework Library",
        folder=root,
        objects_meta={},
    )
    framework = Framework.objects.create(
        name="Framework A",
        folder=root,
        library=framework_library,
    )
    RequirementNode.objects.create(
        framework=framework,
        folder=root,
        name="REQ-1",
        assessable=True,
        ref_id="REQ-1",
    )

    matrix_library = LoadedLibrary.objects.create(
        urn="urn:test:risk-matrix-lib",
        locale="en",
        version=1,
        name="Risk Matrix Library",
        folder=root,
        objects_meta={},
    )
    RiskMatrix.objects.create(
        name="Matrix A",
        folder=root,
        library=matrix_library,
        json_definition={
            "probability": [{"abbreviation": "L", "name": "Low"}],
            "impact": [{"abbreviation": "L", "name": "Low"}],
            "risk": [{"abbreviation": "L", "name": "Low"}],
            "grid": [[0]],
        },
    )
    return framework


def _create_preset_library(root, scaffolded_objects, steps, dependencies=None):
    """Create a StoredLibrary with preset content."""
    return StoredLibrary.objects.create(
        urn="urn:test:preset",
        locale="en",
        version=1,
        name="Test Preset",
        description="Test preset",
        folder=root,
        objects_meta={"preset": 1},
        hash_checksum="preset-checksum",
        dependencies=dependencies or [],
        content={
            "preset": {
                "feature_flags": {},
                "scaffolded_objects": scaffolded_objects,
                "journey": {"steps": steps},
            }
        },
    )


@pytest.mark.django_db
class TestPresetExecutorExistingDomain:
    """Tests for applying a preset to a folder that already has objects."""

    def test_reuses_existing_compliance_assessment_and_backfills_requirement_assessments(
        self,
    ):
        """When applying a preset to a folder with an existing compliance assessment
        matching by name+framework, the preset should reuse it and create its
        requirement assessments."""
        root = Folder.get_root_folder()
        user = User.objects.create_user(email="preset@example.com", password="secret")
        framework = _create_test_libraries(root)

        folder = Folder.objects.create(
            parent_folder=root,
            name="Existing Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        perimeter = Perimeter.objects.create(name="Manual Perimeter", folder=folder)
        existing_assessment = ComplianceAssessment.objects.create(
            name="ISO 27001 Compliance",
            folder=folder,
            perimeter=perimeter,
            framework=framework,
        )
        # No requirement assessments yet
        assert existing_assessment.requirement_assessments.count() == 0

        preset_library = _create_preset_library(
            root,
            scaffolded_objects=[
                {
                    "type": "compliance_assessment",
                    "name": "ISO 27001 Compliance",
                    "framework": "urn:test:framework-lib",
                    "ref": "iso_audit",
                }
            ],
            steps=[
                {
                    "key": "iso_compliance",
                    "title": "Assess ISO 27001 compliance",
                    "target_model": "compliance-assessments",
                    "target_ref": "iso_audit",
                }
            ],
        )

        journey = PresetExecutor(preset_library, user).apply(folder_id=str(folder.id))

        existing_assessment.refresh_from_db()
        assert existing_assessment.requirement_assessments.count() == 1
        assert journey.object_refs["iso_audit"] == str(existing_assessment.id)
        # Journey step should point to the reused assessment
        step = journey.steps.get(key="iso_compliance")
        assert step.target_ref == str(existing_assessment.id)

    def test_does_not_duplicate_objects_on_existing_folder(self):
        """Applying a preset to a folder with matching objects should not create duplicates."""
        root = Folder.get_root_folder()
        user = User.objects.create_user(email="preset2@example.com", password="secret")
        framework = _create_test_libraries(root)

        folder = Folder.objects.create(
            parent_folder=root,
            name="Existing Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        perimeter = Perimeter.objects.create(name="Test Preset", folder=folder)
        ComplianceAssessment.objects.create(
            name="ISO 27001 Compliance",
            folder=folder,
            perimeter=perimeter,
            framework=framework,
        )
        Asset.objects.create(
            name="Main Application",
            folder=folder,
            type="SP",
        )

        preset_library = _create_preset_library(
            root,
            scaffolded_objects=[
                {
                    "type": "compliance_assessment",
                    "name": "ISO 27001 Compliance",
                    "framework": "urn:test:framework-lib",
                    "ref": "iso_audit",
                },
                {
                    "type": "asset",
                    "name": "Main Application",
                    "asset_type": "SP",
                    "ref": "app_asset",
                },
            ],
            steps=[],
        )

        PresetExecutor(preset_library, user).apply(folder_id=str(folder.id))

        assert (
            ComplianceAssessment.objects.filter(
                folder=folder, name="ISO 27001 Compliance"
            ).count()
            == 1
        )
        assert Asset.objects.filter(folder=folder, name="Main Application").count() == 1

    def test_reuses_existing_risk_assessment_by_matrix(self):
        """Risk assessment reuse should match by name AND risk_matrix, not just name."""
        root = Folder.get_root_folder()
        user = User.objects.create_user(email="preset3@example.com", password="secret")
        _create_test_libraries(root)
        matrix = RiskMatrix.objects.first()

        folder = Folder.objects.create(
            parent_folder=root,
            name="Existing Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        perimeter = Perimeter.objects.create(name="Test Preset", folder=folder)
        existing_ra = RiskAssessment.objects.create(
            name="Initial Risk Assessment",
            folder=folder,
            perimeter=perimeter,
            risk_matrix=matrix,
        )

        preset_library = _create_preset_library(
            root,
            scaffolded_objects=[
                {
                    "type": "risk_assessment",
                    "name": "Initial Risk Assessment",
                    "risk_matrix": "urn:test:risk-matrix-lib",
                    "ref": "main_ra",
                },
            ],
            steps=[],
        )

        journey = PresetExecutor(preset_library, user).apply(folder_id=str(folder.id))

        assert RiskAssessment.objects.filter(folder=folder).count() == 1
        assert journey.object_refs["main_ra"] == str(existing_ra.id)

    def test_reuses_existing_risk_scenario_and_backfills_assets(self):
        """Risk scenario reuse should match by name+risk_assessment and add missing assets."""
        root = Folder.get_root_folder()
        user = User.objects.create_user(email="preset4@example.com", password="secret")
        _create_test_libraries(root)
        matrix = RiskMatrix.objects.first()

        folder = Folder.objects.create(
            parent_folder=root,
            name="Existing Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        perimeter = Perimeter.objects.create(name="Test Preset", folder=folder)
        ra = RiskAssessment.objects.create(
            name="Initial Risk Assessment",
            folder=folder,
            perimeter=perimeter,
            risk_matrix=matrix,
        )
        existing_scenario = RiskScenario.objects.create(
            name="Data breach",
            risk_assessment=ra,
        )
        asset = Asset.objects.create(
            name="Web App",
            folder=folder,
            type="SP",
        )
        assert existing_scenario.assets.count() == 0

        preset_library = _create_preset_library(
            root,
            scaffolded_objects=[
                {
                    "type": "risk_assessment",
                    "name": "Initial Risk Assessment",
                    "risk_matrix": "urn:test:risk-matrix-lib",
                    "ref": "main_ra",
                },
                {
                    "type": "asset",
                    "name": "Web App",
                    "asset_type": "SP",
                    "ref": "web_app",
                },
                {
                    "type": "risk_scenario",
                    "name": "Data breach",
                    "risk_assessment_ref": "main_ra",
                    "asset_refs": ["web_app"],
                    "ref": "breach_scenario",
                },
            ],
            steps=[],
        )

        journey = PresetExecutor(preset_library, user).apply(folder_id=str(folder.id))

        existing_scenario.refresh_from_db()
        assert existing_scenario.assets.count() == 1
        assert existing_scenario.assets.first().id == asset.id
        assert journey.object_refs["breach_scenario"] == str(existing_scenario.id)

    def test_creates_new_objects_on_fresh_folder(self):
        """On a new folder, all objects should be created normally."""
        root = Folder.get_root_folder()
        user = User.objects.create_user(email="preset5@example.com", password="secret")
        _create_test_libraries(root)

        preset_library = _create_preset_library(
            root,
            scaffolded_objects=[
                {
                    "type": "risk_assessment",
                    "name": "Initial Risk Assessment",
                    "risk_matrix": "urn:test:risk-matrix-lib",
                    "ref": "main_ra",
                },
                {
                    "type": "compliance_assessment",
                    "name": "ISO 27001 Compliance",
                    "framework": "urn:test:framework-lib",
                    "ref": "iso_audit",
                },
                {
                    "type": "asset",
                    "name": "Web App",
                    "asset_type": "SP",
                    "ref": "web_app",
                },
            ],
            steps=[
                {
                    "key": "risk_step",
                    "title": "Risk Assessment",
                    "target_model": "risk-assessments",
                    "target_ref": "main_ra",
                },
            ],
        )

        journey = PresetExecutor(preset_library, user).apply(
            folder_name="New Domain",
        )

        folder = journey.folder
        assert RiskAssessment.objects.filter(folder=folder).count() == 1
        assert ComplianceAssessment.objects.filter(folder=folder).count() == 1
        assert Asset.objects.filter(folder=folder).count() == 1
        # Compliance assessment should have requirement assessments created
        ca = ComplianceAssessment.objects.get(folder=folder)
        assert ca.requirement_assessments.count() == 1

    def test_rejects_duplicate_preset_on_same_folder(self):
        """Applying the same preset twice to the same folder should raise ValidationError."""
        root = Folder.get_root_folder()
        user = User.objects.create_user(email="preset6@example.com", password="secret")
        _create_test_libraries(root)

        folder = Folder.objects.create(
            parent_folder=root,
            name="Existing Domain",
            content_type=Folder.ContentType.DOMAIN,
        )

        preset_library = _create_preset_library(
            root,
            scaffolded_objects=[],
            steps=[],
        )

        # First apply should succeed
        PresetExecutor(preset_library, user).apply(folder_id=str(folder.id))

        # Second apply should raise
        with pytest.raises(Exception) as exc_info:
            PresetExecutor(preset_library, user).apply(folder_id=str(folder.id))
        assert "already been applied" in str(exc_info.value)
