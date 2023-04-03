from core.models import *
from core.helpers import *
from iam.models import *
from library.utils import *
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
import pytest


@pytest.fixture
def matrix_fixture():
    Folder.objects.create(
        name="Global", content_type=Folder.ContentType.ROOT, builtin=True)
    import_library(get_library('Critical matrix 5x5'))


@pytest.mark.django_db
def test_get_rating_options_no_matrix():
    root_folder = Folder.objects.create(
        name='Global', content_type=Folder.ContentType.ROOT, builtin=True)
    user = User.objects.create(email='test@test.com', password='test')
    assert get_rating_options(user) == []


@pytest.mark.usefixtures('matrix_fixture')
@pytest.mark.django_db
def test_get_rating_options_no_perm_to_view_matrix(matrix_fixture):
    user = User.objects.create(email='test@test.com', password='test')
    assert get_rating_options(user) == []


@pytest.mark.usefixtures('matrix_fixture')
@pytest.mark.django_db
def test_get_rating_options_perm_to_view_matrix():
    user = User.objects.create(email='test@test.com', password='test')
    folder = Folder.objects.create(name='test', content_type=Folder.ContentType.DOMAIN, builtin=False,
                                   parent_folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
    project = Project.objects.create(name='test', folder=folder)
    analysis = Analysis.objects.create(name='test', project=project, rating_matrix=RiskMatrix.objects.latest('created_at'))
    RiskScenario.objects.create(name='test', analysis=analysis, threat=Threat.objects.create(name='test', folder=Folder.objects.get(content_type=Folder.ContentType.ROOT)))
    role = Role.objects.create(name='test')
    auditor_permissions = Permission.objects.filter(codename__in=[
        "view_project",
        "view_analysis",
        "view_securitymeasure",
        "view_riskscenario",
        "view_riskacceptance",
        "view_asset",
        "view_threat",
        "view_securityfunction",
        "view_folder",
        "view_usergroup"
    ])
    role.permissions.set(auditor_permissions)
    role.save()
    role_assignment = RoleAssignment.objects.create(
        user=user,
        role=role,
        folder=folder,
    )
    role_assignment.perimeter_folders.add(folder)
    role_assignment.save()

    assert get_rating_options(user) == [
        (0, _('Very Low')),
        (1, _('Low')),
        (2, _('Medium')),
        (3, _('High')),
        (4, _('Very High')),
    ]


@pytest.mark.django_db
def test_get_rating_options_abbr_no_matrix():
    root_folder = Folder.objects.create(
        name='Global', content_type=Folder.ContentType.ROOT, builtin=True)
    user = User.objects.create(email='test@test.com', password='test')
    assert get_rating_options_abbr(user) == []


@pytest.mark.usefixtures('matrix_fixture')
@pytest.mark.django_db
def test_get_rating_options_abbr_no_perm_to_view_matrix(matrix_fixture):
    user = User.objects.create(email='test@test.com', password='test')
    assert get_rating_options_abbr(user) == []


@pytest.mark.usefixtures('matrix_fixture')
@pytest.mark.django_db
def test_get_rating_options_abbr_perm_to_view_matrix():
    user = User.objects.create(email='test@test.com', password='test')
    folder = Folder.objects.create(name='test', content_type=Folder.ContentType.DOMAIN, builtin=False,
                                   parent_folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
    project = Project.objects.create(name='test', folder=folder)
    analysis = Analysis.objects.create(name='test', project=project, rating_matrix=RiskMatrix.objects.latest('created_at'))
    RiskScenario.objects.create(name='test', analysis=analysis, threat=Threat.objects.create(name='test', folder=Folder.objects.get(content_type=Folder.ContentType.ROOT)))
    role = Role.objects.create(name='test')
    auditor_permissions = Permission.objects.filter(codename__in=[
        "view_project",
        "view_analysis",
        "view_securitymeasure",
        "view_riskscenario",
        "view_riskacceptance",
        "view_asset",
        "view_threat",
        "view_securityfunction",
        "view_folder",
        "view_usergroup"
    ])
    role.permissions.set(auditor_permissions)
    role.save()
    role_assignment = RoleAssignment.objects.create(
        user=user,
        role=role,
        folder=folder,
    )
    role_assignment.perimeter_folders.add(folder)
    role_assignment.save()

    assert get_rating_options_abbr(user) == [
        ('VL', _('Very Low')),
        ('L', _('Low')),
        ('M', _('Medium')),
        ('H', _('High')),
        ('VH', _('Very High'))
    ]
