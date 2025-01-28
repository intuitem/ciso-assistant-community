import pytest

from core.models import (
    Project,
    StoredLibrary,
    FilteringLabel,
    AppliedControl,
)
from iam.models import Folder


@pytest.fixture
def domain_project_fixture():
    root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    folder = Folder.objects.create(
        parent_folder=root_folder,
        name="test folder",
        description="test folder description",
    )
    project = Project.objects.create(name="test project", folder=folder)
    return project


@pytest.fixture
def risk_matrix_fixture():
    library = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:critical_risk_matrix_5x5"
    ).last()
    assert library is not None
    library.load()


@pytest.fixture
def iso27001_csf1_1_frameworks_fixture():
    iso27001_library = StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:iso27001-2022", locale="en"
    )
    assert iso27001_library is not None
    iso27001_library.load()
    csf_1_1_library = StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:nist-csf-1.1", locale="en"
    )
    assert csf_1_1_library is not None
    csf_1_1_library.load()


@pytest.fixture
def filtering_labels():
    labels = [
        FilteringLabel.objects.create(label="critical"),
        FilteringLabel.objects.create(label="internal"),
        FilteringLabel.objects.create(label="external"),
    ]
    return labels


@pytest.fixture
def applied_controls():
    return [
        AppliedControl.objects.create(
            name="Bastion",
        ),
        AppliedControl.objects.create(
            name="Firewall",
        ),
        AppliedControl.objects.create(
            name="IDS",
        ),
    ]
