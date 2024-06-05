from serdes.utils import *
import pytest


@pytest.fixture
def basic_folder_structure():
    Folder.objects.create(
        name="Global", content_type=Folder.ContentType.ROOT, builtin=True
    )
    Folder.objects.create(
        name="Test folder", content_type=Folder.ContentType.DOMAIN, builtin=False
    )
