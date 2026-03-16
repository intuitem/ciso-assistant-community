from django.core.exceptions import ValidationError
import pytest

from rest_framework import serializers

from core.serializers import FolderWriteSerializer
from core.utils import UserGroupCodename
from iam.models import Folder, UserGroup, User


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

    def test_create_default_groups_respects_flag(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(
            name="No IAM Groups",
            parent_folder=root_folder,
            create_iam_groups=False,
        )
        Folder.create_default_ug_and_ra(folder)
        assert not UserGroup.objects.filter(folder=folder).exists()

    def test_disable_iam_groups_with_members_fails(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(
            name="Domain IAM", parent_folder=root_folder, create_iam_groups=True
        )
        Folder.create_default_ug_and_ra(folder)
        reader_group = UserGroup.objects.get(
            folder=folder, name=str(UserGroupCodename.READER)
        )
        user = User.objects.create_user(email="member@example.com")
        reader_group.user_set.add(user)

        serializer = FolderWriteSerializer()
        with pytest.raises(serializers.ValidationError):
            serializer.update(folder, {"create_iam_groups": False})

    def test_disable_iam_groups_without_members(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(
            name="Domain IAM Remove",
            parent_folder=root_folder,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(folder)
        serializer = FolderWriteSerializer()
        serializer.update(folder, {"create_iam_groups": False})
        folder.refresh_from_db()
        assert folder.create_iam_groups is False
        assert not UserGroup.objects.filter(folder=folder, builtin=True).exists()

    def test_enable_iam_groups_creates_defaults(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(
            name="Domain IAM Enable",
            parent_folder=root_folder,
            create_iam_groups=False,
        )
        serializer = FolderWriteSerializer()
        serializer.update(folder, {"create_iam_groups": True})
        folder.refresh_from_db()
        assert folder.create_iam_groups is True
        assert UserGroup.objects.filter(
            folder=folder, name=str(UserGroupCodename.READER)
        ).exists()
