import pytest
from django.apps import apps
from django.db import models
from core.models import Asset, RiskAssessment, RiskMatrix, Terminology
from iam.models import Folder, FolderMixin
from ebios_rm.models import (
    STUDY_FOLDER_CASCADE_MODELS,
    AttackPath,
    EbiosRMStudy,
    ElementaryAction,
    FearedEvent,
    KillChain,
    OperatingMode,
    OperationalScenario,
    RoTo,
    StrategicScenario,
)
from ebios_rm.serializers import EbiosRMStudyWriteSerializer

from ebios_rm.tests.fixtures import *
from tprm.models import Entity

# Folder-scoped ebios_rm models that deliberately do not follow the study on a
# domain move: shared catalog objects (or the study itself) with a user-managed
# folder. Kept alongside the classification guard test below, which asserts that
# every folder-scoped model is either cascaded or explicitly exempted here.
STUDY_FOLDER_EXEMPT_MODELS: set[type[models.Model]] = {EbiosRMStudy, ElementaryAction}


@pytest.mark.django_db
class TestEbiosRMStudy:
    @pytest.mark.usefixtures("ebios_rm_matrix_fixture")
    def test_create_ebios_rm_study_basic(self):
        study = EbiosRMStudy.objects.create(
            name="test study",
            description="test study description",
            risk_matrix=RiskMatrix.objects.get(
                urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
            ),
        )
        assert study.name == "test study"
        assert study.description == "test study description"
        assert study.risk_matrix == RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
        )
        assert study.assets.count() == 0
        assert study.reference_entity == Entity.get_main_entity()

    @pytest.mark.usefixtures("ebios_rm_matrix_fixture", "basic_assets_tree_fixture")
    def test_create_ebios_rm_study_with_assets(self):
        study = EbiosRMStudy.objects.create(
            name="test study",
            description="test study description",
            risk_matrix=RiskMatrix.objects.get(
                urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
            ),
        )
        study.assets.set(Asset.objects.filter(name="Primary Asset 1"))
        assert study.name == "test study"
        assert study.description == "test study description"
        assert study.risk_matrix == RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
        )

        assert study.assets.count() == 1
        assert study.assets.filter(name="Primary Asset 1").exists()


@pytest.mark.django_db
class TestEbiosRMStudyDomainMove:
    def test_folder_scoped_models_are_classified_for_domain_move(self):
        folder_scoped_models = {
            model
            for model in apps.get_app_config("ebios_rm").get_models()
            if issubclass(model, FolderMixin)
        }
        unclassified = (
            folder_scoped_models
            - set(STUDY_FOLDER_CASCADE_MODELS)
            - STUDY_FOLDER_EXEMPT_MODELS
        )
        assert not unclassified, (
            "Folder-scoped ebios_rm models must be added to "
            "STUDY_FOLDER_CASCADE_MODELS (folder follows the study) or "
            f"STUDY_FOLDER_EXEMPT_MODELS (user-managed folder): {unclassified}"
        )

    def test_move_study_between_domains(self, ebios_rm_matrix_fixture):
        matrix = ebios_rm_matrix_fixture
        root = Folder.get_root_folder()
        domain_a = Folder.objects.create(
            name="Domain A", parent_folder=root, content_type=Folder.ContentType.DOMAIN
        )
        domain_b = Folder.objects.create(
            name="Domain B", parent_folder=root, content_type=Folder.ContentType.DOMAIN
        )

        study = EbiosRMStudy.objects.create(
            name="test study", folder=domain_a, risk_matrix=matrix
        )
        feared_event = FearedEvent.objects.create(
            name="test feared event", ebios_rm_study=study
        )
        ro_to = RoTo.objects.create(
            ebios_rm_study=study,
            risk_origin=Terminology.objects.filter(
                field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN
            ).first(),
            target_objective="test target objective",
        )
        strategic_scenario = StrategicScenario.objects.create(
            name="test strategic scenario", ebios_rm_study=study, ro_to_couple=ro_to
        )
        attack_path = AttackPath.objects.create(
            name="test attack path",
            strategic_scenario=strategic_scenario,
            ebios_rm_study=study,
        )
        operational_scenario = OperationalScenario.objects.create(
            ebios_rm_study=study, attack_path=attack_path
        )
        operating_mode = OperatingMode.objects.create(
            name="test operating mode", operational_scenario=operational_scenario
        )
        elementary_action = ElementaryAction.objects.create(
            name="test elementary action", folder=domain_a
        )
        kill_chain = KillChain.objects.create(
            operating_mode=operating_mode, elementary_action=elementary_action
        )
        risk_assessment = RiskAssessment.objects.create(
            name="test risk assessment",
            risk_matrix=matrix,
            ebios_rm_study=study,
            folder=domain_a,
        )

        cascaded_objects = (
            feared_event,
            ro_to,
            strategic_scenario,
            attack_path,
            operational_scenario,
            operating_mode,
            kill_chain,
        )

        # Move through the API write serializer
        serializer = EbiosRMStudyWriteSerializer(
            study, data={"folder": domain_b.id}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        for obj in (study, *cascaded_objects):
            obj.refresh_from_db()
            assert obj.folder == domain_b, (
                f"{type(obj).__name__} was left behind in the old domain"
            )

        # Shared catalog objects and perimeter-anchored deliverables stay put
        for obj in (elementary_action, risk_assessment):
            obj.refresh_from_db()
            assert obj.folder == domain_a, (
                f"{type(obj).__name__} must not follow the study"
            )

        # Move back through a direct model save: the invariant must hold on
        # every write path, not only the serializer
        study.folder = domain_a
        study.save()

        for obj in (study, *cascaded_objects):
            obj.refresh_from_db()
            assert obj.folder == domain_a, (
                f"{type(obj).__name__} did not follow a direct model-level move"
            )
