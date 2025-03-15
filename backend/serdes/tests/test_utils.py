"""
Test suite for serialization/deserialization utilities and domain export functionality.

This test suite covers:
1. Model dependencies detection
2. Dependency graph building
3. Topological sorting
4. Self-referencing field detection
5. Object sorting by self-reference
6. Domain export functionality

Each section includes comprehensive tests for normal cases, edge cases, and error conditions.
"""

import pytest
from serdes.utils import (
    get_model_dependencies,
    build_dependency_graph,
    topological_sort,
    get_self_referencing_field,
    sort_objects_by_self_reference,
    get_domain_export_objects,
)
from core.models import (
    Folder,
    Asset,
    Perimeter,
    RiskAssessment,
    RiskScenario,
    AppliedControl,
    ComplianceAssessment,
    Framework,
    Threat,
    StoredLibrary,
    RiskMatrix,
)
from ebios_rm.models import EbiosRMStudy, FearedEvent

# ============ Fixtures ============


@pytest.fixture
def basic_folder_structure():
    """Creates a basic folder hierarchy for testing."""
    root = Folder.objects.create(
        name="Global", content_type=Folder.ContentType.ROOT, builtin=True
    )
    domain = Folder.objects.create(
        name="Test Domain", content_type=Folder.ContentType.DOMAIN, builtin=False
    )
    subfolder = Folder.objects.create(
        name="Test Subfolder",
        content_type=Folder.ContentType.DOMAIN,
        builtin=False,
        parent=domain,
    )
    return {"root": root, "domain": domain, "subfolder": subfolder}


@pytest.fixture
def framework_fixture():
    library = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:iso27001-2022"
    ).last()
    assert library is not None
    library.load()
    return Framework.objects.get(urn="urn:intuitem:risk:framework:iso27001-2022")


@pytest.fixture
def risk_matrix_fixture():
    library = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:critical_risk_matrix_5x5"
    ).last()
    assert library is not None
    library.load()
    return RiskMatrix.objects.get(
        urn="urn:intuitem:risk:matrix:critical_risk_matrix_5x5"
    )


@pytest.fixture
def complex_model_structure(risk_matrix_fixture):
    """Creates a complex structure of related models for testing."""
    perimeter = Perimeter.objects.create(name="Test Perimeter")
    risk_assessment = RiskAssessment.objects.create(
        name="Test Assessment", perimeter=perimeter, risk_matrix=risk_matrix_fixture
    )
    scenario = RiskScenario.objects.create(name="Test Scenario")
    asset = Asset.objects.create(name="Test Asset")
    return {
        "perimeter": perimeter,
        "risk_assessment": risk_assessment,
        "scenario": scenario,
        "asset": asset,
    }


@pytest.fixture
def complex_domain_structure(risk_matrix_fixture, framework_fixture):
    """
    Creates a complex domain structure with multiple related objects for testing.

    The structure includes:
    - A root domain folder
    - Sub-folders
    - Perimeters attached to folders
    - Risk assessments linked to perimeters
    - Assets and scenarios linked to risk assessments
    - Various related objects (controls, threats, etc.)
    """
    root = Folder.objects.create(
        name="Root Domain", content_type=Folder.ContentType.DOMAIN, builtin=False
    )

    subfolder = Folder.objects.create(
        name="Sub Domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=root,
        builtin=False,
    )

    perimeter = Perimeter.objects.create(name="Test Perimeter", folder=root)

    risk_assessment = RiskAssessment.objects.create(
        name="Test Assessment",
        perimeter=perimeter,
        folder=root,
        risk_matrix=risk_matrix_fixture,
    )

    asset = Asset.objects.create(name="Test Asset", folder=root)

    risk_scenario = RiskScenario.objects.create(
        name="Test Scenario", risk_assessment=risk_assessment
    )
    risk_scenario.assets.add(asset)

    compliance_assessment = ComplianceAssessment.objects.create(
        name="Test Compliance",
        perimeter=perimeter,
        folder=root,
        framework=framework_fixture,
    )

    ebios_study = EbiosRMStudy.objects.create(
        name="Test EBIOS Study", folder=root, risk_matrix=risk_matrix_fixture
    )

    feared_event = FearedEvent.objects.create(
        name="Test Feared Event", ebios_rm_study=ebios_study
    )

    threat = Threat.objects.create(name="Test Threat", folder=root)

    applied_control = AppliedControl.objects.create(name="Test Control", folder=root)

    return {
        "root": root,
        "subfolder": subfolder,
        "perimeter": perimeter,
        "risk_assessment": risk_assessment,
        "asset": asset,
        "risk_scenario": risk_scenario,
        "compliance_assessment": compliance_assessment,
        "ebios_study": ebios_study,
        "feared_event": feared_event,
        "threat": threat,
        "applied_control": applied_control,
    }


# ============ Model Dependencies Tests ============


class TestModelDependencies:
    """Tests for the get_model_dependencies function."""

    @pytest.mark.django_db
    def test_get_model_dependencies_foreign_key(self):
        """Test dependencies detection for foreign key relationships."""
        models_set = {RiskAssessment, Perimeter, RiskScenario, AppliedControl}
        dependencies = get_model_dependencies(RiskAssessment, models_set)
        assert Perimeter in dependencies
        assert len(dependencies) == 1

    @pytest.mark.django_db
    def test_get_model_dependencies_many_to_many(self):
        """Test dependencies detection for many-to-many relationships."""
        models_set = {Asset, RiskScenario}
        asset_dependencies = get_model_dependencies(Asset, models_set)
        scenario_dependencies = get_model_dependencies(RiskScenario, models_set)

        assert Asset in asset_dependencies
        assert Asset in scenario_dependencies
        assert len(asset_dependencies) >= 1
        assert len(scenario_dependencies) >= 1

    @pytest.mark.django_db
    def test_get_model_dependencies_multiple_relations(self):
        """Test dependencies detection with multiple relationships."""
        models_set = {RiskAssessment, Perimeter, Folder}
        dependencies = get_model_dependencies(RiskAssessment, models_set)
        assert Perimeter in dependencies
        assert Folder in dependencies

    @pytest.mark.django_db
    def test_get_model_dependencies_no_dependency(self):
        """Test dependencies detection with no relationships."""
        models_set = {Perimeter, RiskScenario}
        dependencies = get_model_dependencies(RiskScenario, models_set)
        assert Perimeter not in dependencies
        assert len(dependencies) == 0


# ============ Dependency Graph Tests ============


class TestDependencyGraph:
    """Tests for the build_dependency_graph function."""

    @pytest.mark.django_db
    def test_build_dependency_graph_complete(self):
        """Test complete graph building with all relationships."""
        models = [RiskAssessment, Perimeter, Asset, RiskScenario]
        graph = build_dependency_graph(models)

        assert RiskAssessment in graph
        assert Perimeter in graph[RiskAssessment]
        assert len(graph) > 0
        assert isinstance(graph, dict)

    @pytest.mark.django_db
    def test_build_dependency_graph_empty_models(self):
        """Test graph building with empty model list."""
        graph = build_dependency_graph([])
        assert len(graph) == 0

    @pytest.mark.django_db
    def test_build_dependency_graph_folder_inheritance(self):
        """Test graph building with folder inheritance."""
        models = [Perimeter, Folder]
        graph = build_dependency_graph(models)
        assert Folder in graph[Perimeter]
        for model in graph:
            assert isinstance(graph[model], list)


# ============ Topological Sort Tests ============


class TestTopologicalSort:
    """Tests for the topological_sort function."""

    @pytest.mark.django_db
    def test_topological_sort_complex(self):
        """Test complex topological sorting with multiple dependencies."""
        models = [RiskAssessment, Perimeter, RiskScenario, Asset]
        graph = build_dependency_graph(models)
        sorted_models = topological_sort(graph)

        if Perimeter in sorted_models and RiskAssessment in sorted_models:
            assert sorted_models.index(Perimeter) < sorted_models.index(RiskAssessment)

        assert len(sorted_models) == len(set(sorted_models))
        assert set(sorted_models).issubset(set(models + [Folder]))

    @pytest.mark.django_db
    def test_topological_sort_empty_graph(self):
        """Test topological sorting with empty graph."""
        sorted_models = topological_sort({})
        assert len(sorted_models) == 0

    @pytest.mark.django_db
    def test_topological_sort_self_dependency(self):
        """Test topological sorting with self-dependency."""
        graph = {Asset: [Asset]}
        sorted_models = topological_sort(graph)
        assert Asset in sorted_models
        assert len(sorted_models) == 1


# ============ Self-Referencing Field Tests ============


class TestSelfReferencingField:
    """Tests for the get_self_referencing_field function."""

    @pytest.mark.django_db
    def test_get_self_referencing_field_asset(self):
        """Test self-referencing field detection for Asset model."""
        field_name = get_self_referencing_field(Asset)
        assert field_name == "parent_assets"

    @pytest.mark.django_db
    def test_get_self_referencing_field_folder(self):
        """Test self-referencing field detection for Folder model."""
        field_name = get_self_referencing_field(Folder)
        assert field_name == "parent_folder"

    @pytest.mark.django_db
    def test_get_self_referencing_field_no_self_ref(self):
        """Test self-referencing field detection for model without self-reference."""
        field_name = get_self_referencing_field(Perimeter)
        assert field_name is None

    @pytest.mark.django_db
    def test_get_self_referencing_field_risk_assessment(self):
        """Test self-referencing field detection for RiskAssessment model."""
        field_name = get_self_referencing_field(RiskAssessment)
        assert field_name is None


# ============ Object Sorting Tests ============


class TestObjectSorting:
    """Tests for the sort_objects_by_self_reference function."""

    @pytest.mark.django_db
    def test_sort_objects_complex_hierarchy(self):
        """Test sorting objects with complex hierarchy."""
        objects = [
            {"id": 1, "fields": {"parent": []}},
            {"id": 2, "fields": {"parent": [1]}},
            {"id": 3, "fields": {"parent": [1]}},
            {"id": 4, "fields": {"parent": [2, 3]}},
        ]
        sorted_objs = sort_objects_by_self_reference(objects, "parent")
        assert sorted_objs[-1]["id"] == 4
        assert sorted_objs[0]["id"] == 1

    @pytest.mark.django_db
    def test_sort_objects_multiple_roots(self):
        """Test sorting objects with multiple root nodes."""
        objects = [
            {"id": 1, "fields": {"parent": []}},
            {"id": 2, "fields": {"parent": []}},
            {"id": 3, "fields": {"parent": [1]}},
            {"id": 4, "fields": {"parent": [2]}},
        ]
        sorted_objs = sort_objects_by_self_reference(objects, "parent")
        assert len(sorted_objs) == 4
        assert sorted_objs.index(
            {"id": 1, "fields": {"parent": []}}
        ) < sorted_objs.index({"id": 3, "fields": {"parent": [1]}})
        assert sorted_objs.index(
            {"id": 2, "fields": {"parent": []}}
        ) < sorted_objs.index({"id": 4, "fields": {"parent": [2]}})

    @pytest.mark.django_db
    def test_sort_objects_invalid_parent(self):
        """Test sorting objects with invalid parent references."""
        objects = [
            {"id": 1, "fields": {"parent": [999]}},
            {"id": 2, "fields": {"parent": [1]}},
        ]
        sorted_objs = sort_objects_by_self_reference(objects, "parent")
        assert len(sorted_objs) == 2
        assert sorted_objs[0]["id"] == 1
        assert sorted_objs[1]["id"] == 2

    @pytest.mark.django_db
    def test_sort_objects_empty_list(self):
        """Test sorting empty object list."""
        sorted_objs = sort_objects_by_self_reference([], "parent")
        assert sorted_objs == []


# ============ Domain Export Tests ============


class TestDomainExport:
    """Tests for the get_domain_export_objects function."""

    @pytest.mark.django_db
    def test_get_domain_export_objects_basic(self, complex_domain_structure):
        """Test basic domain export functionality."""
        root = complex_domain_structure["root"]
        export_data = get_domain_export_objects(root)

        assert len(export_data["perimeter"]) == 1
        assert len(export_data["riskassessment"]) == 1
        assert len(export_data["asset"]) == 1
        assert len(export_data["riskscenario"]) == 1

        assert complex_domain_structure["perimeter"] in export_data["perimeter"]
        assert (
            complex_domain_structure["risk_assessment"] in export_data["riskassessment"]
        )
        assert complex_domain_structure["asset"] in export_data["asset"]
        assert complex_domain_structure["risk_scenario"] in export_data["riskscenario"]

    @pytest.mark.django_db
    def test_get_domain_export_objects_subfolder_content(
        self, complex_domain_structure
    ):
        """Test export of objects in subfolders."""
        root = complex_domain_structure["root"]
        subfolder = complex_domain_structure["subfolder"]

        subfolder_asset = Asset.objects.create(name="Subfolder Asset", folder=subfolder)

        export_data = get_domain_export_objects(root)
        assert subfolder_asset in export_data["asset"]

    @pytest.mark.django_db
    def test_get_domain_export_objects_compliance(self, complex_domain_structure):
        """
        Tests the export of compliance-related objects and their relationships.
        """
        root = complex_domain_structure["root"]
        export_data = get_domain_export_objects(root)

        assert len(export_data["framework"]) == 1
        assert len(export_data["complianceassessment"]) == 1
        assert (
            complex_domain_structure["compliance_assessment"]
            in export_data["complianceassessment"]
        )

    @pytest.mark.django_db
    def test_get_domain_export_objects_ebios(self, complex_domain_structure):
        """
        Tests the export of EBIOS RM related objects and their relationships.
        """
        root = complex_domain_structure["root"]
        export_data = get_domain_export_objects(root)

        assert len(export_data["ebiosrmstudy"]) == 1
        assert len(export_data["fearedevent"]) == 1
        assert complex_domain_structure["ebios_study"] in export_data["ebiosrmstudy"]
        assert complex_domain_structure["feared_event"] in export_data["fearedevent"]

    @pytest.mark.django_db
    def test_get_domain_export_objects_empty_domain(self):
        """
        Tests export behavior with an empty domain folder.
        Verifies that the function handles empty domains properly.
        """
        empty_domain = Folder.objects.create(
            name="Empty Domain", content_type=Folder.ContentType.DOMAIN, builtin=False
        )

        export_data = get_domain_export_objects(empty_domain)

        # Verify all collections are empty but present
        for key, value in export_data.items():
            assert len(value) == 0

    @pytest.mark.django_db
    def test_get_domain_export_objects_cross_references(self, complex_domain_structure):
        """
        Tests that objects with cross-references are properly exported.
        Verifies that complex relationships between objects are maintained.
        """
        root = complex_domain_structure["root"]

        # Create cross-referenced objects
        threat = complex_domain_structure["threat"]
        risk_scenario = complex_domain_structure["risk_scenario"]
        risk_scenario.threats.add(threat)

        export_data = get_domain_export_objects(root)

        assert threat in export_data["threat"]
        assert (
            risk_scenario in export_data["riskscenario"]
            and threat in export_data["riskscenario"].first().threats.all()
        )
