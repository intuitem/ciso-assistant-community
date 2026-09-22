"""Operational scenario techniques in domain export / import.

Library techniques travel as urns and are re-bound to the rows the target
already holds; a custom one travels as a full object like a custom threat.
"""

import io

import pytest

from core.models import LoadedLibrary, RiskMatrix, StoredLibrary, Terminology, Threat
from ebios_rm.models import (
    AttackPath,
    EbiosRMStudy,
    OperationalScenario,
    RoTo,
    StrategicScenario,
)
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from sec_intel.models import Technique
from serdes.domain_io import export_domain, import_objects, process_uploaded_file
from serdes.utils import get_domain_export_objects


@pytest.fixture
def root_folder():
    return Folder.get_root_folder()


@pytest.fixture
def admin_user(root_folder):
    user = User.objects.create_user("ttp-export@test.com")
    group = UserGroup.objects.create(name="ttpx-admins", folder=root_folder)
    group.user_set.add(user)
    RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-ADM"),
        folder=root_folder,
        is_recursive=True,
    ).perimeter_folders.add(root_folder)
    return user


@pytest.fixture
def ttp_library(root_folder):
    """Stand in for a loaded ATT&CK library without shipping the real one."""
    return LoadedLibrary.objects.create(
        name="TTPX Catalog",
        urn="urn:test:ttpx:library:ttpx",
        version=1,
        folder=root_folder,
    )


@pytest.fixture
def ebios_domain(root_folder, ttp_library):
    library = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm"
    ).last()
    assert library is not None
    library.load()
    matrix = RiskMatrix.objects.get(
        urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
    )

    domain = Folder.objects.create(
        name="TTPX Source",
        parent_folder=root_folder,
        content_type=Folder.ContentType.DOMAIN,
    )
    study = EbiosRMStudy.objects.create(
        name="TTPX study", risk_matrix=matrix, folder=domain
    )
    risk_origin, _ = Terminology.objects.get_or_create(
        name="state",
        field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
        defaults={"is_visible": True},
    )
    ro_to = RoTo.objects.create(
        risk_origin=risk_origin,
        target_objective="TTPX objective",
        ebios_rm_study=study,
    )
    strategic_scenario = StrategicScenario.objects.create(
        name="TTPX strategic scenario", ebios_rm_study=study, ro_to_couple=ro_to
    )
    attack_path = AttackPath.objects.create(
        name="TTPX attack path",
        ebios_rm_study=study,
        strategic_scenario=strategic_scenario,
    )
    operational_scenario = OperationalScenario.objects.create(
        ebios_rm_study=study, attack_path=attack_path
    )

    library_technique = Technique.objects.create(
        ref_id="TTPX-001",
        name="Library Technique",
        urn="urn:test:ttpx:technique:ttpx-001",
        library=ttp_library,
        folder=root_folder,
    )
    custom_technique = Technique.objects.create(
        ref_id="TTPX-C1", name="Custom Technique", folder=domain
    )
    threat = Threat.objects.create(name="TTPX threat", folder=domain)

    operational_scenario.techniques.set([library_technique, custom_technique])
    operational_scenario.threats.set([threat])

    return {
        "domain": domain,
        "operational_scenario": operational_scenario,
        "library_technique": library_technique,
        "custom_technique": custom_technique,
        "threat": threat,
    }


@pytest.mark.django_db
class TestTechniqueExportScope:
    def test_linked_techniques_are_in_scope(self, ebios_domain):
        data = get_domain_export_objects(ebios_domain["domain"])

        assert ebios_domain["library_technique"] in data["technique"]
        assert ebios_domain["custom_technique"] in data["technique"]

    def test_technique_library_is_pulled_in_as_required(
        self, ebios_domain, ttp_library
    ):
        data = get_domain_export_objects(ebios_domain["domain"])

        assert ttp_library in data["loadedlibrary"]

    def test_unrelated_technique_stays_out(self, ebios_domain, root_folder):
        unrelated = Technique.objects.create(
            ref_id="TTPX-999", name="Unrelated", folder=root_folder
        )
        data = get_domain_export_objects(ebios_domain["domain"])

        assert unrelated not in data["technique"]


@pytest.mark.django_db
class TestTechniqueRoundTrip:
    def test_export_import_preserves_techniques(self, ebios_domain, admin_user):
        response = export_domain(ebios_domain["domain"], admin_user)
        assert response.status_code == 200

        json_dump = process_uploaded_file(io.BytesIO(response.content))
        result = import_objects(
            json_dump,
            domain_name="TTPX Imported",
            load_missing_libraries=True,
            user=admin_user,
        )
        assert result["message"] == "Import successful"

        imported = Folder.objects.get(
            name="TTPX Imported", content_type=Folder.ContentType.DOMAIN
        )
        scenario = OperationalScenario.objects.get(ebios_rm_study__folder=imported)

        assert sorted(t.ref_id for t in scenario.techniques.all()) == [
            "TTPX-001",
            "TTPX-C1",
        ]
        assert [t.name for t in scenario.threats.all()] == ["TTPX threat"]

    def test_library_technique_is_rebound_not_duplicated(
        self, ebios_domain, admin_user
    ):
        response = export_domain(ebios_domain["domain"], admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="TTPX Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="TTPX Imported", content_type=Folder.ContentType.DOMAIN
        )
        scenario = OperationalScenario.objects.get(ebios_rm_study__folder=imported)

        # The library row is shared, not copied: same pk on both sides.
        assert scenario.techniques.get(ref_id="TTPX-001").pk == (
            ebios_domain["library_technique"].pk
        )
        assert (
            Technique.objects.filter(urn="urn:test:ttpx:technique:ttpx-001").count()
            == 1
        )

        # The custom one is rebuilt in the new domain, like a custom threat.
        rebuilt = scenario.techniques.get(ref_id="TTPX-C1")
        assert rebuilt.pk != ebios_domain["custom_technique"].pk
        assert rebuilt.folder == imported
