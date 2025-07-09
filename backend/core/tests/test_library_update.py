import pytest

from core.models import (
    LibraryUpdater,
    LoadedLibrary,
    StoredLibrary,
    ReferenceControl,
    Threat,
)


@pytest.fixture
def old_library():
    """Fixture to create a real LoadedLibrary instance in the test DB."""
    return LoadedLibrary.objects.create(
        urn="urn:lib:old:1",
        locale="en",
        default_locale=True,
        provider="TestProvider",
        version=1,
    )


@pytest.fixture
def new_library_content():
    """Fixture for the content of the new StoredLibrary."""
    return {
        "provider": "NewProvider",
        "dependencies": ["urn:lib:dep:1"],
        "reference_controls": [
            {"urn": "urn:rc:1", "name": "Control One New"},
            {"urn": "urn:rc:2", "name": "Control Two Updated"},
        ],
        "threats": [
            {"urn": "urn:threat:100", "name": "New Threat"},
            {"urn": "urn:threat:200", "name": "Threat Two Updated"},
        ],
    }


@pytest.fixture
def new_library(new_library_content):
    """Fixture to create a real StoredLibrary instance in the test DB."""
    return StoredLibrary.objects.create(
        urn="urn:lib:new:1",
        content=new_library_content,
        dependencies=new_library_content["dependencies"],
        provider=new_library_content["provider"],
        version=1,
    )


@pytest.mark.django_db
class TestLibraryUpdater:
    """Test suite for the object synchronization logic in LibraryUpdater."""

    def test_synchronize_full_mixed_mode_for_controls(self, old_library, new_library):
        """Tests create, update, and unlink operations for ReferenceControls in one go."""
        ReferenceControl.objects.create(
            urn="urn:rc:2",
            name="Control Two Original",
            library=old_library,
            locale="en",
            default_locale=True,
            provider="TestProvider",
        )
        ReferenceControl.objects.create(
            urn="urn:rc:3",
            name="Control Three To Unlink",
            library=old_library,
            locale="en",
            default_locale=True,
            provider="TestProvider",
        )

        updater = LibraryUpdater(old_library, new_library)
        created_objects = updater.update_reference_controls()

        assert ReferenceControl.objects.count() == 3
        assert ReferenceControl.objects.get(urn="urn:rc:1").name == "Control One New"
        assert (
            ReferenceControl.objects.get(urn="urn:rc:2").name == "Control Two Updated"
        )
        assert ReferenceControl.objects.get(urn="urn:rc:3").library is None
        assert len(created_objects) == 1 and created_objects[0].urn == "urn:rc:1"

    def test_synchronize_threats(self, old_library, new_library):
        """Tests create, update, and unlink operations for Threats in one go."""
        # Arrange
        Threat.objects.create(
            urn="urn:threat:200",
            name="Threat Two Original",
            library=old_library,
            locale="en",
            default_locale=True,
            provider="TestProvider",
        )
        Threat.objects.create(
            urn="urn:threat:300",
            name="Threat Three To Unlink",
            library=old_library,
            locale="en",
            default_locale=True,
            provider="TestProvider",
        )

        updater = LibraryUpdater(old_library, new_library)
        created_objects = updater.update_threats()

        assert Threat.objects.count() == 3
        assert Threat.objects.get(urn="urn:threat:100").name == "New Threat"
        assert Threat.objects.get(urn="urn:threat:200").name == "Threat Two Updated"
        assert Threat.objects.get(urn="urn:threat:300").library is None
        assert len(created_objects) == 1 and created_objects[0].urn == "urn:threat:100"

    def test_synchronize_only_creates_new_objects(self, old_library, new_library):
        """Tests that all incoming objects are created when the DB is empty."""
        assert ReferenceControl.objects.count() == 0

        updater = LibraryUpdater(old_library, new_library)
        created_objects = updater.update_reference_controls()

        assert ReferenceControl.objects.count() == 2
        assert len(created_objects) == 2
        assert {obj.urn for obj in created_objects} == {"urn:rc:1", "urn:rc:2"}

    def test_synchronize_only_updates_existing_objects(self, old_library, new_library):
        """Tests that existing objects are updated and no new ones are created."""
        ReferenceControl.objects.create(
            urn="urn:rc:1",
            name="Original Name 1",
            library=old_library,
            locale="en",
            default_locale=True,
            provider="TestProvider",
        )
        ReferenceControl.objects.create(
            urn="urn:rc:2",
            name="Original Name 2",
            library=old_library,
            locale="en",
            default_locale=True,
            provider="TestProvider",
        )
        assert ReferenceControl.objects.count() == 2

        updater = LibraryUpdater(old_library, new_library)
        created_objects = updater.update_reference_controls()

        assert ReferenceControl.objects.count() == 2
        assert ReferenceControl.objects.get(urn="urn:rc:1").name == "Control One New"
        assert (
            ReferenceControl.objects.get(urn="urn:rc:2").name == "Control Two Updated"
        )
        assert len(created_objects) == 0

    def test_synchronize_only_unlinks_objects(self, old_library, new_library):
        """Tests that all existing objects are unlinked when incoming data is empty."""
        new_library.content["reference_controls"] = []
        new_library.save()
        ReferenceControl.objects.create(
            urn="urn:rc:to_unlink",
            name="Old Control",
            library=old_library,
            locale="en",
            default_locale=True,
            provider="TestProvider",
        )
        assert ReferenceControl.objects.count() == 1

        updater = LibraryUpdater(old_library, new_library)
        created_objects = updater.update_reference_controls()

        assert ReferenceControl.objects.count() == 1
        assert ReferenceControl.objects.get(urn="urn:rc:to_unlink").library is None
        assert created_objects == []

    def test_synchronize_no_changes_needed(self, old_library, new_library):
        """Tests that nothing changes when DB state matches incoming data."""
        rc1_data = new_library.content["reference_controls"][0]
        rc2_data = new_library.content["reference_controls"][1]
        ReferenceControl.objects.create(
            urn=rc1_data["urn"],
            name=rc1_data["name"],
            library=old_library,
            locale="en",
            default_locale=True,
            provider="NewProvider",
            is_published=True,
        )
        ReferenceControl.objects.create(
            urn=rc2_data["urn"],
            name=rc2_data["name"],
            library=old_library,
            locale="en",
            default_locale=True,
            provider="NewProvider",
            is_published=True,
        )
        assert ReferenceControl.objects.count() == 2

        updater = LibraryUpdater(old_library, new_library)
        created_objects = updater.update_reference_controls()

        assert ReferenceControl.objects.count() == 2
        assert len(created_objects) == 0
        # Verify data is unchanged
        rc1_db = ReferenceControl.objects.get(urn=rc1_data["urn"])
        assert rc1_db.name == rc1_data["name"]
        assert rc1_db.library == old_library
