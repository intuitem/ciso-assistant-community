"""Splash screen nodes are never assessable.

The framework builder used to leave `assessable=True` behind when an existing
requirement node was switched to splash display mode, which made the node
surface as a regular requirement (red result dot) in the respondent view
instead of a splash screen. The loader now normalizes the flag on import.
"""

from pathlib import Path

import pytest

from core.models import Framework, RequirementNode, StoredLibrary

FIXTURE = Path(__file__).parent / "fixtures" / "test-splash-assessable.yaml"


@pytest.mark.django_db
def test_import_forces_splash_nodes_to_non_assessable():
    stored, err = StoredLibrary.store_library_content(FIXTURE.read_bytes())
    assert err is None
    load_err = stored.load()
    assert load_err is None

    framework = Framework.objects.get(
        urn="urn:intuitem:test:framework:splash-assessable"
    )
    splash = RequirementNode.objects.get(
        framework=framework, urn="urn:intuitem:test:req_node:splash:intro"
    )
    assert splash.display_mode == RequirementNode.DisplayMode.SPLASH
    assert splash.assessable is False

    # Regular nodes keep their flag.
    child = RequirementNode.objects.get(
        framework=framework, urn="urn:intuitem:test:req_node:splash:req"
    )
    assert child.assessable is True
