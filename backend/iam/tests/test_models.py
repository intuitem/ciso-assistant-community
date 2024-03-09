from core.models import *
from core.models import *
from iam.models import *
from library.utils import *
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestFolder:
    pytestmark = pytest.mark.django_db

    def test_folder_creation(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(name="Folder", parent_folder=root_folder)
        assert folder.name == "Folder"
        assert folder.parent_folder == root_folder
        assert folder.content_type == Folder.ContentType.DOMAIN

    def test_folder_creation_same_name(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        Folder.objects.create(name="Folder", parent_folder=root_folder)
        with pytest.raises(ValidationError):
            Folder.objects.create(name="Folder", parent_folder=root_folder)

    def test_folder_creation_same_name_different_parent(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        parent_folder = Folder.objects.create(name="Parent", parent_folder=root_folder)

        folder1 = Folder.objects.create(name="Folder", parent_folder=root_folder)
        folder2 = Folder.objects.create(name="Folder", parent_folder=parent_folder)
        assert folder1.name == "Folder"
        assert folder2.name == "Folder"
        assert folder1.content_type == Folder.ContentType.DOMAIN
        assert folder2.content_type == Folder.ContentType.DOMAIN
        assert folder1.parent_folder == root_folder
        assert folder2.parent_folder == parent_folder
