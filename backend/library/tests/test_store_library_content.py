import pytest
from core.models import StoredLibrary

SAMPLE_YAML_LIB_WITH_MAPPINGS = """
urn: urn:intuitem:test:library:map-nist-csf-1.1-nist-csf-2.0
locale: en
ref_id: test-map-nist-csf-1.1-nist-csf-2.0
name: Sample test mapping from nist-csf-1.1 to nist-csf-2.0
description: Sample test mapping from nist-csf-1.1 to nist-csf-2.0
version: 1
publication_date: 2024-06-29
copyright: NIST
provider: NIST
packager: intuitem
dependencies:
- urn:intuitem:risk:library:nist-csf-2.0
- urn:intuitem:risk:library:nist-csf-1.1
objects:
  requirement_mapping_set:
    urn: urn:intuitem:test:requirement_mapping_set:nist-csf-1.1-to-nist-csf-2.0
    ref_id: test-mapping-nist-csf-1.1-nist-csf-2.0
    name: test-mapping-nist-csf-1.1-nist-csf-2.0
    source_framework_urn: urn:intuitem:risk:framework:nist-csf-1.1
    target_framework_urn: urn:intuitem:risk:framework:nist-csf-2.0
    requirement_mappings:
    - source_requirement_urn: urn:intuitem:risk:req_node:nist-csf-1.1:id.gv
      target_requirement_urn: urn:intuitem:risk:req_node:nist-csf-2.0:gv
      relationship: intersect
      rationale: semantic
      annotation: ''
""".lstrip().encode("utf-8")


class TestStoreLibraryContent:
    @pytest.mark.django_db
    def test_store_library_content_sets_autoload_to_true_if_lib_has_mappings(self):
        stored_library = StoredLibrary.store_library_content(
            SAMPLE_YAML_LIB_WITH_MAPPINGS
        )
        assert stored_library is not None
        assert stored_library.autoload is True
