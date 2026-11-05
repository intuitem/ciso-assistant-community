from core.models import (
    ComplianceAssessment,
    Framework,
    LoadedLibrary,
    Perimeter,
    StoredLibrary,
)
from django.test import TestCase
from iam.models import Folder


FRAMEWORK_V1 = """
urn: urn:intuitem:test:library:implementation-group-update
locale: en
ref_id: IG-UPDATE
name: Implementation group update
description: Test implementation group cleanup
copyright: Test
version: 1
publication_date: 2026-07-10
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:implementation-group-update
    ref_id: IG-UPDATE
    name: Implementation group update
    description: Test implementation group cleanup
    implementation_groups_definition:
      - ref_id: kept
        name: Kept
      - ref_id: removed
        name: Removed
    requirement_nodes:
      - urn: urn:intuitem:test:req_node:ig-update:req-1
        assessable: true
        depth: 1
        ref_id: REQ-1
        name: Requirement 1
        implementation_groups:
          - kept
          - removed
""".lstrip()


FRAMEWORK_V2 = """
urn: urn:intuitem:test:library:implementation-group-update
locale: en
ref_id: IG-UPDATE
name: Implementation group update
description: Test implementation group cleanup
copyright: Test
version: 2
publication_date: 2026-07-10
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:implementation-group-update
    ref_id: IG-UPDATE
    name: Implementation group update
    description: Test implementation group cleanup
    implementation_groups_definition:
      - ref_id: kept
        name: Kept
    requirement_nodes:
      - urn: urn:intuitem:test:req_node:ig-update:req-1
        assessable: true
        depth: 1
        ref_id: REQ-1
        name: Requirement 1
        implementation_groups:
          - kept
""".lstrip()


FRAMEWORK_V3_WITHOUT_IMPLEMENTATION_GROUPS = """
urn: urn:intuitem:test:library:implementation-group-update
locale: en
ref_id: IG-UPDATE
name: Implementation group update
description: Test implementation group cleanup
copyright: Test
version: 3
publication_date: 2026-07-10
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:implementation-group-update
    ref_id: IG-UPDATE
    name: Implementation group update
    description: Test implementation group cleanup
    requirement_nodes:
      - urn: urn:intuitem:test:req_node:ig-update:req-1
        assessable: true
        depth: 1
        ref_id: REQ-1
        name: Requirement 1
""".lstrip()


class TestImplementationGroupUpdate(TestCase):
    def test_framework_update_removes_stale_selected_implementation_groups(self):
        stored_v1, error = StoredLibrary.store_library_content(
            FRAMEWORK_V1.encode("utf-8")
        )
        assert error is None
        assert stored_v1.load() is None

        framework = Framework.objects.get(
            urn="urn:intuitem:test:framework:implementation-group-update"
        )
        folder = Folder.get_root_folder()
        perimeter = Perimeter.objects.create(name="IG update perimeter", folder=folder)

        mixed_selection = ComplianceAssessment.objects.create(
            name="Mixed IG selection",
            framework=framework,
            folder=folder,
            perimeter=perimeter,
            selected_implementation_groups=["removed", "kept"],
        )
        removed_only_selection = ComplianceAssessment.objects.create(
            name="Removed-only IG selection",
            framework=framework,
            folder=folder,
            perimeter=perimeter,
            selected_implementation_groups=["removed"],
        )
        valid_selection = ComplianceAssessment.objects.create(
            name="Valid IG selection",
            framework=framework,
            folder=folder,
            perimeter=perimeter,
            selected_implementation_groups=["kept"],
        )

        stored_v2, error = StoredLibrary.store_library_content(
            FRAMEWORK_V2.encode("utf-8")
        )
        assert error is None
        assert stored_v2 is not None

        loaded_library = LoadedLibrary.objects.get(urn=stored_v1.urn)
        assert loaded_library.update(strategy="clamp") is None

        framework.refresh_from_db()
        mixed_selection.refresh_from_db()
        removed_only_selection.refresh_from_db()
        valid_selection.refresh_from_db()

        assert framework.implementation_groups_definition == [
            {"ref_id": "kept", "name": "Kept"}
        ]
        assert mixed_selection.selected_implementation_groups == ["kept"]
        assert removed_only_selection.selected_implementation_groups == []
        assert valid_selection.selected_implementation_groups == ["kept"]

        stored_v3, error = StoredLibrary.store_library_content(
            FRAMEWORK_V3_WITHOUT_IMPLEMENTATION_GROUPS.encode("utf-8")
        )
        assert error is None
        assert stored_v3 is not None
        assert loaded_library.update(strategy="clamp") is None

        framework.refresh_from_db()
        mixed_selection.refresh_from_db()
        removed_only_selection.refresh_from_db()
        valid_selection.refresh_from_db()

        assert framework.implementation_groups_definition is None
        assert mixed_selection.selected_implementation_groups == []
        assert removed_only_selection.selected_implementation_groups == []
        assert valid_selection.selected_implementation_groups == []
