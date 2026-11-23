"""MSIA-CL v0.6 library: import, profiles (implementation groups) and mappings.

Run: uv run pytest library/tests/test_msia_cl_library.py
"""

from pathlib import Path

import yaml
from django.test import TestCase

from core.mappings.engine import MappingEngine
from core.models import (
    ComplianceAssessment,
    Framework,
    LoadedLibrary,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
    StoredLibrary,
)
from iam.models import Folder

LIBRARIES = Path(__file__).resolve().parents[1] / "libraries"
FRAMEWORK_URN = "urn:athanor:risk:framework:msia-cl-0.6"


def _load(filename):
    """Load a built-in library (stored at startup, or stored here if not yet)."""
    content = (LIBRARIES / filename).read_bytes()
    urn = yaml.safe_load(content)["urn"]
    stored = StoredLibrary.objects.filter(urn=urn).order_by("-version").first()
    if stored is None:
        stored, error = StoredLibrary.store_library_content(content, builtin=True)
        assert error is None, error
    if not LoadedLibrary.objects.filter(urn=urn).exists():
        assert stored.load() is None


class TestMsiaClLibrary(TestCase):
    @classmethod
    def setUpTestData(cls):
        for filename in (
            "iso42001-2023.yaml",
            "nist-ai-rmf-1.0.yaml",
            "msia-cl-0.6.yaml",
            "mapping-msia-cl-0.6-to-iso42001-2023.yaml",
            "mapping-msia-cl-0.6-to-nist-ai-rmf-1.0.yaml",
        ):
            _load(filename)

    def test_framework_structure(self):
        framework = Framework.objects.get(urn=FRAMEWORK_URN)
        nodes = RequirementNode.objects.filter(framework=framework)
        assert nodes.filter(assessable=True).count() == 43
        assert nodes.filter(assessable=False, parent_urn__isnull=True).count() == 8
        assert [g["ref_id"] for g in framework.implementation_groups_definition] == [
            "base",
            "estandar",
            "reforzado",
        ]
        # Base is pre-selected in the audit form; an empty selection would show all 43.
        defaults = [
            g["ref_id"]
            for g in framework.implementation_groups_definition
            if g.get("default_selected")
        ]
        assert defaults == ["base"]
        gob01 = nodes.get(ref_id="GOB-01")
        assert gob01.typical_evidence
        assert gob01.annotation.startswith("Riesgo que reduce:")
        assert "**" not in (gob01.description or "")

    def test_profiles_are_cumulative(self):
        framework = Framework.objects.get(urn=FRAMEWORK_URN)
        folder = Folder.get_root_folder()
        perimeter = Perimeter.objects.create(name="MSIA-CL", folder=folder)
        selected = {}
        for group, expected in (("base", 17), ("estandar", 41), ("reforzado", 43)):
            audit = ComplianceAssessment.objects.create(
                name=f"MSIA-CL {group}",
                framework=framework,
                folder=folder,
                perimeter=perimeter,
                selected_implementation_groups=[group],
            )
            audit.create_requirement_assessments()
            assessed = audit.get_requirement_assessments(include_non_assessable=False)
            assert len(assessed) == expected, (group, len(assessed))
            selected[group] = {ra.requirement.urn for ra in assessed}
        # Cumulative: each profile strictly contains the previous one.
        assert selected["base"] < selected["estandar"] < selected["reforzado"]

    def test_mappings(self):
        engine = MappingEngine()
        # Where the framework cites a whole clause, only the requirements the control
        # actually covers are mapped (the rationale is in each mapping's annotation).
        expected = {
            "urn:intuitem:risk:framework:iso42001-2023": 51,
            "urn:intuitem:risk:framework:nist-ai-rmf-1.0": 53,
        }
        for target, count in expected.items():
            assert (FRAMEWORK_URN, target) in engine.direct_mappings
            assert (target, FRAMEWORK_URN) in engine.direct_mappings
            rms = engine.get_rms((FRAMEWORK_URN, target))
            assert len(rms["requirement_mappings"]) == count
        # Clause-level references must not imply unrelated requirements.
        pairs = {
            (m["source_requirement_urn"].rsplit(":", 1)[-1], m["target_requirement_urn"].rsplit(":", 1)[-1])
            for target in expected
            for m in engine.get_rms((FRAMEWORK_URN, target))["requirement_mappings"]
        }
        assert ("inv-05", "a.6.2.4") not in pairs  # retirement is not verification and validation
        assert ("gob-04", "govern-1.7") not in pairs  # acceptable use is not safe decommissioning
        assert ("inv-05", "govern-1.7") in pairs
        assert ("cad-06", "a.6.2.4") in pairs

    def test_results_flow_to_iso42001(self):
        framework = Framework.objects.get(urn=FRAMEWORK_URN)
        folder = Folder.get_root_folder()
        perimeter = Perimeter.objects.create(name="MSIA-CL mapping", folder=folder)
        audit = ComplianceAssessment.objects.create(
            name="MSIA-CL reforzado",
            framework=framework,
            folder=folder,
            perimeter=perimeter,
            selected_implementation_groups=["reforzado"],
        )
        audit.create_requirement_assessments()
        RequirementAssessment.objects.filter(compliance_assessment=audit).update(
            result="compliant"
        )
        engine = MappingEngine()
        results, _ = engine.best_mapping_inferences(
            engine.load_audit_fields(audit),
            FRAMEWORK_URN,
            "urn:intuitem:risk:framework:iso42001-2023",
        )
        inferred = results.get("requirement_assessments", {})
        # GOB-01 (compliant) -> ISO 42001 5.2 through an 'intersect' mapping:
        # the result flows, but an overlap never becomes full compliance.
        iso_5_2 = inferred.get("urn:intuitem:risk:req_node:iso42001-2023:5.2")
        assert iso_5_2 is not None
        assert iso_5_2.get("result") == "partially_compliant", iso_5_2
