from core.models import *
from core.helpers import *
from iam.models import *
from library.utils import *
from django.db.models import Count
import pytest

@pytest.fixture
def matrix_fixture():
    Folder.objects.create(
                name="Global", content_type=Folder.ContentType.ROOT, builtin=True)
    import_package(get_package('Critical matrix 5x5'))

@pytest.mark.django_db
def test_get_rating_options_no_matrix():
    root_folder = Folder.objects.create(name='Global', content_type=Folder.ContentType.ROOT, builtin=True)
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
    user = ...

    assert get_rating_options(user) == [
        (0, 'Very low'),
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Very high'),
    ]

@pytest.mark.django_db
def test_get_rating_options_abbr_no_matrix():
    root_folder = Folder.objects.create(name='Global', content_type=Folder.ContentType.ROOT, builtin=True)
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
    user = ...

    assert get_rating_options_abbr(user) == [
        (0, 'VL'),
        (1, 'L'),
        (2, 'M'),
        (3, 'H'),
        (4, 'VH'),
    ]
