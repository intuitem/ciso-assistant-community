"""End-to-end import check for the OWASP ASI Top 10 2026 library."""

import pytest

from core.apps import startup
from core.models import Framework, LoadedLibrary, RequirementNode, StoredLibrary, Threat


@pytest.mark.django_db
def test_asi_top_10_library_loads():
    startup(None)
    # startup() stores every library shipped in library/libraries; ours must be among them
    stored = StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:owasp-asi-top-10-2026"
    )

    error = stored.load()
    assert error is None, f"load failed: {error}"

    lib = LoadedLibrary.objects.get(
        urn="urn:intuitem:risk:library:owasp-asi-top-10-2026"
    )
    assert lib.threats.count() == 10

    fw = Framework.objects.get(urn="urn:intuitem:risk:framework:owasp-asi-top-10-2026")
    nodes = RequirementNode.objects.filter(framework=fw)
    assert nodes.count() == 96
    assert nodes.filter(assessable=True).count() == 86

    # every assessable node is linked to its parent ASI threat
    linked = [n for n in nodes.filter(assessable=True) if n.threats.count() == 1]
    assert len(linked) == 86

    goal_hijack = Threat.objects.get(
        urn="urn:intuitem:risk:threat:owasp-asi-top-10-2026:asi01"
    )
    assert goal_hijack.name == "Agent Goal Hijack"
    assert goal_hijack.requirements.count() == 9
