"""Essential Eight (Nov 2023) links every requirement to doc-pol reference controls and common-catalog threats."""

import pytest
from core.models import LoadedLibrary, RequirementNode, StoredLibrary

E8 = "urn:intuitem:risk:library:essential-eight-2023"


@pytest.mark.django_db
def test_every_requirement_has_threats_and_reference_controls():
    if not LoadedLibrary.objects.filter(urn=E8).exists():
        assert StoredLibrary.objects.get(urn=E8).load() is None
    nodes = RequirementNode.objects.filter(
        framework__urn="urn:intuitem:risk:framework:essential-eight-2023",
        assessable=True,
    )
    assert nodes.count() == 152
    for node in nodes:
        assert node.reference_controls.exists(), node.urn
        assert node.threats.exists(), node.urn
        assert {t.library.urn for t in node.threats.all()} == {
            "urn:intuitem:risk:library:intuitem-common-catalog"
        }, node.urn
