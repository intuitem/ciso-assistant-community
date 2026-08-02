"""Regression tests for RequirementMappingSetReadSerializer framework name resolution.

Guards against the regression where `source_framework.str` returned the URN
instead of the display name when the referenced framework was not imported
(present only as a StoredLibrary, not as a Framework object).
"""

import pytest

from core.models import StoredLibrary
from core.serializers import RequirementMappingSetReadSerializer


def _make_framework_library(urn, name):
    return StoredLibrary.objects.create(
        urn=urn,
        name=name,
        version=1,
        locale="en",
        hash_checksum=name,
        content={"framework": {"urn": urn, "name": name}},
    )


class _FakeMappingSet:
    def __init__(self, source_urn, target_urn):
        self.content = {
            "requirement_mapping_set": {
                "source_framework_urn": source_urn,
                "target_framework_urn": target_urn,
            }
        }


@pytest.mark.django_db
class TestRequirementMappingSetFrameworkName:
    def test_resolves_name_from_library_when_not_imported(self):
        """Retrieve path: name comes from the framework library content, no import needed."""
        urn = "urn:test:risk:framework:foo"
        _make_framework_library(urn, "Foo Framework")

        serializer = RequirementMappingSetReadSerializer()
        assert serializer._framework_info(urn) == {"str": "Foo Framework", "urn": urn}

    def test_uses_prebuilt_map_on_list_path(self):
        """List path: name comes from the batched framework_map in context."""
        urn = "urn:test:risk:framework:bar"
        serializer = RequirementMappingSetReadSerializer(
            context={"optimized_data": {"framework_map": {urn: "Bar Framework"}}}
        )
        assert serializer._framework_info(urn) == {"str": "Bar Framework", "urn": urn}

    def test_falls_back_to_urn_when_framework_absent(self):
        """No library and no map entry: str equals urn (frameworks_available=False)."""
        urn = "urn:test:risk:framework:missing"
        serializer = RequirementMappingSetReadSerializer()
        assert serializer._framework_info(urn) == {"str": urn, "urn": urn}

    def test_get_source_and_target_framework(self):
        source_urn = "urn:test:risk:framework:src"
        target_urn = "urn:test:risk:framework:tgt"
        _make_framework_library(source_urn, "Source FW")
        _make_framework_library(target_urn, "Target FW")

        serializer = RequirementMappingSetReadSerializer()
        obj = _FakeMappingSet(source_urn, target_urn)

        assert serializer.get_source_framework(obj)["str"] == "Source FW"
        assert serializer.get_target_framework(obj)["str"] == "Target FW"
        # Both frameworks resolvable -> available flag is True.
        assert serializer.get_frameworks_available(obj) is True
