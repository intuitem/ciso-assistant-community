"""Objects a workflow can now build: risk scenarios, BIAs and their asset
assessments, and the privacy register — parent and children."""

import uuid

import pytest

from core.models import (
    Asset,
    Perimeter,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    Terminology,
)
from iam.models import Folder
from privacy.models import DataSubject, PersonalData, Processing, Purpose
from resilience.models import AssetAssessment, BusinessImpactAnalysis
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowInstance, WorkflowVersion
from automation.workflows.tests.helpers import publisher_user


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(a, b):
    return {"id": str(uuid.uuid4()), "source": a["id"], "target": b["id"]}


def make_domain(name):
    return Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def create_flow(folder, *configs):
    workflow = Workflow.objects.create(name=f"Build {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    steps = [
        node("action", label=config.pop("label"), action_config=config)
        for config in configs
    ]
    end = node("end")
    chain = [start, *steps, end]
    save_graph(
        version,
        {"nodes": chain, "edges": [edge(a, b) for a, b in zip(chain, chain[1:])]},
    )
    return version


def make_matrix():
    """A BIA reads the matrix grid, so a stub with only `risk` is not enough."""
    level = [
        {"id": 0, "abbreviation": "L", "name": "Low", "description": "low"},
        {"id": 1, "abbreviation": "H", "name": "High", "description": "high"},
    ]
    return RiskMatrix.objects.create(
        name=f"M {uuid.uuid4().hex[:6]}",
        urn=f"urn:test:risk:library:m-{uuid.uuid4().hex[:6]}:risk_matrix:m",
        folder=Folder.get_root_folder(),
        json_definition={
            "probability": level,
            "impact": level,
            "risk": level,
            "grid": [[0, 1], [1, 1]],
        },
    )


@pytest.mark.django_db
class TestRiskScenario:
    def test_a_scenario_lands_in_its_assessment(self):
        domain = make_domain("Scenarios")
        matrix = make_matrix()
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        assessment = RiskAssessment.objects.create(
            name="RA", perimeter=perimeter, risk_matrix=matrix, folder=domain
        )
        version = create_flow(
            domain,
            {
                "label": "Add scenario",
                "type": "create_object",
                "model": "risk_scenario",
                "fields": {
                    "name": "Ransomware on the ERP",
                    "description": "From the incident review",
                    "risk_assessment": str(assessment.id),
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, [
            log.message for log in instance.logs.filter(event_type="error")
        ]
        scenario = RiskScenario.objects.get(name="Ransomware on the ERP")
        assert scenario.risk_assessment == assessment
        # Unrated and untreated: the analyst still decides.
        assert scenario.treatment == "open"

    def test_ratings_and_treatment_are_not_writable(self):
        from automation.workflows.actions import CREATABLE_MODELS

        fields = CREATABLE_MODELS["risk_scenario"]["fields"]
        assert "treatment" not in fields
        assert not [f for f in fields if "level" in f or "proba" in f or "impact" in f]


@pytest.mark.django_db
class TestBusinessImpactAnalysis:
    def test_a_bia_and_its_asset_assessments(self):
        domain = make_domain("BIA")
        matrix = make_matrix()
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        asset = Asset.objects.create(name="Payroll", folder=domain)
        version = create_flow(
            domain,
            {
                "label": "Open bia",
                "type": "create_object",
                "model": "business_impact_analysis",
                "fields": {
                    "name": "Annual BIA",
                    "perimeter": str(perimeter.id),
                    "risk_matrix": matrix.urn,
                },
            },
            {
                "label": "Add asset",
                "type": "create_object",
                "model": "asset_assessment",
                "fields": {
                    "asset": str(asset.id),
                    "bia": "{{nodes.open_bia.created_object_id}}",
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, [
            log.message for log in instance.logs.filter(event_type="error")
        ]
        bia = BusinessImpactAnalysis.objects.get(name="Annual BIA")
        assert bia.risk_matrix == matrix
        assessment = AssetAssessment.objects.get(bia=bia)
        assert assessment.asset == asset
        # A nameless model still reports something useful downstream.
        assert instance.node_outputs["add_asset"]["created_object_name"]


@pytest.mark.django_db
class TestPrivacyRegister:
    def test_a_processing_with_its_children(self):
        domain = make_domain("Privacy")
        category = Terminology.objects.create(
            name="Health data",
            folder=Folder.get_root_folder(),
            field_path=Terminology.FieldPath.PERSONAL_DATA_CATEGORY,
            is_visible=True,
        )
        version = create_flow(
            domain,
            {
                "label": "Record processing",
                "type": "create_object",
                "model": "processing",
                "fields": {"name": "Payroll", "description": "Monthly payroll run"},
            },
            {
                "label": "Add purpose",
                "type": "create_object",
                "model": "purpose",
                "fields": {
                    "name": "Pay the staff",
                    "processing": "{{nodes.record_processing.created_object_id}}",
                    "legal_basis": "privacy_contract",
                },
            },
            {
                "label": "Add data",
                "type": "create_object",
                "model": "personal_data",
                "fields": {
                    "name": "Sick leave",
                    "processing": "{{nodes.record_processing.created_object_id}}",
                    # A terminology has no urn: it resolves by name, among the
                    # categories this very field accepts.
                    "category": "Health data",
                    "is_sensitive": True,
                },
            },
            {
                "label": "Add subject",
                "type": "create_object",
                "model": "data_subject",
                "fields": {
                    "name": "Employees",
                    "processing": "{{nodes.record_processing.created_object_id}}",
                    "category": "privacy_employee",
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, [
            log.message for log in instance.logs.filter(event_type="error")
        ]
        processing = Processing.objects.get(name="Payroll")
        # Records land as drafts: privacy_approved is an approval.
        assert processing.status == "privacy_draft"
        assert (
            Purpose.objects.get(processing=processing).legal_basis == "privacy_contract"
        )
        data = PersonalData.objects.get(processing=processing)
        assert data.category == category
        assert data.is_sensitive is True
        assert (
            DataSubject.objects.get(processing=processing).category
            == "privacy_employee"
        )

    def test_the_processing_status_is_not_writable(self):
        from automation.workflows.actions import CREATABLE_MODELS

        assert "status" not in CREATABLE_MODELS["processing"]["fields"]

    def test_a_category_from_the_wrong_field_is_not_found(self):
        """limit_choices_to narrows the lookup, so a name that exists as some
        other kind of terminology cannot be attached here."""
        domain = make_domain("Wrong category")
        Terminology.objects.create(
            name="Quarterly",
            folder=Folder.get_root_folder(),
            field_path=Terminology.FieldPath.METRIC_UNIT,
            is_visible=True,
        )
        processing = Processing.objects.create(name="P", folder=domain)
        version = create_flow(
            domain,
            {
                "label": "Add data",
                "type": "create_object",
                "model": "personal_data",
                "fields": {
                    "name": "Something",
                    "processing": str(processing.id),
                    "category": "Quarterly",
                },
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED

    def test_an_ambiguous_name_is_refused_rather_than_guessed(self):
        domain = make_domain("Ambiguous")
        child = Folder.objects.create(
            name="Sub", parent_folder=domain, content_type=Folder.ContentType.DOMAIN
        )
        Processing.objects.create(name="Payroll", folder=domain)
        Processing.objects.create(name="Payroll", folder=child)
        version = create_flow(
            domain,
            {
                "label": "Add purpose",
                "type": "create_object",
                "model": "purpose",
                "fields": {"name": "Pay", "processing": "Payroll"},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED


@pytest.mark.django_db
class TestCreatedValuesAreFenced:
    """create_object refuses a value the column does not accept, the way
    update_object already did — save() never checks choices."""

    def test_a_bad_choice_fails_the_node(self):
        domain = make_domain("Bad choice")
        processing = Processing.objects.create(name="P", folder=domain)
        version = create_flow(
            domain,
            {
                "label": "Add purpose",
                "type": "create_object",
                "model": "purpose",
                "fields": {
                    "name": "Pay",
                    "processing": str(processing.id),
                    "legal_basis": "because we felt like it",
                },
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not Purpose.objects.filter(name="Pay").exists()

    def test_a_bad_literal_is_refused_at_publish(self):
        from automation.workflows.actions import validate_create_config
        from automation.workflows.models import WorkflowNode

        codes = {
            code
            for code, _ in validate_create_config(
                WorkflowNode(
                    action_config={
                        "type": "create_object",
                        "model": "purpose",
                        "fields": {"name": "x", "legal_basis": "nope"},
                    }
                )
            )
        }
        assert "action_create_value_not_allowed" in codes
