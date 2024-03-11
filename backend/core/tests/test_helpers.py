from core.models import *
from core.helpers import *
from iam.models import *
from library.utils import *
from django.utils.translation import gettext_lazy as _
import pytest


@pytest.fixture
def risk_matrix_fixture():
    import_library_view(
        get_library("urn:intuitem:risk:library:critical_risk_matrix_5x5")
    )


@pytest.mark.django_db
def test_get_rating_options_no_matrix():
    user = User.objects.create(email="test@test.com", password="test")
    assert get_rating_options(user) == []


@pytest.mark.usefixtures("risk_matrix_fixture")
@pytest.mark.django_db
def test_get_rating_options_no_perm_to_view_matrix(risk_matrix_fixture):
    user = User.objects.create(email="test@test.com", password="test")
    assert get_rating_options(user) == []


@pytest.mark.usefixtures("risk_matrix_fixture")
@pytest.mark.django_db
def test_get_rating_options_perm_to_view_matrix():
    user = User.objects.create(email="test@test.com", password="test")
    folder = Folder.objects.create(
        name="test",
        content_type=Folder.ContentType.DOMAIN,
        builtin=False,
        parent_folder=Folder.objects.get(content_type=Folder.ContentType.ROOT),
    )
    project = Project.objects.create(name="test", folder=folder)
    risk_assessment = RiskAssessment.objects.create(
        name="test",
        project=project,
        risk_matrix=RiskMatrix.objects.latest("created_at"),
    )
    RiskScenario.objects.create(name="test", risk_assessment=risk_assessment)
    role = Role.objects.create(name="test")
    auditor_permissions = Permission.objects.filter(
        codename__in=[
            "view_project",
            "view_riskassessment",
            "view_appliedcontrol",
            "view_riskscenario",
            "view_riskacceptance",
            "view_asset",
            "view_threat",
            "view_referencecontrol",
            "view_folder",
            "view_usergroup",
        ]
    )
    role.permissions.set(auditor_permissions)
    role.save()
    role_assignment = RoleAssignment.objects.create(
        user=user,
        role=role,
        folder=folder,
        is_recursive=True,
    )
    role_assignment.perimeter_folders.add(folder)
    role_assignment.save()

    assert get_rating_options(user) == [
        (0, _("Very Low")),
        (1, _("Low")),
        (2, _("Medium")),
        (3, _("High")),
        (4, _("Very High")),
    ]


@pytest.mark.django_db
def test_get_rating_options_abbr_no_matrix():
    user = User.objects.create(email="test@test.com", password="test")
    assert get_rating_options_abbr(user) == []


@pytest.mark.usefixtures("risk_matrix_fixture")
@pytest.mark.django_db
def test_get_rating_options_abbr_no_perm_to_view_matrix(risk_matrix_fixture):
    user = User.objects.create(email="test@test.com", password="test")
    assert get_rating_options_abbr(user) == []


@pytest.mark.usefixtures("risk_matrix_fixture")
@pytest.mark.django_db
def test_get_rating_options_abbr_perm_to_view_matrix():
    user = User.objects.create(email="test@test.com", password="test")
    folder = Folder.objects.create(
        name="test",
        content_type=Folder.ContentType.DOMAIN,
        builtin=False,
        parent_folder=Folder.objects.get(content_type=Folder.ContentType.ROOT),
    )
    project = Project.objects.create(name="test", folder=folder)
    risk_assessment = RiskAssessment.objects.create(
        name="test",
        project=project,
        risk_matrix=RiskMatrix.objects.latest("created_at"),
    )
    RiskScenario.objects.create(name="test", risk_assessment=risk_assessment)
    role = Role.objects.create(name="test")
    auditor_permissions = Permission.objects.filter(
        codename__in=[
            "view_project",
            "view_riskassessment",
            "view_appliedcontrol",
            "view_riskscenario",
            "view_riskacceptance",
            "view_asset",
            "view_threat",
            "view_referencecontrol",
            "view_folder",
            "view_usergroup",
        ]
    )
    role.permissions.set(auditor_permissions)
    role.save()
    role_assignment = RoleAssignment.objects.create(
        user=user,
        role=role,
        folder=folder,
        is_recursive=True,
    )
    role_assignment.perimeter_folders.add(folder)
    role_assignment.save()

    assert get_rating_options_abbr(user) == [
        ("VL", _("Very Low")),
        ("L", _("Low")),
        ("M", _("Medium")),
        ("H", _("High")),
        ("VH", _("Very High")),
    ]
