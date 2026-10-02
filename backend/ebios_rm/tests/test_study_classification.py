import pytest

from core.models import ClassificationLevel, ObjectClassification
from ebios_rm.serializers import EbiosRMStudyReadSerializer, EbiosRMStudyWriteSerializer

from ebios_rm.tests.fixtures import *


@pytest.fixture
def restricted_level_fixture():
    scheme = ObjectClassification.objects.create(name="Protection marking")
    return ClassificationLevel.objects.create(
        object_classification=scheme,
        name="Restricted",
        abbreviation="DR",
        hexcolor="#cc0000",
        rank=1,
    )


@pytest.mark.django_db
class TestEbiosRMStudyClassification:
    def test_classification_is_optional(self, basic_ebios_rm_study_fixture):
        assert basic_ebios_rm_study_fixture.classification is None
        data = EbiosRMStudyReadSerializer(basic_ebios_rm_study_fixture).data
        assert data["classification"] is None

    def test_read_serializer_exposes_marking(
        self, basic_ebios_rm_study_fixture, restricted_level_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.classification = restricted_level_fixture
        study.save()

        data = EbiosRMStudyReadSerializer(study).data["classification"]

        assert data == {
            "id": str(restricted_level_fixture.id),
            "name": "DR",
            "abbreviation": "DR",
            "hexcolor": "#cc0000",
        }

    def test_deleting_level_unsets_classification(
        self, basic_ebios_rm_study_fixture, restricted_level_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.classification = restricted_level_fixture
        study.save()

        restricted_level_fixture.delete()
        study.refresh_from_db()

        assert study.classification is None


@pytest.mark.django_db
class TestEbiosRMStudyFramingAndMethods:
    def test_framing_fields_are_exposed(self, basic_ebios_rm_study_fixture):
        study = basic_ebios_rm_study_fixture
        study.objectives = "Assess the payment chain"
        study.constraints_hypotheses = "No production access"
        study.save()

        data = EbiosRMStudyReadSerializer(study).data

        assert data["objectives"] == "Assess the payment chain"
        assert data["constraints_hypotheses"] == "No production access"
        assert data["responsibility_matrix"] is None

    @pytest.mark.parametrize(
        "method, valid",
        [
            ("manual", True),
            ("express", True),
            ("standard", True),
            ("advanced", True),
            ("bogus", False),
        ],
    )
    def test_only_available_methods_can_be_selected(
        self, basic_ebios_rm_study_fixture, method, valid
    ):
        serializer = EbiosRMStudyWriteSerializer(
            basic_ebios_rm_study_fixture,
            data={"quotation_method": method},
            partial=True,
        )

        assert serializer.is_valid() is valid

    def test_quotation_method_display_is_a_translation_key(
        self, basic_ebios_rm_study_fixture
    ):
        data = EbiosRMStudyReadSerializer(basic_ebios_rm_study_fixture).data

        assert (
            data["quotation_method_display"] == "quotationMethodExpressOperatingModes"
        )


@pytest.fixture
def admin_client():
    from iam.models import User, UserGroup
    from knox.models import AuthToken
    from rest_framework.test import APIClient

    from core.apps import startup

    startup(sender=None)
    admin = User.objects.create_superuser("admin@study-raci-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.mark.django_db
class TestStudyResponsibilityMatrixFromName:
    def test_typed_name_creates_then_reuses_a_matrix(
        self, admin_client, basic_ebios_rm_study_fixture
    ):
        from pmbok.models import ResponsibilityMatrix

        study = basic_ebios_rm_study_fixture
        url = f"/api/ebios-rm/studies/{study.id}/"

        response = admin_client.patch(
            url, {"responsibility_matrix": "SuperNova study RACI"}, format="json"
        )
        assert response.status_code == 200, response.content
        study.refresh_from_db()
        matrix = study.responsibility_matrix
        assert matrix.name == "SuperNova study RACI"
        assert matrix.folder_id == study.folder_id
        assert matrix.preset == ResponsibilityMatrix.Preset.RACI

        response = admin_client.patch(
            url, {"responsibility_matrix": "SuperNova study RACI"}, format="json"
        )
        assert response.status_code == 200, response.content
        study.refresh_from_db()
        assert study.responsibility_matrix_id == matrix.id
        assert (
            ResponsibilityMatrix.objects.filter(name="SuperNova study RACI").count()
            == 1
        )

    def test_existing_id_is_left_alone(
        self, admin_client, basic_ebios_rm_study_fixture
    ):
        from pmbok.models import ResponsibilityMatrix

        study = basic_ebios_rm_study_fixture
        matrix = ResponsibilityMatrix.objects.create(
            name="Existing RACI", folder=study.folder
        )

        response = admin_client.patch(
            f"/api/ebios-rm/studies/{study.id}/",
            {"responsibility_matrix": str(matrix.id)},
            format="json",
        )

        assert response.status_code == 200, response.content
        study.refresh_from_db()
        assert study.responsibility_matrix_id == matrix.id
        assert ResponsibilityMatrix.objects.count() == 1
